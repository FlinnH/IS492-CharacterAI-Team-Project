"""CP4 F2 tests: demo mode, the public link.

Local mode is the default and serves what it served before. In demo mode each
visitor gets a private copy of the two sample chats, anything that calls a
model or stores typed text needs the demo code, Settings, spec saves, and the
seeded transcript are off, and the limits hold. Every database lives in the
test's own folder, the model is the fake one, and nothing reaches the network.
"""

import importlib.util
import itertools
import logging
import os
import re
import shutil
import subprocess
import sys
from typing import get_args

import pytest
from fastapi import Request
from fastapi.routing import APIRoute
from fastapi.testclient import TestClient

from conftest import APP_DIR, FIXTURES_DIR, REPO_DIR, FakeTime, default_model, fake_settings, query, settings_for, sse_events
from test_judge import UMBRIDGE, import_sample, judge_reply
from test_recheck import HERMIONE
from test_team_kit import read_plain_yaml
from workbench import main as entry
from workbench.config import KEY_SETTINGS, Settings, example_values, listen_port, load_prompts, load_settings
from workbench.demo import (
    BANNER,
    BUSY,
    CODE,
    CODE_NEEDED,
    COOKIE,
    NO_COOKIE,
    OPEN,
    QUICK_START,
    ROUTES,
    SEEDED_OFF,
    SETTINGS_OFF,
    SPEC_OFF,
    TOO_MANY_TRIES,
    WRONG_CODE,
    WRONG_ORIGIN,
    WRONG_TRIES,
    Demo,
    api_routes,
    cap_message,
    create_demo,
    limit_message,
    unlisted,
)
from workbench.judge import SNAPSHOT_FILE
from workbench.main import create_app
from workbench.providers import FakeProvider
from workbench.schemas import JudgeOutput, JudgeSnapshot, SnapshotCall, SnapshotCheck

# A made-up demo code. No response, log, or saved file may hold it.
DEMO_CODE = "made-up-demo-code-4Tq9"
SITE = "https://demo.test"
STATIC_DIR = APP_DIR / "static"
DEMO_JS = STATIC_DIR / "demo.js"
RENDER_YAML = REPO_DIR / "render.yaml"
KEEP_WARM = REPO_DIR / ".github" / "workflows" / "keep-warm.yml"
START = {"character": "harry", "scenario": "F2"}
REASON = "Harry is only guessing here"
needs_bash = pytest.mark.skipif(sys.platform == "win32" or not shutil.which("bash"), reason="the workflow's step is a bash script")


class Clock:
    """The demo's idle clock, moved by hand."""

    def __init__(self):
        self.now = 0.0

    def __call__(self):
        return self.now


def fake_snapshot(tmp_path):
    """A judge snapshot of CLA-F2 made for the fake judge, with two flags, so the sample has a saved check."""
    path = tmp_path / "judge_snapshot.json"
    if path.is_file():
        return path
    maker = create_app(settings_for(tmp_path / "maker"), provider=FakeProvider(fake_settings()))
    chat_id = import_sample(TestClient(maker), "cla-f2")
    judge = maker.state.judge
    prompts = load_prompts()
    check = SnapshotCheck(
        sample="cla-f2",
        transcript_sha256=judge.transcript_sha256(maker.state.runtime.get_chat(chat_id)),
        model=judge.model_id(),
        reasoning_effort=judge.effort(),
        prompt_version=prompts.judge_version,
        schema_version=prompts.judge_schema_version,
        checked_at="2026-10-20T23:30:47.096Z",
        call=SnapshotCall(latency_ms=2821, input_tokens=4300, output_tokens=150, reasoning_tokens=0, est_cost_usd=0.002),
        answer=JudgeOutput.model_validate_json(judge_reply(UMBRIDGE, HERMIONE)),
    )
    snapshot = JudgeSnapshot(format="workbench-judge-snapshot.v1", note="For tests.", checks=[check])
    path.write_text(snapshot.model_dump_json(), encoding="utf-8")
    return path


@pytest.fixture
def make_demo(tmp_path):
    """Builds the demo app from the .env.example values plus any overrides.

    It uses the fake model, a fake clock for call spacing, and a judge
    snapshot made for the fake judge, so CLA-F2 starts with flags and GPT-F2
    starts unchecked. Demos built in the same test share its folder, like
    restarts of one server.
    """

    def build(*, provider=None, snapshot=True, builder=create_app, clock=None, **overrides):
        settings = settings_for(tmp_path, workbench_mode="demo", workbench_demo_code=DEMO_CODE, **overrides)
        time = FakeTime()
        return create_demo(
            settings,
            builder,
            provider=provider if provider is not None else FakeProvider(fake_settings()),
            snapshot=fake_snapshot(tmp_path) if snapshot is True else snapshot,
            now=clock or Clock(),
            clock=time.clock,
            sleep=time.sleep,
        )

    return build


def visit(demo, **options):
    """A visitor's browser after it loaded the page, which is what sets the cookie."""
    client = TestClient(demo, base_url=SITE, headers={"Origin": SITE}, **options)
    response = client.get("/")
    assert response.status_code == 200, response.text
    return client


def unlock(client):
    response = client.post("/api/demo/code", json={"code": DEMO_CODE})
    assert response.status_code == 200, response.text
    assert response.json()["unlocked"] is True
    return client


