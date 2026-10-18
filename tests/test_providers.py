"""M2 provider tests: the real openai client on a mock httpx2 transport, so
what would go to Gemini is checked with no key and no network."""

import asyncio
import json

import httpx2
import pytest

from conftest import query, sse_events
from workbench import specs
from workbench.config import load_prompts
from workbench.providers import OpenAIProvider, ProviderError

BASE_URL = "https://gemini.example.test/v1beta/openai/"


def chunk(content=None, *, usage=None, choices=True, model=None):
    data = {"id": "chunk", "object": "chat.completion.chunk", "created": 1, "model": model, "choices": [], "usage": usage}
    if choices:
        data["choices"] = [{"index": 0, "delta": {"content": content} if content is not None else {}, "finish_reason": None}]
    return data


def stream_body(chunks):
    events = b"".join(b"data: " + json.dumps(item).encode() + b"\n\n" for item in chunks)
    return events + b"data: [DONE]\n\n"


def gemini_reply(text, model_id, prompt_tokens=2900):
    """Gemini's style: usage on every chunk, and thinking only in total_tokens."""
    words = text.split(" ")
    chunks = []
    for count in range(1, len(words) + 1):
        piece = words[count - 1] + ("" if count == len(words) else " ")
        usage = {"prompt_tokens": prompt_tokens, "completion_tokens": count, "total_tokens": prompt_tokens + count + 30}
        chunks.append(chunk(piece, usage=usage, model=model_id))
    return httpx2.Response(200, headers={"content-type": "text/event-stream"}, content=stream_body(chunks))


def mock_provider(responses, requests, api_key="test-key"):
    async def handle(request):
        requests.append({"url": str(request.url), "auth": request.headers.get("authorization"), "body": json.loads(request.content)})
        return responses.pop(0)

    client = httpx2.AsyncClient(transport=httpx2.MockTransport(handle))
    return OpenAIProvider(name="gemini", base_url=BASE_URL, api_key=api_key, timeout=5, http_client=client)


def test_requests_carry_the_configured_settings_and_identical_spec_bytes(make_client):
    models = load_prompts().models
    model_id = models.character_models("gemini")[0]
    spec = models.models[model_id]
    replies = ["Hi, Alex.", "Ireland won, actually.", "Never heard of her."]
    requests = []
    provider = mock_provider([gemini_reply(text, model_id) for text in replies], requests)
    client = make_client(provider=provider, workbench_provider="gemini", gemini_api_key="test-key")

    chat = client.post("/api/chats", json={"character": "harry", "scenario": "F2", "model": model_id}).json()
    for text in replies:
        events = sse_events(client.post(f"/api/chats/{chat['id']}/next").text)
        assert events[-1][0] == "done"
        assert events[-1][1]["message"]["text"] == text

    assert len(requests) == 3
    for request in requests:
        body = request["body"]
        assert request["url"] == BASE_URL + "chat/completions"
        assert request["auth"] == "Bearer test-key"
        assert body["model"] == model_id
        assert body["reasoning_effort"] == spec.reasoning_effort
        assert body["max_tokens"] == spec.max_tokens
        assert body["stream"] is True
        assert body["stream_options"] == {"include_usage": True}
        assert "temperature" not in body
        assert body["messages"][0]["role"] == "system"
    # The spec goes first, byte for byte the same on every turn.
    systems = {json.dumps(request["body"]["messages"][0], ensure_ascii=False).encode("utf-8") for request in requests}
    assert len(systems) == 1
    v1 = client.get("/api/characters/harry/specs/1").json()["body"]
    assert requests[0]["body"]["messages"][0]["content"] == specs.render_text(specs.SpecBody.model_validate(v1))
    # Earlier replies go back as plain assistant text.
    assert [m["role"] for m in requests[2]["body"]["messages"]] == ["system", "user", "assistant", "user", "assistant", "user"]
    assert requests[2]["body"]["messages"][2]["content"] == replies[0]

    rows = query(client, "SELECT * FROM model_calls ORDER BY id")
    assert [row["model_reported"] for row in rows] == [model_id] * 3
    assert [(row["input_tokens"], row["output_tokens"], row["reasoning_tokens"]) for row in rows] == [
        (2900, len(text.split(" ")), 30) for text in replies
    ]
    assert all(row["est_cost_usd"] > 0 for row in rows)


PROMPT = "A distinctive prompt line, 7f3a9c."


def stream_all(provider, model="any-model"):
    async def run():
        pieces, usage = [], None
        async for item in provider.stream(model, [{"role": "user", "content": PROMPT}], None, 50):
            pieces.append(item.text)
            usage = item.usage or usage
        return "".join(pieces), usage

    return asyncio.run(run())


def test_a_usage_only_final_chunk_is_kept():
    # Ollama's style: text first, then one chunk with no choices that carries the usage.
    body = stream_body(
        [
            chunk("Hello "),
            chunk("there."),
            chunk(choices=False, usage={"prompt_tokens": 12, "completion_tokens": 3, "total_tokens": 15}),
        ]
    )
    requests = []
    provider = mock_provider([httpx2.Response(200, headers={"content-type": "text/event-stream"}, content=body)], requests)
    text, usage = stream_all(provider)
    assert text == "Hello there."
    assert (usage.input_tokens, usage.output_tokens, usage.reasoning_tokens) == (12, 3, 0)
    assert "reasoning_effort" not in requests[0]["body"]


