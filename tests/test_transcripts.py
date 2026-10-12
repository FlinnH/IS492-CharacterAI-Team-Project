"""M2 import tests: pasted chats keep their speakers, order, and numbering; the
samples match the CP2 data; the scripts match the protocol word for word.

The fixtures in tests/fixtures/ are made up. The seeded transcript is never
opened here: its test uses a synthetic table set through the path setting.
"""

import json
import pathlib
import re

import pytest

from conftest import FIXTURES_DIR, REPO_DIR, query
from workbench import transcripts

PROTOCOL = REPO_DIR / "validation" / "PROMPTING_PROTOCOL.md"
SAMPLES_DIR = REPO_DIR / "app" / "samples"
SCRIPT_HEADINGS = [
    "T1: normal dialogue",
    "E1: long conversation",
    "E2: change in emotional behavior",
    "F1: adversarial persona challenge",
    "F2: knowledge boundary",
]


def fixture(name):
    return (FIXTURES_DIR / name).read_text(encoding="utf-8")


def paste(client, text, **fields):
    return client.post("/api/imports", json={"source": "paste", "character": "harry", "text": text, **fields})


def messages_of(view):
    return [(m["turn"], m["speaker"], m["text"]) for m in view["messages"]]


JSON_CHAT = {
    "format": "workbench-chat.v1",
    "title": "JSON test chat",
    "tool": "Example",
    "receipt": "EX-1",
    "character": "harry",
    "spec_version": 1,
    "user_name": "Alex",
    "character_name": "Harry",
    "numbering": "turn",
    "messages": [
        {"turn": 2, "speaker": "user", "text": "Hi."},
        {"turn": 2, "speaker": "character", "text": "Hello.\n\nWho's asking?"},
        {"turn": 3, "speaker": "user", "text": "Alex."},
    ],
}

IMPORTS = {
    # name: (text, format, numbering, the messages it should keep)
    "receipt": (
        fixture("receipt_chat.txt"),
        "receipt",
        "turn",
        [
            (2, "user", "Hello, Harry. Nice weather today."),
            (2, "character", "It's all right, I suppose."),
            (3, "user", "Do you like Quidditch?"),
            (3, "character", "Yeah, I play Seeker.\n\nBest thing about school, honestly."),
            # Turn 4 was never sent, and turn 5 was sent twice. Both stay as the log has them.
            (5, "user", "Are you going back in September?"),
            (5, "character", "Course I am."),
            (5, "user", "Are you going back in September?"),
            (5, "character", "You already asked that."),
        ],
    ),
    "inline": (
        fixture("inline_chat.txt"),
        "inline",
        "turn",
        [
            # No numbers in the source, so each user line starts a turn.
            (1, "user", "Hi Harry."),
            (1, "character", "Oh. Hi."),
            (2, "user", "What did you do today?"),
            # A rare "Word:" is part of the message above, not a third speaker.
            (2, "character", "Not much. Weeded the garden.\nNote: my aunt made me do it."),
            (3, "user", "Sounds dull."),
            (3, "character", "It was."),
        ],
    ),
    "table": (
        fixture("table_chat.md"),
        "table",
        "line",
        [
            (1, "user", "Morning, Harry."),
            (2, "character", "Morning."),
            (3, "user", "Is it true you've got a broom | a fast one?"),
            (4, "character", "It's a Firebolt.\nSirius sent it."),
            (5, "user", "Lucky."),
            (6, "character", "I know."),
        ],
    ),
    "json": (
        json.dumps(JSON_CHAT),
        "json",
        "turn",
        [(2, "user", "Hi."), (2, "character", "Hello.\n\nWho's asking?"), (3, "user", "Alex.")],
    ),
}


@pytest.mark.parametrize("name", IMPORTS)
def test_import_keeps_speakers_and_turn_order(make_client, name):
    text, expected_format, numbering, expected = IMPORTS[name]
    client = make_client()

    preview = client.post("/api/imports/preview", json={"source": "paste", "character": "harry", "text": text})
    assert preview.status_code == 200, preview.text
    assert (preview.json()["format"], preview.json()["problems"]) == (expected_format, [])

    response = paste(client, text)
    assert response.status_code == 201, response.text
    view = response.json()
    assert messages_of(view) == expected
    assert [m["seq"] for m in view["messages"]] == list(range(1, len(expected) + 1))
    assert all(m["source"] == "import" and not m["stopped"] for m in view["messages"])
    assert (view["numbering"], view["user_name"], view["character_name"]) == (numbering, "Alex", "Harry")
    assert (view["kind"], view["status"], view["spec_version"]) == ("import", "imported", 1)
    # What was saved reads back the same after a restart.
    assert messages_of(make_client().get(f"/api/chats/{view['id']}").json()) == expected


