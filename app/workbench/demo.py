"""Demo mode (CP4): the public link, with one private workbench per visitor.

WORKBENCH_MODE=demo starts this in place of the plain app. It wraps the same
create_app that local mode runs, and builds one small app per visitor on that
visitor's own copy of a template database: spec v1 and the two sample chats
with their saved checks, the state the demo reset makes. Every route, old or
new, then reads only that visitor's file, so no service needs to know about
visitors. A copy that sits idle is deleted, and the number of copies is capped.

A visitor is a cookie the server sets (HttpOnly, Secure, SameSite=Lax) and
signs, so nobody can pick an ID. Any request that isn't a GET must come from
the demo's own page, by its Origin header.

Three locks keep model calls behind the demo code:

1. ROUTES names every route that is open with no code or switched off. A
   route that isn't in it, such as one a teammate adds later, needs the code.
2. tests/test_demo_mode.py walks the app's routes and fails when one has no
   place in ROUTES, or when an open route reaches for a model.
3. Each visitor's provider is wrapped in LockedProvider, which refuses every
   call until that visitor has entered the code.

The code arrives in a POST body, is compared in constant time on every gated
request, and lives only in this process's memory. It is never logged, saved, or
sent back. Every visitor's gateway shares one Limiter and one ledger database,
so the call spacing and the daily cap cover all visitors together.
"""

import hashlib
import hmac
import json
import secrets
import sys
import time
import uuid
from collections.abc import Callable
from dataclasses import dataclass, field
from pathlib import Path
from urllib.parse import urlsplit

from starlette.requests import Request
from starlette.responses import HTMLResponse, JSONResponse, Response
from starlette.routing import BaseRoute, Match, Mount
from starlette.types import ASGIApp, Receive, Scope, Send

from workbench import db, providers, telemetry, transcripts
from workbench.config import APP_DIR, Settings, app_path, load_prompts
from workbench.judge import SNAPSHOT_FILE, SnapshotStale, load_snapshot
from workbench.limiter import Limiter
from workbench.schemas import ImportRequest

OPEN = "open"
CODE = "code"
OFF = "off"

# Every route the app serves, by method and path as the route declares it.
# open: anyone may call it. It reads, or it records a call on a flag (no model,
# no typed text). An open route takes no body and no query, which a test checks.
# off: refused in demo mode, whoever asks.
# A route that isn't listed needs the demo code, and so does every route marked
# code. That one is listed only so the table says where each route stands.
ROUTES: dict[tuple[str, str], str] = {
    ("GET", "/api/health"): OPEN,
    # Settings holds the key, so all of it is off.
    ("GET", "/api/settings"): OFF,
    ("POST", "/api/settings"): OFF,
    ("POST", "/api/settings/test"): OFF,
    ("GET", "/api/settings/ollama"): OFF,
    ("GET", "/api/characters"): OPEN,
    ("GET", "/api/characters/{slug}/specs/latest"): OPEN,
    ("GET", "/api/characters/{slug}/specs/{version}"): OPEN,
    # A saved spec version is the visitor's own text.
    ("POST", "/api/characters/{slug}/specs"): OFF,
    ("GET", "/api/run-options"): OPEN,
    ("GET", "/api/chats"): OPEN,
    # Starting a chat can call the test-case writer.
    ("POST", "/api/chats"): CODE,
    ("GET", "/api/chats/{chat_id}"): OPEN,
    ("POST", "/api/chats/{chat_id}/next"): CODE,
    ("POST", "/api/chats/{chat_id}/messages"): CODE,
    ("POST", "/api/chats/{chat_id}/stop"): CODE,
    # GET shows a saved check and never calls a model. POST may call the judge.
    ("GET", "/api/chats/{chat_id}/check"): OPEN,
    ("POST", "/api/chats/{chat_id}/check"): CODE,
    ("GET", "/api/review"): OPEN,
    ("POST", "/api/flags/{flag_id}/evidence"): OPEN,
    ("POST", "/api/flags/{flag_id}/agree"): OPEN,
    # An override's reason is typed text.
    ("POST", "/api/flags/{flag_id}/override"): CODE,
    ("POST", "/api/flags/{flag_id}/undo"): OPEN,
    ("POST", "/api/chats/{chat_id}/recheck"): CODE,
    ("GET", "/api/samples"): OPEN,
    # A pasted chat is the visitor's own text.
    ("POST", "/api/imports/preview"): CODE,
    ("POST", "/api/imports"): CODE,
    # FastAPI's own pages, which list every route.
    ("GET", "/openapi.json"): OFF,
    ("GET", "/docs"): OFF,
    ("GET", "/docs/oauth2-redirect"): OFF,
    ("GET", "/redoc"): OFF,
}

