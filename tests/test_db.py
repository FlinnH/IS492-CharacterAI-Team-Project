"""M1 database tests: saved spec rows never change, and migrations are all or nothing."""

import shutil
import sqlite3

import pytest

from workbench import db


def table_names(conn):
    return sorted(row[0] for row in conn.execute("SELECT name FROM sqlite_master WHERE type = 'table'"))


@pytest.fixture
def conn(tmp_path):
    """A migrated database with one character, its v1, and one line ID, inserted by hand."""
    with db.Database(tmp_path / "workbench.db").connect() as connection:
        db.migrate(connection)
        connection.execute("INSERT INTO characters (id, slug, name) VALUES (1, 'test', 'Test')")
        connection.execute(
            "INSERT INTO spec_versions (character_id, version, parent, body, sha256, note, created_at)"
            " VALUES (1, 1, NULL, '{}', 'hash', '', '2026-10-10T00:00:00Z')"
        )
        connection.execute("INSERT INTO line_ids (character_id, line_id, first_version) VALUES (1, 'X1', 1)")
        yield connection


@pytest.mark.parametrize(
    ("statement", "message"),
    [
        ("UPDATE spec_versions SET note = 'changed'", "immutable"),
        ("DELETE FROM spec_versions", "immutable"),
        # REPLACE deletes the old row without firing DELETE triggers, so it needs its own guard.
        (
            "INSERT OR REPLACE INTO spec_versions (character_id, version, parent, body, sha256, note, created_at)"
            " VALUES (1, 1, NULL, '{\"changed\": true}', 'other', '', '2026-10-11T00:00:00Z')",
            "immutable",
        ),
        ("UPDATE line_ids SET first_version = 2", "insert-only"),
        ("DELETE FROM line_ids", "insert-only"),
        ("INSERT OR REPLACE INTO line_ids (character_id, line_id, first_version) VALUES (1, 'X1', 1)", "insert-only"),
    ],
    ids=["update-version", "delete-version", "replace-version", "update-line-id", "delete-line-id", "replace-line-id"],
)
def test_spec_rows_reject_update_delete_and_replace(conn, statement, message):
    with pytest.raises(sqlite3.IntegrityError, match=message):
        conn.execute(statement)

    versions = [tuple(row) for row in conn.execute("SELECT version, body, sha256, note FROM spec_versions")]
    assert versions == [(1, "{}", "hash", "")]
    assert [tuple(row) for row in conn.execute("SELECT line_id, first_version FROM line_ids")] == [("X1", 1)]


@pytest.mark.parametrize(
    "statement",
    [
        # Reuses v2's row id for a forged v3, which would silently remove v2.
        "INSERT OR REPLACE INTO spec_versions (id, character_id, version, parent, body, sha256, note, created_at)"
        " VALUES (2, 1, 3, 1, '{}', 'forged', '', '2026-10-11T00:00:00Z')",
        # Reuses the first issued line ID's row, which would erase it.
        "INSERT OR REPLACE INTO line_ids (rowid, character_id, line_id, first_version) VALUES (1, 1, 'X2', 1)",
    ],
    ids=["replace-version-by-row-id", "replace-line-id-by-row-id"],
)
def test_replace_by_row_id_cannot_remove_saved_rows(conn, statement):
    conn.execute(
        "INSERT INTO spec_versions (id, character_id, version, parent, body, sha256, note, created_at)"
        " VALUES (2, 1, 2, 1, '{}', 'v2', '', '2026-10-10T01:00:00Z')"
    )

    with pytest.raises(sqlite3.Error):
        conn.execute(statement)

    assert [tuple(row) for row in conn.execute("SELECT version, sha256 FROM spec_versions ORDER BY version")] == [
        (1, "hash"),
        (2, "v2"),
    ]
    assert [tuple(row) for row in conn.execute("SELECT line_id FROM line_ids")] == [("X1",)]


