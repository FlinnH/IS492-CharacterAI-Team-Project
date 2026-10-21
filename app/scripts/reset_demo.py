"""Demo reset: wipes the database and loads a known-good demo state.

Run it from the repo root with the server stopped:

    app/.venv/bin/python app/scripts/reset_demo.py

First it copies the database to a backups folder next to it (app/data/backups/
by default), with the date and time in the file name. Then it builds a fresh
database with spec v1 and the CLA-F2 and GPT-F2 samples. Each sample gets the
check saved in app/samples/judge_snapshot.json, a real AI judge run made
earlier, so Check this chat shows the same flags every time with no model
call. A snapshot made with other judge settings is skipped with a warning, and
the samples start unchecked. Nothing else comes along: no live runs, calls on
flags, model calls, settings history, or events. The fresh file replaces the
old one only once it is complete, so a failure partway leaves the old
database where it was. The seeded transcript isn't loaded, so load it in
Import a chat after the reset. WORKBENCH_DB_PATH picks the database, as it
does for the server, so a scratch copy can be reset instead. It makes no model
calls and prints no chat text.
"""

import asyncio
import os
import socket
import sys
from datetime import datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from workbench import db, providers, specs, transcripts  # noqa: E402
from workbench.config import Settings, load_prompts, load_settings  # noqa: E402
from workbench.gateway import Gateway  # noqa: E402
from workbench.judge import SNAPSHOT_FILE, Judge, SnapshotStale, load_snapshot  # noqa: E402
from workbench.limiter import Limiter  # noqa: E402
from workbench.schemas import ImportRequest  # noqa: E402

REPO_DIR = Path(__file__).resolve().parent.parent.parent
# The samples the demo starts with, loaded in this order.
DEMO_SAMPLES = ("cla-f2", "gpt-f2")
# The files SQLite may keep next to a database while it writes.
SIDECARS = ("-journal", "-wal", "-shm")
SNAPSHOT_HELP = "To make a new one: app/.venv/bin/python app/scripts/judge_snapshot.py"


def shown(path: Path) -> str:
    """A path the way the docs write it: from the repo root when it's inside the repo."""
    try:
        return str(path.relative_to(REPO_DIR))
    except ValueError:
        return str(path)


def server_running(settings: Settings) -> bool:
    """Whether something answers at the server's address.

    The reset needs the server stopped. A running server holds state in
    memory, like a reply that is streaming, that the fresh database wouldn't have.
    """
    try:
        socket.create_connection((settings.workbench_host, settings.workbench_port), timeout=0.5).close()
    except OSError:
        return False
    return True


def backup_path(path: Path, now: datetime) -> Path:
    """backups/<name>-<date>-<time>.db next to the database, with -2, -3, and so
    on when a reset in the same second already made one."""
    folder = path.parent / "backups"
    stem = f"{path.stem}-{now:%Y-%m-%d-%H%M%S}"
    target = folder / f"{stem}{path.suffix}"
    count = 2
    while target.exists():
        target = folder / f"{stem}-{count}{path.suffix}"
        count += 1
    return target


def remove(path: Path) -> None:
    """Deletes a database file and any files SQLite kept next to it."""
    for name in (str(path), *(f"{path}{suffix}" for suffix in SIDECARS)):
        Path(name).unlink(missing_ok=True)


def build(database: db.Database, settings: Settings) -> dict[str, int]:
    """Spec v1 and the demo samples in a new database file. Returns each sample's chat ID."""
    with database.connect() as conn:
        db.migrate(conn)
    specs.seed(database)
    character = transcripts.load_scenarios().character
    for sample in DEMO_SAMPLES:
        request = ImportRequest(source="sample", character=character, sample=sample)
        transcripts.import_chat(database, settings, request, None, record=False)
    with database.connect() as conn:
        loaded = {row["sample"]: row["id"] for row in conn.execute("SELECT sample, id FROM transcripts ORDER BY id")}
    if list(loaded) != list(DEMO_SAMPLES):
        raise RuntimeError("The fresh database didn't get the demo samples.")
    return loaded


