"""Model services. This module is the only one that imports openai or httpx2.

OpenAIProvider talks to an OpenAI-compatible endpoint: Gemini's, a local
Ollama, or another service the creator picks in Settings. FakeProvider streams
a canned reply with no network, for the tests and for running the app without
a key. Both stream Chunk objects the same way, both answer a JSON call with one
Completion, and both raise ProviderError with a message the creator can read
as it is.
"""

import asyncio
import json
from collections.abc import AsyncIterator, Awaitable, Callable, Sequence
from dataclasses import dataclass
from pathlib import Path

import anyio
import httpx2
import openai

from workbench.config import APP_DIR, Settings
from workbench.schemas import FakeSettings, Presets

FAKE_FILE = APP_DIR / "samples" / "fake.v1.json"
# What the creator reads after a 429, real or forced for the demo.
RATE_LIMITED = "The model service says its free limit was reached. Wait a minute and try again."
NO_KEY = "There's no Gemini key yet. Open Settings in the top bar, paste one, and press Test."


@dataclass(frozen=True)
class Usage:
    """Token counts for one call. output_tokens is the visible reply; reasoning_tokens is thinking."""

    input_tokens: int
    cached_tokens: int
    output_tokens: int
    reasoning_tokens: int


@dataclass(frozen=True)
class Chunk:
    text: str
    # The model the service says it used, when the chunk names one.
    model: str | None
    # The latest token counts. Gemini repeats them on every chunk, so the last one wins.
    usage: Usage | None


@dataclass(frozen=True)
class Completion:
    """A whole reply, from a call that asked for JSON."""

    text: str
    model: str | None
    usage: Usage | None
    # "stop", or "length" when the reply ran into max_tokens.
    finish_reason: str | None


class ProviderError(Exception):
    """A failed call. message is for the creator; detail is a short log line with no prompt text."""

    def __init__(self, kind: str, message: str, detail: str = "") -> None:
        super().__init__(message)
        self.kind = kind
        self.message = message
        self.detail = detail or kind


def usage_from(usage) -> Usage:
    """Token counts from an OpenAI-style usage object.

    OpenAI counts thinking inside completion_tokens and says how much in
    completion_tokens_details. Gemini's endpoint leaves the details out and
    counts thinking only in total_tokens, so there it's what total has left over.
    """
    prompt = usage.prompt_tokens or 0
    completion = usage.completion_tokens or 0
    total = usage.total_tokens or 0
    prompt_details = getattr(usage, "prompt_tokens_details", None)
    cached = (getattr(prompt_details, "cached_tokens", None) or 0) if prompt_details else 0
    completion_details = getattr(usage, "completion_tokens_details", None)
    reasoning = getattr(completion_details, "reasoning_tokens", None) if completion_details else None
    if reasoning:
        return Usage(prompt, cached, max(0, completion - reasoning), reasoning)
    return Usage(prompt, cached, completion, max(0, total - prompt - completion))


def _error_detail(error: openai.APIStatusError) -> str:
    """HTTP status plus the service's own short message. Gemini wraps its error in a list."""
    body = error.body
    if isinstance(body, list) and body:
        body = body[0]
    if isinstance(body, dict):
        body = body.get("error", body)
    message = body.get("message") if isinstance(body, dict) else None
    text = message if isinstance(message, str) else error.message
    return " ".join(f"HTTP {error.status_code}: {text}".split())[:200]


def provider_error(error: openai.APIError) -> ProviderError:
    if isinstance(error, openai.APITimeoutError):
        return ProviderError("timeout", "The model service took too long to answer. Try again.", "timeout")
    if isinstance(error, openai.APIConnectionError):
        return ProviderError(
            "connection",
            "Couldn't reach the model service. Check the internet connection (or that Ollama is running) and try again.",
            "connection error",
        )
    if isinstance(error, openai.APIStatusError):
        detail = _error_detail(error)
        status = error.status_code
        if status in (401, 403) or "API key not valid" in detail or "API_KEY_INVALID" in detail:
            # Only the status is logged: a service may quote part of the key it refused.
            return ProviderError(
                "auth",
                "The model service didn't accept the key. Paste it again in Settings and press Test.",
                f"HTTP {status}: key refused",
            )
        if status == 429:
            return ProviderError("rate_limited", RATE_LIMITED, detail)
        if status == 404:
            return ProviderError("not_found", "The model service doesn't know this model. Pick another model in Settings.", detail)
        if status >= 500:
            return ProviderError("server", "The model service had a problem. Try again in a minute.", detail)
        return ProviderError("bad_request", f"The model service refused the request (HTTP {status}).", detail)
    return ProviderError("error", "The model service sent an error partway through the reply. Try again.", "stream error")