def test_migrate_is_idempotent(tmp_path):
    with db.Database(tmp_path / "workbench.db").connect() as conn:
        version = db.migrate(conn)
        tables = table_names(conn)

        assert db.migrate(conn) == version
        assert table_names(conn) == tables
        assert {"characters", "spec_versions", "line_ids"} <= set(tables)


def test_failed_migration_leaves_no_trace(tmp_path):
    folder = tmp_path / "migrations"
    folder.mkdir()
    shutil.copy(db.MIGRATIONS_DIR / "001_specs.sql", folder)
    (folder / "002_broken.sql").write_text("CREATE TABLE half_done (x INTEGER);\nTHIS IS NOT SQL;\n")

    with db.Database(tmp_path / "workbench.db").connect() as conn:
        with pytest.raises(sqlite3.Error):
            db.migrate(conn, folder)

        assert conn.execute("PRAGMA user_version").fetchone()[0] == 1
        assert "half_done" not in table_names(conn)
        assert not conn.in_transaction


def test_newer_database_is_refused(tmp_path):
    with db.Database(tmp_path / "workbench.db").connect() as conn:
        conn.execute("PRAGMA user_version = 99")

        with pytest.raises(RuntimeError, match="workbench.db"):
            db.migrate(conn)


@pytest.fixture
def chat_conn(conn):
    """The migrated database above, plus one chat with a message, a model call, and an event."""
    conn.execute(
        "INSERT INTO transcripts (id, character_id, spec_version, kind, title, numbering, user_name, character_name,"
        " status, created_at) VALUES (1, 1, 1, 'live', 'Test run', 'turn', 'Alex', 'Harry', 'active', '2026-10-11T00:00:00Z')"
    )
    conn.execute(
        "INSERT INTO model_calls (id, started_at, quota_day, role, provider, model_asked, prompt_version,"
        " settings_version, status) VALUES (1, '2026-10-11T00:00:00Z', '2026-10-10', 'character', 'fake', 'test-model',"
        " 'character.v1', 'models.v1', 'ok')"
    )
    conn.execute(
        "INSERT INTO messages (id, transcript_id, seq, turn, speaker, text, source, model_call_id, created_at)"
        " VALUES (1, 1, 1, 2, 'character', 'Hello.', 'model', 1, '2026-10-11T00:00:00Z')"
    )
    conn.execute("INSERT INTO events (id, created_at, kind, transcript_id) VALUES (1, '2026-10-11T00:00:00Z', 'run_started', 1)")
    return conn


@pytest.mark.parametrize("table", ["messages", "model_calls", "events"])
@pytest.mark.parametrize(
    "statement",
    [
        "UPDATE {table} SET id = id",
        "DELETE FROM {table}",
    ],
    ids=["update", "delete"],
)
def test_logs_and_messages_are_append_only(chat_conn, table, statement):
    with pytest.raises(sqlite3.IntegrityError, match="append-only"):
        chat_conn.execute(statement.format(table=table))
    assert chat_conn.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0] == 1


@pytest.mark.parametrize(
    "statement",
    [
        "INSERT OR REPLACE INTO messages (id, transcript_id, seq, turn, speaker, text, source, created_at)"
        " VALUES (1, 1, 1, 2, 'character', 'Rewritten.', 'model', '2026-10-12T00:00:00Z')",
        "INSERT OR REPLACE INTO model_calls (id, started_at, quota_day, role, provider, model_asked, prompt_version,"
        " settings_version, status) VALUES (1, 'x', 'x', 'character', 'fake', 'other', 'v', 'v', 'error')",
        "INSERT OR REPLACE INTO events (id, created_at, kind) VALUES (1, 'x', 'import')",
    ],
    ids=["replace-message", "replace-model-call", "replace-event"],
)
def test_replace_cannot_rewrite_a_logged_row(chat_conn, statement):
    with pytest.raises(sqlite3.IntegrityError, match="append-only"):
        chat_conn.execute(statement)
    assert chat_conn.execute("SELECT text FROM messages").fetchone()[0] == "Hello."


