"""M8 demo prep: the reset copies the old database first, then a known-good
one replaces it, with the judge snapshot saved as the samples' checks.
Preflight flags a retired or rerouted model. Every database here lives in the
test's own folder, and the model is the fake one."""

import importlib.util
from datetime import datetime

import pytest

from conftest import APP_DIR, default_model, query, sample_messages, settings_for
from test_judge import UMBRIDGE, check, import_sample, judge_reply
from test_review import judged, post
from workbench import db, transcripts
from workbench.config import load_prompts
from workbench.judge import SNAPSHOT_FILE, load_snapshot
from workbench.schemas import JudgeOutput, JudgeSnapshot, SnapshotCall, SnapshotCheck

NOW = datetime(2026, 10, 30, 9, 15, 0)
CHECKED_AT = "2026-10-20T23:30:47.096Z"
# Every table a reset with no snapshot leaves empty. app_settings is among
# them, since a server that starts later adds its own startup row.
EMPTY_TABLES = (
    "events",
    "model_calls",
    "judge_runs",
    "flags",
    "rejected_flags",
    "not_checked",
    "rechecks",
    "flag_changes",
    "app_settings",
)


def load_script(name):
    spec = importlib.util.spec_from_file_location(name, APP_DIR / "scripts" / f"{name}.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


@pytest.fixture
def reset_demo(monkeypatch):
    module = load_script("reset_demo")
    # Tests have no network, so the check for a running server always says no.
    monkeypatch.setattr(module, "server_running", lambda settings: False)
    return module


def counts(database):
    with database.connect() as conn:
        tables = [row[0] for row in conn.execute("SELECT name FROM sqlite_master WHERE type = 'table' ORDER BY name")]
        return {table: conn.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0] for table in tables}


def rehearse(make_client):
    """Leaves what a rehearsal leaves: a checked sample with a call on a flag, a live run, and their events."""
    client = make_client(provider=judged(judge_reply(UMBRIDGE)))
    chat_id = import_sample(client, "cla-f2")
    check(client, chat_id)
    flag_id = query(client, "SELECT id FROM flags WHERE transcript_id = ? ORDER BY id LIMIT 1", (chat_id,))[0]["id"]
    assert post(client, flag_id, "evidence").status_code == 200
    assert post(client, flag_id, "agree").status_code == 200
    started = client.post("/api/chats", json={"character": "harry", "scenario": "F2", "model": default_model()})
    assert started.status_code == 201, started.text
    return client.app.state.database


def write_snapshot(reset_demo, tmp_path, answer, **changes):
    """A judge snapshot of CLA-F2, made for today's fake judge unless changes say otherwise."""
    maker = db.Database(tmp_path / "maker" / "workbench.db")
    settings = settings_for(tmp_path / "maker")
    chats = reset_demo.build(maker, settings)
    judge, _ = reset_demo.make_judge(maker, settings)
    chat = transcripts.get_chat(maker, chats["cla-f2"], scenarios=judge.scenarios)
    prompts = load_prompts()
    values = {
        "sample": "cla-f2",
        "transcript_sha256": judge.transcript_sha256(chat),
        "model": judge.model_id(),
        "reasoning_effort": judge.effort(),
        "prompt_version": prompts.judge_version,
        "schema_version": prompts.judge_schema_version,
        "checked_at": CHECKED_AT,
        "call": SnapshotCall(latency_ms=2821, input_tokens=4300, output_tokens=150, reasoning_tokens=0, est_cost_usd=0.002),
        "answer": JudgeOutput.model_validate_json(answer),
        **changes,
    }
    snapshot = JudgeSnapshot(format="workbench-judge-snapshot.v1", note="For tests.", checks=[SnapshotCheck(**values)])
    path = tmp_path / "judge_snapshot.json"
    path.write_text(snapshot.model_dump_json(), encoding="utf-8")
    return path


# The reset.


