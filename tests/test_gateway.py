"""M2 and M6 gateway tests: one log row per attempt with its tokens, call
spacing on a fake clock, the daily cap counted by Pacific day, and, for a busy
service, retries with doubling pauses and then the fallback model."""

import asyncio
from datetime import datetime, timezone

import pytest

from conftest import FakeTime, default_model, fake_settings, query, settings_for
from workbench.config import load_prompts
from workbench.gateway import CapReached, Delta, Gateway, Wait
from workbench.limiter import Limiter
from workbench.providers import RATE_LIMITED, Chunk, FakeProvider, FakeReply, ProviderError, Usage

BUSY = ProviderError("rate_limited", RATE_LIMITED, "HTTP 429: quota")

# 23:59 and 00:01 Pacific time on the night of Oct 11 to 12, 2026 (PDT is UTC-7).
BEFORE_MIDNIGHT = datetime(2026, 10, 12, 6, 59, tzinfo=timezone.utc)
AFTER_MIDNIGHT = datetime(2026, 10, 12, 7, 1, tzinfo=timezone.utc)


class ScriptedProvider:
    """Streams the chunks it is given, like a Gemini reply with usage on every chunk."""

    def __init__(self, chunks, name="gemini", stall_after=None):
        self.name = name
        self.ready = True
        self.chunks = chunks
        self.stall_after = stall_after
        self.starts = []

    async def stream(self, model, messages, reasoning_effort, max_tokens):
        for index, chunk in enumerate(self.chunks):
            if index == self.stall_after:
                await asyncio.sleep(3600)
            yield chunk

    async def aclose(self):
        return None


def make_gateway(tmp_path, database, provider, *, time=None, wall=None, **overrides):
    settings = settings_for(tmp_path, **overrides)
    prompts = load_prompts()
    limiter = Limiter(settings.workbench_calls_per_minute, settings.workbench_daily_call_cap, prompts.models.quota_timezone)
    time = time or FakeTime()
    extra = {"wall": wall} if wall else {}
    return Gateway(database, settings, prompts, provider, limiter, clock=time.clock, sleep=time.sleep, **extra)


def run_call(gateway, model_id, stop=None, on_event=None, **kwargs):
    """Runs one call to the end and returns (events, result)."""

    async def run():
        call = gateway.call(
            role="character",
            model_id=model_id,
            messages=[{"role": "system", "content": "spec"}, {"role": "user", "content": "Hello."}],
            prompt_version="character.v1",
            session=None,
            stop=stop or asyncio.Event(),
            **kwargs,
        )
        events = []
        async for event in call.events():
            events.append(event)
            if on_event:
                on_event(event, call)
        return events, call.result

    return asyncio.run(run())


def test_a_streamed_reply_is_logged_with_its_tokens(tmp_path, database):
    model_id = default_model("gemini")
    provider = ScriptedProvider(
        [
            Chunk("Hel", "reported-model-1", Usage(2900, 1200, 1, 40)),
            Chunk("lo.", "reported-model-1", Usage(2900, 1200, 2, 47)),
            Chunk("", "reported-model-1", Usage(2900, 1200, 3, 47)),
        ]
    )
    gateway = make_gateway(tmp_path, database, provider, workbench_provider="gemini")

    events, result = run_call(gateway, model_id, transcript_id=None, turn=2)
    assert [event.text for event in events if isinstance(event, Delta)] == ["Hel", "lo."]
    assert (result.status, result.text, result.model_reported) == ("ok", "Hello.", "reported-model-1")

    [row] = query(database, "SELECT * FROM model_calls")
    # The last usage seen wins: Gemini repeats running totals on every chunk.
    assert (row["input_tokens"], row["cached_tokens"], row["output_tokens"], row["reasoning_tokens"]) == (2900, 1200, 3, 47)
    price = load_prompts().models.models[model_id]
    expected = ((2900 - 1200) * price.input_price + 1200 * price.cached_input_price + (3 + 47) * price.output_price) / 1_000_000
    assert row["est_cost_usd"] == pytest.approx(expected)
    assert (row["provider"], row["model_asked"], row["model_reported"]) == ("gemini", model_id, "reported-model-1")
    assert row["reasoning_effort"] == price.reasoning_effort
    assert (row["status"], row["error"], row["turn"]) == ("ok", None, 2)
    assert row["ttft_ms"] is not None and row["latency_ms"] is not None


def test_a_stopped_reply_keeps_the_tokens_it_saw(tmp_path, database):
    provider = ScriptedProvider(
        [Chunk("Partial", "reported-model-1", Usage(100, 0, 2, 5)), Chunk(" rest", None, Usage(100, 0, 4, 5))],
        stall_after=1,
    )
    gateway = make_gateway(tmp_path, database, provider, workbench_provider="gemini")
    stop = asyncio.Event()

    def stop_after_first_text(event, call):
        if isinstance(event, Delta):
            stop.set()

    events, result = run_call(gateway, default_model("gemini"), stop=stop, on_event=stop_after_first_text)
    assert (result.status, result.text) == ("stopped", "Partial")
    [row] = query(database, "SELECT status, input_tokens, output_tokens, reasoning_tokens FROM model_calls")
    assert row == {"status": "stopped", "input_tokens": 100, "output_tokens": 2, "reasoning_tokens": 5}


