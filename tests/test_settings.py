"""M6.5 Settings tests: the dialog's routes answer only this computer, a key
goes into app/.env and nowhere else, Test says what happened and what to do
next in plain words, and a saved change applies to the next call with no
restart, logged as a dated row. All with the fake model and no network."""

import asyncio
import json
import logging
import re
import sqlite3

import httpx2
import pytest
from fastapi.testclient import TestClient

from conftest import APP_DIR, SESSION, FakeTime, default_model, fake_settings, query, settings_for, sse_events
from workbench.config import Settings, load_prompts, save_env
from workbench.main import create_app
from workbench.providers import FakeProvider, FakeReply, OpenAIProvider, ProviderError, build
from workbench.schemas import BASE_URL

PROMPTS = load_prompts()
MODELS = PROMPTS.models
PRESETS = PROMPTS.presets
# A made-up key in Gemini's format. No response, row, log, or request may hold it.
KEY = "AIzaTEST-made-up-key-for-tests-0123456789wXyZ"
OTHER = "https://service.example.test/v1"


@pytest.fixture(autouse=True)
def clean_environment(monkeypatch):
    """A setting the shell sets, like an exported GEMINI_API_KEY, would lock its field in Settings."""
    for name in Settings.model_fields:
        monkeypatch.delenv(name.upper(), raising=False)


def current(client):
    response = client.get("/api/settings")
    assert response.status_code == 200, response.text
    return response.json()


def choice(view, provider):
    """The provider and the models a fresh choice of it starts from, as the dialog sends them."""
    menus = next(menu for menu in view["providers"] if menu["provider"] == provider)
    return {"provider": provider, "character_model": menus["default_character"], "judge_model": menus["default_judge"]}


def draft_from(view, **changes):
    """What the dialog sends: the settings on screen, with the creator's changes."""
    values = {
        "provider": view["provider"],
        "base_url": view["base_url"],
        "api_key": None,
        "character_model": view["character_model"],
        "judge_model": view["judge_model"],
        "calls_per_minute": view["calls_per_minute"],
        "daily_call_cap": view["daily_call_cap"],
        "session_run_limit": view["session_run_limit"],
        "session_judge_limit": view["session_judge_limit"],
        "simulate_busy": view["simulate_busy"],
    }
    return {**values, **changes}


def compatible(url=OTHER):
    return {"provider": "openai_compatible", "base_url": url, "character_model": "test-model-a", "judge_model": "test-model-b"}


def preset(preset_id):
    return next(item for item in PRESETS.presets if item.id == preset_id)


def start_run(client, model=None):
    model = model or client.get("/api/run-options").json()["default_model"]
    response = client.post("/api/chats", json={"character": "harry", "scenario": "F2", "model": model})
    assert response.status_code == 201, response.text
    return response.json()


def import_sample(client, name="cla-f2"):
    response = client.post("/api/imports", json={"source": "sample", "character": "harry", "sample": name})
    assert response.status_code in (200, 201), response.text
    return response.json()["id"]


# Only this computer.


@pytest.mark.parametrize(
    ("address", "host", "origin", "session"),
    [
        ("10.0.0.7", "127.0.0.1:8492", None, SESSION),
        ("127.0.0.1", "evil.example:8492", None, SESSION),
        ("127.0.0.1", "127.0.0.1:8492", "http://evil.example", SESSION),
        ("127.0.0.1", "127.0.0.1:8492", None, None),
    ],
    ids=["another-computer", "another-host-name", "another-site", "no-session-header"],
)
def test_settings_answer_only_this_computer(make_client, env_file, address, host, origin, session):
    app = make_client(local=True).app
    client = TestClient(app, base_url=f"http://{host}", client=(address, 50000))
    headers = {**({"Origin": origin} if origin else {}), **({"X-Workbench-Session": session} if session else {})}
    view_draft = {
        **compatible(),
        "api_key": KEY,
        "calls_per_minute": 5,
        "daily_call_cap": 50,
        "session_run_limit": 5,
        "session_judge_limit": 5,
    }

    changes = [
        client.post("/api/settings", json=view_draft, headers=headers),
        client.post("/api/settings/test", json=view_draft, headers=headers),
    ]
    reads = [client.get("/api/settings", headers=headers), client.get("/api/settings/ollama", headers=headers)]
    # Without the session header, only a change is refused: reading needs no header.
    refused = changes if session is None else changes + reads
    if session is None:
        assert [response.status_code for response in reads] == [200, 200]
    for response in refused:
        assert response.status_code == 403
        assert response.json()["detail"] == "Settings work only in the workbench on the computer running it, at http://127.0.0.1:8492."
    assert not env_file.exists()
    assert [row["source"] for row in query(client, "SELECT source FROM app_settings")] == ["startup"]
    assert query(client, "SELECT * FROM model_calls") == []