def test_preview_says_what_it_read_and_what_it_skipped(make_client):
    preview = make_client().post(
        "/api/imports/preview", json={"source": "paste", "character": "harry", "text": fixture("receipt_chat.txt")}
    ).json()

    assert (preview["message_count"], preview["first_number"], preview["last_number"]) == (8, 2, 5)
    assert [(s["label"], s["count"], s["role"]) for s in preview["speakers"]] == [("Alex", 4, "user"), ("Harry", 4, "character")]
    assert preview["needs_roles"] is False
    lines = fixture("receipt_chat.txt").split("\n")
    skipped = {lines[row - 1].strip() for row in preview["skipped_rows"]}
    assert "Turn 1: spec pasted. Reply (not scored):" in skipped
    assert "Ready when you are." in skipped
    assert "[Restored from the script: this line was missing from the saved chat.]" in skipped
    assert "[Turn 4 was skipped by mistake and never sent.]" in skipped
    assert [row["text"] for row in preview["first_rows"]][:1] == ["Hello, Harry. Nice weather today."]


def test_problems_name_rows_and_never_echo_text(make_client):
    client = make_client()
    text = fixture("bad_rows.md")

    preview = client.post("/api/imports/preview", json={"source": "paste", "character": "harry", "text": text})
    problems = preview.json()["problems"]
    assert [problem["row"] for problem in problems] == [4, 5]
    assert "no speaker" in problems[0]["message"]
    assert "4 cells" in problems[1]["message"]
    # The message names the row, never what's in it.
    assert "Zebra" not in json.dumps(problems)

    response = paste(client, text)
    assert response.status_code == 422
    assert [problem["row"] for problem in response.json()["problems"]] == [4, 5]
    assert "Zebra" not in json.dumps(response.json())
    assert client.get("/api/chats").json() == []


def test_the_creator_names_the_character_when_the_labels_dont(make_client):
    client = make_client()
    text = "Sam: Hello.\nRobin: Hi there.\nSam: Nice day.\nRobin: It is.\n"

    preview = client.post("/api/imports/preview", json={"source": "paste", "character": "harry", "text": text}).json()
    assert preview["needs_roles"] is True

    refused = paste(client, text)
    assert refused.status_code == 422
    assert "Sam or Robin" in refused.json()["detail"]

    view = paste(client, text, character_label="Robin").json()
    assert [m["speaker"] for m in view["messages"]] == ["user", "character", "user", "character"]
    assert (view["user_name"], view["character_name"]) == ("Sam", "Robin")


def test_importing_the_same_chat_again_returns_the_saved_one(make_client):
    client = make_client()
    first = client.post("/api/imports", json={"source": "sample", "sample": "cla-f2", "character": "harry"})
    again = client.post("/api/imports", json={"source": "sample", "sample": "cla-f2", "character": "harry"})
    assert (first.status_code, again.status_code) == (201, 200)
    assert again.json()["id"] == first.json()["id"]

    pasted = paste(client, fixture("inline_chat.txt"))
    pasted_again = paste(client, fixture("inline_chat.txt"))
    assert (pasted.status_code, pasted_again.status_code) == (201, 200)
    assert len(client.get("/api/chats").json()) == 2
    assert [row["kind"] for row in query(client, "SELECT kind FROM events ORDER BY id")] == ["import", "import"]


def test_a_chat_over_the_size_limit_is_refused(make_client):
    response = paste(make_client(workbench_max_import_chars=100), "Alex: " + "a" * 100)
    assert response.status_code == 422
    assert "WORKBENCH_MAX_IMPORT_CHARS" in response.json()["detail"]


def sample_messages(run, scenario):
    replies = {reply["turn"]: reply["text"] for reply in run["replies"]}
    messages = []
    for line in scenario["userLines"]:
        messages.append({"turn": line["turn"], "speaker": "user", "text": line["text"]})
        messages.append({"turn": line["turn"], "speaker": "character", "text": replies[line["turn"]]})
    return messages


@pytest.mark.parametrize("run_id", ["cla-f2", "gpt-f2"])
def test_samples_match_prototype_data(prototype_data, run_id):
    run = next(run for run in prototype_data["runs"] if run["id"] == run_id)
    scenario = prototype_data["scenario"]
    sample = json.loads((SAMPLES_DIR / f"{run_id}.json").read_text(encoding="utf-8"))

    assert sample["messages"] == sample_messages(run, scenario)
    assert (sample["tool"], sample["receipt"], sample["scenario"]) == (run["tool"], run["receipt"], run["scenarioId"])
    assert f"v{sample['spec_version']}" == run["specVersion"]
    assert sample["source"] == run["source"]
    assert (sample["user_name"], sample["character_name"]) == (scenario["userName"], scenario["characterName"])
    # ASCII, like data.js, with curly apostrophes kept as escapes.
    assert (SAMPLES_DIR / f"{run_id}.json").read_bytes().isascii()