@pytest.mark.parametrize(("per_minute", "gap"), [(15, 4.0), (30, 2.0)])
def test_calls_start_at_least_60_over_n_seconds_apart(tmp_path, database, per_minute, gap):
    time = FakeTime()
    starts = []

    class Recording(FakeProvider):
        async def stream(self, *args, **kwargs):
            starts.append(time.now)
            async for chunk in super().stream(*args, **kwargs):
                yield chunk

    gateway = make_gateway(tmp_path, database, Recording(fake_settings()), time=time, workbench_calls_per_minute=per_minute)
    waits = []
    for _ in range(3):
        events, _ = run_call(gateway, default_model())
        waits.append([event.seconds for event in events if isinstance(event, Wait)])

    assert [round(start - starts[0], 6) for start in starts] == [0, gap, 2 * gap]
    assert waits == [[], [gap], [gap]]
    # Once the gap has passed, a call starts right away.
    time.now += 60
    assert not any(isinstance(event, Wait) for event in run_call(gateway, default_model())[0])


def test_at_the_cap_no_provider_call_is_made(tmp_path, database):
    provider = FakeProvider(fake_settings())
    gateway = make_gateway(tmp_path, database, provider, workbench_daily_call_cap=2)
    run_call(gateway, default_model())
    run_call(gateway, default_model())

    with pytest.raises(CapReached, match="Today's 2 model calls are used up") as caught:
        run_call(gateway, default_model())
    assert "midnight Pacific time" in str(caught.value)
    assert "WORKBENCH_DAILY_CALL_CAP" in str(caught.value)
    assert len(provider.requests) == 2
    assert [row["status"] for row in query(database, "SELECT status FROM model_calls ORDER BY id")] == ["ok", "ok", "capped"]
    # A refused call never reached the provider, so it doesn't count.
    assert gateway.used_today() == 2


def test_the_cap_stops_start_and_next_with_a_friendly_message(make_client):
    client = make_client(workbench_daily_call_cap=2)
    start = {"character": "harry", "scenario": "F2", "model": default_model()}
    chat = client.post("/api/chats", json=start).json()
    client.post(f"/api/chats/{chat['id']}/next")
    client.post(f"/api/chats/{chat['id']}/next")

    refused = client.post(f"/api/chats/{chat['id']}/next")
    assert refused.status_code == 429
    assert "Today's 2 model calls are used up" in refused.json()["detail"]
    assert client.post("/api/chats", json=start).status_code == 429
    # Nothing was saved for the refused turn, and no empty chat was made.
    assert len(client.get(f"/api/chats/{chat['id']}").json()["messages"]) == 4
    assert len(client.get("/api/chats").json()) == 1
    options = client.get("/api/run-options").json()
    assert (options["used_today"], options["daily_cap"]) == (2, 2)


def test_the_daily_count_follows_pacific_days(tmp_path, database):
    limiter = Limiter(15, 200, load_prompts().models.quota_timezone)
    assert limiter.quota_day(BEFORE_MIDNIGHT) == "2026-10-11"
    assert limiter.quota_day(AFTER_MIDNIGHT) == "2026-10-12"
    assert limiter.hours_left(BEFORE_MIDNIGHT) == 1

    now = [BEFORE_MIDNIGHT]
    gateway = make_gateway(tmp_path, database, FakeProvider(fake_settings()), wall=lambda: now[0], workbench_daily_call_cap=1)
    run_call(gateway, default_model())
    with pytest.raises(CapReached):
        run_call(gateway, default_model())

    # A new Pacific day starts the count over.
    now[0] = AFTER_MIDNIGHT
    assert gateway.used_today() == 0
    events, result = run_call(gateway, default_model())
    assert result.status == "ok"
    days = [row["quota_day"] for row in query(database, "SELECT quota_day FROM model_calls ORDER BY id")]
    assert days == ["2026-10-11", "2026-10-11", "2026-10-12"]


# Retries and the fallback model (M6).


def fallback_of(model_id):
    return load_prompts().models.fallback_for(model_id)


