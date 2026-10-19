"""The model call log and the event log. Both are append-only.

A model_calls row holds names, versions, timings, token counts, and a short
error, never prompt or chat text. An events row records what the creator did,
for the CP4 study, including each call on a flag and each opening of its
evidence. Errors and reasons are redacted before they are saved.
"""

from dataclasses import asdict, dataclass
from datetime import datetime, timezone

from workbench import db, redact


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


def timestamp(when: datetime) -> str:
    """UTC with milliseconds, like 2026-10-11T21:04:05.123Z."""
    return when.astimezone(timezone.utc).isoformat(timespec="milliseconds").replace("+00:00", "Z")


@dataclass(frozen=True)
class CallRecord:
    """One attempt to call a model. Field names are the model_calls columns."""

    started_at: str
    quota_day: str
    session: str | None
    role: str
    transcript_id: int | None
    turn: int | None
    provider: str
    model_asked: str
    model_reported: str | None
    prompt_version: str
    settings_version: str
    reasoning_effort: str | None
    status: str
    error: str | None = None
    attempt: int = 1
    fallback: bool = False
    # Failed on purpose for the demo (WORKBENCH_FORCE_MODEL_ERROR), so the provider never saw it.
    forced: bool = False
    same_model: bool = False
    ttft_ms: int | None = None
    latency_ms: int | None = None
    input_tokens: int | None = None
    cached_tokens: int | None = None
    output_tokens: int | None = None
    reasoning_tokens: int | None = None
    est_cost_usd: float | None = None
    # The app_settings row the call ran with (M6.5).
    app_settings_id: int | None = None


def record_call(database: db.Database, record: CallRecord) -> int:
    values = asdict(record)
    # A service's error message could quote what it was sent.
    values["error"] = redact.optional(values["error"])
    columns = ", ".join(values)
    marks = ", ".join("?" for _ in values)
    with database.connect() as conn:
        return conn.execute(f"INSERT INTO model_calls ({columns}) VALUES ({marks})", tuple(values.values())).lastrowid


def calls_on_day(database: db.Database, provider: str, quota_day: str) -> int:
    """Calls that reached this provider on this quota day. Capped and forced attempts never did."""
    with database.connect() as conn:
        return conn.execute(
            "SELECT COUNT(*) FROM model_calls WHERE quota_day = ? AND provider = ? AND status != 'capped' AND forced = 0",
            (quota_day, provider),
        ).fetchone()[0]


def insert_event(
    conn: db.Connection,
    kind: str,
    *,
    session: str | None = None,
    transcript_id: int | None = None,
    flag_id: int | None = None,
    flag_type: str | None = None,
    reason: str | None = None,
) -> int:
    """One events row on the caller's connection, so it can share the caller's transaction.

    The reason is redacted first: an override reason or a question is the creator's own text.
    """
    return conn.execute(
        "INSERT INTO events (created_at, session, kind, transcript_id, flag_id, flag_type, reason)"
        " VALUES (?, ?, ?, ?, ?, ?, ?)",
        (timestamp(utc_now()), session, kind, transcript_id, flag_id, flag_type, redact.optional(reason)),
    ).lastrowid


def record_event(
    database: db.Database,
    kind: str,
    *,
    session: str | None = None,
    transcript_id: int | None = None,
    reason: str | None = None,
) -> int:
    with database.connect() as conn:
        return insert_event(conn, kind, session=session, transcript_id=transcript_id, reason=reason)