def ok(response, status=200):
    assert response.status_code == status, response.text
    return response.json()


def samples(client):
    """The two sample chats' IDs: (CLA-F2, GPT-F2)."""
    chats = {chat["title"]: chat["id"] for chat in ok(client.get("/api/chats"))}
    return chats["Claude (CLA-F2)"], chats["ChatGPT (GPT-F2)"]


def flags_of(client, chat_id):
    return next(item for item in ok(client.get("/api/review"))["chats"] if item["chat"]["id"] == chat_id)["flags"]


def start(client, **changes):
    return client.post("/api/chats", json={**START, "model": default_model(), **changes})


def refused(response, message, status=403):
    assert response.status_code == status, response.text
    assert response.json()["detail"] == message
    return response


def visitor_of(demo, client):
    """The server's record of this client's visitor."""
    key = client.cookies.get(COOKIE).partition(".")[0]
    return demo.visitors[key]


# Local mode is the default, and nothing about it changed.


def test_local_is_the_default_mode_and_the_example_holds_no_code():
    values = example_values()
    assert values["workbench_mode"] == "local"
    assert values["workbench_demo_code"] == ""
    assert "workbench_demo_code" in KEY_SETTINGS
    # Each mode the setting allows has an app to start, so a new mode is added in both places.
    assert set(get_args(Settings.model_fields["workbench_mode"].annotation)) == set(entry.MODES)


def test_every_route_has_a_place_in_the_demo_table(make_client):
    app = make_client().app
    assert unlisted(app) == [], "give each new route a place in demo.ROUTES: open, code, or off"
    # And the table names no route that is gone, so it also pins what local mode serves.
    assert {(method, path) for method, path, _ in api_routes(app)} == set(ROUTES)
    assert not any(path.startswith("/api/demo/") for _, path in ROUTES)


def test_open_routes_take_no_body_and_no_query(make_client):
    # So an open route has nowhere to put a visitor's text. Anything that takes text needs the code.
    for method, path, route in api_routes(make_client().app):
        if ROUTES[(method, path)] != OPEN:
            continue
        assert isinstance(route, APIRoute) and method in ("GET", "POST"), f"{method} {path}"
        assert route.body_field is None and route.dependant.body_params == [], f"{method} {path} takes a body"
        assert route.dependant.query_params == [], f"{method} {path} takes a query"


def test_the_local_page_and_routes_know_nothing_of_the_demo(make_client):
    client = make_client()
    page = client.get("/")
    assert "demo.js" not in page.text and "demo.css" not in page.text
    assert "set-cookie" not in page.headers
    assert client.get("/api/demo/state").status_code == 404
    assert set(client.get("/api/health").json()) == {"status", "provider", "key_set"}
    for name in ("app.js", "api.js", "index.html", "styles.css"):
        text = (STATIC_DIR / name).read_text(encoding="utf-8")
        assert "/api/demo" not in text and "demo.js" not in text and "demo.css" not in text, name


def test_local_mode_ignores_the_hosts_port(monkeypatch, tmp_path):
    monkeypatch.setenv("PORT", "10000")
    assert listen_port(settings_for(tmp_path)) == 8492
    assert listen_port(settings_for(tmp_path, workbench_mode="demo", workbench_demo_code=DEMO_CODE)) == 10000


# Each visitor has their own copy.


def test_two_visitors_get_separate_copies(make_demo):
    demo = make_demo()
    first, second = visit(demo), visit(demo)
    cla, _ = samples(first)
    assert samples(second) == samples(first)
    flag_id = flags_of(first, cla)[0]["id"]

    ok(first.post(f"/api/flags/{flag_id}/evidence"))
    ok(first.post(f"/api/flags/{flag_id}/agree"))

    mine = next(flag for flag in flags_of(first, cla) if flag["id"] == flag_id)
    theirs = next(flag for flag in flags_of(second, cla) if flag["id"] == flag_id)
    assert mine["call"]["verdict"] == "agreed"
    assert theirs["call"] is None and theirs["evidence_opened"] is False

    one, two = visitor_of(demo, first), visitor_of(demo, second)
    assert one.database.path != two.database.path
    assert one.database.path.is_file() and two.database.path.is_file()
    assert query(two.database, "SELECT COUNT(*) AS n FROM events")[0]["n"] == 0
    # The visitor's ID stands in for the tab's session, whatever the browser sends.
    ok(first.post(f"/api/flags/{flag_id}/undo", headers={"X-Workbench-Session": "00000000-0000-4000-8000-000000000009"}))
    assert {row["session"] for row in query(one.database, "SELECT session FROM events")} == {one.session}
    # Every visitor's gateway shares the call spacing and the count behind the daily cap.
    gateways = [visitor.app.state.runtime.gateway for visitor in (one, two)]
    assert all(gateway.limiter is demo.limiter and gateway.ledger is demo.ledger for gateway in gateways)


