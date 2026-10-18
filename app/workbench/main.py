"""HTTP entry point: the API routes, then the screens in app/static/.

Routes only call services, like specs, transcripts, runtime, judge, recheck,
and review, which open their own database connections. A live turn streams as server-sent events.
Its checks run in a dependency, before the stream starts, so a refused turn
gets a plain JSON error with the right status.
"""

import re
import sys
from collections.abc import AsyncIterable, AsyncIterator, Awaitable, Callable
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Annotated

import uvicorn
from fastapi import Depends, FastAPI, Request, Response
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from fastapi.sse import EventSourceResponse, ServerSentEvent
from fastapi.staticfiles import StaticFiles
from pydantic import ValidationError

from workbench import db, providers, specs, transcripts
from workbench.config import Settings, load_prompts, load_settings
from workbench.gateway import CapReached, Gateway
from workbench.judge import CheckBusy, Judge, NothingToCheck
from workbench.limiter import Limiter
from workbench.recheck import NothingToRecheck, QuestionInvalid, Recheck, RecheckBusy
from workbench.review import CallInvalid, CallRefused, FlagNotFound, FlagOutdated, Review
from workbench.runtime import ChatBusy, ChatClosed, NoKey, RunInvalid, Runtime, SessionLimitReached, Turn
from workbench.schemas import (
    Character,
    ChatSummary,
    ChatView,
    CheckState,
    CheckView,
    ImportPreview,
    ImportRequest,
    OverrideCall,
    RecheckRequest,
    ReviewChat,
    ReviewState,
    RunOptions,
    SampleInfo,
    SpecEdit,
    SpecView,
    StartChat,
    TypedLine,
)

STATIC_DIR = Path(__file__).resolve().parent.parent / "static"
SESSION_HEADER = "x-workbench-session"
SESSION_ID = re.compile(r"[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}")


class NoCacheStaticFiles(StaticFiles):
    """Makes the browser revalidate each file, so an edited file never shows stale."""

    def file_response(self, *args, **kwargs):
        response = super().file_response(*args, **kwargs)
        response.headers["Cache-Control"] = "no-cache"
        return response


def error_response(status: int):
    """A handler that sends a service error's message, which the screens show as is."""

    async def handle(request: Request, error: Exception) -> JSONResponse:
        content = {"detail": str(error)}
        if isinstance(error, specs.SpecInvalid):
            # The draft field to fix, so the Spec editor can move focus to it.
            content["field"] = error.field
        if isinstance(error, transcripts.ImportInvalid):
            # The rows to fix, so the Import dialog can list them.
            content["problems"] = [problem.model_dump() for problem in error.problems]
        return JSONResponse(status_code=status, content=content)

    return handle


async def invalid_request(request: Request, error: RequestValidationError) -> JSONResponse:
    # FastAPI's default answer echoes the request back. This one only says where it went wrong.
    places = sorted({".".join(str(part) for part in item["loc"][1:]) or "body" for item in error.errors()})
    return JSONResponse(
        status_code=422,
        content={"detail": f"The request has a missing or wrong value at {', '.join(places)}."},
    )


def session_of(request: Request) -> str | None:
    """The browser tab's session ID from api.js, if it looks like one."""
    value = request.headers.get(SESSION_HEADER, "")
    return value if SESSION_ID.fullmatch(value) else None