# The key.


def test_a_key_goes_into_app_env_and_nowhere_else(make_client, env_file, caplog, capsys):
    caplog.set_level(logging.DEBUG)
    provider = FakeProvider(fake_settings())
    client = make_client(provider=provider, local=True)
    view = current(client)
    gemini = choice(view, "gemini")
    wrong = KEY.replace("TEST", "WRONG")

    responses = [client.post("/api/settings/test", json=draft_from(view, **gemini, api_key=KEY))]
    assert responses[-1].json()["ok"] is True
    responses.append(client.post("/api/settings", json=draft_from(view, **gemini, api_key=KEY)))
    saved = responses[-1].json()
    assert saved["keys"]["gemini"] == {"saved": True, "last4": KEY[-4:], "locked": False}
    # A wrong key that the service refuses, then a run on the saved one.
    provider.replies.append(FakeReply(error=ProviderError("auth", "The model service didn't accept the key.", "HTTP 401: key refused")))
    responses.append(client.post("/api/settings/test", json=draft_from(saved, api_key=wrong)))
    assert responses[-1].json()["message"] == "Gemini didn't accept this key."
    chat = start_run(client)
    responses.append(client.post(f"/api/chats/{chat['id']}/next"))
    responses += [client.get("/api/settings"), client.get("/api/run-options"), client.get("/api/health")]

    secrets = (KEY, KEY[:-4], wrong, wrong[:-4])
    for response in responses:
        assert response.status_code == 200, response.text
        assert not any(secret in response.text for secret in secrets)
    with sqlite3.connect(client.app.state.database.path) as conn:
        dump = "\n".join(conn.iterdump())
    assert not any(secret in dump for secret in secrets)
    output = capsys.readouterr()
    assert not any(secret in text for secret in secrets for text in (caplog.text, output.out, output.err))
    assert not any(secret in json.dumps(request) for secret in secrets for request in provider.requests)
    # app/.env holds the saved key, and only its owner may read the file.
    assert f"GEMINI_API_KEY={KEY}\n" in env_file.read_text(encoding="utf-8")
    assert wrong not in env_file.read_text(encoding="utf-8")
    assert env_file.stat().st_mode & 0o777 == 0o600


def test_a_refused_key_never_reaches_the_log():
    # Some services quote the key they refused. Only the status is kept.
    async def refuse(request):
        return httpx2.Response(401, json={"error": {"message": f"Incorrect API key provided: {KEY}."}})

    client = httpx2.AsyncClient(transport=httpx2.MockTransport(refuse))
    provider = OpenAIProvider(name="openai_compatible", base_url=OTHER, api_key=KEY, timeout=5, http_client=client)

    async def run():
        try:
            async for _ in provider.stream("test-model-a", [{"role": "user", "content": "Hi."}], None, 50):
                pass
        finally:
            await provider.aclose()

    with pytest.raises(ProviderError) as caught:
        asyncio.run(run())
    assert (caught.value.kind, caught.value.detail) == ("auth", "HTTP 401: key refused")
    assert KEY not in caught.value.message and KEY[-4:] not in caught.value.detail


def test_a_key_with_a_space_is_refused_before_anything_is_written(make_client, env_file):
    client = make_client(local=True)
    view = current(client)
    response = client.post("/api/settings", json=draft_from(view, **choice(view, "gemini"), api_key="AIza two words"))
    assert response.status_code == 422
    assert response.json() == {
        "detail": "That key has a space or a character keys don't use. Copy the key again and paste it.",
        "field": "api_key",
    }
    assert not env_file.exists()