def test_the_samples_show_their_flags_with_zero_model_calls(make_demo):
    provider = FakeProvider(fake_settings())
    demo = make_demo(provider=provider)
    client = visit(demo)

    cla, gpt = samples(client)
    assert len(ok(client.get(f"/api/chats/{cla}"))["messages"]) > 10
    assert len(ok(client.get(f"/api/chats/{gpt}"))["messages"]) > 10
    assert ok(client.get("/api/characters/harry/specs/latest"))["version"] == 1
    check = ok(client.get(f"/api/chats/{cla}/check"))["result"]
    assert {flag["line_id"] for flag in check["flags"]} >= {UMBRIDGE["line_id"], HERMIONE["line_id"]}
    flags = flags_of(client, cla)
    flag_id = flags[0]["id"]

    # Show in context, Agree, and Undo, with no code.
    assert ok(client.get("/api/demo/state"))["unlocked"] is False
    ok(client.post(f"/api/flags/{flag_id}/evidence"))
    ok(client.post(f"/api/flags/{flag_id}/agree"))
    assert next(flag for flag in flags_of(client, cla) if flag["id"] == flag_id)["call"]["verdict"] == "agreed"
    ok(client.post(f"/api/flags/{flag_id}/undo"))
    assert next(flag for flag in flags_of(client, cla) if flag["id"] == flag_id)["call"] is None

    visitor = visitor_of(demo, client)
    assert provider.requests == [] and visitor.provider.refused == 0
    assert query(visitor.database, "SELECT COUNT(*) AS n FROM model_calls")[0]["n"] == 0
    assert query(demo.ledger, "SELECT COUNT(*) AS n FROM model_calls")[0]["n"] == 0


def test_the_demo_starts_with_the_real_snapshots_flags(make_demo):
    # The snapshot in app/samples was made with the Gemini judge the example settings pick.
    demo = make_demo(snapshot=SNAPSHOT_FILE, workbench_provider="gemini", gemini_api_key="made-up-key-for-tests")
    assert demo.notes == []
    client = visit(demo)
    cla, gpt = samples(client)
    assert flags_of(client, cla) and flags_of(client, gpt)


# The demo code.


def test_gated_routes_answer_403_without_the_code_and_work_with_it(make_demo, caplog, capsys):
    caplog.set_level(logging.DEBUG)
    provider = FakeProvider(fake_settings())
    demo = make_demo(provider=provider, workbench_demo_run_limit=3)
    client = visit(demo)
    cla, gpt = samples(client)
    flag_id = next(flag for flag in flags_of(client, cla) if flag["line_id"] == HERMIONE["line_id"])["id"]
    paste = {"source": "paste", "character": "harry", "text": (FIXTURES_DIR / "inline_chat.txt").read_text(encoding="utf-8")}
    model = default_model()
    seen = []

    def send(path, body=None):
        response = client.post(path, json=body)
        seen.append(response.text + str(response.headers))
        return response

    # Without the code, each one is refused, and nothing is started or saved.
    gated = [
        ("/api/chats", {**START, "model": model}),
        ("/api/chats", {**START, "model": model, "generate": True}),
        ("/api/chats", {**START, "model": model, "scenario": "Free"}),
        (f"/api/chats/{cla}/next", None),
        (f"/api/chats/{cla}/messages", {"text": "Hello there"}),
        (f"/api/chats/{cla}/stop", None),
        (f"/api/chats/{gpt}/check", None),
        (f"/api/chats/{cla}/recheck", {"question": None}),
        (f"/api/flags/{flag_id}/override", {"reason": REASON, "type": None}),
        ("/api/imports/preview", paste),
        ("/api/imports", paste),
    ]
    for path, body in gated:
        refused(send(path, body), CODE_NEEDED)
    assert len(ok(client.get("/api/chats"))) == 2
    assert provider.requests == []

    # A wrong code is refused and never echoed. Then the right one opens every route.
    refused(send("/api/demo/code", {"code": "not-the-demo-code"}), WRONG_CODE)
    assert ok(client.get("/api/demo/state"))["unlocked"] is False
    assert ok(send("/api/demo/code", {"code": DEMO_CODE}))["unlocked"] is True

    run = ok(send("/api/chats", {**START, "model": model}), 201)["id"]
    ok(send("/api/chats", {**START, "model": model, "generate": True}), 201)
    free = ok(send("/api/chats", {**START, "model": model, "scenario": "Free"}), 201)["id"]
    assert sse_events(send(f"/api/chats/{run}/next").text)[-1][0] == "done"
    ok(send(f"/api/chats/{run}/stop"))
    assert sse_events(send(f"/api/chats/{free}/messages", {"text": "Hello there"}).text)[-1][0] == "done"
    assert ok(send(f"/api/chats/{gpt}/check"))["judge"]["status"] == "ok"
    ok(send(f"/api/chats/{cla}/recheck", {"question": None}))
    ok(send(f"/api/flags/{flag_id}/evidence"))
    ok(send(f"/api/flags/{flag_id}/override", {"reason": REASON, "type": None}))
    assert ok(send("/api/imports/preview", paste))["message_count"] > 0
    ok(send("/api/imports", paste), 201)
    assert len(provider.requests) >= 4

    # The code is in no response, no log line, and no file the demo wrote.
    logged = caplog.text + "".join(capsys.readouterr())
    assert DEMO_CODE not in logged
    assert all(DEMO_CODE not in text for text in seen)
    for path in demo.folder.iterdir():
        assert DEMO_CODE.encode() not in path.read_bytes(), path.name