@pytest.mark.parametrize(
    "statement",
    ["UPDATE transcripts SET spec_version = 2", "UPDATE transcripts SET model = 'other'", "UPDATE transcripts SET kind = 'import'"],
    ids=["spec-version", "model", "kind"],
)
def test_a_chat_keeps_its_spec_version_and_settings(chat_conn, statement):
    with pytest.raises(sqlite3.IntegrityError, match="keeps the spec version"):
        chat_conn.execute(statement)


def test_only_a_chats_status_changes_and_chats_are_kept(chat_conn):
    chat_conn.execute("UPDATE transcripts SET status = 'stopped'")
    assert chat_conn.execute("SELECT status FROM transcripts").fetchone()[0] == "stopped"
    with pytest.raises(sqlite3.IntegrityError, match="chats are kept"):
        chat_conn.execute("DELETE FROM transcripts")


def test_migration_002_makes_the_chat_tables(tmp_path):
    with db.Database(tmp_path / "workbench.db").connect() as conn:
        assert db.migrate(conn) >= 2
        assert {"transcripts", "messages", "model_calls", "events"} <= set(table_names(conn))


@pytest.fixture
def check_conn(chat_conn):
    """The chat above, plus a judge run with a rule flag, a judge flag, a hidden flag, and a not-checked topic."""
    chat_conn.execute(
        "INSERT INTO judge_runs (id, transcript_id, content_key, cache_key, prompt_version, schema_version, model,"
        " attempts, status, created_at) VALUES (1, 1, 'content', 'cache', 'judge.v1', 'judge.schema.v1', 'test-model',"
        " 1, 'ok', '2026-10-12T00:00:00Z')"
    )
    flag = (
        "INSERT INTO flags (id, transcript_id, content_key, run_id, source, turn, type, line_id, quote, confidence,"
        " first_confidence, why, created_at) VALUES ({id}, 1, 'content', {run}, '{source}', 2, 'style drift', 'X1',"
        " 'Hello.', 'high', 'high', 'Why.', '2026-10-12T00:00:00Z')"
    )
    chat_conn.execute(flag.format(id=1, run="NULL", source="rule"))
    chat_conn.execute(flag.format(id=2, run=1, source="judge"))
    chat_conn.execute(
        "INSERT INTO rejected_flags (id, run_id, transcript_id, reason, raw_json, created_at)"
        " VALUES (1, 1, 1, 'quote_not_found', '{}', '2026-10-12T00:00:00Z')"
    )
    chat_conn.execute(
        "INSERT INTO not_checked (id, run_id, transcript_id, topic, why, created_at)"
        " VALUES (1, 1, 1, 'Tone', 'Why.', '2026-10-12T00:00:00Z')"
    )
    return chat_conn


def test_migration_003_makes_the_check_tables(tmp_path):
    with db.Database(tmp_path / "workbench.db").connect() as conn:
        assert db.migrate(conn) >= 3
        assert {"judge_runs", "flags", "rejected_flags", "not_checked"} <= set(table_names(conn))


@pytest.mark.parametrize("table", ["judge_runs", "rejected_flags", "not_checked"])
@pytest.mark.parametrize("statement", ["UPDATE {table} SET id = id", "DELETE FROM {table}"], ids=["update", "delete"])
def test_judge_runs_and_what_they_hid_are_append_only(check_conn, table, statement):
    with pytest.raises(sqlite3.IntegrityError, match="append-only"):
        check_conn.execute(statement.format(table=table))
    assert check_conn.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0] == 1


@pytest.mark.parametrize(
    "statement",
    [
        "UPDATE flags SET quote = 'Changed.' WHERE id = 2",
        "UPDATE flags SET turn = 3 WHERE id = 2",
        "UPDATE flags SET line_id = 'X2' WHERE id = 2",
        "UPDATE flags SET first_confidence = 'low' WHERE id = 2",
    ],
    ids=["quote", "turn", "line", "first-confidence"],
)
def test_a_flag_keeps_its_evidence(check_conn, statement):
    with pytest.raises(sqlite3.IntegrityError, match="keeps its evidence"):
        check_conn.execute(statement)


