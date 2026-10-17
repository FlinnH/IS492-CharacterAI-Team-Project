"""The creator's calls on flags: Agree, Override, and Undo, and each time the
creator opens a flag's evidence.

Every call and every opening is an events row with its time, so the log keeps
the whole history, and an Undo never erases the call it undid. A flag's
standing call is its latest Agree, Override, or Undo, from the decisions view.
The rules:

- Calls go only to the flags of a chat's saved check, as the chat stands now.
  A chat that changed after its check waits for a new one, and the calls on
  its old flags stay in the log.
- Agree only after the creator has opened the flag's evidence at least once.
- An override gives a reason of at least MIN_REASON_WORDS words. It may say
  which type is right instead, and then the flag still counts as a break.
- One standing call per flag: Undo it before making another.

A refused call writes nothing. Migration 004's triggers back up the rules for
every connection.
"""

import typing

from workbench import db, telemetry, transcripts
from workbench.config import Settings
from workbench.judge import Judge
from workbench.schemas import (
    ChatSummary,
    ChatView,
    CheckFlag,
    CheckView,
    FailureType,
    FlagCall,
    OverrideCall,
    ReviewChat,
    ReviewFlag,
    ReviewState,
)

MIN_REASON_WORDS = 3


class FlagNotFound(Exception):
    """No flag has this ID."""


class FlagOutdated(Exception):
    """The flag isn't part of its chat's saved check as the chat stands now."""


class CallRefused(Exception):
    """The call doesn't fit the flag's state, like an Agree before the evidence was opened."""


class CallInvalid(Exception):
    """The override's reason or type can't be used."""


def _call(row) -> FlagCall | None:
    """The standing call from a decisions row. An Undo, or no row, leaves the flag open."""
    if row is None or row["kind"] == "undo":
        return None
    if row["kind"] == "agree":
        return FlagCall(verdict="agreed", reason=None, type=None, made_at=row["created_at"])
    return FlagCall(verdict="overridden", reason=row["reason"], type=row["flag_type"], made_at=row["created_at"])