class OpenAIProvider:
    """Any OpenAI-compatible endpoint, through the openai library with no automatic retries.

    token_field is the request field that caps a reply's length, and
    stream_usage says whether a streamed reply asks for token counts with
    stream_options. Both come from a preset in Settings, since services differ.
    """

    def __init__(
        self,
        *,
        name: str,
        base_url: str,
        api_key: str,
        timeout: float,
        http_client: httpx2.AsyncClient | None = None,
        token_field: str = "max_tokens",
        stream_usage: bool = True,
    ) -> None:
        self.name = name
        self.ready = bool(api_key)
        self._base_url = base_url
        self._api_key = api_key
        self._timeout = timeout
        self._http_client = http_client
        self._token_field = token_field
        self._stream_usage = stream_usage
        self._client: openai.AsyncOpenAI | None = None

    def _openai(self) -> openai.AsyncOpenAI:
        # Built on first use, so the app starts without a key and says what's missing instead.
        if not self.ready:
            raise ProviderError("auth", NO_KEY, "no key")
        if self._client is None:
            self._client = openai.AsyncOpenAI(
                api_key=self._api_key,
                base_url=self._base_url,
                max_retries=0,
                timeout=httpx2.Timeout(self._timeout),
                http_client=self._http_client,
            )
        return self._client

    async def stream(
        self, model: str, messages: Sequence[dict], reasoning_effort: str | None, max_tokens: int
    ) -> AsyncIterator[Chunk]:
        """Streams one reply. Temperature is never sent: newer Gemini models ignore it."""
        options = {"reasoning_effort": reasoning_effort} if reasoning_effort else {}
        if self._stream_usage:
            options["stream_options"] = {"include_usage": True}
        options[self._token_field] = max_tokens
        try:
            stream = await self._openai().chat.completions.create(
                model=model,
                messages=[dict(message) for message in messages],
                stream=True,
                **options,
            )
        except openai.APIError as error:
            raise provider_error(error) from None
        try:
            async for chunk in stream:
                text = "".join(choice.delta.content or "" for choice in chunk.choices if choice.delta)
                yield Chunk(
                    text=text,
                    model=chunk.model or None,
                    usage=usage_from(chunk.usage) if chunk.usage else None,
                )
        except openai.APIError as error:
            raise provider_error(error) from None
        finally:
            # Closing the response stops the download, and with it the reply, when
            # the creator presses Stop. Shielded, since a dropped connection may
            # have cancelled the request already.
            with anyio.CancelScope(shield=True):
                await stream.close()

    async def complete(
        self,
        model: str,
        messages: Sequence[dict],
        reasoning_effort: str | None,
        max_tokens: int,
        response_format: dict,
        timeout: float,
    ) -> Completion:
        """One whole reply in the given response format, not streamed.

        Google's OpenAI compatibility page shows structured output only without
        streaming. timeout covers the whole call, thinking included.
        """
        options = {"reasoning_effort": reasoning_effort} if reasoning_effort else {}
        options[self._token_field] = max_tokens
        try:
            response = await self._openai().chat.completions.create(
                model=model,
                messages=[dict(message) for message in messages],
                response_format=response_format,
                timeout=timeout,
                **options,
            )
        except openai.APIError as error:
            raise provider_error(error) from None
        choice = response.choices[0] if response.choices else None
        return Completion(
            text=(choice.message.content or "") if choice and choice.message else "",
            model=response.model or None,
            usage=usage_from(response.usage) if response.usage else None,
            finish_reason=choice.finish_reason if choice else None,
        )

    async def list_models(self) -> list[str]:
        """Model IDs the service offers, without Gemini's "models/" prefix."""
        try:
            return [item.id.removeprefix("models/") async for item in self._openai().models.list()]
        except openai.APIError as error:
            raise provider_error(error) from None

    async def aclose(self) -> None:
        if self._client is not None:
            await self._client.close()


@dataclass(frozen=True)
class FakeReply:
    """One scripted call for FakeProvider. Fields left as None use fake.v1.json."""

    text: str | None = None
    # Raised before the first chunk.
    error: ProviderError | None = None
    # Seconds before the first chunk, and between chunks.
    first_token_seconds: float | None = None
    chunk_seconds: float | None = None


