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