def test_only_a_flags_status_and_confidence_change_and_flags_are_kept(check_conn):
    check_conn.execute("UPDATE flags SET status = 'withdrawn', confidence = 'low' WHERE id = 2")
    row = check_conn.execute("SELECT status, confidence, first_confidence FROM flags WHERE id = 2").fetchone()
    assert tuple(row) == ("withdrawn", "low", "high")
    with pytest.raises(sqlite3.IntegrityError, match="flags are kept"):
        check_conn.execute("DELETE FROM flags")
    with pytest.raises(sqlite3.IntegrityError, match="flags are kept"):
        check_conn.execute(
            "INSERT OR REPLACE INTO flags (id, transcript_id, content_key, source, turn, type, line_id, quote, confidence,"
            " first_confidence, why, created_at) VALUES (1, 1, 'content', 'rule', 9, 'style drift', 'X1', 'Other.',"
            " 'low', 'low', 'Why.', 'x')"
        )


def test_one_ok_judge_run_per_cache_key(check_conn):
    insert = (
        "INSERT INTO judge_runs (transcript_id, content_key, cache_key, prompt_version, schema_version, model, attempts,"
        " status, failure, created_at) VALUES (1, 'content', 'cache', 'judge.v1', 'judge.schema.v1', 'test-model', 2,"
        " '{status}', {failure}, '2026-10-12T00:01:00Z')"
    )
    # A failed run can sit beside the ok one, but a second ok run can't.
    check_conn.execute(insert.format(status="failed", failure="'schema'"))
    with pytest.raises(sqlite3.IntegrityError, match="UNIQUE"):
        check_conn.execute(insert.format(status="ok", failure="NULL"))


def test_rule_flags_have_no_run_and_judge_flags_need_one(check_conn):
    with pytest.raises(sqlite3.IntegrityError, match="CHECK"):
        check_conn.execute(
            "INSERT INTO flags (transcript_id, content_key, run_id, source, turn, type, line_id, quote, confidence,"
            " first_confidence, why, created_at) VALUES (1, 'content', NULL, 'judge', 2, 'style drift', 'X1', 'Hello.',"
            " 'high', 'high', 'Why.', 'x')"
        )


def test_migration_004_adds_calls_to_events(tmp_path):
    with db.Database(tmp_path / "workbench.db").connect() as conn:
        assert db.migrate(conn) >= 4
        columns = {row["name"] for row in conn.execute("PRAGMA table_info(events)")}
        assert {"flag_id", "flag_type"} <= columns
        assert [row[0] for row in conn.execute("SELECT name FROM sqlite_master WHERE type = 'view'")] == ["decisions"]


def call(conn, kind, flag_id=1, flag_type=None, reason=None):
    """One event on a flag of the check_conn chat, as review.py writes it."""
    conn.execute(
        "INSERT INTO events (created_at, kind, transcript_id, flag_id, flag_type, reason)"
        " VALUES ('2026-10-12T00:00:00Z', ?, 1, ?, ?, ?)",
        (kind, flag_id, flag_type, reason),
    )


@pytest.mark.parametrize(
    ("before", "refused", "message"),
    [
        ([], ("agree",), "after the evidence"),
        ([("evidence_opened",), ("agree",)], ("agree",), "one call at a time"),
        ([("evidence_opened",), ("agree",)], ("override", 1, None, "The quote is fine."), "one call at a time"),
        ([], ("undo",), "no call to undo"),
        ([], ("override", 1, None, "   "), "needs a reason"),
        ([], ("agree", None), "CHECK|after the evidence"),
        ([], ("evidence_opened", 1, "persona drift"), "CHECK"),
        ([], ("evidence_opened", 99), "FOREIGN KEY"),
    ],
    ids=[
        "agree-before-evidence",
        "second-agree",
        "override-while-agreed",
        "undo-without-a-call",
        "override-without-a-reason",
        "call-without-a-flag",
        "type-on-an-opening",
        "unknown-flag",
    ],
)
def test_the_database_backs_up_the_call_rules(check_conn, before, refused, message):
    # review.py refuses these first, with a plain message. The database refuses
    # them too, for any other connection.
    for event in before:
        call(check_conn, *event)
    with pytest.raises(sqlite3.IntegrityError, match=message):
        call(check_conn, *refused)
    assert check_conn.execute("SELECT COUNT(*) FROM events WHERE flag_id IS NOT NULL").fetchone()[0] == len(before)