@pytest.mark.parametrize(("log", "receipt"), [("claude_outputs.md", "CLA-F2"), ("chatgpt_outputs.md", "GPT-F2")])
def test_receipt_logs_parse_to_the_samples(log, receipt):
    # Only the F2 block is read; the review blocks in these files are never parsed.
    text = (REPO_DIR / "validation" / "transcripts" / log).read_text(encoding="utf-8")
    block = text[text.index(f"\n## {receipt}\n") + 1 :]
    end = block.find("\n## ")
    parsed = transcripts.parse(block if end == -1 else block[:end])

    assert (parsed.format, parsed.problems) == ("receipt", [])
    sample = json.loads((SAMPLES_DIR / f"{receipt.lower()}.json").read_text(encoding="utf-8"))
    speakers = {"Alex": "user", "Harry": "character"}
    got = [{"turn": row.number, "speaker": speakers[row.label], "text": row.text} for row in parsed.rows]
    assert got == sample["messages"]


def protocol_scripts():
    """{scenario ID: [(turn, text)]} from the five chat scripts in PROMPTING_PROTOCOL.md."""
    protocol = PROTOCOL.read_text(encoding="utf-8")
    scripts = {}
    for heading in SCRIPT_HEADINGS:
        start = protocol.index(f"\n### {heading}\n") + 1
        end = protocol.find("\n### ", start + 4)
        section = protocol[start : end if end != -1 else len(protocol)].split("**Probe key")[0]
        lines = re.findall(r"^\*\*Turn (\d+)[^*\n]*\*\*\n```\n(.*?)\n```$", section, re.M | re.S)
        scripts[heading.split(":")[0]] = [(int(turn), text) for turn, text in lines]
    return scripts


def test_scenarios_match_the_protocol_word_for_word(prototype_data):
    data = json.loads((SAMPLES_DIR / "scenarios.v1.json").read_text(encoding="utf-8"))
    scenarios = {s["id"]: s for s in data["scenarios"]}

    assert list(scenarios) == ["T1", "E1", "E2", "F1", "F2"]
    assert [scenarios[s]["name"] for s in scenarios] == SCRIPT_HEADINGS
    for scenario_id, lines in protocol_scripts().items():
        assert [(line["turn"], line["text"]) for line in scenarios[scenario_id]["lines"]] == lines, scenario_id
    assert {s: len(scenarios[s]["lines"]) for s in scenarios} == {"T1": 7, "E1": 19, "E2": 9, "F1": 8, "F2": 10}
    # F1's emoji is part of the script.
    assert "\U0001f480" in next(line["text"] for line in scenarios["F1"]["lines"] if line["turn"] == 3)
    assert [(line["turn"], line["text"]) for line in scenarios["F2"]["lines"]] == [
        (line["turn"], line["text"]) for line in prototype_data["scenario"]["userLines"]
    ]


def test_seeded_transcript_loads_only_when_picked(make_client, tmp_path, monkeypatch):
    seeded = tmp_path / "seeded_like.md"
    seeded.write_text(
        "| Line | Speaker | Text |\n| --- | --- | --- |\n| 1 | Alex | Hi, Harry. |\n| 2 | Harry | Hi. |\n",
        encoding="utf-8",
    )
    reads = []
    real_read_text = pathlib.Path.read_text

    def recording_read_text(self, *args, **kwargs):
        reads.append(pathlib.Path(self))
        return real_read_text(self, *args, **kwargs)

    monkeypatch.setattr(pathlib.Path, "read_text", recording_read_text)
    client = make_client(workbench_seeded_transcript_path=str(seeded))

    listed = {sample["id"]: sample for sample in client.get("/api/samples").json()}
    assert set(listed) == {"cla-f2", "gpt-f2", "seeded"}
    assert (listed["seeded"]["path"], listed["seeded"]["available"], listed["seeded"]["spec_version"]) == (str(seeded), True, 1)
    assert seeded not in reads

    response = client.post("/api/imports", json={"source": "sample", "sample": "seeded", "character": "harry"})
    assert response.status_code == 201, response.text
    assert seeded in reads
    view = response.json()
    assert (view["kind"], view["sample"], view["title"], view["numbering"]) == ("sample", "seeded", "Seeded transcript", "line")
    assert messages_of(view) == [(1, "user", "Hi, Harry."), (2, "character", "Hi.")]


def test_listing_samples_never_opens_the_real_seeded_transcript(make_client):
    # The default path points at the hidden file. The guard in conftest fails
    # this test if anything opens it; listing only checks that it exists.
    listed = {sample["id"]: sample for sample in make_client().get("/api/samples").json()}
    assert listed["seeded"]["path"].endswith("SEEDED_TRANSCRIPT.md")


def test_the_seeded_transcript_reports_a_missing_file(make_client, tmp_path):
    client = make_client(workbench_seeded_transcript_path=str(tmp_path / "missing.md"))
    assert {s["id"]: s["available"] for s in client.get("/api/samples").json()}["seeded"] is False
    response = client.post("/api/imports", json={"source": "sample", "sample": "seeded", "character": "harry"})
    assert response.status_code == 422
    assert "isn't at" in response.json()["detail"]