def make_judge(database: db.Database, settings: Settings) -> tuple[Judge, providers.Provider]:
    """The judge as the server builds it. Close the provider after use."""
    prompts = load_prompts()
    provider = providers.build(settings, prompts.presets)
    limiter = Limiter(settings.workbench_calls_per_minute, settings.workbench_daily_call_cap, prompts.models.quota_timezone)
    gateway = Gateway(database, settings, prompts, provider, limiter)
    scenarios = {scenario.id: scenario for scenario in transcripts.load_scenarios().scenarios}
    # No reply streams here, so no chat is ever busy.
    return Judge(database, settings, prompts, gateway, scenarios, busy=lambda: ()), provider


def flags_text(flags) -> str:
    """Like "3 flags (1 from automatic checks and 2 from the AI judge)"."""
    rule = sum(flag.source == "rule" for flag in flags)
    return f"{len(flags)} flag{'' if len(flags) == 1 else 's'} ({rule} from automatic checks and {len(flags) - rule} from the AI judge)"


def load_checks(database: db.Database, settings: Settings, chats: dict[str, int], snapshot: Path | None) -> list[str]:
    """Saves the judge snapshot's runs as the samples' checks. Returns lines to print."""
    if snapshot is None:
        return ["The samples start unchecked."]
    if not snapshot.is_file():
        return [f"Warning: there's no judge snapshot at {shown(snapshot)}, so the samples start unchecked.", SNAPSHOT_HELP]
    saved = load_snapshot(snapshot)
    judge, provider = make_judge(database, settings)
    lines = []
    try:
        for check in saved.checks:
            if check.sample not in chats:
                continue
            try:
                view = judge.replay(chats[check.sample], check)
            except SnapshotStale as error:
                lines.append(f"Warning: the judge snapshot for {check.sample} doesn't fit today's judge. {error}")
                lines.append(f"{check.sample} starts unchecked. {SNAPSHOT_HELP}")
                continue
            when = datetime.fromisoformat(check.checked_at.replace("Z", "+00:00")).astimezone()
            lines.append(f"{check.sample}: the saved check from {when:%b %d, %Y, %H:%M}, with {flags_text(view.flags)}.")
    finally:
        asyncio.run(provider.aclose())
    return lines


def main(settings: Settings | None = None, now: datetime | None = None, snapshot: Path | None = SNAPSHOT_FILE) -> int:
    settings = settings or load_settings()
    if server_running(settings):
        print(
            f"The workbench is running at http://{settings.workbench_host}:{settings.workbench_port}. "
            "Stop it first (Ctrl+C in its terminal), then run the reset again."
        )
        return 1

    database = db.Database(settings.workbench_db_path)
    path = database.path
    backup = None
    if path.is_file():
        backup = backup_path(path, now or datetime.now())
        database.backup(backup)
        print(f"Copied {shown(path)} to {shown(backup)}.")
    else:
        print(f"There's no database at {shown(path)} yet, so there's nothing to back up.")

    # Built next to the old file, so the swap below is one rename on the same disk.
    fresh = db.Database(path.with_name(f"{path.name}.reset"))
    remove(fresh.path)
    try:
        chats = build(fresh, settings)
        checks = load_checks(fresh, settings, chats, snapshot)
        with fresh.connect() as conn:
            titles = [row["title"] for row in conn.execute("SELECT title FROM transcripts ORDER BY id")]
    except BaseException:
        remove(fresh.path)
        raise
    # A journal left by the old file would be applied to the new one, so it goes first.
    for suffix in SIDECARS:
        Path(f"{path}{suffix}").unlink(missing_ok=True)
    os.replace(fresh.path, path)

    print(f"Reset {shown(path)}: spec v1, and the samples {' and '.join(titles)}.")
    for line in checks:
        print(line)
    print("It has no live runs, calls on flags, model calls, or events.")
    print("Next: start the app with app/run.sh, then load the seeded transcript in Import a chat.")
    if backup is not None:
        print(f"To undo: stop the app, then copy {shown(backup)} over {shown(path)}.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
