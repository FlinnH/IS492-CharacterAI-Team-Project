"""The only path to a model: the daily cap, call spacing, and one log row per attempt.

A call waits for its slot (the creator can stop it while it waits), streams the
reply, and writes exactly one model_calls row when it ends, however it ends.
A JSON call (the AI judge's) answers in one piece, checked against a Pydantic
model, and a reply that doesn't match is tried once more, each attempt with
its own row. Backoff and fallback come in M6; the fallback column holds its
default until then.
"""

import asyncio
import re
import time
from collections.abc import AsyncIterator, Awaitable, Callable, Sequence
from dataclasses import dataclass, field
from datetime import datetime

import anyio
from pydantic import BaseModel, ValidationError

from workbench import db, telemetry
from workbench.config import Prompts, Settings
from workbench.limiter import Limiter
from workbench.providers import Completion, Provider, ProviderError, Usage
from workbench.schemas import ModelSpec


class CapReached(Exception):
    """The daily cap is reached. The message says when the count starts over."""


@dataclass(frozen=True)
class Wait:
    seconds: float


@dataclass(frozen=True)
class Delta:
    text: str


@dataclass
class CallResult:
    """How a call ended. status starts as stopped, the outcome of an interrupted call."""

    status: str = "stopped"
    text: str = ""
    usage: Usage | None = None
    model_reported: str | None = None
    model_call_id: int | None = None
    # For the creator when status is error, timeout, or empty.
    message: str = ""
    # False when no request was sent, as when Stop came during the wait.
    sent: bool = False
    detail: str | None = None
    ttft_ms: int | None = None
    latency_ms: int | None = None


@dataclass
class JsonResult:
    """How a JSON call ended, after at most one retry.

    status is ok (value holds the answer), invalid (no attempt matched the
    model), error (the service failed), or capped. failure is a short code
    for the logs, like schema, cut_off, or the provider's kind of error.
    """

    status: str = "error"
    value: BaseModel | None = None
    text: str = ""
    # For the creator when the service failed or the cap was reached.
    message: str = ""
    failure: str | None = None
    model_reported: str | None = None
    model_call_id: int | None = None
    attempts: int = 0


# What waiting for the next chunk can end in, besides a chunk.
_ENDED = object()
_STOPPED = object()
_TIMED_OUT = object()

# A reply wrapped in a markdown code fence, which some models add around JSON.
_FENCED = re.compile(r"^```(?:json)?\s*\n(.*)\n```$", re.DOTALL)


def estimated_cost(spec: ModelSpec, usage: Usage | None) -> float | None:
    """What the call would cost on the paid tier, in US dollars. Thinking bills as output."""
    if usage is None:
        return None
    return round(
        (
            (usage.input_tokens - usage.cached_tokens) * spec.input_price
            + usage.cached_tokens * spec.cached_input_price
            + (usage.output_tokens + usage.reasoning_tokens) * spec.output_price
        )
        / 1_000_000,
        8,
    )


def _parse(output: type[BaseModel], completion: Completion, schema_version: str) -> tuple[BaseModel | None, str | None]:
    """The reply as output, or None and a short reason that never quotes the reply."""
    text = completion.text.strip()
    fenced = _FENCED.match(text)
    try:
        return output.model_validate_json(fenced[1] if fenced else text), None
    except ValidationError as error:
        problems = error.errors()
    if completion.finish_reason == "length":
        return None, f"reply cut off at max_tokens, so it didn't match {schema_version}"
    if any(problem["type"] == "json_invalid" for problem in problems):
        return None, f"reply wasn't JSON, so it didn't match {schema_version}"
    places = sorted({".".join(str(part) for part in problem["loc"]) or "the top" for problem in problems})
    return None, f"reply didn't match {schema_version} at {', '.join(places[:4])}"


async def _cancel_and_wait(tasks: Sequence[asyncio.Task]) -> None:
    """Cancels unfinished tasks and waits until they are done, so none outlives the call."""
    pending = [task for task in tasks if not task.done()]
    for task in pending:
        task.cancel()
    if pending:
        with anyio.CancelScope(shield=True):
            await asyncio.wait(pending)


