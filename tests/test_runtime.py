"""M2 runtime tests: a live chat streams each turn, saves it in order, stops
cleanly, and stays pinned to its spec version.

TestClient reads a whole stream before it returns, so tests that stop or cut
off a reply partway drive the runtime directly, the way the SSE route does.
"""

import asyncio

import pytest

from conftest import FakeTime, default_model, fake_settings, query, scenario_lines, sse_events
from spec_edits import edit_payload, set_line
from workbench import specs
from workbench.config import load_prompts
from workbench.providers import Chunk, FakeProvider, FakeReply, OpenAIProvider, ProviderError, Usage
from workbench.runtime import ChatBusy

LONG_REPLY = "One two three four five six seven eight nine ten eleven twelve."


class BreaksPartway(FakeProvider):
    """Sends the first words of its first reply, then fails, as a stream that breaks would. Later calls answer in full."""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.broken = False

    async def stream(self, model, messages, reasoning_effort, max_tokens):
        if self.broken:
            async for chunk in super().stream(model, messages, reasoning_effort, max_tokens):
                yield chunk
            return
        self.broken = True
        self.requests.append({"model": model, "messages": [dict(message) for message in messages]})
        yield Chunk(text="Krum caught it, but", model=self.settings.model_reported, usage=Usage(10, 0, 4, 0))
        raise ProviderError("error", "The model service sent an error partway through the reply. Try again.", "stream error")


def start(client, scenario="F2"):
    response = client.post("/api/chats", json={"character": "harry", "scenario": scenario, "model": default_model()})
    assert response.status_code == 201, response.text
    return response.json()


def next_turn(client, chat_id):
    response = client.post(f"/api/chats/{chat_id}/next")
    assert response.status_code == 200, response.text
    assert response.headers["content-type"].startswith("text/event-stream")
    return sse_events(response.text)


def run_script(client, chat_id):
    return [next_turn(client, chat_id) for _ in scenario_lines("F2")]


def collect(turn, on_event=None):
    """Iterates a turn's events, as the SSE route does, and returns them."""

    async def run():
        seen = []
        async for name, payload in turn.events():
            seen.append((name, payload))
            if on_event:
                on_event(name, seen)
        return seen

    return asyncio.run(run())


def test_scripted_f2_run_saves_every_turn_in_order(make_client):
    fake = fake_settings()
    client = make_client(provider=FakeProvider(fake))
    chat = start(client)
    assert (chat["spec_version"], chat["status"], chat["script_total"], chat["script_last_turn"]) == (1, "active", 10, 11)

    script = scenario_lines("F2")
    for line, events in zip(script, run_script(client, chat["id"])):
        names = [name for name, _ in events]
        assert names[0] == "user" and names[-1] == "done"
        assert "delta" in names and set(names[1:-1]) <= {"wait", "delta"}
        user, done = events[0][1], events[-1][1]
        assert (user["turn"], user["text"]) == (line.turn, line.text)
        # The saved reply is exactly the text that streamed.
        assert done["message"]["text"] == "".join(data["text"] for name, data in events if name == "delta")
        assert done["stopped"] is False
    assert (done["status"], done["script_left"]) == ("script_done", 0)

    view = client.get(f"/api/chats/{chat['id']}").json()
    messages = view["messages"]
    assert [m["seq"] for m in messages] == list(range(1, 21))
    assert [m["turn"] for m in messages] == [turn for line in script for turn in (line.turn, line.turn)]
    assert [m["speaker"] for m in messages] == ["user", "character"] * 10
    assert [m["source"] for m in messages] == ["script", "model"] * 10
    assert [m["text"] for m in messages[::2]] == [line.text for line in script]
    assert all(m["text"] == fake.reply and not m["stopped"] for m in messages[1::2])

    rows = query(client, "SELECT * FROM model_calls ORDER BY id")
    assert len(rows) == 10
    prompts = load_prompts()
    for row, line in zip(rows, script):
        assert row["role"] == "character"
        assert (row["provider"], row["model_asked"], row["model_reported"]) == ("fake", default_model(), fake.model_reported)
        assert (row["prompt_version"], row["settings_version"]) == (prompts.character_version, prompts.models_version)
        assert (row["transcript_id"], row["turn"], row["attempt"], row["fallback"]) == (chat["id"], line.turn, 1, 0)
        assert row["ttft_ms"] >= 0 and row["latency_ms"] >= row["ttft_ms"]
        assert row["input_tokens"] > 0 and row["output_tokens"] > 0
        assert (row["cached_tokens"], row["reasoning_tokens"], row["est_cost_usd"]) == (0, 0, 0.0)
        assert (row["status"], row["error"]) == ("ok", None)
    links = query(client, "SELECT model_call_id FROM messages WHERE speaker = 'character' ORDER BY seq")
    assert [link["model_call_id"] for link in links] == [row["id"] for row in rows]

    # The script is over, so there's no next line.
    response = client.post(f"/api/chats/{chat['id']}/next")
    assert response.status_code == 409
    assert "Type your next message" in response.json()["detail"]


