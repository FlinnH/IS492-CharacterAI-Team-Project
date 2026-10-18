"""Live chats: one turn at a time, each reply streamed from the model.

A turn saves the user's line, waits for its call slot, streams the reply, and
saves it. The system message is the character prompt with the chat's pinned
spec version rendered into it. It's built once per chat, so its bytes are the
same on every turn whatever spec version is saved later.

Turn.finish() is safe to call more than once. The SSE route calls it when the
response ends, so a reply cut off by a closed tab is still saved (marked
stopped) and logged, and the chat isn't left busy. A reply that a model error
cuts off is saved the same way, and Try again answers its line again.
"""

import asyncio
from collections.abc import AsyncIterator

import anyio
from pydantic import BaseModel

from workbench import db, specs, telemetry, transcripts
from workbench.config import SPEC_PLACEHOLDER, Prompts, Settings
from workbench.gateway import CapReached, Delta, Gateway, Wait
from workbench.schemas import (
    ChatSummary,
    ChatView,
    DeltaEvent,
    DoneEvent,
    ErrorEvent,
    ModelOption,
    RunOptions,
    ScenarioFile,
    ScenarioLine,
    ScenarioOption,
    UserEvent,
    WaitEvent,
)

ROLE = "character"


class ChatBusy(Exception):
    """A reply is still streaming in this chat."""


class ChatClosed(Exception):
    """This chat can't take another turn of the kind asked for."""


class RunInvalid(Exception):
    """The request names an unknown scenario or model, or the typed text can't be sent."""


class NoKey(Exception):
    """The provider needs a key and none is set."""


class SessionLimitReached(Exception):
    """This browser session has started as many runs as one session may."""


NO_KEY_MESSAGE = "Add your Gemini key to app/.env as GEMINI_API_KEY, then restart app/run.sh."