async def _anext_or_ended(chunks: AsyncIterator):
    try:
        return await chunks.__anext__()
    except StopAsyncIteration:
        return _ENDED


async def _next_or_stop(chunks: AsyncIterator, stop: asyncio.Event, timeout: float | None):
    """The next chunk, or _ENDED, _STOPPED, or _TIMED_OUT, whichever comes first.

    A reply that finished counts even if Stop came at the same moment, and a
    chunk or error that arrives together with Stop is dropped.
    """
    next_chunk = asyncio.ensure_future(_anext_or_ended(chunks))
    stopped = asyncio.ensure_future(stop.wait())
    try:
        done, _ = await asyncio.wait({next_chunk, stopped}, timeout=timeout, return_when=asyncio.FIRST_COMPLETED)
    finally:
        await _cancel_and_wait([next_chunk, stopped])
    if next_chunk in done:
        error = next_chunk.exception()
        if error is None and next_chunk.result() is _ENDED:
            return _ENDED
        if stopped not in done:
            if error is not None:
                raise error
            return next_chunk.result()
    if stopped in done:
        return _STOPPED
    return _TIMED_OUT


async def _sleep_or_stop(seconds: float, stop: asyncio.Event, sleep: Callable[[float], Awaitable[None]]) -> bool:
    """Sleeps, but returns True early if stop is set first."""
    if stop.is_set():
        return True
    sleeper = asyncio.ensure_future(sleep(seconds))
    stopped = asyncio.ensure_future(stop.wait())
    try:
        done, _ = await asyncio.wait({sleeper, stopped}, return_when=asyncio.FIRST_COMPLETED)
    finally:
        await _cancel_and_wait([sleeper, stopped])
    return stopped in done