def test_app_env_keeps_its_other_lines_and_refuses_unsafe_values(tmp_path):
    path = tmp_path / "app.env"
    before = "# My notes\nWORKBENCH_PORT=8493\nGEMINI_API_KEY=old-key-1234\n"
    path.write_text(before, encoding="utf-8")
    # A path given as text works too, as a launcher reading it from the environment passes it.
    save_env({"GEMINI_API_KEY": "new-key-5678", "WORKBENCH_CALLS_PER_MINUTE": "5"}, str(path))
    after = "# My notes\nWORKBENCH_PORT=8493\nGEMINI_API_KEY=new-key-5678\nWORKBENCH_CALLS_PER_MINUTE=5\n"
    assert path.read_text(encoding="utf-8") == after
    assert path.stat().st_mode & 0o777 == 0o600

    # A line break would start a new setting, so it never gets in, and the error never repeats the value.
    for name, value in [
        ("GEMINI_API_KEY", "zz-value\nWORKBENCH_HOST=0.0.0.0"),
        ("GEMINI_API_KEY", "zz two words"),
        ("GEMINI_API_KEY", "zz#comment"),
        ("GEMINI_API_KEY", "'zz-quoted'"),
        ("NOT_A_SETTING", "zz-value"),
    ]:
        with pytest.raises(ValueError) as caught:
            save_env({name: value}, path)
        assert "zz" not in str(caught.value)
    assert path.read_text(encoding="utf-8") == after


# Test, in plain words.


def test_test_tries_the_settings_as_typed_and_saves_none_of_them(make_client, env_file):
    provider = FakeProvider(fake_settings())
    client = make_client(provider=provider, local=True)
    view = current(client)

    same = client.post("/api/settings/test", json=draft_from(view)).json()
    assert same["ok"] is True and same["message"].startswith("The fake model answered in ")
    assert same["next"] == "It's the model in use now."
    gemini = choice(view, "gemini")
    tried = client.post("/api/settings/test", json=draft_from(view, **gemini, api_key=KEY)).json()
    label = MODELS.models[gemini["character_model"]].label
    assert tried["ok"] is True and tried["message"].startswith(f"Connected. {label} answered in ")
    assert tried["next"] == "Press Save to use these settings."

    # Nothing was saved, but each call names the settings it tried.
    assert current(client)["provider"] == "fake"
    assert not env_file.exists()
    rows = query(client, "SELECT id, source, provider, changed, key_set FROM app_settings ORDER BY id")
    assert [(row["source"], row["provider"], row["key_set"]) for row in rows] == [
        ("startup", "fake", 0),
        ("connection_test", "fake", 0),
        ("connection_test", "gemini", 1),
    ]
    assert rows[2]["changed"].split(", ")[-1] == "key" and "provider" in rows[2]["changed"]
    calls = query(client, "SELECT role, model_asked, prompt_version, app_settings_id, attempt FROM model_calls ORDER BY id")
    assert [(call["role"], call["prompt_version"], call["attempt"]) for call in calls] == [
        ("connection_test", "connection_test.v1", 1),
        ("connection_test", "connection_test.v1", 1),
    ]
    assert [call["app_settings_id"] for call in calls] == [rows[1]["id"], rows[2]["id"]]
    assert [call["model_asked"] for call in calls] == [view["character_model"], gemini["character_model"]]
    # The test message is the versioned prompt, alone.
    assert provider.requests[-1]["messages"] == [{"role": "user", "content": PROMPTS.connection_test_template.strip()}]