def test_a_forced_429_is_tried_again_then_the_fallback_model_answers(tmp_path, database):
    time = FakeTime()
    provider = FakeProvider(fake_settings())
    gateway = make_gateway(tmp_path, database, provider, time=time, workbench_force_model_error="primary")
    model_id = default_model()
    fallback = fallback_of(model_id)

    events, result = run_call(gateway, model_id)
    assert (result.status, result.text) == ("ok", fake_settings().reply)
    assert (result.model_used, result.fallback, result.attempts) == (fallback, True, 4)
    assert [(event.reason, event.seconds) for event in events if isinstance(event, Wait)] == [
        ("retry", 2),
        ("retry", 4),
        ("fallback", 0),
    ]
    # The pauses double on the fake clock. A forced attempt takes no call slot, so nothing else waits.
    assert time.sleeps == [2, 4]
    forced = "forced 429 (WORKBENCH_FORCE_MODEL_ERROR=primary)"
    assert query(database, "SELECT attempt, fallback, forced, model_asked, status, error FROM model_calls ORDER BY id") == [
        {"attempt": 1, "fallback": 0, "forced": 1, "model_asked": model_id, "status": "error", "error": forced},
        {"attempt": 2, "fallback": 0, "forced": 1, "model_asked": model_id, "status": "error", "error": forced},
        {"attempt": 3, "fallback": 0, "forced": 1, "model_asked": model_id, "status": "error", "error": forced},
        {"attempt": 4, "fallback": 1, "forced": 0, "model_asked": fallback, "status": "ok", "error": None},
    ]
    # Only the fallback model's call reached the provider, so only it counts toward the daily cap.
    assert [request["model"] for request in provider.requests] == [fallback]
    assert gateway.used_today() == 1
    assert result.model_call_id == query(database, "SELECT MAX(id) AS id FROM model_calls")[0]["id"]


def test_with_every_attempt_forced_to_fail_the_call_ends_in_an_error(tmp_path, database):
    provider = FakeProvider(fake_settings())
    gateway = make_gateway(tmp_path, database, provider, workbench_force_model_error="all")
    events, result = run_call(gateway, default_model())
    assert (result.status, result.message, result.fallback, result.attempts) == ("error", RATE_LIMITED, True, 4)
    assert provider.requests == [] and gateway.used_today() == 0
    rows = query(database, "SELECT forced, fallback FROM model_calls ORDER BY id")
    assert [(row["forced"], row["fallback"]) for row in rows] == [(1, 0), (1, 0), (1, 0), (1, 1)]


@pytest.mark.parametrize(
    ("kind", "requests"),
    [("rate_limited", 4), ("server", 4), ("auth", 1), ("not_found", 1), ("bad_request", 1), ("connection", 1), ("timeout", 1)],
)
def test_only_a_busy_service_is_tried_again(tmp_path, database, kind, requests):
    failure = ProviderError(kind, "It failed.", f"{kind} detail")
    provider = FakeProvider(fake_settings(), replies=[FakeReply(error=failure)] * 4)
    gateway = make_gateway(tmp_path, database, provider)
    events, result = run_call(gateway, default_model())
    assert (result.status, result.message, len(provider.requests)) == ("error", "It failed.", requests)


def test_with_no_retries_the_fallback_model_comes_next(tmp_path, database):
    provider = FakeProvider(fake_settings(), replies=[FakeReply(error=BUSY)])
    gateway = make_gateway(tmp_path, database, provider, workbench_retries=0)
    events, result = run_call(gateway, default_model())
    assert (result.status, result.fallback) == ("ok", True)
    assert [request["model"] for request in provider.requests] == [default_model(), fallback_of(default_model())]


def test_a_reply_that_breaks_after_its_first_words_is_not_started_over(tmp_path, database):
    class Breaks(ScriptedProvider):
        async def stream(self, model, messages, reasoning_effort, max_tokens):
            self.starts.append(model)
            yield Chunk("Hel", "reported-model-1", Usage(10, 0, 1, 0))
            raise BUSY

    provider = Breaks([])
    gateway = make_gateway(tmp_path, database, provider)
    events, result = run_call(gateway, default_model())
    assert (result.status, result.text, result.attempts) == ("error", "Hel", 1)
    assert provider.starts == [default_model()]


def test_stop_during_a_retry_pause_ends_the_call(tmp_path, database):
    provider = FakeProvider(fake_settings(), replies=[FakeReply(error=BUSY)])
    gateway = make_gateway(tmp_path, database, provider)
    stop = asyncio.Event()

    def stop_at_the_pause(event, call):
        if isinstance(event, Wait) and event.reason == "retry":
            stop.set()

    events, result = run_call(gateway, default_model(), stop=stop, on_event=stop_at_the_pause)
    assert (result.status, result.message) == ("stopped", "")
    assert len(provider.requests) == 1
    assert [row["status"] for row in query(database, "SELECT status FROM model_calls")] == ["error"]


def test_every_message_sent_to_a_model_is_redacted(tmp_path, database):
    provider = FakeProvider(fake_settings())
    gateway = make_gateway(tmp_path, database, provider)

    async def run():
        call = gateway.call(
            role="character",
            model_id=default_model(),
            messages=[{"role": "system", "content": "spec"}, {"role": "user", "content": "Mail me at alex@example.com."}],
            prompt_version="character.v1",
            session=None,
            stop=asyncio.Event(),
        )
        async for _ in call.events():
            pass

    asyncio.run(run())
    assert provider.requests[0]["messages"][1]["content"] == "Mail me at [email removed]."