class Review:
    def __init__(self, database: db.Database, settings: Settings, judge: Judge) -> None:
        self.database = database
        self.settings = settings
        self.judge = judge

    # Reading.

    def state(self) -> ReviewState:
        """Every checked chat, oldest first, with its flags and the calls on them."""
        with self.database.connect() as conn:
            chat_ids = [row[0] for row in conn.execute("SELECT DISTINCT transcript_id FROM judge_runs ORDER BY transcript_id")]
        chats: list[ReviewChat] = []
        changed: list[ChatSummary] = []
        for chat_id in chat_ids:
            chat = self._chat(chat_id)
            check = self.judge.saved_check(chat, fallback=True)
            if check is None:
                changed.append(ChatSummary(**chat.model_dump(exclude={"source", "messages"})))
            else:
                chats.append(self._review(chat, check))
        return ReviewState(
            min_reason_words=MIN_REASON_WORDS,
            max_reason_chars=self.settings.workbench_max_typed_chars,
            failure_types=list(typing.get_args(FailureType)),
            open_calls=sum(item.open_calls for item in chats),
            chats=chats,
            changed=changed,
        )

    def _chat(self, chat_id: int) -> ChatView:
        return transcripts.get_chat(self.database, chat_id, scenarios=self.judge.scenarios)

    def _review(self, chat: ChatView, check: CheckView) -> ReviewChat:
        ids = [flag.id for flag in check.flags]
        calls, opened, last = {}, set(), 0
        if ids:
            marks = ", ".join("?" for _ in ids)
            with self.database.connect() as conn:
                calls = {row["flag_id"]: row for row in conn.execute(f"SELECT * FROM decisions WHERE flag_id IN ({marks})", ids)}
                opened = {
                    row["flag_id"]
                    for row in conn.execute(
                        f"SELECT DISTINCT flag_id FROM events WHERE kind = 'evidence_opened' AND flag_id IN ({marks})", ids
                    )
                }
                last = conn.execute(f"SELECT MAX(id) FROM events WHERE flag_id IN ({marks})", ids).fetchone()[0] or 0

        flags = []
        for flag in check.flags:
            call = _call(calls.get(flag.id))
            flags.append(
                ReviewFlag(
                    **flag.model_dump(),
                    evidence_opened=flag.id in opened,
                    call=call,
                    counts_as_break=call is None or call.verdict == "agreed" or call.type is not None,
                )
            )
        breaks = [flag.turn for flag in flags if flag.counts_as_break]
        return ReviewChat(
            chat=chat,
            spec_version=check.spec_version,
            judge=check.judge,
            flags=flags,
            hidden=check.hidden,
            not_checked=check.not_checked,
            open_calls=sum(flag.call is None for flag in flags),
            first_break=min(breaks, default=None),
            agreed_with_every=bool(flags) and all(flag.call is not None and flag.call.verdict == "agreed" for flag in flags),
            last_event_id=last,
        )

    # Calls. Each answers with the flag's chat as it now stands.

    def open_evidence(self, flag_id: int, session: str | None) -> ReviewChat:
        chat, check, _ = self._current(flag_id)
        self._log(chat, flag_id, "evidence_opened", session)
        return self._review(chat, check)

    def agree(self, flag_id: int, session: str | None) -> ReviewChat:
        chat, check, _ = self._current(flag_id)
        self._log(chat, flag_id, "agree", session)
        return self._review(chat, check)

    def override(self, flag_id: int, call: OverrideCall, session: str | None) -> ReviewChat:
        chat, check, flag = self._current(flag_id)
        reason = call.reason.strip()
        if len(reason.split()) < MIN_REASON_WORDS:
            raise CallInvalid(f"Write a reason of at least {MIN_REASON_WORDS} words.")
        limit = self.settings.workbench_max_typed_chars
        if len(reason) > limit:
            raise CallInvalid(f"Keep the reason to {limit:,} characters or fewer.")
        if call.type == flag.type:
            raise CallInvalid("Pick a type other than the flag's own, or none.")
        self._log(chat, flag_id, "override", session, reason=reason, flag_type=call.type)
        return self._review(chat, check)

    def undo(self, flag_id: int, session: str | None) -> ReviewChat:
        chat, check, _ = self._current(flag_id)
        self._log(chat, flag_id, "undo", session)
        return self._review(chat, check)

    def _current(self, flag_id: int) -> tuple[ChatView, CheckView, CheckFlag]:
        """The flag's chat, its saved check, and the flag. Raises for an unknown or outdated flag."""
        with self.database.connect() as conn:
            row = conn.execute("SELECT transcript_id FROM flags WHERE id = ?", (flag_id,)).fetchone()
        if row is None:
            raise FlagNotFound(f"There is no flag {flag_id}.")
        chat = self._chat(row["transcript_id"])
        check = self.judge.saved_check(chat, fallback=True)
        flag = next((item for item in check.flags if item.id == flag_id), None) if check else None
        if flag is None:
            raise FlagOutdated("This flag is from an older check of the chat. Reload Flag review to see the current flags.")
        return chat, check, flag

    def _log(
        self,
        chat: ChatView,
        flag_id: int,
        kind: str,
        session: str | None,
        *,
        reason: str | None = None,
        flag_type: str | None = None,
    ) -> None:
        """Checks the flag's state and writes the event in one transaction, so two tabs can't both decide."""
        try:
            with self.database.connect() as conn, db.transaction(conn):
                standing = conn.execute("SELECT kind FROM decisions WHERE flag_id = ?", (flag_id,)).fetchone()
                decided = standing is not None and standing["kind"] != "undo"
                if kind == "agree":
                    opened = conn.execute(
                        "SELECT 1 FROM events WHERE kind = 'evidence_opened' AND flag_id = ? LIMIT 1", (flag_id,)
                    ).fetchone()
                    if opened is None:
                        raise CallRefused("Open this flag's evidence with Show in context before you agree.")
                if kind in ("agree", "override") and decided:
                    raise CallRefused("This flag already has your call. Undo it first to change it.")
                if kind == "undo" and not decided:
                    raise CallRefused("This flag has no call to undo.")
                telemetry.insert_event(
                    conn,
                    kind,
                    session=session,
                    transcript_id=chat.id,
                    flag_id=flag_id,
                    flag_type=flag_type,
                    reason=reason,
                )
        except db.IntegrityError as error:
            # A backstop trigger refused it: another tab got there first.
            raise CallRefused("This flag's call changed in another tab. Reload Flag review.") from error