FAILURES = [
    ("gemini-no-key", None, "There's no Gemini key yet.", "Get a free key at aistudio.google.com"),
    ("gemini", ProviderError("auth", "x", "HTTP 401: key refused"), "Gemini didn't accept this key.", "Copy the key again"),
    ("gemini", ProviderError("rate_limited", "x", "HTTP 429: busy"), "Gemini says its free limit was reached.", "Wait a minute"),
    ("ollama", ProviderError("connection", "x", "connection error"), "Ollama isn't running.", "ollama serve"),
    ("ollama", ProviderError("not_found", "x", "HTTP 404: no"), "Ollama doesn't have", "ollama pull"),
    ("groq", ProviderError("not_found", "x", "HTTP 404: no"), "Groq doesn't know the model test-model-a.", "model ID"),
    ("other", ProviderError("connection", "x", "connection error"), f"Couldn't reach {OTHER}.", "internet connection"),
    ("lmstudio", ProviderError("connection", "x", "connection error"), "Couldn't reach", "running on this computer"),
    ("gemini", ProviderError("server", "x", "HTTP 503: down"), "Gemini had a problem on its side.", "in a minute"),
]


@pytest.mark.parametrize(("case", "error", "message", "next_words"), FAILURES, ids=[f"{case}-{index}" for index, (case, *_) in enumerate(FAILURES)])
def test_test_says_what_went_wrong_and_what_to_do_next(make_client, case, error, message, next_words):
    provider = FakeProvider(fake_settings(), replies=[FakeReply(error=error)] if error else [])
    client = make_client(provider=provider, local=True)
    view = current(client)
    picked = {
        "gemini-no-key": choice(view, "gemini"),
        "gemini": {**choice(view, "gemini"), "api_key": KEY},
        "ollama": choice(view, "ollama"),
        "groq": compatible(preset("groq").base_url),
        "other": compatible(),
        "lmstudio": compatible(preset("lmstudio").base_url),
    }[case]
    result = client.post("/api/settings/test", json=draft_from(view, **picked)).json()
    assert result["ok"] is False
    assert result["message"].startswith(message)
    assert next_words in result["next"]
    # One try at most: no retry, no fallback model, and no call at all without a key.
    calls = query(client, "SELECT role FROM model_calls")
    assert calls == ([] if error is None else [{"role": "connection_test"}])


# Changes apply to the next call, with no restart.


def test_switching_the_judge_changes_the_next_check(make_client, env_file):
    client = make_client(local=True)
    view = current(client)
    harry = view["character_model"]
    assert view["judge_model"] != harry

    saved = client.post("/api/settings", json=draft_from(view, judge_model=harry)).json()
    assert saved["judge_model"] == harry
    check = client.post(f"/api/chats/{import_sample(client)}/check")
    assert check.status_code == 200, check.text
    [call] = query(client, "SELECT model_asked, app_settings_id FROM model_calls WHERE role = 'judge'")
    [row] = query(client, "SELECT id, source, session, changed, judge_model, saved_at FROM app_settings WHERE source = 'settings'")
    assert call == {"model_asked": harry, "app_settings_id": row["id"]}
    assert (row["session"], row["changed"], row["judge_model"]) == (SESSION, "judge_model", harry)
    assert row["saved_at"].endswith("Z")
    # A model change writes both models, so the pair holds after a restart.
    text = env_file.read_text(encoding="utf-8")
    assert f"WORKBENCH_JUDGE_MODEL={harry}\n" in text and f"WORKBENCH_CHARACTER_MODEL={harry}\n" in text


def test_switching_harrys_model_changes_the_next_run(make_client):
    provider = FakeProvider(fake_settings())
    client = make_client(provider=provider, local=True, workbench_provider="ollama")
    view = current(client)
    installed = "llama3.2:3b"

    saved = client.post("/api/settings", json=draft_from(view, character_model=installed)).json()
    assert saved["character_model"] == installed
    options = client.get("/api/run-options").json()
    assert options["default_model"] == installed
    assert {"id": installed, "label": installed} in options["models"]
    chat = start_run(client)
    assert sse_events(client.post(f"/api/chats/{chat['id']}/next").text)[-1][0] == "done"
    # A model the models file doesn't list gets its [unlisted] settings: no reasoning effort, no price.
    request = provider.requests[-1]
    assert (request["model"], request["reasoning_effort"], request["max_tokens"]) == (installed, None, MODELS.unlisted.max_tokens)
    [call] = query(client, "SELECT model_asked, reasoning_effort, est_cost_usd FROM model_calls WHERE role = 'character'")
    assert call == {"model_asked": installed, "reasoning_effort": None, "est_cost_usd": None}


