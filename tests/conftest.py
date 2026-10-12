"""Shared test setup. Tests use the fake model, so they need no key and no network.

Only the live test (tests/test_live.py, run with --live) reads app/.env and
calls the provider it names. Every test, the live one included, is blocked
from opening the hidden test set.
"""

import asyncio
import builtins
import json
import os
import pathlib
import socket
import sys
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

REPO_DIR = Path(__file__).resolve().parent.parent
APP_DIR = REPO_DIR / "app"
FIXTURES_DIR = Path(__file__).resolve().parent / "fixtures"
sys.path.insert(0, str(APP_DIR))

from workbench import db, specs, transcripts  # noqa: E402
from workbench.config import Settings, example_values, load_prompts  # noqa: E402
from workbench.gateway import Gateway  # noqa: E402
from workbench.limiter import Limiter  # noqa: E402
from workbench.main import create_app  # noqa: E402
from workbench.providers import FAKE_FILE, FakeProvider  # noqa: E402
from workbench.runtime import Runtime  # noqa: E402
from workbench.schemas import FakeSettings, MessageView, SampleChat, SpecBody  # noqa: E402

# The frozen CP2 prototype. app/static/data.js is a copy that M4 removes.
PROTOTYPE_DATA = REPO_DIR / "prototype" / "data.js"

# The hidden test set in validation/fixtures/. No test may open these.
HIDDEN_FILES = {"SEEDED_TRANSCRIPT.md", "ANSWER_KEY.md"}


def pytest_addoption(parser):
    parser.addoption("--live", action="store_true", default=False, help="also run the live test, which calls the model in app/.env")


def pytest_configure(config):
    config.addinivalue_line("markers", "live: calls a real model service, so it runs only with --live")


def pytest_collection_modifyitems(config, items):
    if config.getoption("--live"):
        return
    skip = pytest.mark.skip(reason="calls a real model service; run with --live")
    for item in items:
        if "live" in item.keywords:
            item.add_marker(skip)


@pytest.fixture(autouse=True)
def no_network(request, monkeypatch):
    """Any attempt to open a network connection fails, except in the live test."""
    if request.node.get_closest_marker("live"):
        return

    def refuse(*args, **kwargs):
        raise RuntimeError("Tests don't use the network. Use the fake model or a mock transport.")

    monkeypatch.setattr(socket.socket, "connect", refuse)
    monkeypatch.setattr(socket.socket, "connect_ex", refuse)
    monkeypatch.setattr(socket, "create_connection", refuse)
    monkeypatch.setattr(socket, "getaddrinfo", refuse)


@pytest.fixture(autouse=True)
def hidden_set_guard(monkeypatch):
    """Fails any test that opens a file of the hidden test set, by any path."""
    real_open = builtins.open
    real_path_open = pathlib.Path.open

    def check(file):
        if isinstance(file, (str, bytes, os.PathLike)) and os.path.basename(os.fsdecode(file)) in HIDDEN_FILES:
            raise AssertionError(f"A test opened {os.path.basename(os.fsdecode(file))}, which is part of the hidden test set.")

    def guarded_open(file, *args, **kwargs):
        check(file)
        return real_open(file, *args, **kwargs)

    def guarded_path_open(self, *args, **kwargs):
        check(self)
        return real_path_open(self, *args, **kwargs)

    monkeypatch.setattr(builtins, "open", guarded_open)
    monkeypatch.setattr(pathlib.Path, "open", guarded_path_open)


def js_literal_to_json(source):
    """Turns the object literal in data.js into JSON: quotes bare keys, drops comments.

    Strings are copied as they are, so apostrophes, \\u2019 escapes, and \\" inside
    them survive. Anything else JSON can't read (single quotes, backticks,
    trailing commas) makes json.loads fail loudly.
    """
    out = []
    i = 0
    while i < len(source):
        char = source[i]
        if char == '"':
            end = i + 1
            while source[end] != '"':
                end += 2 if source[end] == "\\" else 1
            out.append(source[i : end + 1])
            i = end + 1
        elif source.startswith("//", i):
            i = source.index("\n", i)
        elif source.startswith("/*", i):
            i = source.index("*/", i) + 2
        elif char.isalpha() or char == "_":
            end = i
            while end < len(source) and (source[end].isalnum() or source[end] in "_$"):
                end += 1
            word = source[i:end]
            out.append(word if word in ("true", "false", "null") else json.dumps(word))
            i = end
        else:
            out.append(char)
            i += 1
    return "".join(out)


def load_prototype_data():
    """window.WORKBENCH_DATA from prototype/data.js, as Python data."""
    source = PROTOTYPE_DATA.read_text(encoding="utf-8")
    start = source.index("window.WORKBENCH_DATA = ") + len("window.WORKBENCH_DATA = ")
    return json.loads(js_literal_to_json(source[start : source.rindex(";")]))