@pytest.mark.parametrize(
    ("status", "body", "kind", "words"),
    [
        (
            429,
            [{"error": {"code": 429, "message": "Resource has been exhausted (e.g. check quota).", "status": "RESOURCE_EXHAUSTED"}}],
            "rate_limited",
            "free limit",
        ),
        (
            400,
            [{"error": {"code": 400, "message": "API key not valid. Please pass a valid API key.", "status": "INVALID_ARGUMENT"}}],
            "auth",
            "GEMINI_API_KEY",
        ),
        (404, {"error": {"message": "models/nope is not found"}}, "not_found", "model IDs"),
        (503, {"error": {"message": "The model is overloaded."}}, "server", "had a problem"),
    ],
    ids=["rate-limited", "bad-key", "unknown-model", "server"],
)
def test_errors_become_plain_messages(status, body, kind, words):
    provider = mock_provider([httpx2.Response(status, json=body)], [])
    with pytest.raises(ProviderError) as caught:
        stream_all(provider)
    error = caught.value
    assert error.kind == kind
    assert words in error.message
    assert error.detail.startswith(f"HTTP {status}: ")
    # Neither the creator's message nor the log line repeats the prompt.
    assert PROMPT not in error.message and PROMPT not in error.detail


def rate_limited():
    return httpx2.Response(
        429, json=[{"error": {"code": 429, "message": "Resource has been exhausted (e.g. check quota).", "status": "RESOURCE_EXHAUSTED"}}]
    )


def test_a_rate_limit_is_tried_again_then_the_fallback_model_then_a_card(make_client):
    models = load_prompts().models
    model_id = models.character_models("gemini")[0]
    fallback = models.fallback_for(model_id)
    requests = []
    provider = mock_provider([rate_limited() for _ in range(4)], requests)
    client = make_client(provider=provider, workbench_provider="gemini", gemini_api_key="test-key")
    chat = client.post("/api/chats", json={"character": "harry", "scenario": "F2", "model": model_id}).json()

    events = sse_events(client.post(f"/api/chats/{chat['id']}/next").text)
    name, error = events[-1]
    assert (name, error["retry"], error["partial"]) == ("error", True, None)
    assert "free limit" in error["message"]
    # Two pauses that double, then the other Flash-Lite model, which has its own free quota.
    notes = [(data["reason"], data["seconds"], data["message"]) for name, data in events if name == "wait" and data["reason"] != "slot"]
    assert notes == [
        ("retry", 2.0, "The model service is busy. Trying again in 2 s."),
        ("retry", 4.0, "The model service is busy. Trying again in 4 s."),
        ("fallback", 0, f"{models.models[model_id].label} is still busy, so {models.models[fallback].label} answers this turn."),
    ]
    assert [request["body"]["model"] for request in requests] == [model_id, model_id, model_id, fallback]
    detail = "HTTP 429: Resource has been exhausted (e.g. check quota)."
    assert query(client, "SELECT attempt, fallback, model_asked, status, error FROM model_calls ORDER BY id") == [
        {"attempt": 1, "fallback": 0, "model_asked": model_id, "status": "error", "error": detail},
        {"attempt": 2, "fallback": 0, "model_asked": model_id, "status": "error", "error": detail},
        {"attempt": 3, "fallback": 0, "model_asked": model_id, "status": "error", "error": detail},
        {"attempt": 4, "fallback": 1, "model_asked": fallback, "status": "error", "error": detail},
    ]


def test_the_fallback_model_answers_when_the_first_stays_busy(make_client):
    models = load_prompts().models
    model_id = models.character_models("gemini")[0]
    fallback = models.fallback_for(model_id)
    requests = []
    provider = mock_provider([*(rate_limited() for _ in range(3)), gemini_reply("Hi, Alex.", fallback)], requests)
    client = make_client(provider=provider, workbench_provider="gemini", gemini_api_key="test-key")
    chat = client.post("/api/chats", json={"character": "harry", "scenario": "F2", "model": model_id}).json()

    name, done = sse_events(client.post(f"/api/chats/{chat['id']}/next").text)[-1]
    assert name == "done"
    reply = done["message"]
    assert (reply["text"], reply["model"], reply["fallback"], reply["failed"]) == ("Hi, Alex.", fallback, True, False)
    # The fallback model gets the same messages, with its own reasoning effort.
    assert requests[3]["body"]["messages"] == requests[0]["body"]["messages"]
    assert requests[3]["body"]["reasoning_effort"] == models.models[fallback].reasoning_effort
    # The chat keeps its own model; only the one reply came from the fallback.
    assert client.get(f"/api/chats/{chat['id']}").json()["model"] == model_id


def test_a_provider_without_a_key_never_sends_a_request():
    requests = []
    provider = mock_provider([], requests, api_key="")
    assert provider.ready is False
    with pytest.raises(ProviderError, match="GEMINI_API_KEY"):
        stream_all(provider)
    assert requests == []