def test_decisions_take_the_latest_call_per_flag(check_conn):
    call(check_conn, "evidence_opened")
    call(check_conn, "agree")
    call(check_conn, "undo")
    call(check_conn, "override", 1, "persona drift", "a b c")
    # Only the four flag calls must name a flag; another kind may, as a later re-check might.
    call(check_conn, "recheck", 2)
    rows = [tuple(row) for row in check_conn.execute("SELECT flag_id, kind, reason, flag_type FROM decisions")]
    assert rows == [(1, "override", "a b c", "persona drift")]


def test_migration_005_makes_the_recheck_tables(tmp_path):
    with db.Database(tmp_path / "workbench.db").connect() as conn:
        assert db.migrate(conn) >= 5
        assert {"rechecks", "flag_changes"} <= set(table_names(conn))
        assert "recheck_id" in {row["name"] for row in conn.execute("PRAGMA table_info(rejected_flags)")}


RECHECK = (
    "INSERT INTO rechecks (id, transcript_id, run_id, content_key, cache_key, prompt_version, schema_version, model,"
    " attempts, status, failure, created_at) VALUES ({id}, 1, 1, 'content', 'recheck-cache', 'recheck.v1',"
    " 'recheck.schema.v1', 'test-model', 1, '{status}', {failure}, '2026-10-17T00:00:00Z')"
)


@pytest.fixture
def recheck_conn(check_conn):
    """The check above, plus a re-check that re-rated the judge flag."""
    check_conn.execute(RECHECK.format(id=1, status="ok", failure="NULL"))
    check_conn.execute(
        "INSERT INTO flag_changes (id, recheck_id, flag_id, change, from_confidence, to_confidence, why, created_at)"
        " VALUES (1, 1, 2, 'rerated', 'high', 'medium', 'Why.', '2026-10-17T00:00:00Z')"
    )
    return check_conn


@pytest.mark.parametrize("table", ["rechecks", "flag_changes"])
@pytest.mark.parametrize("statement", ["UPDATE {table} SET id = id", "DELETE FROM {table}"], ids=["update", "delete"])
def test_rechecks_and_their_changes_are_append_only(recheck_conn, table, statement):
    with pytest.raises(sqlite3.IntegrityError, match="append-only"):
        recheck_conn.execute(statement.format(table=table))
    assert recheck_conn.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0] == 1


def test_one_ok_recheck_per_cache_key(recheck_conn):
    # A failed re-check can sit beside the ok one, but a second ok one can't.
    recheck_conn.execute(RECHECK.format(id=2, status="failed", failure="'schema'"))
    with pytest.raises(sqlite3.IntegrityError, match="UNIQUE"):
        recheck_conn.execute(RECHECK.format(id=3, status="ok", failure="NULL"))


@pytest.mark.parametrize(
    ("change", "before", "after", "kept_because"),
    [("rerated", "high", "high", "NULL"), ("kept", "high", "low", "NULL"), ("withdrawn", "high", "high", "'needs_call'")],
    ids=["rerated-to-the-same", "kept-but-changed", "withdrawn-but-kept"],
)
def test_a_flag_change_says_what_happened(recheck_conn, change, before, after, kept_because):
    with pytest.raises(sqlite3.IntegrityError, match="CHECK"):
        recheck_conn.execute(
            "INSERT INTO flag_changes (recheck_id, flag_id, change, from_confidence, to_confidence, kept_because, why,"
            f" created_at) VALUES (1, 1, '{change}', '{before}', '{after}', {kept_because}, 'Why.', 'x')"
        )