@pytest.fixture(scope="session")
def prototype_data():
    return load_prototype_data()


@pytest.fixture
def database(tmp_path):
    """A migrated database seeded with v1, in this test's own folder."""
    database = db.Database(tmp_path / "workbench.db")
    with database.connect() as conn:
        db.migrate(conn)
    specs.seed(database)
    return database


class FakeTime:
    """A clock that moves only when something sleeps, so call spacing costs no real time."""

    def __init__(self):
        self.now = 1000.0
        self.sleeps = []

    def clock(self):
        return self.now

    async def sleep(self, seconds):
        self.sleeps.append(seconds)
        self.now += seconds
        await asyncio.sleep(0)


def fake_settings(**changes):
    """The fake model's defaults from fake.v1.json, with no delays unless changed."""
    settings = FakeSettings.model_validate_json(FAKE_FILE.read_text(encoding="utf-8"))
    return settings.model_copy(update={"first_token_seconds": 0, "chunk_seconds": 0, **changes})


def settings_for(tmp_path, **overrides):
    """Settings from .env.example only, with the fake provider and a database in tmp_path."""
    values = {
        **example_values(),
        "workbench_db_path": str(tmp_path / "workbench.db"),
        "workbench_provider": "fake",
        **overrides,
    }
    # Init values beat environment variables, so the shell can't change a test.
    settings = Settings(_env_file=None, **values)
    assert APP_DIR / "data" not in db.Database(settings.workbench_db_path).path.parents
    return settings



@pytest.fixture
def make_client(tmp_path):
    """Builds a test client from the .env.example values plus any overrides.

    It uses the fake model with no delays and a fake clock, unless the test
    passes its own. The database lives in this test's own folder, so tests
    never touch app/data. Clients built in the same test share it, like
    restarts of one server.
    """

    def build(*, provider=None, time=None, **overrides):
        settings = settings_for(tmp_path, **overrides)
        time = time or FakeTime()
        provider = provider if provider is not None else FakeProvider(fake_settings())
        return TestClient(create_app(settings, provider=provider, clock=time.clock, sleep=time.sleep))

    return build


@pytest.fixture
def make_runtime(tmp_path, database):
    """Builds the runtime with no HTTP in between, for what TestClient can't show:
    a stream stopped partway, a closed connection, a turn that is still running."""

    def build(provider, *, clock=None, sleep=None, **overrides):
        settings = settings_for(tmp_path, **overrides)
        prompts = load_prompts()
        limiter = Limiter(settings.workbench_calls_per_minute, settings.workbench_daily_call_cap, prompts.models.quota_timezone)
        time = FakeTime()
        gateway = Gateway(
            database, settings, prompts, provider, limiter, clock=clock or time.clock, sleep=sleep or time.sleep
        )
        return Runtime(database, settings, prompts, gateway, transcripts.load_scenarios())

    return build


def sse_events(text):
    """(event name, data) for each server-sent event in a response body."""
    events = []
    for block in text.replace("\r\n", "\n").split("\n\n"):
        name, data = None, []
        for line in block.split("\n"):
            if line.startswith("event: "):
                name = line[len("event: ") :]
            elif line.startswith("data: "):
                data.append(line[len("data: ") :])
        if name and data:
            events.append((name, json.loads("\n".join(data))))
    return events


def query(database, sql, params=()):
    """Rows as dicts. database is a db.Database or a TestClient."""
    if isinstance(database, TestClient):
        database = database.app.state.database
    with database.connect() as conn:
        return [dict(row) for row in conn.execute(sql, params)]


def scenario_lines(scenario_id):
    return next(s for s in transcripts.load_scenarios().scenarios if s.id == scenario_id).lines


def default_model(provider="fake"):
    return load_prompts().models.character_models(provider)[0]


def v1_body():
    """Spec v1's body, as app/samples/spec_v1.json holds it."""
    return SpecBody.model_validate(json.loads(specs.SAMPLE_FILE.read_text(encoding="utf-8"))["body"])


def messages(*rows):
    """A chat's messages from (turn, speaker, text) rows, or (turn, speaker, text, stopped)."""
    return [
        MessageView(seq=seq, turn=row[0], speaker=row[1], text=row[2], source="import", stopped=len(row) > 3 and row[3])
        for seq, row in enumerate(rows, start=1)
    ]


def sample_messages(name):
    """A sample chat's messages (cla-f2, gpt-f2), as an import saves them."""
    chat = SampleChat.model_validate_json((APP_DIR / "samples" / f"{name}.json").read_text(encoding="utf-8"))
    return messages(*((message.turn, message.speaker, message.text) for message in chat.messages))