class Gateway:
    def __init__(
        self,
        database: db.Database,
        settings: Settings,
        prompts: Prompts,
        provider: Provider,
        limiter: Limiter,
        *,
        clock: Callable[[], float] = time.monotonic,
        sleep: Callable[[float], Awaitable[None]] = asyncio.sleep,
        wall: Callable[[], datetime] = telemetry.utc_now,
    ) -> None:
        self.database = database
        self.settings = settings
        self.prompts = prompts
        self.provider = provider
        self.limiter = limiter
        self.clock = clock
        self.sleep = sleep
        self.wall = wall
        # Calls sent but not yet logged, so two chats can't both take the last call of the day.
        self.in_flight = 0

    def used_today(self) -> int:
        day = self.limiter.quota_day(self.wall())
        return telemetry.calls_on_day(self.database, self.provider.name, day) + self.in_flight

    def check_cap(
        self,
        *,
        role: str,
        model_id: str,
        prompt_version: str,
        session: str | None,
        transcript_id: int | None = None,
        turn: int | None = None,
    ) -> None:
        """Raises CapReached, after logging a capped row, when today's calls are used up."""
        now = self.wall()
        message = self.limiter.cap_message(self.used_today(), now)
        if message is None:
            return
        telemetry.record_call(
            self.database,
            telemetry.CallRecord(
                started_at=telemetry.timestamp(now),
                quota_day=self.limiter.quota_day(now),
                session=session,
                role=role,
                transcript_id=transcript_id,
                turn=turn,
                provider=self.provider.name,
                model_asked=model_id,
                model_reported=None,
                prompt_version=prompt_version,
                settings_version=self.prompts.models_version,
                reasoning_effort=None,
                status="capped",
                error="daily cap reached",
            ),
        )
        raise CapReached(message)

    def call(
        self,
        *,
        role: str,
        model_id: str,
        messages: Sequence[dict],
        prompt_version: str,
        session: str | None,
        stop: asyncio.Event,
        transcript_id: int | None = None,
        turn: int | None = None,
        reasoning_effort: str | None = None,
    ) -> "Call":
        """A call to make. Iterate Call.events(); Call.result says how it ended."""
        spec = self.prompts.models.models[model_id]
        effort = reasoning_effort if reasoning_effort is not None else spec.reasoning_effort
        return Call(self, role, model_id, list(messages), prompt_version, session, stop, transcript_id, turn, effort)

    async def complete_json(
        self,
        *,
        role: str,
        model_id: str,
        messages: Sequence[dict],
        prompt_version: str,
        session: str | None,
        output: type[BaseModel],
        schema: dict,
        schema_version: str,
        reasoning_effort: str | None,
        max_tokens: int,
        timeout: float,
        transcript_id: int | None = None,
        same_model: bool = False,
        attempts: int = 2,
    ) -> JsonResult:
        """One call that answers in JSON, checked against output.

        A reply that doesn't match is tried once more (attempts counts both).
        A failed service isn't retried, since the same request would fail the
        same way until M6 adds backoff. Every attempt checks the cap, waits for
        its slot, and writes its own model_calls row with no reply text.
        """
        spec = self.prompts.models.models[model_id]
        response_format = {
            "type": "json_schema",
            "json_schema": {"name": schema_version.replace(".", "_"), "schema": schema, "strict": True},
        }
        result = JsonResult()
        for attempt in range(1, attempts + 1):
            result.attempts = attempt
            try:
                self.check_cap(
                    role=role, model_id=model_id, prompt_version=prompt_version, session=session, transcript_id=transcript_id
                )
            except CapReached as error:
                result.status, result.failure, result.message = "capped", "capped", str(error)
                return result
            wait = self.limiter.reserve(self.clock())
            if wait > 0:
                await self.sleep(wait)

            started_at, started = self.wall(), self.clock()
            completion = value = None
            status, detail = "stopped", "stopped before the reply came"
            self.in_flight += 1
            try:
                completion = await self.provider.complete(
                    model_id, list(messages), reasoning_effort, max_tokens, response_format, timeout
                )
                value, detail = _parse(output, completion, schema_version)
                status = "ok" if value is not None else "error"
            except ProviderError as error:
                status, detail = "error", error.detail
                result.status, result.failure, result.message = "error", error.kind, error.message
            finally:
                try:
                    result.model_call_id = telemetry.record_call(
                        self.database,
                        telemetry.CallRecord(
                            started_at=telemetry.timestamp(started_at),
                            quota_day=self.limiter.quota_day(started_at),
                            session=session,
                            role=role,
                            transcript_id=transcript_id,
                            turn=None,
                            provider=self.provider.name,
                            model_asked=model_id,
                            model_reported=completion.model if completion else None,
                            prompt_version=prompt_version,
                            settings_version=self.prompts.models_version,
                            reasoning_effort=reasoning_effort,
                            status=status,
                            error=detail if status != "ok" else None,
                            attempt=attempt,
                            same_model=same_model,
                            latency_ms=round((self.clock() - started) * 1000),
                            input_tokens=completion.usage.input_tokens if completion and completion.usage else None,
                            cached_tokens=completion.usage.cached_tokens if completion and completion.usage else None,
                            output_tokens=completion.usage.output_tokens if completion and completion.usage else None,
                            reasoning_tokens=completion.usage.reasoning_tokens if completion and completion.usage else None,
                            est_cost_usd=estimated_cost(spec, completion.usage if completion else None),
                        ),
                    )
                finally:
                    self.in_flight -= 1

            if completion is None:
                return result
            result.model_reported = completion.model or result.model_reported
            if value is not None:
                result.status, result.value, result.text, result.failure, result.message = "ok", value, completion.text, None, ""
                return result
            result.status = "invalid"
            result.failure = "cut_off" if detail.startswith("reply cut off") else "schema"
        return result