# The demo's own routes. demo.js is their only caller.
STATE_PATH = "/api/demo/state"
CODE_PATH = "/api/demo/code"
DEMO_PREFIX = "/api/demo/"
HEALTH_PATH = "/api/health"

# Routes that spend model calls, with the visitor's limit each one counts toward.
START_CHAT = ("POST", "/api/chats")
CHECK = ("POST", "/api/chats/{chat_id}/check")
RECHECK = ("POST", "/api/chats/{chat_id}/recheck")
MODEL_ROUTES = {
    START_CHAT: "runs",
    ("POST", "/api/chats/{chat_id}/next"): None,
    ("POST", "/api/chats/{chat_id}/messages"): None,
    CHECK: "checks",
    RECHECK: "rechecks",
}
IMPORT_ROUTES = {("POST", "/api/imports/preview"), ("POST", "/api/imports")}

COOKIE = "workbench_visitor"
COOKIE_SECONDS = 24 * 60 * 60
SESSION_HEADER = b"x-workbench-session"
MIN_CODE_CHARS = 12
# Wrong tries at the code that one visitor may make in ten minutes.
WRONG_TRIES = 5
WRONG_TRY_SECONDS = 600.0
# The files SQLite may keep next to a database while it writes.
SIDECARS = ("", "-journal", "-wal", "-shm")
PAGE = APP_DIR / "static" / "index.html"
# What the page loads only in demo mode: the banner, the code card, and what they hide.
PAGE_STYLE = '  <link rel="stylesheet" href="demo.css">\n'
PAGE_SCRIPT = '  <script src="demo.js"></script>\n'
QUICK_START = "https://github.com/FlinnH/IS492-CharacterAI-Team-Project#how-to-run-the-app"
# The samples every visitor starts with, as the demo reset loads them.
DEMO_SAMPLES = ("cla-f2", "gpt-f2")

# What a visitor is told. The screens show these as they are.
BANNER = (
    "Public demo. Don't type anything personal: text sent to the AI goes to Google's free tier, "
    "which may use it to improve its products. Your copy of the demo is wiped after {time}."
)
CODE_NEEDED = (
    "Live AI needs a demo code. This link is a demo. The workbench is built to run "
    "on your own computer, with your own free AI key. Setup takes about 15 minutes."
)
BUSY = "The demo is busy. Try again in a few minutes."
NO_COOKIE = "The demo keeps your copy with a cookie, and this request had none. Reload the page, and allow cookies for this site."
WRONG_ORIGIN = "The demo takes changes only from its own page. Open the demo's address and try again."
WRONG_CODE = "That isn't the demo code. Check it and try again."
TOO_MANY_TRIES = "Too many wrong tries. Wait 10 minutes, then try again."
SETTINGS_OFF = "Settings is off in the public demo. To use your own key and models, run the workbench on your own computer."
SPEC_OFF = "Saving a spec version is off in the public demo. To edit the spec, run the workbench on your own computer."
SEEDED_OFF = "The seeded transcript is off in the public demo."
OFF_MESSAGES = {("POST", "/api/characters/{slug}/specs"): SPEC_OFF}
SAMPLES_WORK = "The sample chats and their flags still work."


class Busy(Exception):
    """Every copy is taken, so a new visitor has to wait."""


def _count(number: int, word: str) -> str:
    return f"{number} {word}{'' if number == 1 else 's'}"