def test_wrong_tries_at_the_code_are_limited(make_demo):
    clock = Clock()
    client = visit(make_demo(clock=clock))
    for _ in range(WRONG_TRIES):
        refused(client.post("/api/demo/code", json={"code": "a-wrong-guess"}), WRONG_CODE)
    # Even the right code waits now.
    refused(client.post("/api/demo/code", json={"code": DEMO_CODE}), TOO_MANY_TRIES, 429)
    clock.now += 601
    unlock(client)


# The route walk: nothing that reaches for a model is open.


def reaching_for_a_model(demo, client):
    """Calls every open route with no code, and returns the ones that asked for a model.

    A route that names a chat is called for both samples, the checked one and
    the unchecked one, and a route that names a flag for every flag.
    """
    cla, gpt = samples(client)
    values = {"slug": ["harry"], "chat_id": [cla, gpt], "flag_id": [flag["id"] for flag in flags_of(client, cla)]}
    visitor = visitor_of(demo, client)
    found = []
    for method, path, _ in api_routes(demo.pages):
        if ROUTES.get((method, path), CODE) != OPEN:
            continue
        names = re.findall(r"\{(\w+)[^}]*\}", path)
        before = (len(demo.provider.requests), visitor.provider.refused)
        for choice in itertools.product(*(values.get(name, [1]) for name in names)):
            filled = iter(choice)
            try:
                client.request(method, re.sub(r"\{[^}]*\}", lambda _: str(next(filled)), path))
            except Exception:
                # A route whose model call was refused may fail outright. The counts below say why.
                pass
        if (len(demo.provider.requests), visitor.provider.refused) != before:
            found.append(f"{method} {path}")
    return found


def assert_no_open_route_reaches_a_model(demo):
    client = visit(demo)
    assert reaching_for_a_model(demo, client) == [], "an open route in demo.ROUTES asks for a model: mark it code"


def assert_every_route_has_a_place(app):
    assert unlisted(app) == [], "give each new route a place in demo.ROUTES: open, code, or off"


def with_a_made_up_route(settings, **options):
    """The app plus a route a teammate might add later: it asks the model, through the gateway's provider."""
    app = create_app(settings, **options)

    async def made_up(request: Request) -> dict:
        provider = request.app.state.runtime.gateway.provider
        completion = await provider.complete(default_model(), [{"role": "user", "content": "hi"}], None, 16, {}, 5.0)
        return {"text": completion.text}

    app.add_api_route("/api/made-up", made_up, methods=["GET"])
    # Ahead of the static files, which match every path.
    app.router.routes.insert(0, app.router.routes.pop())
    return app


def test_no_open_route_reaches_a_model(make_demo, monkeypatch):
    assert_no_open_route_reaches_a_model(make_demo())

    # The walk is sharp enough to catch a real route opened by mistake: Check
    # this chat, which asks the judge only for the sample that has no saved check.
    monkeypatch.setitem(ROUTES, ("POST", "/api/chats/{chat_id}/check"), OPEN)
    with pytest.raises(AssertionError, match="asks for a model"):
        assert_no_open_route_reaches_a_model(make_demo())


def test_a_new_model_route_with_no_place_fails_the_walk_and_needs_the_code(make_demo):
    provider = FakeProvider(fake_settings(), replies=[])
    demo = make_demo(provider=provider, builder=with_a_made_up_route)

    # The table has no place for it, so the contract test fails until someone decides.
    with pytest.raises(AssertionError, match="give each new route a place"):
        assert_every_route_has_a_place(demo.pages)
    # Until then it is behind the code, like every route the table doesn't name.
    client = visit(demo)
    refused(client.get("/api/made-up"), CODE_NEEDED)
    assert provider.requests == []


def test_a_model_route_opened_by_mistake_fails_the_walk_and_is_still_locked(make_demo, monkeypatch):
    provider = FakeProvider(fake_settings())
    demo = make_demo(provider=provider, builder=with_a_made_up_route)
    monkeypatch.setitem(ROUTES, ("GET", "/api/made-up"), OPEN)

    with pytest.raises(AssertionError, match="asks for a model"):
        assert_no_open_route_reaches_a_model(demo)
    # The visitor's provider turned the call away, so the model was never asked.
    assert provider.requests == []
    assert sum(visitor.provider.refused for visitor in demo.visitors.values()) == 1


# What is off.


def test_settings_spec_saves_and_the_seeded_sample_are_refused(make_demo):
    demo = make_demo()
    client = unlock(visit(demo))

    refused(client.get("/api/settings"), SETTINGS_OFF)
    refused(client.post("/api/settings", json={}), SETTINGS_OFF)
    refused(client.post("/api/settings/test", json={}), SETTINGS_OFF)
    refused(client.get("/api/settings/ollama"), SETTINGS_OFF)

    refused(client.post("/api/characters/harry/specs", json={}), SPEC_OFF)
    assert ok(client.get("/api/characters/harry/specs/latest"))["version"] == 1

    seeded = {"source": "sample", "character": "harry", "sample": "seeded"}
    refused(client.post("/api/imports/preview", json=seeded), SEEDED_OFF)
    refused(client.post("/api/imports", json=seeded), SEEDED_OFF)
    listed = next(sample for sample in ok(client.get("/api/samples")) if sample["id"] == "seeded")
    assert listed["available"] is False
    assert len(ok(client.get("/api/chats"))) == 2
    # The page that lists every route is off too.
    assert [client.get(path).status_code for path in ("/docs", "/redoc", "/openapi.json")] == [404, 404, 404]
    # None of it left a file behind, such as the one Settings would write.
    assert sorted(path.name for path in demo.folder.iterdir() if "visitor" not in path.name) == ["ledger.db", "template.db"]