def test_a_chat_keeps_its_model_after_the_provider_changes(make_client):
    client = make_client(local=True)
    chat = start_run(client)
    assert sse_events(client.post(f"/api/chats/{chat['id']}/next").text)[-1][0] == "done"
    view = current(client)
    assert client.post("/api/settings", json=draft_from(view, **choice(view, "ollama"))).status_code == 200

    response = client.post(f"/api/chats/{chat['id']}/next")
    assert response.status_code == 409
    assert "Switch back in Settings" in response.json()["detail"]


def test_connect_an_ai_takes_a_key_with_no_restart(tmp_path, env_file):
    time = FakeTime()
    first_run = OpenAIProvider(name="gemini", base_url="https://gemini.example.test/v1/", api_key="", timeout=5)
    connected = FakeProvider(fake_settings())
    settings = settings_for(tmp_path, workbench_provider="gemini", gemini_api_key="")
    app = create_app(settings, provider=first_run, build_provider=lambda _: connected, env_file=env_file, clock=time.clock, sleep=time.sleep)
    client = TestClient(app, base_url="http://127.0.0.1:8492", client=("127.0.0.1", 50000), headers={"X-Workbench-Session": SESSION})
    assert client.get("/api/run-options").json()["key_set"] is False

    view = current(client)
    assert view["keys"]["gemini"] == {"saved": False, "last4": None, "locked": False}
    saved = client.post("/api/settings", json=draft_from(view, api_key=KEY)).json()
    assert saved["keys"]["gemini"]["saved"] is True
    assert client.get("/api/run-options").json()["key_set"] is True
    assert client.get("/api/health").json()["key_set"] is True
    assert query(client, "SELECT changed FROM app_settings WHERE source = 'settings'") == [{"changed": "key_set, key"}]


def test_limits_stay_within_safe_bounds(make_client, env_file):
    client = make_client(local=True)
    view = current(client)
    most, cap = view["max_calls_per_minute"], view["max_daily_call_cap"]
    assert (most, cap) == (MODELS.limits.calls_per_minute, MODELS.limits.daily_call_cap)

    for changes, field, detail in [
        ({"calls_per_minute": most + 1}, "calls_per_minute", f"Calls per minute can be 1 to {most}. Gemini's free tier allows {most}."),
        ({"calls_per_minute": 0}, "calls_per_minute", f"Calls per minute can be 1 to {most}. Gemini's free tier allows {most}."),
        ({"daily_call_cap": cap + 1}, "daily_call_cap", f"The daily cap can be 1 to {cap}, Google's daily limit for each model."),
    ]:
        response = client.post("/api/settings", json=draft_from(view, **changes))
        assert response.status_code == 422
        assert response.json() == {"detail": detail, "field": field}
    assert not env_file.exists()

    saved = client.post("/api/settings", json=draft_from(view, calls_per_minute=5, daily_call_cap=40))
    assert saved.status_code == 200
    limiter = client.app.state.runtime.gateway.limiter
    assert (limiter.interval, limiter.daily_cap) == (12.0, 40)
    options = client.get("/api/run-options").json()
    assert (options["calls_per_minute"], options["daily_cap"]) == (5, 40)
    text = env_file.read_text(encoding="utf-8")
    assert "WORKBENCH_CALLS_PER_MINUTE=5\n" in text and "WORKBENCH_DAILY_CALL_CAP=40\n" in text
    # The models were defaults and didn't change, so app/.env doesn't pin them.
    assert "MODEL" not in text