def _idle_time(minutes: int) -> str:
    """Like "2 hours" or "45 minutes"."""
    return _count(minutes // 60, "hour") if minutes % 60 == 0 else _count(minutes, "minute")


def limit_message(kind: str, limit: int) -> str:
    """What a visitor reads when one of their own limits is used up."""
    if kind == "runs":
        allowed = f"{_count(limit, 'live chat')} (test cases and free chats count together)"
        return f"The demo gives each visitor {allowed}, and you've started {'it' if limit == 1 else 'them'}. {SAMPLES_WORK}"
    what = _count(limit, "AI check" if kind == "checks" else "re-check")
    return f"The demo gives each visitor {what}, and you've used {'it' if limit == 1 else 'them'}. {SAMPLES_WORK}"


def cap_message(cap: int) -> str:
    return (
        f"The demo has used today's {_count(cap, 'AI call')}, which every visitor shares. "
        f"The count starts over at midnight Pacific time. {SAMPLES_WORK}"
    )


def api_routes(app: ASGIApp) -> list[tuple[str, str, BaseRoute]]:
    """(method, path, route) for each route the app serves, leaving out the static files."""
    found = []
    for route in app.routes:
        if isinstance(route, Mount):
            continue
        for method in sorted(route.methods - {"HEAD", "OPTIONS"}):
            found.append((method, route.path, route))
    return found


def unlisted(app: ASGIApp) -> list[str]:
    """Routes with no place in ROUTES, like "POST /api/new". They still need the code."""
    return [f"{method} {path}" for method, path, _ in api_routes(app) if (method, path) not in ROUTES]


def _remove(path: Path) -> None:
    """Deletes a database file and any files SQLite kept next to it."""
    for suffix in SIDECARS:
        Path(f"{path}{suffix}").unlink(missing_ok=True)


def _json(status: int, message: str, **more: object) -> JSONResponse:
    """An error as the screens read one: the message under detail."""
    return JSONResponse({"detail": message, **more}, status_code=status, headers={"Cache-Control": "no-store"})


class LockedProvider:
    """One visitor's view of the provider every visitor shares.

    It refuses every call until that visitor has entered the demo code, so a
    route opened by mistake still can't reach a model. refused counts the calls
    it turned away, which the route-walking test reads.
    """

    def __init__(self, inner: providers.Provider, unlocked: Callable[[], bool]) -> None:
        self.inner = inner
        self.unlocked = unlocked
        self.refused = 0

    @property
    def name(self) -> str:
        return self.inner.name

    @property
    def ready(self) -> bool:
        return self.inner.ready

    def _check(self) -> None:
        if not self.unlocked():
            self.refused += 1
            raise providers.ProviderError("auth", CODE_NEEDED, "demo code not entered")

    async def stream(self, model, messages, reasoning_effort, max_tokens):
        self._check()
        chunks = self.inner.stream(model, messages, reasoning_effort, max_tokens)
        try:
            async for chunk in chunks:
                yield chunk
        finally:
            await chunks.aclose()

    async def complete(self, model, messages, reasoning_effort, max_tokens, response_format, timeout):
        self._check()
        return await self.inner.complete(model, messages, reasoning_effort, max_tokens, response_format, timeout)

    async def list_models(self) -> list[str]:
        self._check()
        return await self.inner.list_models()

    async def aclose(self) -> None:
        # The shared provider closes once, when the demo shuts down.
        return None


@dataclass
class Visitor:
    """One visitor: their copy of the database and the app built on it."""

    key: str
    # Stands in for the browser tab's session ID, so the app's own session
    # limits count per visitor and a new tab can't dodge them.
    session: str
    database: db.Database
    seen: float
    app: ASGIApp | None = None
    provider: LockedProvider | None = None
    # What the visitor typed in the code card, once it was right. Memory only.
    code: str = ""
    wrong_tries: list[float] = field(default_factory=list)
    # Requests of theirs still running, like a reply that is streaming.
    active: int = 0


class Demo:
    """The ASGI app that demo mode serves."""

    def __init__(
        self,
        settings: Settings,
        build: Callable[..., ASGIApp],
        *,
        provider: providers.Provider | None = None,
        snapshot: Path | None = SNAPSHOT_FILE,
        now: Callable[[], float] = time.monotonic,
        **app_options,
    ) -> None:
        """build is main.create_app. provider, now, and app_options (the gateway's
        clock and sleep) are for tests. snapshot holds the samples' saved checks."""
        self.code = settings.workbench_demo_code.get_secret_value()
        if len(self.code) < MIN_CODE_CHARS:
            raise RuntimeError(
                f"Demo mode needs WORKBENCH_DEMO_CODE, with at least {MIN_CODE_CHARS} characters. "
                "Set it where the demo runs (docs/deployment.md), never in app/.env.example."
            )
        page = PAGE.read_text(encoding="utf-8")
        if page.count("</head>") != 1 or page.count("</body>") != 1:
            raise RuntimeError("Demo mode adds its files to app/static/index.html, which needs one </head> and one </body>.")

        self.settings = settings
        self.build = build
        self.now = now
        self.app_options = app_options
        self.idle_seconds = settings.workbench_demo_idle_minutes * 60.0
        self.limits = {
            "runs": settings.workbench_demo_run_limit,
            "checks": settings.workbench_demo_check_limit,
            "rechecks": settings.workbench_demo_recheck_limit,
        }
        # Signs the visitor cookie. It comes from the code, so a cookie still
        # counts after a restart, and its visitor just gets a fresh copy.
        self.cookie_key = hmac.new(self.code.encode(), b"workbench visitor cookie", hashlib.sha256).digest()

        prompts = load_prompts()
        self.provider = provider if provider is not None else providers.build(settings, prompts.presets)
        self.limiter = Limiter(settings.workbench_calls_per_minute, settings.workbench_daily_call_cap, prompts.models.quota_timezone)

        # Everything the demo writes sits in one folder next to the database.
        self.folder = app_path(settings.workbench_db_path).parent / "demo"
        self.folder.mkdir(parents=True, exist_ok=True)
        # Copies from an earlier start belong to nobody now.
        for stale in self.folder.glob("visitor-*.db*"):
            stale.unlink(missing_ok=True)
        # The count behind the daily cap. It survives a restart when the disk does.
        self.ledger = db.Database(self.folder / "ledger.db")
        with self.ledger.connect() as conn:
            db.migrate(conn)

        self.visitors: dict[str, Visitor] = {}
        self.template = db.Database(self.folder / "template.db")
        _remove(self.template.path)
        # The template's app also serves the static files and knows the routes.
        # No request for data ever reaches it, and its provider never unlocks.
        self.pages = self._app(self.template, LockedProvider(self.provider, lambda: False))
        self.routes = list(self.pages.routes)
        self.notes = self._fill_template(snapshot)
        for note in self.notes:
            print(f"demo: {note}", file=sys.stderr)

    # Building the template and each visitor's copy.

    def _app(self, database: db.Database, provider: LockedProvider) -> ASGIApp:
        """The workbench on one database file, as local mode builds it, with the demo's limits."""
        settings = self.settings.model_copy(
            update={
                "workbench_db_path": database.path,
                # The demo refuses at its own limits first, with its own cards. The
                # app's session limits sit one past them, as a second guard, so its
                # screens never show their own wording, which points at Settings.
                # Every tab of a visitor shares one session, so these hold per visitor.
                "workbench_session_run_limit": self.limits["runs"] + 1,
                "workbench_session_judge_limit": self.limits["checks"] + self.limits["rechecks"] + 1,
                # A path with no file, so the seeded transcript can't be read.
                "workbench_seeded_transcript_path": Path("off-in-the-public-demo"),
            }
        )
        return self.build(
            settings,
            provider=provider,
            build_provider=lambda _settings: provider,
            # Settings is off, so nothing ever writes this file.
            env_file=self.folder / "settings-are-off.env",
            limiter=self.limiter,
            ledger=self.ledger,
            **self.app_options,
        )

    def _fill_template(self, snapshot: Path | None) -> list[str]:
        """Loads the samples and their saved checks, with no model call. Returns what went wrong, if anything."""
        state = self.pages.state
        character = transcripts.load_scenarios().character
        for sample in DEMO_SAMPLES:
            request = ImportRequest(source="sample", character=character, sample=sample)
            transcripts.import_chat(self.template, state.settings, request, None, record=False)
        with self.template.connect() as conn:
            chats = {row["sample"]: row["id"] for row in conn.execute("SELECT sample, id FROM transcripts ORDER BY id")}
        if list(chats) != list(DEMO_SAMPLES):
            raise RuntimeError("The demo's template didn't get its sample chats.")
        if snapshot is None or not snapshot.is_file():
            return ["there's no judge snapshot, so the samples start with no flags."]
        notes = []
        for check in load_snapshot(snapshot).checks:
            if check.sample not in chats:
                continue
            try:
                state.judge.replay(chats[check.sample], check)
            except SnapshotStale as error:
                notes.append(f"the judge snapshot for {check.sample} doesn't fit today's judge, so it starts with no flags. {error}")
        return notes

    def _create(self, key: str) -> Visitor:
        """A new visitor's copy of the template and the app on it. Raises Busy at the cap."""
        if len(self.visitors) >= self.settings.workbench_demo_max_visitors:
            raise Busy(BUSY)
        path = self.folder / f"visitor-{hashlib.sha256(key.encode()).hexdigest()[:32]}.db"
        _remove(path)
        self.template.backup(path)
        session = str(uuid.UUID(hashlib.sha256(f"session {key}".encode()).hexdigest()[:32]))
        visitor = Visitor(key=key, session=session, database=db.Database(path), seen=self.now())
        visitor.provider = LockedProvider(self.provider, lambda: self.unlocked(visitor))
        visitor.app = self._app(visitor.database, visitor.provider)
        self.visitors[key] = visitor
        return visitor

    def sweep(self) -> None:
        """Deletes each copy that has sat idle too long."""
        now = self.now()
        for key, visitor in list(self.visitors.items()):
            if visitor.active == 0 and now - visitor.seen >= self.idle_seconds:
                del self.visitors[key]
                _remove(visitor.database.path)

    def full(self) -> bool:
        return len(self.visitors) >= self.settings.workbench_demo_max_visitors

    # The cookie and the code.

    def _sign(self, key: str) -> str:
        return hmac.new(self.cookie_key, key.encode(), hashlib.sha256).hexdigest()

    def _visitor_key(self, request: Request) -> str | None:
        """The visitor a request's cookie names, when this server signed it."""
        key, _, signature = request.cookies.get(COOKIE, "").partition(".")
        if key and signature and hmac.compare_digest(signature.encode(), self._sign(key).encode()):
            return key
        return None

    def _set_cookie(self, response: Response) -> None:
        key = secrets.token_urlsafe(24)
        response.set_cookie(
            COOKIE, f"{key}.{self._sign(key)}", max_age=COOKIE_SECONDS, path="/", secure=True, httponly=True, samesite="lax"
        )

    def unlocked(self, visitor: Visitor) -> bool:
        """Whether this visitor entered the demo code. Compared again on every request, in constant time."""
        return hmac.compare_digest(visitor.code.encode(), self.code.encode())

    def _enter_code(self, visitor: Visitor, body: bytes) -> Response:
        now = self.now()
        visitor.wrong_tries = [when for when in visitor.wrong_tries if now - when < WRONG_TRY_SECONDS]
        if len(visitor.wrong_tries) >= WRONG_TRIES:
            return _json(429, TOO_MANY_TRIES, demo="tries")
        try:
            entered = json.loads(body)["code"]
        except (ValueError, KeyError, TypeError):
            entered = None
        if not isinstance(entered, str) or not hmac.compare_digest(entered.strip().encode(), self.code.encode()):
            visitor.wrong_tries.append(now)
            return _json(403, WRONG_CODE, demo="code")
        visitor.code = entered.strip()
        visitor.wrong_tries = []
        return JSONResponse(self.state(visitor), headers={"Cache-Control": "no-store"})

    # What a visitor has used, and what is left.

    def used(self, visitor: Visitor) -> dict[str, int]:
        """Live chats started, and checks and re-checks that asked the AI judge, in this visitor's copy."""
        with visitor.database.connect() as conn:
            row = conn.execute(
                "SELECT (SELECT COUNT(*) FROM transcripts WHERE kind = 'live') AS runs,"
                " (SELECT COUNT(*) FROM judge_runs WHERE attempts > 0) AS checks,"
                " (SELECT COUNT(*) FROM rechecks WHERE attempts > 0) AS rechecks"
            ).fetchone()
        return dict(row)

    def calls_left(self) -> bool:
        """Whether the whole demo has model calls left today."""
        day = self.limiter.quota_day(telemetry.utc_now())
        return telemetry.calls_on_day(self.ledger, self.provider.name, day) < self.limiter.daily_cap

    def state(self, visitor: Visitor) -> dict:
        """What demo.js needs to draw the banner and pick a card. Never the code."""
        used = self.used(visitor)
        limits = {kind: {"used": used[kind], "limit": limit, "message": limit_message(kind, limit)} for kind, limit in self.limits.items()}
        return {
            "unlocked": self.unlocked(visitor),
            "limits": limits,
            "calls_left": self.calls_left(),
            "cap_message": cap_message(self.limiter.daily_cap),
            "banner": BANNER.format(time=_idle_time(self.settings.workbench_demo_idle_minutes)),
            "code_needed": CODE_NEEDED,
            "spec_off": SPEC_OFF,
            "quick_start": QUICK_START,
        }

    def _limit(self, visitor: Visitor, route: tuple[str, str]) -> Response | None:
        """The card for a limit this request would pass, or None when it may go on."""
        kind = MODEL_ROUTES[route]
        if kind is not None and self.used(visitor)[kind] >= self.limits[kind]:
            return _json(429, limit_message(kind, self.limits[kind]), demo="limit")
        if not self.calls_left():
            return _json(429, cap_message(self.limiter.daily_cap), demo="cap")
        return None

    # Requests.

    def _match(self, scope: Scope) -> BaseRoute | None:
        """The route that serves this request, found the way the app's own router finds it."""
        for route in self.routes:
            match, _ = route.matches(scope)
            if match is Match.FULL:
                return route
        return None

    @staticmethod
    def _own_page(request: Request) -> bool:
        """Whether the request's Origin is the address it was sent to, so the demo's own page sent it."""
        origin = urlsplit(request.headers.get("origin", ""))
        host = request.headers.get("host", "")
        return origin.scheme in ("http", "https") and bool(host) and origin.netloc.lower() == host.lower()

    def _page(self, request: Request) -> Response:
        """The workbench page with the demo's files added, or the busy page when no copy is free."""
        key = self._visitor_key(request)
        if (key is None or key not in self.visitors) and self.full():
            return HTMLResponse(BUSY_PAGE, status_code=503, headers={"Retry-After": "300", "Cache-Control": "no-store"})
        page = PAGE.read_text(encoding="utf-8")
        page = page.replace("</head>", f"{PAGE_STYLE}</head>").replace("</body>", f"{PAGE_SCRIPT}</body>")
        response = HTMLResponse(page, headers={"Cache-Control": "no-cache"})
        if key is None:
            # Set with the page, before any script runs, so every later request carries it.
            self._set_cookie(response)
        return response

    @staticmethod
    async def _body(receive: Receive, limit: int) -> bytes | None:
        """The whole request body, or None when it is longer than limit bytes."""
        body = b""
        while True:
            message = await receive()
            if message["type"] != "http.request":
                return body
            body += message.get("body", b"")
            if len(body) > limit:
                return None
            if not message.get("more_body"):
                return body

    def _health(self) -> Response:
        # Says whether a key is set, never the key or the code.
        return JSONResponse(
            {
                "status": "ok",
                "mode": "demo",
                "provider": self.settings.workbench_provider,
                "key_set": self.provider.ready,
                "visitors": len(self.visitors),
            },
            headers={"Cache-Control": "no-store"},
        )

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] == "lifespan":
            await self._lifespan(receive, send)
            return
        if scope["type"] != "http":
            # The workbench has no websockets.
            await send({"type": "websocket.close", "code": 1008})
            return

        # On every request, the health check's and the keep-warm job's included,
        # so an idle copy goes even when its own visitor never comes back.
        self.sweep()
        request = Request(scope, receive)
        method = "GET" if scope["method"] == "HEAD" else scope["method"]
        path = scope["path"]
        if method == "GET" and scope["method"] == "GET" and path in ("/", "/index.html"):
            await self._page(request)(scope, receive, send)
            return
        # Render's health check and the keep-warm job ask this, so it makes no copy.
        if method == "GET" and path == HEALTH_PATH:
            await self._health()(scope, receive, send)
            return

        own = path.startswith(DEMO_PREFIX)
        route = None if own else self._match(scope)
        if not own and (route is None or isinstance(route, Mount)):
            # A static file, or a path nothing serves. Neither touches a visitor's data.
            await self.pages(scope, receive, send)
            return

        key = (method, path if own else route.path)
        # The demo's own routes take no code: one of them is where the code is entered.
        place = OPEN if own else ROUTES.get(key, CODE)
        if place == OFF:
            if key[1].startswith("/api/"):
                await _json(403, OFF_MESSAGES.get(key, SETTINGS_OFF), demo="off")(scope, receive, send)
            else:
                await _json(404, "Not found.")(scope, receive, send)
            return
        if method != "GET" and not self._own_page(request):
            await _json(403, WRONG_ORIGIN, demo="origin")(scope, receive, send)
            return
        visitor_key = self._visitor_key(request)
        if visitor_key is None:
            await _json(403, NO_COOKIE, demo="cookie")(scope, receive, send)
            return
        try:
            visitor = self.visitors.get(visitor_key) or self._create(visitor_key)
        except Busy as error:
            await _json(503, str(error), demo="busy")(scope, receive, send)
            return
        visitor.seen = self.now()

        if own:
            if key == ("GET", STATE_PATH):
                response = JSONResponse(self.state(visitor), headers={"Cache-Control": "no-store"})
            elif key == ("POST", CODE_PATH):
                body = await self._body(receive, 2048)
                response = _json(413, WRONG_CODE, demo="code") if body is None else self._enter_code(visitor, body)
            else:
                response = _json(404, "Not found.")
            await response(scope, receive, send)
            return

        if place == CODE:
            if not self.unlocked(visitor):
                await _json(403, CODE_NEEDED, demo="code")(scope, receive, send)
                return
            if key in MODEL_ROUTES:
                refused = self._limit(visitor, key)
                if refused is not None:
                    await refused(scope, receive, send)
                    return
            if key in IMPORT_ROUTES:
                # Read here to refuse the seeded transcript, then handed on as it came.
                body = await self._body(receive, self.settings.workbench_max_import_chars * 4 + 4096)
                if body is None:
                    await _json(413, "That chat is too long to import.")(scope, receive, send)
                    return
                if self._asks_for_seeded(body):
                    await _json(403, SEEDED_OFF, demo="off")(scope, receive, send)
                    return
                receive = self._replay(body, receive)

        # The visitor's ID stands in for the tab's session ID.
        headers = [(name, value) for name, value in scope["headers"] if name != SESSION_HEADER]
        headers.append((SESSION_HEADER, visitor.session.encode()))
        visitor.active += 1
        try:
            await visitor.app({**scope, "headers": headers}, receive, send)
        finally:
            visitor.active -= 1
            visitor.seen = self.now()

    @staticmethod
    def _asks_for_seeded(body: bytes) -> bool:
        try:
            data = json.loads(body)
        except ValueError:
            return False
        return isinstance(data, dict) and data.get("sample") == transcripts.SEEDED

    @staticmethod
    def _replay(body: bytes, receive: Receive) -> Receive:
        """A receive that hands the app the body that was already read."""
        sent = False

        async def replay():
            nonlocal sent
            if not sent:
                sent = True
                return {"type": "http.request", "body": body, "more_body": False}
            return await receive()

        return replay

    async def _lifespan(self, receive: Receive, send: Send) -> None:
        while True:
            message = await receive()
            if message["type"] == "lifespan.startup":
                await send({"type": "lifespan.startup.complete"})
            elif message["type"] == "lifespan.shutdown":
                await self.provider.aclose()
                await send({"type": "lifespan.shutdown.complete"})
                return