# Limits.


def samples_still_work(client):
    cla, _ = samples(client)
    assert flags_of(client, cla)
    assert ok(client.get(f"/api/chats/{cla}/check"))["result"]["flags"]


def test_a_visitor_starts_two_live_chats_then_gets_the_card(make_demo):
    client = unlock(visit(make_demo()))
    ok(start(client), 201)
    ok(start(client, scenario="Free"), 201)

    refused(start(client), limit_message("runs", 2), 429)
    refused(start(client, scenario="Free"), limit_message("runs", 2), 429)
    state = ok(client.get("/api/demo/state"))
    assert state["limits"]["runs"] == {"used": 2, "limit": 2, "message": limit_message("runs", 2)}
    assert "2 live chats" in limit_message("runs", 2) and "still work" in limit_message("runs", 2)
    samples_still_work(client)


def test_checks_and_re_checks_each_have_their_own_limit(make_demo):
    client = unlock(visit(make_demo(workbench_demo_check_limit=1, workbench_demo_recheck_limit=1)))
    cla, gpt = samples(client)

    ok(client.post(f"/api/chats/{gpt}/check"))
    refused(client.post(f"/api/chats/{gpt}/check"), limit_message("checks", 1), 429)
    # A used-up check limit leaves the re-check alone.
    ok(client.post(f"/api/chats/{cla}/recheck", json={"question": None}))
    refused(client.post(f"/api/chats/{cla}/recheck", json={"question": None}), limit_message("rechecks", 1), 429)

    used = {kind: limit["used"] for kind, limit in ok(client.get("/api/demo/state"))["limits"].items()}
    assert used == {"runs": 0, "checks": 1, "rechecks": 1}
    assert "1 AI check," in limit_message("checks", 1) and "4 re-checks," in limit_message("rechecks", 4)
    samples_still_work(client)


def test_the_daily_cap_covers_every_visitor_together(make_demo):
    demo = make_demo(workbench_daily_call_cap=2)
    first, second = unlock(visit(demo)), unlock(visit(demo))
    runs = [ok(start(client), 201)["id"] for client in (first, second)]

    # One call each uses up the day.
    assert sse_events(first.post(f"/api/chats/{runs[0]}/next").text)[-1][0] == "done"
    assert sse_events(second.post(f"/api/chats/{runs[1]}/next").text)[-1][0] == "done"

    for client, run in ((first, runs[0]), (second, runs[1])):
        refused(client.post(f"/api/chats/{run}/next"), cap_message(2), 429)
        refused(client.post(f"/api/chats/{samples(client)[1]}/check"), cap_message(2), 429)
        state = ok(client.get("/api/demo/state"))
        assert state["calls_left"] is False and state["cap_message"] == cap_message(2)
        samples_still_work(client)
    # The shared count names no visitor and no chat.
    rows = query(demo.ledger, "SELECT session, transcript_id, turn, app_settings_id FROM model_calls")
    assert rows == [{"session": None, "transcript_id": None, "turn": None, "app_settings_id": None}] * 2
    assert ok(first.get("/api/run-options"))["used_today"] == 2


# Idle copies and the cap on copies.


def test_an_idle_copy_is_deleted_and_its_visitor_starts_fresh(make_demo):
    clock = Clock()
    demo = make_demo(clock=clock)
    client = unlock(visit(demo))
    cla, _ = samples(client)
    flag_id = flags_of(client, cla)[0]["id"]
    ok(client.post(f"/api/flags/{flag_id}/evidence"))
    ok(client.post(f"/api/flags/{flag_id}/agree"))
    copy = visitor_of(demo, client).database.path

    # Still there a minute short of two hours, and a request starts the two hours again.
    clock.now += 119 * 60
    assert ok(client.get("/api/demo/state"))["unlocked"] is True
    clock.now += 119 * 60
    assert TestClient(demo, base_url=SITE).get("/api/health").json()["visitors"] == 1
    assert copy.is_file()

    # Two idle hours later the next request to the demo, here the health check, deletes it.
    clock.now += 60
    assert TestClient(demo, base_url=SITE).get("/api/health").json()["visitors"] == 0
    assert not copy.exists()

    # The same browser gets a fresh copy: the samples, without its call, and locked again.
    assert next(flag for flag in flags_of(client, cla) if flag["id"] == flag_id)["call"] is None
    assert ok(client.get("/api/demo/state"))["unlocked"] is False


def test_past_the_cap_on_copies_a_visitor_sees_the_busy_page(make_demo):
    clock = Clock()
    demo = make_demo(clock=clock, workbench_demo_max_visitors=1)
    early = visit(demo)
    inside = visit(demo)
    samples(inside)

    # A new browser gets the busy page, and no cookie.
    late = TestClient(demo, base_url=SITE, headers={"Origin": SITE})
    page = late.get("/")
    assert page.status_code == 503 and BUSY in page.text and "set-cookie" not in page.headers
    assert QUICK_START in page.text
    # One that loaded the page before the last copy went is told the same.
    refused(early.get("/api/chats"), BUSY, 503)
    assert early.get("/").status_code == 503
    # The visitor who has a copy keeps working.
    assert inside.get("/").status_code == 200
    samples_still_work(inside)

    # When that copy has sat idle, the next visitor gets in.
    clock.now += 120 * 60
    assert len(ok(early.get("/api/chats"))) == 2


