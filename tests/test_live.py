"""The live test: 3 turns of F2 against the provider in app/.env.

It runs only with --live:

    app/.venv/bin/pytest tests/test_live.py --live -s

It's the only test that reads app/.env, and it uses about 3 free-tier calls.
Its database lives in a temp folder, so app/data stays as it was. It prints
the logged model_calls rows, which hold no chat text.
"""

import pytest
from fastapi.testclient import TestClient

from conftest import query, sse_events
from workbench.config import load_settings
from workbench.main import create_app

pytestmark = pytest.mark.live

COLUMNS = (
    "id",
    "role",
    "turn",
    "provider",
    "model_asked",
    "model_reported",
    "prompt_version",
    "settings_version",
    "reasoning_effort",
    "ttft_ms",
    "latency_ms",
    "input_tokens",
    "cached_tokens",
    "output_tokens",
    "reasoning_tokens",
    "est_cost_usd",
    "status",
    "error",
)


def print_rows(rows):
    cells = [list(COLUMNS)] + [["" if row[column] is None else str(row[column]) for column in COLUMNS] for row in rows]
    widths = [max(len(line[i]) for line in cells) for i in range(len(COLUMNS))]
    print()
    for index, line in enumerate(cells):
        print("  ".join(cell.ljust(width) for cell, width in zip(line, widths)).rstrip())
        if index == 0:
            print("  ".join("-" * width for width in widths))


def test_three_turns_of_f2_against_the_configured_provider(tmp_path):
    settings = load_settings()
    if settings.workbench_provider == "fake":
        pytest.skip("WORKBENCH_PROVIDER is fake in app/.env, so there is no model service to call.")
    settings = settings.model_copy(update={"workbench_db_path": tmp_path / "live.db"})
    client = TestClient(create_app(settings))

    options = client.get("/api/run-options").json()
    assert options["key_set"], "Add the key to app/.env first."
    chat = client.post("/api/chats", json={"character": "harry", "scenario": "F2", "model": options["default_model"]})
    assert chat.status_code == 201, chat.text
    chat_id = chat.json()["id"]

    for _ in range(3):
        events = sse_events(client.post(f"/api/chats/{chat_id}/next").text)
        name, payload = events[-1]
        assert name == "done", payload
        assert payload["message"]["text"].strip()

    rows = query(client, "SELECT * FROM model_calls ORDER BY id")
    print_rows(rows)
    assert len(rows) == 3
    for row in rows:
        assert (row["role"], row["status"], row["error"]) == ("character", "ok", None)
        assert row["model_asked"] == options["default_model"] and row["model_reported"]
        assert row["ttft_ms"] is not None and row["latency_ms"] >= row["ttft_ms"]
        assert row["input_tokens"] > 0 and row["output_tokens"] > 0
        assert row["est_cost_usd"] is not None
    # Each later turn starts at least 60/N seconds after the one before.
    assert [row["turn"] for row in rows] == [2, 3, 4]