def test_the_busy_switch_applies_at_once_and_a_restart_turns_it_off(make_client, env_file):
    provider = FakeProvider(fake_settings())
    client = make_client(provider=provider, local=True)
    saved = client.post("/api/settings", json=draft_from(current(client), simulate_busy=True)).json()
    assert (saved["simulate_busy"], saved["force_mode"]) == (True, "primary")
    assert not env_file.exists()

    chat = start_run(client)
    name, done = sse_events(client.post(f"/api/chats/{chat['id']}/next").text)[-1]
    assert name == "done"
    model_id = default_model()
    assert (done["message"]["model"], done["message"]["fallback"]) == (MODELS.fallback_for(model_id), True)
    calls = query(client, "SELECT forced, fallback FROM model_calls WHERE role = 'character' ORDER BY id")
    assert calls[-1] == {"forced": 0, "fallback": 1} and all(call["forced"] for call in calls[:-1])

    restarted = make_client(provider=provider, local=True)
    assert current(restarted)["simulate_busy"] is False
    row = query(restarted, "SELECT source, changed, force_model_error FROM app_settings ORDER BY id DESC LIMIT 1")[0]
    assert row == {"source": "startup", "changed": "force_model_error", "force_model_error": "off"}


def test_each_change_is_a_dated_row(make_client):
    client = make_client(local=True)
    assert query(client, "SELECT source, changed FROM app_settings") == [{"source": "startup", "changed": ""}]
    # A plain restart adds no row.
    make_client(local=True)
    assert len(query(client, "SELECT id FROM app_settings")) == 1

    client.post("/api/settings", json=draft_from(current(client), calls_per_minute=10))
    client.post("/api/settings", json=draft_from(current(client), daily_call_cap=100))
    # Saving the settings as they are changes nothing and adds no row.
    client.post("/api/settings", json=draft_from(current(client)))
    rows = query(client, "SELECT source, session, changed, calls_per_minute, daily_call_cap, saved_at FROM app_settings ORDER BY id")
    assert [(row["source"], row["session"], row["changed"]) for row in rows] == [
        ("startup", None, ""),
        ("settings", SESSION, "calls_per_minute"),
        ("settings", SESSION, "daily_call_cap"),
    ]
    assert [(row["calls_per_minute"], row["daily_call_cap"]) for row in rows[1:]] == [(10, 200), (10, 100)]
    assert rows[1]["saved_at"] <= rows[2]["saved_at"]
    assert current(client)["saved_at"] == rows[2]["saved_at"]


def test_a_setting_the_shell_sets_is_locked(make_client, env_file, monkeypatch):
    client = make_client(local=True)
    monkeypatch.setenv("WORKBENCH_CALLS_PER_MINUTE", "15")
    monkeypatch.setenv("GEMINI_API_KEY", "set-in-the-shell")
    view = current(client)
    assert view["locked"] == ["GEMINI_API_KEY", "WORKBENCH_CALLS_PER_MINUTE"]
    assert view["keys"]["gemini"]["locked"] is True

    response = client.post("/api/settings", json=draft_from(view, calls_per_minute=5))
    assert response.status_code == 409
    assert response.json()["detail"].startswith("WORKBENCH_CALLS_PER_MINUTE is set in the shell that started the server")
    assert not env_file.exists()
    # Fields the shell doesn't set still save.
    assert client.post("/api/settings", json=draft_from(view, daily_call_cap=50)).status_code == 200


def test_saving_waits_until_a_reply_or_check_ends(make_client, env_file):
    client = make_client(local=True)
    client.app.state.runtime.running[1] = object()
    response = client.post("/api/settings", json=draft_from(current(client), calls_per_minute=5))
    client.app.state.runtime.running.clear()
    assert response.status_code == 409
    assert response.json()["detail"] == "A reply or a check is running. Save when it ends, or press Stop first."
    assert not env_file.exists()


# The session limits, which Settings changes too.


def test_raising_the_session_run_limit_takes_effect_at_once(make_client, env_file):
    client = make_client(local=True, workbench_session_run_limit=1)
    start_run(client)
    refused = client.post("/api/chats", json={"character": "harry", "scenario": "F2", "model": default_model()})
    assert refused.status_code == 429
    assert refused.json()["detail"] == (
        "This browser session has started 1 run, the most one session may start. "
        "To allow more, raise the session run limit in Settings."
    )

    saved = client.post("/api/settings", json=draft_from(current(client), session_run_limit=2)).json()
    assert saved["session_run_limit"] == 2
    # No restart: the same session starts again, and the Run screen knows the new limit.
    start_run(client)
    assert client.get("/api/run-options").json()["session_run_limit"] == 2
    assert query(client, "SELECT changed, session_run_limit FROM app_settings WHERE source = 'settings'") == [
        {"changed": "session_run_limit", "session_run_limit": 2}
    ]
    assert "WORKBENCH_SESSION_RUN_LIMIT=2\n" in env_file.read_text(encoding="utf-8")