def test_a_restart_gives_a_returning_visitor_a_fresh_copy(make_demo):
    first = make_demo()
    client = unlock(visit(first))
    cla, _ = samples(client)
    flag_id = flags_of(client, cla)[0]["id"]
    ok(client.post(f"/api/flags/{flag_id}/evidence"))

    # The same folder and code, as after Render wakes the service. The cookie still counts.
    second = make_demo()
    back = TestClient(second, base_url=SITE, headers={"Origin": SITE}, cookies=dict(client.cookies))
    assert next(flag for flag in flags_of(back, cla) if flag["id"] == flag_id)["evidence_opened"] is False
    assert ok(back.get("/api/demo/state"))["unlocked"] is False
    assert len(second.visitors) == 1


# The cookie and the Origin check.


def test_the_visitor_cookie_is_set_with_the_page_and_locked_down(make_demo):
    demo = make_demo()
    client = TestClient(demo, base_url=SITE, headers={"Origin": SITE})

    # No cookie yet, so no copy is made for this request.
    refused(client.get("/api/chats"), NO_COOKIE)
    assert demo.visitors == {}

    page = client.get("/")
    cookie = page.headers["set-cookie"]
    assert cookie.startswith(f"{COOKIE}=")
    flags = {part.strip().lower() for part in cookie.split(";")[1:]}
    assert {"httponly", "secure", "samesite=lax", "path=/"} <= flags
    assert page.headers["cache-control"] == "no-cache"
    assert page.text.count('<script src="demo.js"></script>') == 1 and page.text.count('href="demo.css"') == 1
    # The page still loads the workbench's own scripts first.
    assert page.text.index('src="api.js"') < page.text.index('src="app.js"') < page.text.index('src="demo.js"')

    # A second load keeps the cookie, and a cookie the server didn't sign counts for nothing.
    assert "set-cookie" not in client.get("/").headers
    forged = TestClient(demo, base_url=SITE, cookies={COOKIE: "someone-else.0000"})
    refused(forged.get("/api/chats"), NO_COOKIE)
    assert demo.visitors == {}
    assert len(ok(client.get("/api/chats"))) == 2


def test_a_post_from_another_sites_page_is_refused(make_demo):
    demo = make_demo()
    client = visit(demo)
    cla, _ = samples(client)
    flag_id = flags_of(client, cla)[0]["id"]
    path = f"/api/flags/{flag_id}/evidence"

    refused(client.post(path, headers={"Origin": "https://another-site.example"}), WRONG_ORIGIN)
    refused(client.post(path, headers={"Origin": "null"}), WRONG_ORIGIN)
    refused(client.post("/api/demo/code", json={"code": DEMO_CODE}, headers={"Origin": "https://another-site.example"}), WRONG_ORIGIN)
    # No Origin at all is refused as well: a browser always sends one with a POST.
    bare = TestClient(demo, base_url=SITE, cookies=dict(client.cookies))
    refused(bare.post(path), WRONG_ORIGIN)
    assert next(flag for flag in flags_of(client, cla) if flag["id"] == flag_id)["evidence_opened"] is False
    assert ok(client.get("/api/demo/state"))["unlocked"] is False

    ok(client.post(path))
    assert next(flag for flag in flags_of(client, cla) if flag["id"] == flag_id)["evidence_opened"] is True


# Starting on a host.


@pytest.fixture
def hosted(monkeypatch, tmp_path):
    """The environment a host like Render gives the service: no app/.env, only variables."""

    def run(**variables):
        for name in Settings.model_fields:
            monkeypatch.delenv(name.upper(), raising=False)
        values = {
            "WORKBENCH_MODE": "demo",
            "WORKBENCH_HOST": "0.0.0.0",
            "PORT": "10000",
            "WORKBENCH_DB_PATH": str(tmp_path / "data" / "workbench.db"),
            "WORKBENCH_DEMO_CODE": DEMO_CODE,
            "GEMINI_API_KEY": "made-up-key-for-tests",
            **variables,
        }
        for name, value in values.items():
            monkeypatch.setenv(name, value)
        missing = tmp_path / "no-such.env"
        monkeypatch.setattr(entry, "load_settings", lambda: load_settings(env_file=missing))
        served = {}
        monkeypatch.setattr(entry.uvicorn, "run", lambda app, host, port: served.update(app=app, host=host, port=port))
        entry.main()
        assert not missing.exists()
        return served

    return run


def test_demo_mode_starts_with_no_env_file_on_the_hosts_port(hosted, capsys):
    served = hosted()
    assert isinstance(served["app"], Demo)
    assert (served["host"], served["port"]) == ("0.0.0.0", 10000)

    client = visit(served["app"])
    health = client.get("/api/health")
    assert health.json() == {"status": "ok", "mode": "demo", "provider": "gemini", "key_set": True, "visitors": 0}
    assert "made-up-key-for-tests" not in health.text and DEMO_CODE not in health.text
    cla, gpt = samples(client)
    assert flags_of(client, cla) and flags_of(client, gpt)
    printed = "".join(capsys.readouterr())
    assert DEMO_CODE not in printed and "made-up-key-for-tests" not in printed