def test_reset_backs_up_the_old_database_then_leaves_only_the_demo_state(reset_demo, make_client, tmp_path, capsys):
    old = rehearse(make_client)
    before = counts(old)
    assert before["events"] and before["model_calls"] and before["flags"]

    assert reset_demo.main(settings_for(tmp_path), now=NOW, snapshot=None) == 0

    # The backup holds everything the old database had.
    backup = tmp_path / "backups" / "workbench-2026-10-30-091500.db"
    assert counts(db.Database(backup)) == before

    fresh = db.Database(tmp_path / "workbench.db")
    after = counts(fresh)
    assert {table: after[table] for table in EMPTY_TABLES} == dict.fromkeys(EMPTY_TABLES, 0)
    assert after["spec_versions"] == 1
    chats = query(fresh, "SELECT kind, sample, status, session FROM transcripts ORDER BY id")
    assert chats == [
        {"kind": "sample", "sample": "cla-f2", "status": "imported", "session": None},
        {"kind": "sample", "sample": "gpt-f2", "status": "imported", "session": None},
    ]
    assert after["messages"] == len(sample_messages("cla-f2")) + len(sample_messages("gpt-f2"))
    with fresh.connect() as conn:
        # Fully migrated, so migrate finds nothing left to apply.
        version = conn.execute("PRAGMA user_version").fetchone()[0]
        assert db.migrate(conn) == version
    # Only the database and the backup folder are left: no half-built file.
    assert sorted(path.name for path in tmp_path.iterdir() if path.name.startswith("workbench")) == ["workbench.db"]

    printed = capsys.readouterr().out
    assert "Claude (CLA-F2) and ChatGPT (GPT-F2)" in printed
    assert "To undo:" in printed


def test_a_server_that_starts_after_the_reset_shows_the_demo_state(reset_demo, make_client, tmp_path):
    rehearse(make_client)
    assert reset_demo.main(settings_for(tmp_path), now=NOW, snapshot=None) == 0

    client = make_client()
    chats = client.get("/api/chats").json()
    # Newest first, as the Chat menu lists them.
    assert [chat["title"] for chat in chats] == ["ChatGPT (GPT-F2)", "Claude (CLA-F2)"]
    assert client.get("/api/review").json()["chats"] == []
    assert client.get("/api/characters/harry/specs/latest").json()["version"] == 1


def test_reset_refuses_while_the_server_runs(reset_demo, make_client, tmp_path, monkeypatch, capsys):
    old = rehearse(make_client)
    before = counts(old)
    monkeypatch.setattr(reset_demo, "server_running", lambda settings: True)

    assert reset_demo.main(settings_for(tmp_path), now=NOW) == 1

    assert counts(old) == before
    assert not (tmp_path / "backups").exists()
    assert "Stop it first" in capsys.readouterr().out


def test_without_a_database_the_reset_makes_one_and_backs_up_nothing(reset_demo, tmp_path, capsys):
    assert reset_demo.main(settings_for(tmp_path), now=NOW, snapshot=None) == 0

    assert not (tmp_path / "backups").exists()
    assert [row["sample"] for row in query(db.Database(tmp_path / "workbench.db"), "SELECT sample FROM transcripts ORDER BY id")] == [
        "cla-f2",
        "gpt-f2",
    ]
    assert "nothing to back up" in capsys.readouterr().out


def test_two_resets_in_one_second_keep_both_backups(reset_demo, make_client, tmp_path):
    rehearse(make_client)
    assert reset_demo.main(settings_for(tmp_path), now=NOW, snapshot=None) == 0
    assert reset_demo.main(settings_for(tmp_path), now=NOW, snapshot=None) == 0

    assert sorted(path.name for path in (tmp_path / "backups").iterdir()) == [
        "workbench-2026-10-30-091500-2.db",
        "workbench-2026-10-30-091500.db",
    ]


def test_a_reset_that_fails_partway_leaves_the_old_database_in_place(reset_demo, make_client, tmp_path, monkeypatch):
    old = rehearse(make_client)
    before = counts(old)

    def broken(*args, **kwargs):
        raise RuntimeError("a sample failed to load")

    monkeypatch.setattr(transcripts, "import_chat", broken)
    with pytest.raises(RuntimeError, match="a sample failed to load"):
        reset_demo.main(settings_for(tmp_path), now=NOW, snapshot=None)

    assert counts(old) == before
    assert not (tmp_path / "workbench.db.reset").exists()
    # The backup was made before anything else, and it stays.
    assert counts(db.Database(tmp_path / "backups" / "workbench-2026-10-30-091500.db")) == before


# The judge snapshot.


def test_after_a_reset_checking_cla_f2_needs_no_model_call(reset_demo, make_client, tmp_path, capsys):
    snapshot = write_snapshot(reset_demo, tmp_path, judge_reply(UMBRIDGE))
    assert reset_demo.main(settings_for(tmp_path), now=NOW, snapshot=snapshot) == 0
    printed = capsys.readouterr().out
    assert "cla-f2: the saved check from Oct 2" in printed
    assert "with 2 flags (1 from automatic checks and 1 from the AI judge)." in printed

    client = make_client()
    cla_f2 = next(chat["id"] for chat in client.get("/api/chats").json() if chat["title"] == "Claude (CLA-F2)")
    view = check(client, cla_f2)

    assert view["cached"] is True
    assert [(flag["source"], flag["turn"]) for flag in view["flags"]] == [("rule", 2), ("judge", 4)]
    assert view["judge"]["checked_at"] == CHECKED_AT
    assert query(client, "SELECT COUNT(*) AS n FROM model_calls WHERE role = 'judge'")[0]["n"] == 0
    run = query(client, "SELECT attempts, model_call_id, session FROM judge_runs")
    assert run == [{"attempts": 0, "model_call_id": None, "session": None}]
    # The flags need the creator's call like any other, and nothing is logged yet.
    review = client.get("/api/review").json()
    assert [item["chat"]["id"] for item in review["chats"]] == [cla_f2]
    assert query(client, "SELECT COUNT(*) AS n FROM events")[0]["n"] == 0
    # GPT-F2 has no answer in this snapshot, so it starts unchecked.
    gpt_f2 = next(chat["id"] for chat in client.get("/api/chats").json() if chat["title"] == "ChatGPT (GPT-F2)")
    assert client.get(f"/api/chats/{gpt_f2}/check").json()["result"] is None


