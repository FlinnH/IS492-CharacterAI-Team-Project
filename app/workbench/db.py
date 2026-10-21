"""The SQLite database. This module is the only one that imports sqlite3.

Services open a short connection per call with Database.connect(), so a
connection never crosses threads. Schema changes are numbered SQL files in
migrations/, applied in order and counted in PRAGMA user_version.
"""

import sqlite3
from collections.abc import Iterator
from contextlib import contextmanager
from pathlib import Path

from workbench.config import APP_DIR

# Other modules catch and type these through db, so sqlite3 stays in this file.
IntegrityError = sqlite3.IntegrityError
Connection = sqlite3.Connection

MIGRATIONS_DIR = Path(__file__).resolve().parent / "migrations"


class Database:
    """The database file. A relative path counts from app/, as .env.example says."""

    def __init__(self, path: Path) -> None:
        path = Path(path).expanduser()
        self.path = path if path.is_absolute() else APP_DIR / path

    @contextmanager
    def connect(self) -> Iterator[Connection]:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        # isolation_level=None stops the sqlite3 module from opening
        # transactions on its own, so transaction() and migrate() decide.
        conn = sqlite3.connect(self.path, isolation_level=None)
        try:
            conn.row_factory = sqlite3.Row
            # Does nothing inside a transaction, so it comes first.
            conn.execute("PRAGMA foreign_keys = ON")
            yield conn
        finally:
            conn.close()

    def backup(self, target: Path) -> None:
        """Copies the database to target, a file that doesn't exist yet, then checks the copy.

        SQLite's backup API copies the database as one consistent snapshot, so
        the copy is whole even if a write ended a moment before.
        """
        target = Path(target)
        if not self.path.is_file():
            raise FileNotFoundError(f"There's no database at {self.path} to copy.")
        if target.exists():
            raise FileExistsError(f"{target} already exists.")
        target.parent.mkdir(parents=True, exist_ok=True)
        with self.connect() as conn:
            copy = sqlite3.connect(target)
            try:
                conn.backup(copy)
                result = copy.execute("PRAGMA quick_check").fetchone()[0]
            finally:
                copy.close()
        if result != "ok":
            raise RuntimeError(f"The copy at {target} failed SQLite's check: {result}")


@contextmanager
def transaction(conn: Connection) -> Iterator[Connection]:
    """BEGIN IMMEDIATE takes the write lock up front, so two saves can't interleave."""
    conn.execute("BEGIN IMMEDIATE")
    try:
        yield conn
    except BaseException:
        # SQLite rolls back by itself after some errors, and a second
        # ROLLBACK would raise and hide the first error.
        if conn.in_transaction:
            conn.execute("ROLLBACK")
        raise
    conn.execute("COMMIT")


def migrate(conn: Connection, folder: Path = MIGRATIONS_DIR) -> int:
    """Applies every NNN_name.sql above PRAGMA user_version and returns the new version."""
    files = sorted(folder.glob("[0-9][0-9][0-9]_*.sql"))
    latest = int(files[-1].name[:3]) if files else 0
    current = conn.execute("PRAGMA user_version").fetchone()[0]
    if current > latest:
        path = conn.execute("PRAGMA database_list").fetchone()["file"]
        raise RuntimeError(
            f"{path} was made by a newer version of the workbench: its database version is "
            f"{current}, and this code knows up to {latest}. Switch to the branch that made it, "
            "or delete the file to start fresh."
        )

    for file in files:
        number = int(file.name[:3])
        if number <= current:
            continue
        # executescript commits any open transaction before it runs, so the
        # BEGIN goes inside the script to apply each file all or nothing.
        script = f"BEGIN IMMEDIATE;\n{file.read_text(encoding='utf-8')}\nPRAGMA user_version = {number};\nCOMMIT;"
        try:
            conn.executescript(script)
        except BaseException:
            if conn.in_transaction:
                conn.execute("ROLLBACK")
            raise
        current = number
    return current