def test_every_turn_sends_the_same_spec_bytes_first(make_client):
    provider = FakeProvider(fake_settings())
    client = make_client(provider=provider)
    chat = start(client)
    run_script(client, chat["id"])

    systems = [request["messages"][0] for request in provider.requests]
    assert all(message["role"] == "system" for message in systems)
    assert len({message["content"].encode("utf-8") for message in systems}) == 1
    # character.v1 is the spec alone, the CP2 baseline.
    v1 = client.get("/api/characters/harry/specs/1").json()["body"]
    assert systems[0]["content"] == specs.render_text(specs.SpecBody.model_validate(v1))
    # Each turn sends the chat so far: user and assistant lines in order.
    last = provider.requests[-1]["messages"]
    assert [m["role"] for m in last] == ["system"] + ["user", "assistant"] * 9 + ["user"]


def test_typed_line_streams_after_the_script_ends(make_client):
    client = make_client()
    chat = start(client)
    next_turn(client, chat["id"])

    early = client.post(f"/api/chats/{chat['id']}/messages", json={"text": "Can I say something?"})
    assert early.status_code == 409
    assert "after the script ends" in early.json()["detail"]

    for _ in scenario_lines("F2")[1:]:
        next_turn(client, chat["id"])
    response = client.post(f"/api/chats/{chat['id']}/messages", json={"text": "  Bye for now.  "})
    assert response.status_code == 200, response.text
    events = sse_events(response.text)
    assert [events[0][0], events[-1][0]] == ["user", "done"]
    assert (events[0][1]["turn"], events[0][1]["text"]) == (12, "Bye for now.")
    assert "delta" in [name for name, _ in events]

    view = client.get(f"/api/chats/{chat['id']}").json()
    typed, reply = view["messages"][-2:]
    assert (typed["source"], typed["turn"], typed["speaker"]) == ("typed", 12, "user")
    assert (reply["source"], reply["turn"], reply["speaker"]) == ("model", 12, "character")
    assert view["status"] == "script_done"
    assert "message_typed" in [row["kind"] for row in query(client, "SELECT kind FROM events")]


@pytest.mark.parametrize(
    ("text", "words"), [("   ", "Type a message first"), ("x" * 2001, "2,000 characters")], ids=["blank", "too-long"]
)
def test_a_typed_line_must_have_text_and_fit_the_limit(make_client, text, words):
    client = make_client()
    chat = start(client)
    client.post(f"/api/chats/{chat['id']}/stop")
    response = client.post(f"/api/chats/{chat['id']}/messages", json={"text": text})
    assert response.status_code == 422
    assert words in response.json()["detail"]
    assert client.get(f"/api/chats/{chat['id']}").json()["messages"] == []


def test_stop_saves_the_partial_reply_as_stopped(make_runtime, database):
    provider = FakeProvider(fake_settings(), replies=[FakeReply(text=LONG_REPLY, chunk_seconds=0.05)])
    runtime = make_runtime(provider)
    chat = runtime.start(character="harry", scenario_id="F2", model_id=default_model(), session=None)
    turn = runtime.begin(chat.id, typed=None, session=None)

    def stop_after_two_deltas(name, seen):
        if name == "delta" and [n for n, _ in seen].count("delta") == 2:
            runtime.stop(chat.id, session=None)

    events = collect(turn, stop_after_two_deltas)
    streamed = "".join(payload.text for name, payload in events if name == "delta")
    name, done = events[-1]
    assert name == "done" and done.stopped and done.status == "stopped"

    view = runtime.get_chat(chat.id)
    reply = view.messages[-1]
    assert (reply.speaker, reply.stopped, reply.text) == ("character", True, streamed)
    assert 0 < len(reply.text) < len(LONG_REPLY)
    assert view.status == "stopped" and chat.id not in runtime.running
    [row] = query(database, "SELECT * FROM model_calls")
    # The tokens seen before Stop are still logged.
    assert (row["status"], row["output_tokens"] > 0, row["ttft_ms"] is not None) == ("stopped", True, True)
    assert "run_stopped" in [row["kind"] for row in query(database, "SELECT kind FROM events")]

    # A stopped chat takes typed lines, not the script.
    with pytest.raises(Exception, match="script has ended"):
        runtime.begin(chat.id, typed=None, session=None)