def test_raising_the_session_judge_limit_takes_effect_at_once(make_client):
    client = make_client(local=True, workbench_session_judge_limit=1)
    first = client.post(f"/api/chats/{import_sample(client)}/check").json()
    assert first["judge"]["status"] == "ok"
    second = import_sample(client, "gpt-f2")
    limited = client.post(f"/api/chats/{second}/check").json()
    assert limited["judge"]["status"] == "failed"
    assert limited["judge"]["note"].endswith("To allow more, raise the session judge limit in Settings.")

    assert client.post("/api/settings", json=draft_from(current(client), session_judge_limit=3)).status_code == 200
    again = client.post(f"/api/chats/{second}/check").json()
    assert again["judge"]["status"] == "ok"
    assert len(query(client, "SELECT id FROM model_calls WHERE role = 'judge'")) == 2


@pytest.mark.parametrize(
    ("changes", "field", "most"),
    [
        ({"session_run_limit": 0}, "session_run_limit", 200),
        ({"session_judge_limit": 201}, "session_judge_limit", 200),
        # The same save's daily cap bounds them: a lower cap needs lower session limits.
        ({"daily_call_cap": 5}, "session_run_limit", 5),
        ({"daily_call_cap": 15, "session_run_limit": 10}, "session_judge_limit", 15),
    ],
    ids=["run-limit-zero", "judge-limit-above-the-cap", "a-lower-daily-cap", "a-lower-daily-cap-for-the-judge"],
)
def test_session_limits_stay_within_the_daily_cap(make_client, env_file, changes, field, most):
    client = make_client(local=True)
    view = current(client)
    assert (view["daily_call_cap"], view["session_run_limit"], view["session_judge_limit"]) == (200, 10, 20)
    response = client.post("/api/settings", json=draft_from(view, **changes))
    name = "The session run limit" if field == "session_run_limit" else "The session judge limit"
    assert response.status_code == 422
    assert response.json() == {"detail": f"{name} can be 1 to {most}, the daily cap.", "field": field}
    assert not env_file.exists()


def test_a_session_limit_the_shell_sets_is_locked(make_client, env_file, monkeypatch):
    client = make_client(local=True)
    monkeypatch.setenv("WORKBENCH_SESSION_JUDGE_LIMIT", "20")
    view = current(client)
    assert view["locked"] == ["WORKBENCH_SESSION_JUDGE_LIMIT"]
    response = client.post("/api/settings", json=draft_from(view, session_judge_limit=5))
    assert response.status_code == 409
    assert response.json()["detail"].startswith("WORKBENCH_SESSION_JUDGE_LIMIT is set in the shell that started the server")
    assert not env_file.exists()


# Presets and the local model helper.


def test_the_provider_label_names_only_services_with_presets():
    # The label shows the presets before the choice is picked, so each name it lists has one.
    app_js = (APP_DIR / "static" / "app.js").read_text(encoding="utf-8")
    label = re.search(r'id: "openai_compatible", label: "([^"]+)"', app_js)[1]
    named = re.fullmatch(r"Another service \((.+), and more\)", label)[1].split(", ")
    assert named == ["OpenAI", "Claude", "Grok", "Groq", "OpenRouter"]
    words = [preset.label.split() for preset in PRESETS.presets]
    assert [name for name in named if not any(name in label_words for label_words in words)] == []