def create_app(
    settings: Settings,
    *,
    provider: providers.Provider | None = None,
    clock: Callable[[], float] | None = None,
    sleep: Callable[[float], Awaitable[None]] | None = None,
) -> FastAPI:
    # Startup work runs here, not in a lifespan handler, because TestClient
    # only runs lifespan inside a with block.
    prompts = load_prompts()
    database = db.Database(settings.workbench_db_path)
    with database.connect() as conn:
        db.migrate(conn)
    specs.seed(database)

    provider = provider if provider is not None else providers.build(settings)
    limiter = Limiter(settings.workbench_calls_per_minute, settings.workbench_daily_call_cap, prompts.models.quota_timezone)
    timing = {name: value for name, value in (("clock", clock), ("sleep", sleep)) if value is not None}
    gateway = Gateway(database, settings, prompts, provider, limiter, **timing)
    runtime = Runtime(database, settings, prompts, gateway, transcripts.load_scenarios())
    judge = Judge(database, settings, prompts, gateway, runtime.scenarios, busy=lambda: runtime.running)
    recheck = Recheck(database, settings, prompts, gateway, judge)
    review = Review(database, settings, judge, recheck)

    @asynccontextmanager
    async def lifespan(app: FastAPI) -> AsyncIterator[None]:
        yield
        await provider.aclose()

    app = FastAPI(title="Character Consistency Workbench", lifespan=lifespan)
    app.state.settings = settings
    app.state.database = database
    app.state.runtime = runtime
    app.state.judge = judge
    app.state.recheck = recheck
    app.state.review = review

    app.add_exception_handler(specs.SpecNotFound, error_response(404))
    app.add_exception_handler(transcripts.ChatNotFound, error_response(404))
    app.add_exception_handler(FlagNotFound, error_response(404))
    app.add_exception_handler(specs.SpecConflict, error_response(409))
    app.add_exception_handler(ChatBusy, error_response(409))
    app.add_exception_handler(ChatClosed, error_response(409))
    app.add_exception_handler(CheckBusy, error_response(409))
    app.add_exception_handler(RecheckBusy, error_response(409))
    app.add_exception_handler(FlagOutdated, error_response(409))
    app.add_exception_handler(CallRefused, error_response(409))
    app.add_exception_handler(specs.SpecInvalid, error_response(422))
    app.add_exception_handler(RunInvalid, error_response(422))
    app.add_exception_handler(transcripts.ImportInvalid, error_response(422))
    app.add_exception_handler(NothingToCheck, error_response(422))
    app.add_exception_handler(NothingToRecheck, error_response(422))
    app.add_exception_handler(QuestionInvalid, error_response(422))
    app.add_exception_handler(CallInvalid, error_response(422))
    app.add_exception_handler(CapReached, error_response(429))
    app.add_exception_handler(SessionLimitReached, error_response(429))
    app.add_exception_handler(NoKey, error_response(503))
    app.add_exception_handler(RequestValidationError, invalid_request)

    @app.get("/api/health")
    def health() -> dict:
        # Says whether a key is set, never the key itself.
        return {
            "status": "ok",
            "provider": settings.workbench_provider,
            "key_set": bool(settings.gemini_api_key.get_secret_value()),
        }

    @app.get("/api/characters", response_model=list[Character])
    def characters() -> list[Character]:
        return specs.list_characters(database)

    # Declared before the numbered route, so "latest" is never read as a version.
    @app.get("/api/characters/{slug}/specs/latest", response_model=SpecView)
    def latest_spec(slug: str) -> SpecView:
        return specs.get_spec(database, slug)

    @app.get("/api/characters/{slug}/specs/{version}", response_model=SpecView)
    def spec_version(slug: str, version: int) -> SpecView:
        return specs.get_spec(database, slug, version)

    @app.post("/api/characters/{slug}/specs", response_model=SpecView, status_code=201)
    def save_spec(slug: str, edit: SpecEdit) -> SpecView:
        return specs.save_edit(database, slug, edit)

    # Run a conversation. The chat routes are async, so the runtime's turn state
    # is only ever touched on the event loop.

    @app.get("/api/run-options", response_model=RunOptions)
    async def run_options(request: Request) -> RunOptions:
        return runtime.run_options(session_of(request))

    @app.get("/api/chats", response_model=list[ChatSummary])
    async def chats() -> list[ChatSummary]:
        return runtime.list_chats()

    @app.post("/api/chats", response_model=ChatView, status_code=201)
    async def start_chat(start: StartChat, request: Request) -> ChatView:
        return runtime.start(character=start.character, scenario_id=start.scenario, model_id=start.model, session=session_of(request))

    @app.get("/api/chats/{chat_id}", response_model=ChatView)
    async def chat(chat_id: int) -> ChatView:
        return runtime.get_chat(chat_id)

    async def next_turn(chat_id: int, request: Request) -> AsyncIterator[Turn]:
        turn = runtime.begin(chat_id, typed=None, session=session_of(request))
        try:
            yield turn
        finally:
            # Saves and logs a reply that a closed tab cut off. Does nothing after a normal end.
            await turn.finish()

    async def typed_turn(chat_id: int, line: TypedLine, request: Request) -> AsyncIterator[Turn]:
        turn = runtime.begin(chat_id, typed=line.text, session=session_of(request))
        try:
            yield turn
        finally:
            await turn.finish()

    async def stream(turn: Turn) -> AsyncIterator[ServerSentEvent]:
        async for name, payload in turn.events():
            yield ServerSentEvent(event=name, data=payload)

    @app.post("/api/chats/{chat_id}/next", response_class=EventSourceResponse)
    async def chat_next(turn: Annotated[Turn, Depends(next_turn)]) -> AsyncIterable[ServerSentEvent]:
        async for event in stream(turn):
            yield event

    @app.post("/api/chats/{chat_id}/messages", response_class=EventSourceResponse)
    async def chat_message(turn: Annotated[Turn, Depends(typed_turn)]) -> AsyncIterable[ServerSentEvent]:
        async for event in stream(turn):
            yield event

    @app.post("/api/chats/{chat_id}/stop", response_model=ChatSummary)
    async def stop_chat(chat_id: int, request: Request) -> ChatSummary:
        return runtime.stop(chat_id, session_of(request))

    # Checks: the rule checks and the AI judge. GET reads the saved check of the
    # chat as it stands and never calls a model; POST checks it, reusing a saved
    # judge run when one covers this exact chat.

    @app.get("/api/chats/{chat_id}/check", response_model=CheckState)
    async def chat_check(chat_id: int) -> CheckState:
        return judge.state(chat_id)

    @app.post("/api/chats/{chat_id}/check", response_model=CheckView)
    async def check_chat(chat_id: int, request: Request) -> CheckView:
        return await judge.check(chat_id, session_of(request))

    # Flag review: the creator's calls on the flags of each saved check. Each
    # call answers with the flag's chat as it now stands, so the screen redraws
    # from what was saved. Like the chat routes, these are async, and nothing
    # inside a call waits, so two calls never interleave.

    @app.get("/api/review", response_model=ReviewState)
    async def review_state() -> ReviewState:
        return review.state()

    @app.post("/api/flags/{flag_id}/evidence", response_model=ReviewChat)
    async def open_evidence(flag_id: int, request: Request) -> ReviewChat:
        return review.open_evidence(flag_id, session_of(request))

    @app.post("/api/flags/{flag_id}/agree", response_model=ReviewChat)
    async def agree(flag_id: int, request: Request) -> ReviewChat:
        return review.agree(flag_id, session_of(request))

    @app.post("/api/flags/{flag_id}/override", response_model=ReviewChat)
    async def override(flag_id: int, call: OverrideCall, request: Request) -> ReviewChat:
        return review.override(flag_id, call, session_of(request))

    @app.post("/api/flags/{flag_id}/undo", response_model=ReviewChat)
    async def undo(flag_id: int, request: Request) -> ReviewChat:
        return review.undo(flag_id, session_of(request))

    # The follow-up re-check: the judge's model looks again at the weakest
    # flags of a chat's saved check, with the creator's question if there is
    # one. It answers with the chat's review as it now stands, so the screen
    # redraws What changed from what was saved.
    @app.post("/api/chats/{chat_id}/recheck", response_model=ReviewChat)
    async def recheck_chat(chat_id: int, body: RecheckRequest, request: Request) -> ReviewChat:
        await recheck.run(chat_id, body.question, session_of(request))
        return review.chat(chat_id)

    # Import.

    @app.get("/api/samples", response_model=list[SampleInfo])
    def samples() -> list[SampleInfo]:
        return transcripts.list_samples(settings)

    @app.post("/api/imports/preview", response_model=ImportPreview)
    def import_preview(body: ImportRequest) -> ImportPreview:
        return transcripts.preview(database, settings, body)

    @app.post("/api/imports", response_model=ChatView, status_code=201)
    async def import_chat(body: ImportRequest, request: Request, response: Response) -> ChatView:
        chat_id, created = transcripts.import_chat(database, settings, body, session_of(request))
        if not created:
            response.status_code = 200
        return runtime.get_chat(chat_id)

    # Mounted last, so the API routes above win over file paths.
    app.mount("/", NoCacheStaticFiles(directory=STATIC_DIR, html=True), name="static")
    return app


def refusal(error: Exception) -> str:
    """Why the app won't start, as one plain line instead of a traceback."""
    if isinstance(error, ValidationError):
        names = sorted({str(item["loc"][0]).upper() for item in error.errors() if item["loc"]})
        return f"app/.env has a missing or wrong value for {', '.join(names)}. app/.env.example lists every setting."
    return " ".join(str(error).split())


def main() -> None:
    try:
        settings = load_settings()
        app = create_app(settings)
    except (RuntimeError, ValidationError) as error:
        # The refusals already say what to fix, so the traceback would only bury them.
        print(f"run.sh: {refusal(error)}", file=sys.stderr)
        raise SystemExit(1) from None
    # One process and one worker.
    uvicorn.run(app, host=settings.workbench_host, port=settings.workbench_port)


if __name__ == "__main__":
    main()