class Runtime:
    def __init__(
        self, database: db.Database, settings: Settings, prompts: Prompts, gateway: Gateway, scenarios: ScenarioFile
    ) -> None:
        self.database = database
        self.settings = settings
        self.prompts = prompts
        self.gateway = gateway
        self.scenario_file = scenarios
        self.scenarios = {scenario.id: scenario for scenario in scenarios.scenarios}
        # The turn streaming in each chat, by chat ID.
        self.running: dict[int, "Turn"] = {}
        self._system: dict[int, str] = {}

    # Reading.

    def get_chat(self, chat_id: int) -> ChatView:
        return transcripts.get_chat(self.database, chat_id, scenarios=self.scenarios, busy=set(self.running))

    def list_chats(self) -> list[ChatSummary]:
        return transcripts.list_chats(self.database, scenarios=self.scenarios, busy=set(self.running))

    def models(self) -> list[str]:
        return self.prompts.models.character_models(self.settings.workbench_provider)

    def run_options(self, session: str | None) -> RunOptions:
        character = specs.list_characters(self.database)[0]
        latest = specs.get_spec(self.database, character.slug)
        models = self.prompts.models.models
        return RunOptions(
            character=character,
            latest_spec_version=latest.version,
            provider=self.settings.workbench_provider,
            key_set=self.gateway.provider.ready,
            scenarios=[
                ScenarioOption(id=s.id, name=s.name, turns=len(s.lines), last_turn=s.lines[-1].turn)
                for s in self.scenario_file.scenarios
            ],
            models=[ModelOption(id=model_id, label=models[model_id].label) for model_id in self.models()],
            model_labels={
                model_id: spec.label for model_id, spec in models.items() if spec.provider == self.settings.workbench_provider
            },
            default_model=self.models()[0],
            calls_per_minute=self.settings.workbench_calls_per_minute,
            daily_cap=self.settings.workbench_daily_call_cap,
            used_today=self.gateway.used_today(),
            session_runs=transcripts.session_runs(self.database, session),
            session_run_limit=self.settings.workbench_session_run_limit,
            max_typed_chars=self.settings.workbench_max_typed_chars,
            max_import_chars=self.settings.workbench_max_import_chars,
        )

    # Starting and stopping.

    def _check_ready(self, model_id: str, session: str | None, chat_id: int | None = None, turn: int | None = None) -> None:
        if not self.gateway.provider.ready:
            raise NoKey(NO_KEY_MESSAGE)
        self.gateway.check_cap(
            role=ROLE,
            model_id=model_id,
            prompt_version=self.prompts.character_version,
            session=session,
            transcript_id=chat_id,
            turn=turn,
        )

    def start(self, *, character: str, scenario_id: str, model_id: str, session: str | None) -> ChatView:
        """A new live chat, pinned to the character's latest spec version."""
        scenario = self.scenarios.get(scenario_id)
        if scenario is None:
            raise RunInvalid(f"There is no scenario called {scenario_id}.")
        if model_id not in self.models():
            raise RunInvalid(f"{model_id} isn't in the Model menu for the {self.settings.workbench_provider} provider.")
        limit = self.settings.workbench_session_run_limit
        if transcripts.session_runs(self.database, session) >= limit:
            raise SessionLimitReached(
                f"This browser session has started {limit} {'run' if limit == 1 else 'runs'}, the most one session may "
                "start. To allow more, raise WORKBENCH_SESSION_RUN_LIMIT in app/.env and restart app/run.sh."
            )
        # Checked first, so Start never leaves an empty chat behind.
        self._check_ready(model_id, session)
        spec = specs.get_spec(self.database, character)
        chat_id = transcripts.create_live(
            self.database,
            character=spec.character.slug,
            spec_version=spec.version,
            scenario=scenario,
            model=model_id,
            user_name=self.scenario_file.user_name,
            character_name=self.scenario_file.character_name,
            session=session,
        )
        telemetry.record_event(self.database, "run_started", session=session, transcript_id=chat_id, reason=scenario_id)
        return self.get_chat(chat_id)

    def begin(self, chat_id: int, *, typed: str | None, session: str | None) -> "Turn":
        """Checks that a turn can run, then marks the chat busy. typed is None for the next scripted line."""
        chat = self.get_chat(chat_id)
        if chat.kind != "live":
            raise ChatClosed("Imported chats can't continue. Start a run to chat live.")
        if chat_id in self.running:
            raise ChatBusy(f"{chat.character_name} is still answering. Wait for the reply, or press Stop.")

        # A line still waits for its reply when nothing answered it, or when a
        # model error cut the reply off: Try again answers it again.
        last = chat.messages[-1] if chat.messages else None
        pending = last is not None and (last.speaker == "user" or last.failed)
        last_turn = last.turn if last else None
        line: ScenarioLine | None = None
        if typed is None:
            if not pending:
                if chat.status != "active" or chat.script_left == 0:
                    raise ChatClosed("The script has ended. Type your next message below.")
                scenario = self.scenarios[chat.scenario]
                line = scenario.lines[len(scenario.lines) - chat.script_left]
            turn = line.turn if line else last_turn
        else:
            if chat.status == "active":
                raise ChatClosed("Type your own message after the script ends, or press Stop first.")
            typed = typed.strip()
            if not typed:
                raise RunInvalid("Type a message first.")
            if len(typed) > self.settings.workbench_max_typed_chars:
                raise RunInvalid(f"Keep messages to {self.settings.workbench_max_typed_chars:,} characters or fewer.")
            # The script's turn 1 is the spec, so a chat's first line is turn 2.
            turn = (last_turn or 1) + 1

        self._check_ready(chat.model, session, chat_id, turn)
        current = Turn(self, chat, line=line, typed=typed, turn=turn, session=session)
        self.running[chat_id] = current
        return current

    def stop(self, chat_id: int, session: str | None) -> ChatSummary:
        """Stops the reply that is streaming, if any, and ends the script for this chat."""
        chat = self.get_chat(chat_id)
        if chat.kind != "live":
            raise ChatClosed("Imported chats have nothing to stop.")
        current = self.running.get(chat_id)
        if current is not None:
            current.stop_event.set()
        if chat.status == "active":
            transcripts.set_status(self.database, chat_id, "stopped")
        telemetry.record_event(self.database, "run_stopped", session=session, transcript_id=chat_id)
        return self.summary(chat_id)

    def summary(self, chat_id: int) -> ChatSummary:
        view = self.get_chat(chat_id)
        return ChatSummary(**view.model_dump(exclude={"source", "messages"}))

    # What the model sees.

    def system_message(self, chat: ChatView) -> str:
        """The character prompt with the chat's pinned spec rendered in. Same bytes every turn."""
        if chat.id not in self._system:
            body = specs.get_spec(self.database, chat.character.slug, chat.spec_version).body
            text = self.prompts.character_template.replace(SPEC_PLACEHOLDER, specs.render_text(body))
            self._system[chat.id] = text.strip()
        return self._system[chat.id]

    def model_messages(self, chat: ChatView) -> list[dict]:
        """System message first, then the chat. Back-to-back user lines are sent as one.

        A reply a model error cut off is left out, since its line is asked again.
        """
        messages = [{"role": "system", "content": self.system_message(chat)}]
        for message in chat.messages:
            role = "user" if message.speaker == "user" else "assistant"
            if not message.text or message.failed:
                continue
            if role == "user" and messages[-1]["role"] == "user":
                messages[-1] = {"role": "user", "content": f"{messages[-1]['content']}\n\n{message.text}"}
            else:
                messages.append({"role": role, "content": message.text})
        return messages