# Shown in place of the workbench when every copy is taken.
BUSY_PAGE = f"""<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>Character Consistency Workbench: the demo is busy</title>
  <style>
    body {{ font-family: Roboto, system-ui, sans-serif; margin: 0; padding: 48px 24px; background: #fef7ff; color: #1d1b20; }}
    main {{ max-width: 560px; margin: 0 auto; }}
    h1 {{ font-size: 28px; line-height: 36px; font-weight: 400; margin: 0 0 16px; }}
    p {{ font-size: 16px; line-height: 24px; margin: 0 0 16px; }}
    a {{ color: #6750a4; }}
    @media (prefers-color-scheme: dark) {{
      body {{ background: #141218; color: #e6e0e9; }}
      a {{ color: #d0bcff; }}
    }}
  </style>
</head>
<body>
  <main>
    <h1>{BUSY}</h1>
    <p>Each visitor gets a private copy of the demo, and every copy is in use right now. A copy frees up when its visitor has been away for a while.</p>
    <p>You can also <a href="{QUICK_START}">run the workbench on your own computer</a> in about 15 minutes.</p>
  </main>
</body>
</html>
"""


def create_demo(settings: Settings, build: Callable[..., ASGIApp], **options) -> Demo:
    """The app for WORKBENCH_MODE=demo. build is main.create_app."""
    return Demo(settings, build, **options)