def test_migration_006_marks_forced_calls(tmp_path):
    with db.Database(tmp_path / "workbench.db").connect() as conn:
        assert db.migrate(conn) >= 6
        forced = {row["name"]: row for row in conn.execute("PRAGMA table_info(model_calls)")}["forced"]
        assert (forced["notnull"], forced["dflt_value"]) == (1, "0")
        assert "transcripts_session" in {row["name"] for row in conn.execute("PRAGMA index_list(transcripts)")}


def test_a_call_is_forced_or_not(conn):
    with pytest.raises(sqlite3.IntegrityError, match="CHECK"):
        conn.execute(
            "INSERT INTO model_calls (started_at, quota_day, role, provider, model_asked, prompt_version, settings_version,"
            " status, forced) VALUES ('x', 'x', 'character', 'fake', 'm', 'p', 's', 'error', 2)"
        )


def settings_row(conn, row_id=1, source="startup"):
    conn.execute(
        "INSERT INTO app_settings (id, saved_at, session, source, changed, provider, base_url, character_model,"
        " judge_model, calls_per_minute, daily_call_cap, force_model_error, key_set, models_version)"
        f" VALUES ({row_id}, 'x', NULL, '{source}', '', 'fake', '', 'a', 'b', 15, 200, 'off', 0, 'models.v5')"
    )


def test_migration_007_saves_settings_as_data(tmp_path):
    with db.Database(tmp_path / "workbench.db").connect() as conn:
        assert db.migrate(conn) >= 7
        assert "app_settings" in table_names(conn)
        column = {row["name"]: row for row in conn.execute("PRAGMA table_info(model_calls)")}["app_settings_id"]
        # Calls from before M6.5 keep NULL.
        assert (column["notnull"], column["dflt_value"]) == (0, None)
        # No column could hold a key: a row says only whether there was one.
        columns = {row["name"] for row in conn.execute("PRAGMA table_info(app_settings)")}
        assert "key_set" in columns and not {name for name in columns if "key" in name} - {"key_set"}


@pytest.mark.parametrize(
    "statement",
    [
        "UPDATE app_settings SET provider = 'gemini'",
        "DELETE FROM app_settings",
        "INSERT OR REPLACE INTO app_settings (id, saved_at, source, changed, provider, base_url, character_model,"
        " judge_model, calls_per_minute, daily_call_cap, force_model_error, key_set, models_version)"
        " VALUES (1, 'y', 'settings', '', 'gemini', '', 'a', 'b', 15, 200, 'off', 1, 'models.v5')",
    ],
    ids=["update", "delete", "replace"],
)
def test_settings_rows_are_append_only(conn, statement):
    settings_row(conn)
    with pytest.raises(sqlite3.IntegrityError, match="append-only"):
        conn.execute(statement)


def test_a_settings_row_says_where_it_came_from(conn):
    with pytest.raises(sqlite3.IntegrityError, match="CHECK"):
        settings_row(conn, source="somewhere")


def test_migration_008_records_the_session_limits(tmp_path):
    with db.Database(tmp_path / "workbench.db").connect() as conn:
        assert db.migrate(conn) >= 8
        columns = {row["name"]: row for row in conn.execute("PRAGMA table_info(app_settings)")}
        # Rows from before the session limits joined Settings keep NULL.
        assert [(columns[name]["notnull"], columns[name]["dflt_value"]) for name in ("session_run_limit", "session_judge_limit")] == [
            (0, None),
            (0, None),
        ]


def test_a_session_limit_in_a_settings_row_is_at_least_1(conn):
    with pytest.raises(sqlite3.IntegrityError, match="CHECK"):
        conn.execute(
            "INSERT INTO app_settings (saved_at, source, changed, provider, base_url, character_model, judge_model,"
            " calls_per_minute, daily_call_cap, force_model_error, key_set, models_version, session_run_limit)"
            " VALUES ('x', 'settings', '', 'fake', '', 'a', 'b', 15, 200, 'off', 0, 'models.v5', 0)"
        )