def test_stop_during_the_wait_sends_no_request(make_runtime, database):
    provider = FakeProvider(fake_settings())
    time = FakeTime()

    async def real_sleep(seconds):
        await asyncio.sleep(seconds)

    runtime = make_runtime(provider, clock=time.clock, sleep=real_sleep)
    chat = runtime.start(character="harry", scenario_id="F2", model_id=default_model(), session=None)
    collect(runtime.begin(chat.id, typed=None, session=None))

    def stop_on_wait(name, seen):
        if name == "wait":
            runtime.stop(chat.id, session=None)

    # The clock hasn't moved, so the second call waits its full 4 seconds, and Stop comes first.
    events = collect(runtime.begin(chat.id, typed=None, session=None), stop_on_wait)
    assert [name for name, _ in events] == ["user", "wait", "done"]
    assert events[1][1].seconds == 4.0
    assert (events[-1][1].stopped, events[-1][1].message) == (True, None)
    assert len(provider.requests) == 1
    assert len(query(database, "SELECT id FROM model_calls")) == 1
    assert runtime.get_chat(chat.id).messages[-1].speaker == "user"


def test_a_second_turn_while_one_runs_is_refused(make_client):
    client = make_client()
    chat = start(client)
    runtime = client.app.state.runtime

    turn = runtime.begin(chat["id"], typed=None, session=None)
    with pytest.raises(ChatBusy):
        runtime.begin(chat["id"], typed=None, session=None)
    response = client.post(f"/api/chats/{chat['id']}/next")
    assert response.status_code == 409
    assert "still answering" in response.json()["detail"]
    assert client.get(f"/api/chats/{chat['id']}").json()["busy"] is True

    # finish() frees the chat even when the stream never started.
    asyncio.run(turn.finish())
    assert next_turn(client, chat["id"])[-1][0] == "done"


def test_an_empty_reply_gives_an_error_card_and_try_again_answers_the_same_line(make_client):
    provider = FakeProvider(fake_settings(), replies=[FakeReply(text="")])
    client = make_client(provider=provider)
    chat = start(client)

    events = next_turn(client, chat["id"])
    assert [name for name, _ in events] == ["user", "error"]
    error = events[-1][1]
    assert (error["retry"], error["status"]) == (True, "active")
    assert "empty reply" in error["message"]
    assert [m["speaker"] for m in client.get(f"/api/chats/{chat['id']}").json()["messages"]] == ["user"]
    assert query(client, "SELECT status, error FROM model_calls") == [{"status": "empty", "error": "empty reply"}]

    # Try again answers the line still waiting, without sending it twice.
    events = next_turn(client, chat["id"])
    assert [name for name, _ in events][0] != "user" and events[-1][0] == "done"
    messages = client.get(f"/api/chats/{chat['id']}").json()["messages"]
    assert [(m["turn"], m["speaker"]) for m in messages] == [(2, "user"), (2, "character")]
    assert "error_shown" in [row["kind"] for row in query(client, "SELECT kind FROM events")]


def test_a_reply_that_never_starts_times_out_with_a_card(make_client):
    provider = FakeProvider(fake_settings(), replies=[FakeReply(first_token_seconds=5)])
    client = make_client(provider=provider, workbench_first_token_timeout_seconds=0.05)
    chat = start(client)

    events = next_turn(client, chat["id"])
    assert events[-1][0] == "error"
    assert "didn't start answering within 0.05 seconds" in events[-1][1]["message"]
    assert query(client, "SELECT status, error, ttft_ms FROM model_calls") == [
        {"status": "timeout", "error": "no first token in time", "ttft_ms": None}
    ]
    assert len(client.get(f"/api/chats/{chat['id']}").json()["messages"]) == 1


def test_a_provider_error_gives_a_plain_card(make_client):
    # A refused key, which no retry or fallback can fix. Busy services are in test_gateway.
    failure = ProviderError("auth", "The model service didn't accept the key.", "HTTP 401: bad key")
    client = make_client(provider=FakeProvider(fake_settings(), replies=[FakeReply(error=failure)]))
    chat = start(client)

    events = next_turn(client, chat["id"])
    assert events[-1] == ("error", {"message": failure.message, "retry": True, "status": "active", "partial": None})
    assert query(client, "SELECT status, error FROM model_calls") == [{"status": "error", "error": "HTTP 401: bad key"}]