def test_a_snapshot_quote_that_fails_the_evidence_checks_stays_hidden(reset_demo, make_client, tmp_path):
    made_up = {**UMBRIDGE, "quote": "Umbridge is the new Defence teacher."}
    snapshot = write_snapshot(reset_demo, tmp_path, judge_reply(made_up))
    assert reset_demo.main(settings_for(tmp_path), now=NOW, snapshot=snapshot) == 0

    client = make_client()
    view = check(client, 1)
    assert [flag["source"] for flag in view["flags"]] == ["rule"]
    assert view["hidden"] == [{"reason": "quote_not_found", "count": 1}]


@pytest.mark.parametrize(
    ("changes", "says"),
    [
        ({"model": "another-judge"}, "another judge model another-judge"),
        ({"prompt_version": "judge.v0"}, "prompt judge.v0"),
        ({"transcript_sha256": "0" * 64}, "a different version of this chat"),
    ],
)
def test_a_snapshot_that_doesnt_fit_today_is_skipped_with_a_warning(reset_demo, tmp_path, capsys, changes, says):
    snapshot = write_snapshot(reset_demo, tmp_path, judge_reply(UMBRIDGE), **changes)
    assert reset_demo.main(settings_for(tmp_path), now=NOW, snapshot=snapshot) == 0

    printed = capsys.readouterr().out
    assert "Warning: the judge snapshot for cla-f2 doesn't fit today's judge." in printed
    assert says in printed
    assert counts(db.Database(tmp_path / "workbench.db"))["judge_runs"] == 0


def test_a_missing_snapshot_leaves_the_samples_unchecked(reset_demo, tmp_path, capsys):
    assert reset_demo.main(settings_for(tmp_path), now=NOW, snapshot=tmp_path / "none.json") == 0
    assert "Warning: there's no judge snapshot" in capsys.readouterr().out
    assert counts(db.Database(tmp_path / "workbench.db"))["judge_runs"] == 0


def test_the_saved_snapshot_fits_the_samples_and_the_judge_prompt(reset_demo, tmp_path):
    # A sample or a judge prompt that changes needs a new snapshot, or the reset would skip it.
    snapshot = load_snapshot(SNAPSHOT_FILE)
    assert SNAPSHOT_FILE.read_bytes().isascii()
    assert [check.sample for check in snapshot.checks] == list(reset_demo.DEMO_SAMPLES)
    prompts = load_prompts()
    maker = db.Database(tmp_path / "workbench.db")
    settings = settings_for(tmp_path)
    chats = reset_demo.build(maker, settings)
    judge, _ = reset_demo.make_judge(maker, settings)
    for saved in snapshot.checks:
        chat = transcripts.get_chat(maker, chats[saved.sample], scenarios=judge.scenarios)
        assert saved.transcript_sha256 == judge.transcript_sha256(chat)
        assert (saved.prompt_version, saved.schema_version) == (prompts.judge_version, prompts.judge_schema_version)
        assert saved.model == prompts.models.judge_model("gemini")
        assert saved.reasoning_effort == prompts.models.judge_effort(saved.model)


# Preflight.


def test_preflight_flags_a_retired_or_rerouted_model():
    preflight = load_script("preflight")
    reported = {"model-a": {"model-a"}, "model-b": {"model-b-2026-10-01"}, "model-c": {"model-d"}}

    assert preflight.model_problems(["model-a", "model-b", "model-c"], {"model-a", "model-b", "model-c"}, reported) == [
        "model-c was answered by model-d, so the service reroutes it."
    ]
    assert preflight.model_problems(["model-a", "model-gone"], {"model-a"}, {}) == [
        "model-gone isn't in the service's model list any more, so it may be retired."
    ]
    # A model list that couldn't be read says nothing either way.
    assert preflight.model_problems(["model-gone"], None, {}) == []