@dataclass
class Call:
    gateway: Gateway
    role: str
    model_id: str
    messages: list[dict]
    prompt_version: str
    session: str | None
    stop: asyncio.Event
    transcript_id: int | None
    turn: int | None
    reasoning_effort: str | None
    result: CallResult = field(default_factory=CallResult)

    async def events(self) -> AsyncIterator[Wait | Delta]:
        gateway = self.gateway
        spec = gateway.prompts.models.models[self.model_id]
        result = self.result
        chunks = None
        started_at = None
        started = first_text = ended = None
        try:
            gateway.check_cap(
                role=self.role,
                model_id=self.model_id,
                prompt_version=self.prompt_version,
                session=self.session,
                transcript_id=self.transcript_id,
                turn=self.turn,
            )
            wait = gateway.limiter.reserve(gateway.clock())
            if wait > 0:
                yield Wait(wait)
                if await _sleep_or_stop(wait, self.stop, gateway.sleep):
                    return
            if self.stop.is_set():
                return

            started_at = gateway.wall()
            started = gateway.clock()
            result.sent = True
            gateway.in_flight += 1
            # The first-token timeout runs on the event loop's own clock.
            deadline = asyncio.get_running_loop().time() + gateway.settings.workbench_first_token_timeout_seconds
            chunks = gateway.provider.stream(self.model_id, self.messages, self.reasoning_effort, spec.max_tokens)
            while True:
                timeout = None if first_text is not None else max(0.0, deadline - asyncio.get_running_loop().time())
                outcome = await _next_or_stop(chunks, self.stop, timeout)
                if outcome is _STOPPED:
                    break
                if outcome is _TIMED_OUT:
                    result.status = "timeout"
                    result.message = (
                        f"The model didn't start answering within "
                        f"{gateway.settings.workbench_first_token_timeout_seconds:g} seconds. Try again."
                    )
                    result.detail = "no first token in time"
                    break
                if outcome is _ENDED:
                    if result.text.strip():
                        result.status = "ok"
                    else:
                        result.status = "empty"
                        result.message = "The model sent an empty reply. Try again."
                        result.detail = "empty reply"
                    break
                if outcome.model:
                    result.model_reported = outcome.model
                if outcome.usage is not None:
                    result.usage = outcome.usage
                if outcome.text:
                    if first_text is None:
                        first_text = gateway.clock()
                    result.text += outcome.text
                    yield Delta(outcome.text)
            ended = gateway.clock()
        except ProviderError as error:
            ended = gateway.clock()
            result.status = "error"
            result.message = error.message
            result.detail = error.detail
        finally:
            if chunks is not None:
                # Stops the provider's stream if it's still open, as after Stop.
                with anyio.CancelScope(shield=True):
                    await chunks.aclose()
            if result.sent:
                try:
                    self._log(spec, started_at, started, first_text, ended if ended is not None else gateway.clock())
                finally:
                    gateway.in_flight -= 1

    def _log(self, spec, started_at: datetime, started: float, first_text: float | None, ended: float) -> None:
        gateway = self.gateway
        result = self.result
        usage = result.usage
        result.ttft_ms = round((first_text - started) * 1000) if first_text is not None else None
        result.latency_ms = round((ended - started) * 1000)
        cost = estimated_cost(spec, usage)
        result.model_call_id = telemetry.record_call(
            gateway.database,
            telemetry.CallRecord(
                started_at=telemetry.timestamp(started_at),
                quota_day=gateway.limiter.quota_day(started_at),
                session=self.session,
                role=self.role,
                transcript_id=self.transcript_id,
                turn=self.turn,
                provider=gateway.provider.name,
                model_asked=self.model_id,
                model_reported=result.model_reported,
                prompt_version=self.prompt_version,
                settings_version=gateway.prompts.models_version,
                reasoning_effort=self.reasoning_effort,
                status=result.status,
                error=(result.detail or None) if result.status != "ok" else None,
                ttft_ms=result.ttft_ms,
                latency_ms=result.latency_ms,
                input_tokens=usage.input_tokens if usage else None,
                cached_tokens=usage.cached_tokens if usage else None,
                output_tokens=usage.output_tokens if usage else None,
                reasoning_tokens=usage.reasoning_tokens if usage else None,
                est_cost_usd=cost,
            ),
        )