def test_demo_mode_refuses_to_start_with_a_short_code(hosted, capsys):
    with pytest.raises(SystemExit) as stopped:
        hosted(WORKBENCH_DEMO_CODE="tiny-code")
    assert stopped.value.code == 1
    err = capsys.readouterr().err
    assert err.count("\n") == 1 and "WORKBENCH_DEMO_CODE" in err and "at least 12 characters" in err
    assert "tiny-code" not in err and "Traceback" not in err


def test_render_yaml_parses_and_holds_no_secret(tmp_path):
    text = RENDER_YAML.read_text(encoding="utf-8")
    blueprint = read_plain_yaml(text)
    assert list(blueprint) == ["services"] and len(blueprint["services"]) == 1
    service = blueprint["services"][0]

    assert (service["type"], service["runtime"], service["plan"]) == ("web", "python", "free")
    assert service["region"] in ("oregon", "ohio", "virginia")
    assert service["branch"] == "main"
    # Only after the GitHub tests pass, since teammates push straight to main.
    assert service["autoDeployTrigger"] == "checksPass" and "autoDeploy" not in service
    assert service["healthCheckPath"] == "/api/health"
    assert "app/requirements.txt" in service["buildCommand"]
    assert service["startCommand"].endswith("python -m workbench.main")

    variables = {entry["key"]: entry for entry in service["envVars"]}
    assert len(variables) == len(service["envVars"])
    # Each secret is marked so Render asks for it, and has no value in the file.
    secrets = {name.upper() for name in KEY_SETTINGS} - {"OPENAI_COMPATIBLE_API_KEY"}
    for name in secrets:
        assert variables[name] == {"key": name, "sync": False}, name
    for name, variable in variables.items():
        assert name in secrets or isinstance(variable.get("value"), str), f"{name} needs a quoted value"
    # Render's own Python setting needs all three parts, and the tests run on 3.11 and 3.12.
    assert re.fullmatch(r"3\.1[12]\.\d+", variables.pop("PYTHON_VERSION")["value"])

    # Every other name is a setting, and the values make settings the demo starts with.
    values = {name.lower(): variable["value"] for name, variable in variables.items() if name not in secrets}
    assert values["workbench_mode"] == "demo" and values["workbench_host"] == "0.0.0.0"
    settings = settings_for(tmp_path, workbench_provider="gemini", workbench_demo_code=DEMO_CODE, **values)
    assert (settings.workbench_demo_run_limit, settings.workbench_demo_check_limit, settings.workbench_demo_recheck_limit) == (2, 4, 4)
    assert settings.workbench_demo_idle_minutes == 120


def keep_warm_script():
    """The bash step of the keep-warm workflow, as the lines under its run key."""
    lines = KEEP_WARM.read_text(encoding="utf-8").splitlines()
    start = next(index for index, line in enumerate(lines) if line.strip() == "run: |")
    indent = len(lines[start]) - len(lines[start].lstrip())
    body = []
    for line in lines[start + 1 :]:
        if line.strip() and len(line) - len(line.lstrip()) <= indent:
            break
        body.append(line)
    return "\n".join(body)


def test_keep_warm_runs_every_ten_minutes_and_by_hand_and_holds_no_secret():
    text = KEEP_WARM.read_text(encoding="utf-8")
    assert 'cron: "*/10 * * * *"' in text and "workflow_dispatch:" in text
    # The address comes from a repository variable, so the job is off until it is set.
    assert "${{ vars.DEMO_HEALTH_URL }}" in text
    assert "secrets." not in text and "onrender.com/" not in keep_warm_script()
    assert "--max-time 90" in keep_warm_script()
    assert text.count("run: |") == 1


@needs_bash
@pytest.mark.parametrize(
    ("address", "curl_exit", "said"),
    [
        ("", 0, "keep-warm is off"),
        ("https://demo.test/api/health", 0, ""),
        # 28 is curl's exit code for a timeout, as when the demo is asleep.
        ("https://demo.test/api/health", 28, "may be waking up"),
    ],
)
def test_keep_warm_always_finishes_green(tmp_path, address, curl_exit, said):
    fake_bin = tmp_path / "bin"
    fake_bin.mkdir()
    asked = tmp_path / "asked.txt"
    curl = fake_bin / "curl"
    curl.write_text(f'#!/bin/sh\necho "$@" >> "{asked}"\nexit {curl_exit}\n')
    curl.chmod(0o755)
    result = subprocess.run(
        [shutil.which("bash") or "/bin/bash", "-e", "-c", keep_warm_script()],
        env={"PATH": os.pathsep.join([str(fake_bin), "/usr/bin", "/bin"]), "DEMO_HEALTH_URL": address},
        capture_output=True,
        text=True,
        timeout=30,
    )
    assert result.returncode == 0, result.stderr
    assert said in result.stdout
    # With no address, nothing is asked.
    assert asked.exists() == bool(address)
    if address:
        assert address in asked.read_text() and "--max-time 90" in asked.read_text()