def test_each_preset_fills_in_an_address_settings_accepts():
    assert [item.label for item in PRESETS.presets] == [
        "OpenAI",
        "Anthropic Claude",
        "xAI Grok",
        "Groq",
        "OpenRouter",
        "Mistral",
        "DeepSeek",
        "LM Studio on this computer",
    ]
    assert all(BASE_URL.fullmatch(item.base_url) for item in PRESETS.presets)
    anthropic = preset("anthropic")
    assert "response_format" in anthropic.note
    # A trailing slash and the host's case don't matter.
    assert PRESETS.match("https://API.anthropic.com/v1") is anthropic
    assert PRESETS.match(OTHER) is None
    # Each hint prefix points to one service only, so the longest match can't be wrong.
    prefixes = [prefix for item in PRESETS.presets for prefix in item.key_prefixes] + PRESETS.gemini_key_prefixes
    assert not [(a, b) for a in prefixes for b in prefixes if a != b and a.startswith(b)]


def one_reply():
    data = {
        "id": "c",
        "object": "chat.completion.chunk",
        "created": 1,
        "model": "test-model-a",
        "choices": [{"index": 0, "delta": {"content": "ready"}, "finish_reason": None}],
    }
    return httpx2.Response(200, headers={"content-type": "text/event-stream"}, content=b"data: " + json.dumps(data).encode() + b"\n\ndata: [DONE]\n\n")


@pytest.mark.parametrize(
    ("preset_id", "token_field", "usage"),
    [("openai", "max_completion_tokens", True), ("mistral", "max_tokens", False), (None, "max_tokens", True)],
    ids=["openai", "mistral", "any-other-address"],
)
def test_a_preset_sends_the_fields_its_service_takes(tmp_path, preset_id, token_field, usage):
    url = preset(preset_id).base_url if preset_id else OTHER
    settings = settings_for(
        tmp_path,
        workbench_provider="openai_compatible",
        openai_compatible_base_url=url,
        openai_compatible_api_key="test-key",
        workbench_character_model="test-model-a",
        workbench_judge_model="test-model-b",
    )
    provider = build(settings, PRESETS)
    requests = []

    async def handle(request):
        requests.append(json.loads(request.content))
        return one_reply()

    # Only the transport is swapped, so the request is the one build() set up.
    provider._http_client = httpx2.AsyncClient(transport=httpx2.MockTransport(handle))

    async def run():
        async for _ in provider.stream("test-model-a", [{"role": "user", "content": "Hi."}], None, 99):
            pass
        await provider.aclose()

    asyncio.run(run())
    [body] = requests
    other_field = "max_tokens" if token_field == "max_completion_tokens" else "max_completion_tokens"
    assert body[token_field] == 99 and other_field not in body
    assert ("stream_options" in body) is usage


def test_the_view_carries_the_menus_presets_and_hints(make_client):
    view = current(make_client(local=True))
    assert view["character_name"] == "Harry"
    assert [item["id"] for item in view["presets"]] == [item.id for item in PRESETS.presets]
    assert view["gemini_key_prefixes"] == PRESETS.gemini_key_prefixes
    menus = {menu["provider"]: menu for menu in view["providers"]}
    assert set(menus) == {"gemini", "ollama", "fake", "openai_compatible"}
    # The judge starts from another model than the character's when the provider has one.
    assert menus["gemini"]["default_judge"] != menus["gemini"]["default_character"]
    assert menus["openai_compatible"]["default_character"] is None
    assert view["keys"]["gemini"] == {"saved": False, "last4": None, "locked": False}


def test_the_local_model_helper_lists_what_ollama_has(make_client):
    provider = FakeProvider(fake_settings())

    async def installed():
        return ["qwen3:8b", "llama3.2:3b"]

    provider.list_models = installed
    found = make_client(provider=provider, local=True).get("/api/settings/ollama").json()
    assert found == {
        "running": True,
        "models": ["llama3.2:3b", "qwen3:8b"],
        "missing": MODELS.character_models("ollama"),
        "message": "Ollama is running with 2 installed models.",
    }


def test_the_local_model_helper_says_how_to_start_ollama(make_client):
    provider = FakeProvider(fake_settings())

    async def refused():
        raise ProviderError("connection", "Couldn't reach the model service.", "connection error")

    provider.list_models = refused
    found = make_client(provider=provider, local=True).get("/api/settings/ollama").json()
    assert found["running"] is False and found["models"] == []
    assert found["message"] == (
        "Ollama isn't running. Start it with OLLAMA_CONTEXT_LENGTH=32768 ollama serve, then press Check again."
    )