class FakeProvider:
    """Streams a canned reply with no network. It records every request it gets."""

    def __init__(
        self,
        settings: FakeSettings,
        replies: Sequence[FakeReply] = (),
        sleep: Callable[[float], Awaitable[None]] = asyncio.sleep,
    ) -> None:
        self.name = "fake"
        self.ready = True
        self.settings = settings
        self.replies = list(replies)
        self.requests: list[dict] = []
        self.sleep = sleep

    @classmethod
    def from_file(cls, path: Path = FAKE_FILE, **kwargs) -> "FakeProvider":
        return cls(FakeSettings.model_validate_json(path.read_text(encoding="utf-8")), **kwargs)

    async def stream(
        self, model: str, messages: Sequence[dict], reasoning_effort: str | None, max_tokens: int
    ) -> AsyncIterator[Chunk]:
        self.requests.append(
            {
                "model": model,
                "messages": [dict(message) for message in messages],
                "reasoning_effort": reasoning_effort,
                "max_tokens": max_tokens,
            }
        )
        script = self.replies.pop(0) if self.replies else FakeReply()
        if script.error is not None:
            raise script.error
        text = self.settings.reply if script.text is None else script.text
        per_token = self.settings.chars_per_token
        input_tokens = max(1, sum(len(message["content"]) for message in messages) // per_token)
        first = self.settings.first_token_seconds if script.first_token_seconds is None else script.first_token_seconds
        between = self.settings.chunk_seconds if script.chunk_seconds is None else script.chunk_seconds

        await self.sleep(first)
        size = self.settings.chunk_chars
        pieces = [text[start : start + size] for start in range(0, len(text), size)] or [""]
        sent = 0
        for index, piece in enumerate(pieces):
            if index:
                await self.sleep(between)
            sent += len(piece)
            # Usage on every chunk, counting up, the way Gemini sends it.
            output = -(-sent // per_token) if sent else 0
            yield Chunk(text=piece, model=self.settings.model_reported, usage=Usage(input_tokens, 0, output, 0))

    async def complete(
        self,
        model: str,
        messages: Sequence[dict],
        reasoning_effort: str | None,
        max_tokens: int,
        response_format: dict,
        timeout: float,
    ) -> Completion:
        """The next scripted reply, or else the smallest answer the requested schema allows."""
        self.requests.append(
            {
                "model": model,
                "messages": [dict(message) for message in messages],
                "reasoning_effort": reasoning_effort,
                "max_tokens": max_tokens,
                "response_format": response_format,
                "timeout": timeout,
            }
        )
        script = self.replies.pop(0) if self.replies else FakeReply()
        if script.error is not None:
            raise script.error
        await self.sleep(self.settings.first_token_seconds if script.first_token_seconds is None else script.first_token_seconds)
        if script.text is not None:
            text = script.text
        else:
            text = json.dumps(smallest_instance(response_format["json_schema"]["schema"]))
        per_token = self.settings.chars_per_token
        input_tokens = max(1, sum(len(message["content"]) for message in messages) // per_token)
        # A JSON call reports the model it was asked for.
        return Completion(text=text, model=model, usage=Usage(input_tokens, 0, -(-len(text) // per_token), 0), finish_reason="stop")

    async def list_models(self) -> list[str]:
        return []

    async def aclose(self) -> None:
        return None


def smallest_instance(schema: dict):
    """The smallest value a JSON schema allows: empty lists and strings, zero, false, or the first choice."""
    if "enum" in schema:
        return schema["enum"][0]
    kind = schema.get("type")
    if kind == "object":
        return {name: smallest_instance(schema["properties"][name]) for name in schema.get("required", [])}
    return {"array": [], "string": "", "integer": 0, "number": 0, "boolean": False}.get(kind)


Provider = OpenAIProvider | FakeProvider


def build(settings: Settings, presets: Presets | None = None) -> Provider:
    """The provider WORKBENCH_PROVIDER names.

    For another OpenAI-compatible service, the preset whose base URL matches,
    if any, says which token-limit field to send and whether to ask for token
    counts. Any other address gets max_tokens, with token counts asked for.
    """
    timeout = settings.workbench_first_token_timeout_seconds
    if settings.workbench_provider == "fake":
        return FakeProvider.from_file()
    if settings.workbench_provider == "ollama":
        # Ollama needs some key but ignores it.
        return OpenAIProvider(name="ollama", base_url=settings.ollama_base_url, api_key="ollama", timeout=timeout)
    if settings.workbench_provider == "openai_compatible":
        preset = presets.match(settings.openai_compatible_base_url) if presets is not None else None
        options = {"token_field": preset.token_field, "stream_usage": preset.stream_usage} if preset is not None else {}
        return OpenAIProvider(
            name="openai_compatible",
            base_url=settings.openai_compatible_base_url,
            # A service on this computer may take no key, but the openai library needs some string.
            api_key=settings.openai_compatible_api_key.get_secret_value() or "none",
            timeout=timeout,
            **options,
        )
    return OpenAIProvider(
        name="gemini",
        base_url=settings.gemini_base_url,
        api_key=settings.gemini_api_key.get_secret_value(),
        timeout=timeout,
    )