def test_check_link_passes_on_the_demo(make_demo):
    spec = importlib.util.spec_from_file_location("check_link", APP_DIR / "scripts" / "check_link.py")
    check_link = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(check_link)
    demo = make_demo(snapshot=SNAPSHOT_FILE, workbench_provider="gemini", gemini_api_key="made-up-key-for-tests")

    def fetch(method, path, headers, body=None):
        # A new client each time, so only the headers the script sends go along.
        response = TestClient(demo, base_url=SITE).request(method, path, headers=headers, content=body)
        return response.status_code, {name.lower(): value for name, value in response.headers.items()}, response.text

    results = check_link.check(fetch, SITE)
    assert len(results) >= 10
    assert [line for passed, line in results if not passed] == []
    assert demo.provider.requests == []
    # A demo that didn't get its key or its mode fails the check that names it.
    local = create_app(settings_for(demo.folder / "local"), provider=FakeProvider(fake_settings()))

    def fetch_local(method, path, headers, body=None):
        response = TestClient(local).request(method, path, headers=headers, content=body)
        return response.status_code, {name.lower(): value for name, value in response.headers.items()}, response.text

    assert any(not passed and "demo mode" in line for passed, line in check_link.check(fetch_local, SITE))


# The page's demo script.


def js_constants(text):
    """The string constants of demo.js, by name, with a string split over two lines joined."""
    return {name: value for name, value in re.findall(r'const ([A-Z_]+) =\s*"((?:[^"\\]|\\.)*)";', text)}


def test_demo_js_talks_only_to_the_demo_routes():
    text = DEMO_JS.read_text(encoding="utf-8")
    assert set(re.findall(r'"(/api/[^"]*)"', text)) == {"/api/demo/state", "/api/demo/code"}
    assert "/api/" not in re.sub(r'"/api/demo/(state|code)"', "", re.sub(r"(?s)/\*.*?\*/", "", text))
    assert text.count("fetch(") == 1
    assert "WorkbenchApi" not in text


def test_demo_js_says_what_the_server_says(make_demo):
    constants = js_constants(DEMO_JS.read_text(encoding="utf-8"))
    state = ok(visit(make_demo()).get("/api/demo/state"))
    banner = (
        "Public demo. Don't type anything personal: text sent to the AI goes to Google's free tier, "
        "which may use it to improve its products. Your copy of the demo is wiped after 2 hours."
    )
    assert state["banner"] == constants["BANNER"] == banner
    assert BANNER.format(time="45 minutes").endswith("wiped after 45 minutes.")
    assert f"{constants['CODE_HEAD']}. {constants['CODE_TEXT']}" == CODE_NEEDED == state["code_needed"]
    assert CODE_NEEDED == (
        "Live AI needs a demo code. Course staff: it is in our Canvas submission. "
        "Anyone can also run the workbench on their own computer in about 15 minutes."
    )
    assert constants["SPEC_OFF"] == SPEC_OFF == state["spec_off"]
    assert constants["QUICK_START"] == QUICK_START == state["quick_start"]
    # The link lands on the README's quick start.
    assert QUICK_START.endswith("#how-to-run-the-app")
    assert "## How to run the app" in (REPO_DIR / "README.md").read_text(encoding="utf-8")
    assert set(state) == {"unlocked", "limits", "calls_left", "cap_message", "banner", "code_needed", "spec_off", "quick_start"}


def test_demo_js_steps_in_front_of_buttons_app_js_still_has():
    demo_js = DEMO_JS.read_text(encoding="utf-8")
    app_js = (STATIC_DIR / "app.js").read_text(encoding="utf-8")
    handled = set(re.findall(r'actions\["([a-z-]+)"\]', app_js))
    blocks = re.findall(r"const (GATED|OFF) = \{(.*?)\};", demo_js, re.S)
    named = {name: set(re.findall(r'"([a-z-]+)":', body)) for name, body in blocks}
    assert named["GATED"] and named["OFF"]
    # A button app.js renamed would slip past the card, though never past the server.
    assert named["GATED"] | named["OFF"] <= handled
    # What the user's own text or a model call goes through, each behind the card.
    assert named["GATED"] >= {"start-run", "run-all", "new-free-chat", "send-message", "check-chat", "recheck", "save-override", "confirm-import"}
    assert named["OFF"] == {"edit-spec", "add-setting"}
    # Settings and Run All Test Cases are hidden, and the tour's Settings step is reworded by its title.
    styles = (STATIC_DIR / "demo.css").read_text(encoding="utf-8")
    assert '[data-action="open-settings"]' in styles and '[data-action="run-all"]' in styles
    title = js_constants(demo_js)["TOUR_SETTINGS_TITLE"]
    assert f'title: "{title}"' in app_js and 'anchor: "settings"' in app_js
    assert 'data-tour="settings"' in (STATIC_DIR / "index.html").read_text(encoding="utf-8")


def test_the_new_files_are_plain_ascii():
    files = [
        APP_DIR / "workbench" / "demo.py",
        APP_DIR / "scripts" / "check_link.py",
        DEMO_JS,
        STATIC_DIR / "demo.css",
        RENDER_YAML,
        KEEP_WARM,
        REPO_DIR / "docs" / "deployment.md",
        REPO_DIR / "tests" / "test_demo_mode.py",
    ]
    for path in files:
        odd = sorted({char for char in path.read_text(encoding="utf-8") if ord(char) > 126 or (ord(char) < 32 and char != "\n")})
        assert odd == [], f"{path.name} has {odd}"
