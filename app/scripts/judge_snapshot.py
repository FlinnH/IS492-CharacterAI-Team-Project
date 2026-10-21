"""Judge snapshot: one real AI judge run on each demo sample, saved for the demo reset.

Run it from the repo root, with no run or check going in the app (call
spacing is per process):

    app/.venv/bin/python app/scripts/judge_snapshot.py

It loads the CLA-F2 and GPT-F2 samples into a temporary database, checks each
one with the AI judge in app/.env, and writes the answers to
app/samples/judge_snapshot.json. That's 2 judge calls, or a few more if the
service is busy. They are logged only in the temporary database, which is
deleted at the end, so they don't count toward the app's daily cap. It refuses
an answer from a fallback model, since the reset could never match it to
today's judge. Make a new snapshot whenever the judge model, its reasoning
effort, its prompt, or its schema changes. It prints counts, never chat text.
"""

import asyncio
import json
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
sys.path.insert(0, str(Path(__file__).resolve().parent))

from reset_demo import build, flags_text, make_judge, shown  # noqa: E402
from workbench import db, transcripts  # noqa: E402
from workbench.config import load_settings  # noqa: E402
from workbench.judge import SNAPSHOT_FILE  # noqa: E402
from workbench.schemas import JudgeOutput, JudgeSnapshot, SnapshotCall, SnapshotCheck  # noqa: E402

NOTE = (
    "Real AI judge runs on the CLA-F2 and GPT-F2 samples, made with app/scripts/judge_snapshot.py. "
    "The demo reset saves them as the samples' checks, so a check shows the same flags with no model call."
)


async def capture(database: db.Database, settings, chats: dict[str, int]) -> list[SnapshotCheck]:
    judge, provider = make_judge(database, settings)
    checks = []
    try:
        for sample, chat_id in chats.items():
            print(f"Checking {sample}.", flush=True)
            view = await judge.check(chat_id, None)
            if view.judge.status != "ok":
                raise SystemExit(f"The judge gave no usable answer on {sample}: {view.judge.note}")
            if view.judge.fallback or view.judge.model != judge.model_id():
                raise SystemExit(f"The fallback model answered on {sample}. Run this again when {judge.model_id()} isn't busy.")
            with database.connect() as conn:
                run = conn.execute("SELECT * FROM judge_runs WHERE id = ?", (view.judge.id,)).fetchone()
                call = conn.execute("SELECT * FROM model_calls WHERE id = ?", (run["model_call_id"],)).fetchone()
            chat = transcripts.get_chat(database, chat_id, scenarios=judge.scenarios)
            checks.append(
                SnapshotCheck(
                    sample=sample,
                    transcript_sha256=judge.transcript_sha256(chat),
                    model=run["model"],
                    reasoning_effort=run["reasoning_effort"],
                    prompt_version=run["prompt_version"],
                    schema_version=run["schema_version"],
                    checked_at=run["created_at"],
                    call=SnapshotCall(**{field: call[field] for field in SnapshotCall.model_fields}),
                    answer=JudgeOutput.model_validate_json(run["raw_json"]),
                )
            )
            hidden = sum(item.count for item in view.hidden)
            print(f"  {flags_text(view.flags)}, {hidden} hidden, in {call['latency_ms'] / 1000:.1f} s.", flush=True)
    finally:
        await provider.aclose()
    return checks


def main() -> int:
    settings = load_settings()
    if settings.workbench_provider == "fake":
        print("WORKBENCH_PROVIDER is fake, whose judge never flags anything. Connect a real AI first.")
        return 1
    if settings.workbench_force_model_error != "off":
        print("WORKBENCH_FORCE_MODEL_ERROR is on in app/.env. Set it to off first.")
        return 1
    with tempfile.TemporaryDirectory() as folder:
        temporary = settings.model_copy(update={"workbench_db_path": Path(folder) / "snapshot.db"})
        database = db.Database(temporary.workbench_db_path)
        chats = build(database, temporary)
        checks = asyncio.run(capture(database, temporary, chats))
    snapshot = JudgeSnapshot(format="workbench-judge-snapshot.v1", note=NOTE, checks=checks)
    # ASCII only, so a curly quote in a judge answer stays an escape in the file.
    SNAPSHOT_FILE.write_text(json.dumps(snapshot.model_dump(mode="json"), indent=2, ensure_ascii=True) + "\n", encoding="utf-8")
    print(f"Wrote {shown(SNAPSHOT_FILE)}. The next demo reset will use it.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