class Turn:
    """One turn of a live chat: the user's line, then the streamed reply."""

    def __init__(
        self, runtime: Runtime, chat: ChatView, *, line: ScenarioLine | None, typed: str | None, turn: int, session: str | None
    ) -> None:
        self.runtime = runtime
        self.chat = chat
        self.line = line
        self.typed = typed
        self.turn = turn
        self.session = session
        self.stop_event = asyncio.Event()
        self.call = None
        self.settled = False
        self.finished = False
        self._events = None

    def events(self) -> AsyncIterator[tuple[str, BaseModel]]:
        """(event name, payload) pairs: user, wait, delta, then done or error."""
        if self._events is None:
            self._events = self._run()
        return self._events

    async def _run(self) -> AsyncIterator[tuple[str, BaseModel]]:
        runtime = self.runtime
        database = runtime.database
        chat_id = self.chat.id
        call_events = None
        try:
            if self.line is not None or self.typed is not None:
                saved = transcripts.add_message(
                    database,
                    chat_id,
                    turn=self.turn,
                    speaker="user",
                    text=self.line.text if self.line is not None else self.typed,
                    source="script" if self.line is not None else "typed",
                )
                if self.typed is not None:
                    telemetry.record_event(database, "message_typed", session=self.session, transcript_id=chat_id)
                yield "user", UserEvent(seq=saved.seq, turn=saved.turn, text=saved.text, injection=saved.injection)

            chat = runtime.get_chat(chat_id)
            self.call = runtime.gateway.call(
                role=ROLE,
                model_id=chat.model,
                messages=runtime.model_messages(chat),
                prompt_version=runtime.prompts.character_version,
                session=self.session,
                stop=self.stop_event,
                transcript_id=chat_id,
                turn=self.turn,
            )
            call_events = self.call.events()
            async for event in call_events:
                if isinstance(event, Wait):
                    yield "wait", self._wait_event(event)
                elif isinstance(event, Delta):
                    yield "delta", DeltaEvent(text=event.text)
            outcome = self._settle()
            if outcome is not None:
                yield outcome
        except CapReached as error:
            self.settled = True
            telemetry.record_event(database, "error_shown", session=self.session, transcript_id=chat_id, reason="capped")
            yield "error", ErrorEvent(message=str(error), retry=False, status=self._status())
        finally:
            if call_events is not None:
                with anyio.CancelScope(shield=True):
                    await call_events.aclose()
            self._settle()
            self._release()

    def _status(self) -> str:
        return self.runtime.get_chat(self.chat.id).status

    def _wait_event(self, wait: Wait) -> WaitEvent:
        """A pause, in words for the Run screen when it is a retry or the fallback model."""
        models = self.runtime.prompts.models.models
        message = ""
        if wait.reason == "retry":
            message = f"The model service is busy. Trying again in {wait.seconds:g} s."
        elif wait.reason == "fallback":
            message = f"{models[self.chat.model].label} is still busy, so {models[wait.model].label} answers this turn."
        return WaitEvent(seconds=round(wait.seconds, 1), reason=wait.reason, message=message)

    def _settle(self) -> tuple[str, BaseModel] | None:
        """Saves the reply the call ended with and returns the closing event. Runs once.

        Text that came before a model error is saved too, marked as cut off.
        """
        if self.settled:
            return None
        self.settled = True
        runtime = self.runtime
        database = runtime.database
        result = self.call.result if self.call is not None else None
        status = result.status if result is not None else "stopped"

        saved = False
        if result is not None and result.text and status in ("ok", "stopped", "error"):
            transcripts.add_message(
                database,
                self.chat.id,
                turn=self.turn,
                speaker="character",
                text=result.text,
                source="model",
                stopped=status != "ok",
                model_call_id=result.model_call_id,
            )
            saved = True

        chat = runtime.get_chat(self.chat.id)
        # Read back, so the reply carries what the log says about it: its model, a fallback, an error.
        message = chat.messages[-1] if saved else None
        if status not in ("ok", "stopped"):
            telemetry.record_event(database, "error_shown", session=self.session, transcript_id=self.chat.id, reason=status)
            return "error", ErrorEvent(message=result.message, retry=True, status=chat.status, partial=message)
        if status == "ok" and chat.status == "active" and chat.script_left == 0:
            transcripts.set_status(database, self.chat.id, "script_done")
            chat = runtime.get_chat(self.chat.id)
        return "done", DoneEvent(
            message=message,
            stopped=status == "stopped",
            status=chat.status,
            script_left=chat.script_left,
            used_today=runtime.gateway.used_today(),
        )

    def _release(self) -> None:
        if self.runtime.running.get(self.chat.id) is self:
            del self.runtime.running[self.chat.id]
        self.finished = True

    async def finish(self) -> None:
        """Ends the turn if the response stopped early. Safe to call again, and after a normal end."""
        if self.finished:
            return
        with anyio.CancelScope(shield=True):
            if self._events is not None:
                # Runs _run's finally: the call is logged and the partial reply saved.
                await self._events.aclose()
        if not self.finished:
            # The stream never started, so there's nothing to save.
            self.settled = True
            self._release()