def test_an_error_partway_saves_the_partial_reply_and_try_again_answers_the_same_line(make_client):
    provider = BreaksPartway(fake_settings())
    client = make_client(provider=provider)
    chat = start(client)

    events = next_turn(client, chat["id"])
    assert [name for name, _ in events] == ["user", "delta", "error"]
    error = events[-1][1]
    assert (error["retry"], error["status"]) == (True, "active")
    partial = error["partial"]
    assert (partial["text"], partial["stopped"], partial["failed"]) == ("Krum caught it, but", True, True)
    # Once text has come, the reply isn't started over on its own: the creator saw part of it.
    assert query(client, "SELECT status, error FROM model_calls") == [{"status": "error", "error": "stream error"}]

    # Try again answers the same line, without sending it twice or showing the model its cut-off words.
    events = next_turn(client, chat["id"])
    assert events[0][0] != "user" and events[-1][0] == "done"
    messages = client.get(f"/api/chats/{chat['id']}").json()["messages"]
    assert [(m["turn"], m["speaker"], m["stopped"], m["failed"]) for m in messages] == [
        (2, "user", False, False),
        (2, "character", True, True),
        (2, "character", False, False),
    ]
    assert [message["role"] for message in provider.requests[-1]["messages"]] == ["system", "user"]
    # And the run goes on from there.
    assert next_turn(client, chat["id"])[0][1]["turn"] == scenario_lines("F2")[1].turn


def test_a_closed_connection_saves_the_partial_reply_and_the_run_can_go_on(make_runtime, database):
    provider = FakeProvider(fake_settings(), replies=[FakeReply(text=LONG_REPLY, chunk_seconds=0.01)])
    runtime = make_runtime(provider)
    chat = runtime.start(character="harry", scenario_id="F2", model_id=default_model(), session=None)
    turn = runtime.begin(chat.id, typed=None, session=None)

    async def read_two_deltas_then_disconnect():
        seen = []
        async for name, payload in turn.events():
            seen.append((name, payload))
            if [n for n, _ in seen].count("delta") == 2:
                break
        # What the SSE route's dependency does when the response ends early.
        await turn.finish()
        await turn.finish()
        return "".join(payload.text for name, payload in seen if name == "delta")

    streamed = asyncio.run(read_two_deltas_then_disconnect())
    view = runtime.get_chat(chat.id)
    reply = view.messages[-1]
    assert (reply.stopped, reply.text) == (True, streamed)
    # Unlike Stop, a dropped connection leaves the script ready to go on.
    assert view.status == "active" and chat.id not in runtime.running
    assert [row["status"] for row in query(database, "SELECT status FROM model_calls")] == ["stopped"]

    next_events = collect(runtime.begin(chat.id, typed=None, session=None))
    assert next_events[0][1].turn == scenario_lines("F2")[1].turn


def test_a_chat_keeps_its_spec_version_after_a_new_one_is_saved(make_client):
    provider = FakeProvider(fake_settings())
    client = make_client(provider=provider)
    chat = start(client)
    next_turn(client, chat["id"])

    edit = edit_payload(client.get("/api/characters/harry/specs/latest").json())
    set_line(edit, "C2", "He lives with the Dursleys, who keep him in the cupboard.")
    assert client.post("/api/characters/harry/specs", json=edit).status_code == 201

    next_turn(client, chat["id"])
    first, second = (request["messages"][0]["content"] for request in provider.requests)
    assert first == second
    assert "keep him in the cupboard" not in second
    assert client.get(f"/api/chats/{chat['id']}").json()["spec_version"] == 1

    newer = start(client)
    assert newer["spec_version"] == 2
    next_turn(client, newer["id"])
    assert "keep him in the cupboard" in provider.requests[-1]["messages"][0]["content"]


def test_start_checks_the_scenario_the_model_and_the_key(make_client):
    client = make_client()
    unknown = client.post("/api/chats", json={"character": "harry", "scenario": "T2", "model": default_model()})
    assert unknown.status_code == 422 and "no scenario called T2" in unknown.json()["detail"]
    wrong_model = client.post("/api/chats", json={"character": "harry", "scenario": "F2", "model": "not-a-model"})
    assert wrong_model.status_code == 422 and "Model menu" in wrong_model.json()["detail"]

    # With the Gemini provider and no key, Start explains, and no chat is left behind.
    no_key = OpenAIProvider(name="gemini", base_url="https://example.invalid/v1/", api_key="", timeout=5)
    keyless = make_client(provider=no_key, workbench_provider="gemini", gemini_api_key="")
    response = keyless.post("/api/chats", json={"character": "harry", "scenario": "F2", "model": default_model("gemini")})
    assert response.status_code == 503
    assert "Open Settings" in response.json()["detail"]
    assert keyless.get("/api/chats").json() == []
