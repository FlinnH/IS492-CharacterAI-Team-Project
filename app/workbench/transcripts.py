"""Saved chats: live runs, imports, and samples, with their messages.

parse() reads a pasted chat in one of four formats and keeps the source's own
numbering. Problems name rows of the pasted text, never the text itself. A
chat keeps the spec version it was made with; only its status changes, and
its messages are append-only.

The seeded transcript is read only by read_sample(), and only when the creator
picks it in Import. Listing the samples checks that its file exists and never
opens it.

Nothing is saved unredacted: an import is redacted message by message once it
is parsed, with its title, tool, receipt, and source notes, and a live
message is redacted as it is saved. A message that reads like an instruction
to the AI is marked as possible injection wherever it shows, and is saved as it is.
"""

import hashlib
import json
import re
from collections import Counter
from dataclasses import dataclass, field
from pathlib import Path

from pydantic import ValidationError

from workbench import db, injection, redact, specs, telemetry
from workbench.config import APP_DIR, Settings, app_path
from workbench.schemas import (
    Character,
    ChatSource,
    ChatSummary,
    ChatView,
    ImportPreview,
    ImportRequest,
    MessageView,
    PreviewRow,
    Removed,
    RowProblem,
    SampleChat,
    SampleInfo,
    Scenario,
    ScenarioFile,
    SpeakerCount,
)

SAMPLES_DIR = APP_DIR / "samples"
SCENARIOS_FILE = SAMPLES_DIR / "scenarios.v1.json"
SEEDED = "seeded"

# How many rows the preview shows from each end of the chat, and how much of each.
PREVIEW_ROWS = 3
PREVIEW_CHARS = 160

# A speaker label: a name of up to 40 characters, starting with a letter.
LABEL = r"[A-Za-z][\w .'\-]{0,39}?"
# "Turn 2 Alex:" or "Turn 4 Alex (PROBE):" on a line of its own, as the receipts write them.
RECEIPT_LABEL = re.compile(rf"^\s*Turn\s+(\d+)\s+({LABEL})\s*(?:\([^)]*\))?\s*:\s*$")
# "Turn 1: spec pasted. Reply (not scored):", the turn that only loaded the spec.
SPEC_TURN = re.compile(r"^\s*Turn\s+\d+\s*:")
# A line that is a note in brackets, like "[Turn 17 was skipped by mistake and never sent.]".
NOTE = re.compile(r"^\s*\[[^\]]*\]\s*$")
# Markdown or HTML around a log: fences, tags, headings, and rules.
STRUCTURE = re.compile(r"^\s*(?:```|~~~|</?[A-Za-z][^>]*>\s*$|#{1,6}\s|(?:-\s*){3,}$|(?:\*\s*){3,}$)")
# One message per line: "Alex: text", "**Alex:** text", "Turn 2 Alex: text", "3. Alex: text", "[3] Alex: text".
INLINE = re.compile(
    r"^\s*(?:Turn\s+(?P<turn>\d+)\s+|(?P<line>\d+)[.)]\s+|\[(?P<bracket>\d+)\]\s*)?"
    rf"(?:\*\*|__)?(?P<label>{LABEL})\s*(?:\([^)]*\))?\s*(?:\*\*|__)?\s*:\s*(?:\*\*|__)?\s*(?P<text>.*)$"
)
# A markdown table's divider row, like "| --- | :---: |".
TABLE_DIVIDER = re.compile(r"^\s*\|?\s*:?-{3,}:?\s*(?:\|\s*:?-{3,}:?\s*)*\|?\s*$")
TABLE_NUMBER = re.compile(r"^(?:[Ll](?:ine)?\s*)?(\d+)\.?$")
NUMBER_HEADERS = {"#", "n", "no", "no.", "num", "number", "line", "line #", "line no", "line no.", "line number", "row", "turn"}
SPEAKER_HEADERS = {"speaker", "who", "name", "role", "from", "character", "said by", "person", "voice"}
TEXT_HEADERS = {"text", "line", "message", "says", "what they say", "dialogue", "content", "utterance", "words", "reply", "said"}


class ChatNotFound(Exception):
    """No chat has that ID."""


class ImportInvalid(Exception):
    """The chat can't be imported as it is. problems name the rows to fix."""

    def __init__(self, message: str, problems: list[RowProblem] | None = None) -> None:
        super().__init__(message)
        self.problems = problems or []


@dataclass
class Row:
    """One message as the source wrote it. row is the line of the source where it starts."""

    row: int
    number: int | None
    label: str
    lines: list[str] = field(default_factory=list)

    @property
    def text(self) -> str:
        return "\n".join(self.lines).strip("\n")


@dataclass
class Parsed:
    format: str
    numbering: str
    rows: list[Row]
    skipped_rows: list[int]
    problems: list[RowProblem]
    chat: SampleChat | None = None


@dataclass(frozen=True)
class ImportPlan:
    """A parsed chat with its speakers sorted out, ready to preview or save."""

    parsed: Parsed
    character: Character
    spec_version: int
    title: str
    sample: str | None
    tool: str
    receipt: str
    scenario: str | None
    source: ChatSource
    user_name: str
    character_name: str
    # (number, speaker, text) in source order.
    messages: list[tuple[int, str, str]]
    speakers: list[SpeakerCount]
    needs_roles: bool
    content_sha256: str
    # What redaction took out of the pasted or loaded text.
    removed: Removed


# Parsing.


def _lines(text: str) -> list[str]:
    return text.lstrip("\ufeff").replace("\r\n", "\n").replace("\r", "\n").split("\n")


def _clean_label(label: str) -> str:
    return " ".join(label.strip("*_ :").split())


def parse(text: str) -> Parsed:
    """Reads a pasted chat: workbench JSON, the receipt log, a markdown table, or one message per line."""
    if text.lstrip("\ufeff").strip().startswith("{"):
        return _parse_json(text)
    lines = _lines(text)
    if sum(1 for line in lines if RECEIPT_LABEL.match(line)) >= 2:
        return _parse_receipt(lines)
    table = _parse_table(lines)
    if table is not None:
        return table
    return _parse_inline(lines)


def _parse_json(text: str) -> Parsed:
    try:
        chat = SampleChat.model_validate_json(text.lstrip("\ufeff"))
    except ValidationError as error:
        places = sorted({".".join(str(part) for part in item["loc"]) or "the top" for item in error.errors()})
        message = f"The JSON doesn't match the workbench chat format at {', '.join(places[:5])}."
        return Parsed("json", "turn", [], [], [RowProblem(row=1, message=message)])
    rows = [
        Row(row=1, number=item.turn, label=chat.character_name if item.speaker == "character" else chat.user_name, lines=[item.text])
        for item in chat.messages
    ]
    return Parsed("json", chat.numbering, rows, [], [], chat)


def _parse_receipt(lines: list[str]) -> Parsed:
    """The receipt log: a "Turn N Name:" line, then the message indented 4 spaces."""
    rows: list[Row] = []
    skipped: list[int] = []
    current: Row | None = None
    in_spec_turn = False
    for index, raw in enumerate(lines, start=1):
        line = raw.rstrip()
        label = RECEIPT_LABEL.match(line)
        if label:
            current = Row(row=index, number=int(label[1]), label=_clean_label(label[2]))
            rows.append(current)
            in_spec_turn = False
            continue
        if SPEC_TURN.match(line):
            current, in_spec_turn = None, True
            skipped.append(index)
            continue
        if NOTE.match(line) or STRUCTURE.match(line):
            if current is not None and not line.startswith("    "):
                current = None
            skipped.append(index)
            continue
        if in_spec_turn:
            if line:
                skipped.append(index)
            continue
        if current is not None:
            # Up to 4 spaces of indent belong to the log, not the message.
            current.lines.append(line[4:] if line.startswith("    ") else line.lstrip())
            continue
        if line:
            skipped.append(index)
    return Parsed("receipt", "turn", rows, skipped, _empty_rows(rows))


def _empty_rows(rows: list[Row]) -> list[RowProblem]:
    return [RowProblem(row=row.row, message=f"Row {row.row} has a speaker but no text.") for row in rows if not row.text]


def _split_cells(line: str) -> list[str]:
    inner = line.strip()
    if inner.startswith("|"):
        inner = inner[1:]
    if inner.endswith("|") and not inner.endswith("\\|"):
        inner = inner[:-1]
    cells = re.split(r"(?<!\\)\|", inner)
    return [re.sub(r"<br\s*/?>", "\n", cell.strip().replace("\\|", "|"), flags=re.I) for cell in cells]


def _number(cell: str) -> int | None:
    match = TABLE_NUMBER.match(cell.strip("*_ "))
    return int(match[1]) if match else None


def _tables(lines: list[str]) -> list[tuple[int, int]]:
    """(header index, end index) for each markdown table, using 0-based line indexes."""
    found = []
    index = 0
    while index < len(lines) - 1:
        if "|" in lines[index] and TABLE_DIVIDER.match(lines[index + 1]):
            end = index + 2
            while end < len(lines) and lines[end].strip() and "|" in lines[end]:
                end += 1
            found.append((index, end))
            index = end
        else:
            index += 1
    return found


def _columns(header: list[str], body: list[list[str]]) -> tuple[int | None, int | None, int | None]:
    """Picks the number, speaker, and text columns of a table."""
    names = [_clean_label(cell).lower() for cell in header]
    width = len(header)

    def column(position: int) -> list[str]:
        return [cells[position] for cells in body if position < len(cells) and cells[position]]

    def all_numbers(position: int) -> bool:
        values = column(position)
        return bool(values) and all(_number(value) is not None for value in values)

    number = next((i for i in range(width) if names[i] in NUMBER_HEADERS and all_numbers(i)), None)
    if number is None:
        number = next((i for i in range(width) if all_numbers(i)), None)

    def short_and_repeated(position: int) -> bool:
        values = [_clean_label(value) for value in column(position)]
        return bool(values) and len(set(values)) <= 4 and all(len(value) <= 40 and len(value.split()) <= 4 for value in values)

    others = [i for i in range(width) if i != number]
    speaker = next((i for i in others if names[i] in SPEAKER_HEADERS), None)
    if speaker is None:
        speaker = next((i for i in others if short_and_repeated(i) and len(others) > 1), None)
    rest = [i for i in others if i != speaker]
    text = next((i for i in rest if names[i] in TEXT_HEADERS), None)
    if text is None and rest:
        text = max(rest, key=lambda i: sum(len(value) for value in column(i)))
    return number, speaker, text


def _parse_table(lines: list[str]) -> Parsed | None:
    """A markdown table with a speaker column (or "Name: text" cells), and maybe a number column."""
    best = None
    for start, end in _tables(lines):
        header = _split_cells(lines[start])
        body = [_split_cells(lines[i]) for i in range(start + 2, end)]
        number, speaker, text = _columns(header, body)
        if text is None:
            continue
        if best is None or (speaker is not None, end - start) > (best[4] is not None, best[1] - best[0]):
            best = (start, end, header, number, speaker, text)
    if best is None:
        return None
    start, end, header, number, speaker, text = best

    rows: list[Row] = []
    problems: list[RowProblem] = []
    skipped = [i + 1 for i, line in enumerate(lines) if line.strip() and not start <= i < end]
    is_turns = number is not None and "turn" in _clean_label(header[number]).lower()
    for index in range(start + 2, end):
        row_number = index + 1
        cells = _split_cells(lines[index])
        if len(cells) != len(header):
            problems.append(
                RowProblem(row=row_number, message=f"Row {row_number} has {len(cells)} cells, but the table has {len(header)} columns.")
            )
            continue
        value = None
        if number is not None:
            value = _number(cells[number])
            if value is None:
                problems.append(RowProblem(row=row_number, message=f"Row {row_number} has no whole number in its number column."))
                continue
        words = cells[text]
        label = _clean_label(cells[speaker]) if speaker is not None else ""
        if speaker is None:
            inline = INLINE.match(words)
            if inline:
                label, words = _clean_label(inline["label"]), inline["text"]
        if not label:
            problems.append(RowProblem(row=row_number, message=f"Row {row_number} has no speaker."))
            continue
        if not words.strip():
            problems.append(RowProblem(row=row_number, message=f"Row {row_number} has no text."))
            continue
        rows.append(Row(row=row_number, number=value, label=label, lines=[words]))
    numbering = "turn" if number is None or is_turns else "line"
    return Parsed("table", numbering, rows, skipped, problems)


def _parse_inline(lines: list[str]) -> Parsed:
    """One message per line, starting with the speaker's name and a colon. Lines after it continue it."""
    matches = [INLINE.match(line) if line.strip() and not SPEC_TURN.match(line) else None for line in lines]
    counts = Counter(_clean_label(match["label"]).casefold() for match in matches if match)
    # The two names used most are the speakers. A rarer "Word:" is part of a message.
    speakers = {label for label, _ in counts.most_common(2)}

    rows: list[Row] = []
    skipped: list[int] = []
    current: Row | None = None
    in_spec_turn = False
    kinds = set()
    for index, (raw, match) in enumerate(zip(lines, matches), start=1):
        line = raw.rstrip()
        if SPEC_TURN.match(line) and not match:
            current, in_spec_turn = None, True
            skipped.append(index)
            continue
        if match and _clean_label(match["label"]).casefold() in speakers:
            number = None
            for kind in ("turn", "line", "bracket"):
                if match[kind] is not None:
                    number = int(match[kind])
                    kinds.add("turn" if kind == "turn" else "line")
            current = Row(row=index, number=number, label=_clean_label(match["label"]), lines=[match["text"]])
            rows.append(current)
            in_spec_turn = False
            continue
        if NOTE.match(line) or STRUCTURE.match(line):
            skipped.append(index)
            continue
        if in_spec_turn or current is None:
            if line.strip():
                skipped.append(index)
            continue
        current.lines.append(line.strip())

    problems = _empty_rows(rows)
    if not rows:
        problems.append(RowProblem(row=1, message="No messages found. Start each one with the speaker's name and a colon, like Alex: Hello."))
    numbered = [row for row in rows if row.number is not None]
    if numbered and len(numbered) != len(rows):
        for row in rows:
            if row.number is None:
                problems.append(RowProblem(row=row.row, message=f"Row {row.row} has no number, but other messages do."))
    numbering = "line" if kinds == {"line"} else "turn"
    return Parsed("inline", numbering, rows, skipped, problems)


# Speakers and numbers.


def _assign_roles(parsed: Parsed, character: Character, character_label: str | None) -> tuple[dict[str, str], list[SpeakerCount], bool]:
    """Which label is the character and which is the user. Labels compare without case."""
    order: list[str] = []
    counts: Counter = Counter()
    for row in parsed.rows:
        key = row.label.casefold()
        if key not in counts:
            order.append(row.label)
        counts[key] += 1

    if parsed.chat is not None:
        roles = {parsed.chat.character_name.casefold(): "character", parsed.chat.user_name.casefold(): "user"}
    else:
        names = {character.name.casefold(), character.name.split()[0].casefold()}
        chosen = character_label.casefold() if character_label else None
        if chosen is None:
            chosen = next((label.casefold() for label in order if label.casefold() in names), None)
        roles = {}
        if chosen is not None and chosen in counts:
            roles = {label.casefold(): ("character" if label.casefold() == chosen else "user") for label in order}

    speakers = [SpeakerCount(label=label, count=counts[label.casefold()], role=roles.get(label.casefold())) for label in order]
    needs_roles = len(order) > 1 and not roles
    return roles, speakers, needs_roles


def _numbered(rows: list[Row], roles: dict[str, str]) -> list[tuple[int, str, str]]:
    """(number, speaker, text) per message. With no numbers in the source, a user line starts a new turn."""
    messages = []
    turn = 0
    for position, row in enumerate(rows):
        speaker = roles.get(row.label.casefold(), "user")
        if row.number is not None:
            number = row.number
        else:
            if position == 0 or speaker == "user":
                turn += 1
            number = turn
        messages.append((number, speaker, row.text))
    return messages


# Samples and import.


def sample_files() -> dict[str, Path]:
    """The chat samples in app/samples/, by ID (the file name without .json)."""
    found = {}
    for path in sorted(SAMPLES_DIR.glob("*.json")):
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
        except ValueError:
            continue
        if isinstance(data, dict) and data.get("format") == "workbench-chat.v1":
            found[path.stem] = path
    return found


def list_samples(settings: Settings) -> list[SampleInfo]:
    samples = []
    for sample_id, path in sample_files().items():
        chat = SampleChat.model_validate_json(path.read_text(encoding="utf-8"))
        samples.append(SampleInfo(id=sample_id, label=chat.title, spec_version=chat.spec_version, path=None, available=True))
    seeded = settings.workbench_seeded_transcript_path
    samples.append(
        SampleInfo(
            id=SEEDED,
            label="Seeded transcript",
            spec_version=1,
            path=str(seeded),
            # Only checks that the file is there. It is read when picked.
            available=app_path(seeded).is_file(),
        )
    )
    return samples


def read_sample(settings: Settings, sample_id: str) -> str:
    if sample_id == SEEDED:
        path = app_path(settings.workbench_seeded_transcript_path)
        if not path.is_file():
            raise ImportInvalid(f"The seeded transcript isn't at {settings.workbench_seeded_transcript_path}.")
        return path.read_text(encoding="utf-8")
    path = sample_files().get(sample_id)
    if path is None:
        raise ImportInvalid(f"There is no sample called {sample_id}.")
    return path.read_text(encoding="utf-8")


def _content_sha256(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def plan_import(database: db.Database, settings: Settings, request: ImportRequest) -> ImportPlan:
    """Reads and parses the chat the request names. Raises ImportInvalid for what can't be read."""
    if request.source == "sample":
        if not request.sample:
            raise ImportInvalid("Pick a sample to load.")
        text = read_sample(settings, request.sample)
    else:
        text = request.text or ""
        if not text.strip():
            raise ImportInvalid("Paste a chat, or choose a file, first.")
    limit = settings.workbench_max_import_chars
    if len(text) > limit:
        raise ImportInvalid(
            f"That chat has {len(text):,} characters, and the limit is {limit:,} "
            "(WORKBENCH_MAX_IMPORT_CHARS in app/.env)."
        )

    parsed = parse(text)
    chat = parsed.chat
    seeded = request.source == "sample" and request.sample == SEEDED
    if chat is not None:
        default_version = chat.spec_version
    elif seeded:
        default_version = 1
    else:
        default_version = None
    view = specs.get_spec(database, request.character, request.spec_version or default_version)

    roles, speakers, needs_roles = _assign_roles(parsed, view.character, request.character_label)
    if len(speakers) > 2:
        extra = speakers[2].label
        first_row = next(row.row for row in parsed.rows if row.label.casefold() == extra.casefold())
        parsed.problems.append(
            RowProblem(
                row=first_row,
                message=f"Row {first_row} adds a third speaker, {extra}. A chat can have the character and one other speaker.",
            )
        )
    user_name = next((s.label for s in speakers if s.role == "user"), "User")
    character_name = next((s.label for s in speakers if s.role == "character"), view.character.name.split()[0])

    # Redacted after parsing, so a label like [email removed] can't read as a
    # note in brackets and change what the parser keeps.
    removed = Removed()

    def scrub(value: str) -> str:
        nonlocal removed
        value, found = redact.scrub(value)
        removed += found
        return value

    messages = [(number, speaker, scrub(words)) for number, speaker, words in _numbered(parsed.rows, roles)]
    tool = scrub((chat.tool if chat else "") or request.tool.strip())
    receipt = scrub((chat.receipt if chat else "") or request.receipt.strip())
    source = ChatSource(**{name: scrub(value) for name, value in chat.source.model_dump().items()}) if chat else ChatSource()
    if chat is not None:
        title = scrub(chat.title)
    elif seeded:
        title = "Seeded transcript"
    elif tool and receipt:
        title = f"{tool} ({receipt})"
    else:
        title = receipt or tool or "Pasted chat"
    return ImportPlan(
        parsed=parsed,
        character=view.character,
        spec_version=view.version,
        title=title,
        sample=request.sample if request.source == "sample" else None,
        tool=tool,
        receipt=receipt,
        scenario=chat.scenario if chat else None,
        source=source,
        user_name=user_name,
        character_name=character_name,
        messages=messages,
        speakers=speakers,
        needs_roles=needs_roles,
        # Of the redacted text, so the saved hash never stands for the personal data.
        content_sha256=_content_sha256(redact.text(text)),
        removed=removed,
    )


def _kind(plan: ImportPlan) -> str:
    return "sample" if plan.sample else "import"


def _duplicate(conn: db.Connection, plan: ImportPlan) -> int | None:
    row = conn.execute(
        "SELECT transcripts.id FROM transcripts JOIN characters ON characters.id = transcripts.character_id"
        " WHERE characters.slug = ? AND transcripts.kind = ? AND transcripts.spec_version = ?"
        " AND transcripts.content_sha256 = ? ORDER BY transcripts.id LIMIT 1",
        (plan.character.slug, _kind(plan), plan.spec_version, plan.content_sha256),
    ).fetchone()
    return row["id"] if row else None


def _preview_rows(plan: ImportPlan, indexes: range) -> list[PreviewRow]:
    rows = plan.parsed.rows
    out = []
    for i in indexes:
        number, speaker, text = plan.messages[i]
        short = text if len(text) <= PREVIEW_CHARS else text[: PREVIEW_CHARS - 3].rstrip() + "..."
        out.append(
            PreviewRow(
                row=rows[i].row,
                number=number,
                label=rows[i].label,
                speaker=None if plan.needs_roles else speaker,
                text=short,
                injection=injection.marked(text),
            )
        )
    return out


def preview(database: db.Database, settings: Settings, request: ImportRequest) -> ImportPreview:
    plan = plan_import(database, settings, request)
    count = len(plan.messages)
    with database.connect() as conn:
        duplicate = _duplicate(conn, plan)
    return ImportPreview(
        format=plan.parsed.format,
        numbering=plan.parsed.numbering,
        message_count=count,
        first_number=plan.messages[0][0] if count else None,
        last_number=plan.messages[-1][0] if count else None,
        speakers=plan.speakers,
        needs_roles=plan.needs_roles,
        first_rows=_preview_rows(plan, range(min(PREVIEW_ROWS, count))),
        last_rows=_preview_rows(plan, range(max(PREVIEW_ROWS, count - PREVIEW_ROWS), count)),
        skipped_rows=plan.parsed.skipped_rows,
        problems=plan.parsed.problems,
        spec_version=plan.spec_version,
        title=plan.title,
        duplicate_of=duplicate,
        removed=plan.removed,
        injection_numbers=[number for number, _, text in plan.messages if injection.marked(text)],
    )


def import_chat(database: db.Database, settings: Settings, request: ImportRequest, session: str | None) -> tuple[int, bool]:
    """Saves the chat and returns (chat ID, True), or (the saved chat's ID, False) if it's already in."""
    plan = plan_import(database, settings, request)
    if plan.parsed.problems:
        raise ImportInvalid("Some rows can't be read. Fix them and try again.", plan.parsed.problems)
    if not plan.messages:
        raise ImportInvalid("The chat has no messages.")
    if plan.needs_roles:
        labels = " or ".join(s.label for s in plan.speakers)
        raise ImportInvalid(f"Say which speaker is the character: {labels}.")

    with database.connect() as conn, db.transaction(conn):
        duplicate = _duplicate(conn, plan)
        if duplicate is not None:
            return duplicate, False
        character_id = conn.execute("SELECT id FROM characters WHERE slug = ?", (plan.character.slug,)).fetchone()["id"]
        now = telemetry.timestamp(telemetry.utc_now())
        chat_id = conn.execute(
            "INSERT INTO transcripts (character_id, spec_version, kind, title, sample, tool, receipt, scenario, model,"
            " numbering, user_name, character_name, source_json, content_sha256, status, session, created_at)"
            " VALUES (?, ?, ?, ?, ?, ?, ?, ?, NULL, ?, ?, ?, ?, ?, 'imported', ?, ?)",
            (
                character_id,
                plan.spec_version,
                _kind(plan),
                plan.title,
                plan.sample,
                plan.tool,
                plan.receipt,
                plan.scenario,
                plan.parsed.numbering,
                plan.user_name,
                plan.character_name,
                plan.source.model_dump_json(),
                plan.content_sha256,
                session,
                now,
            ),
        ).lastrowid
        conn.executemany(
            "INSERT INTO messages (transcript_id, seq, turn, speaker, text, source, stopped, model_call_id, created_at)"
            " VALUES (?, ?, ?, ?, ?, 'import', 0, NULL, ?)",
            [(chat_id, seq, number, speaker, text, now) for seq, (number, speaker, text) in enumerate(plan.messages, start=1)],
        )
    telemetry.record_event(database, "import", session=session, transcript_id=chat_id, reason=plan.sample or "paste")
    return chat_id, True


# Live chats.


def load_scenarios(path: Path = SCENARIOS_FILE) -> ScenarioFile:
    return ScenarioFile.model_validate_json(path.read_text(encoding="utf-8"))


def create_live(
    database: db.Database,
    *,
    character: str,
    spec_version: int,
    scenario: Scenario,
    model: str,
    user_name: str,
    character_name: str,
    session: str | None,
) -> int:
    with database.connect() as conn, db.transaction(conn):
        character_id = conn.execute("SELECT id FROM characters WHERE slug = ?", (character,)).fetchone()["id"]
        return conn.execute(
            "INSERT INTO transcripts (character_id, spec_version, kind, title, scenario, model, numbering,"
            " user_name, character_name, status, session, created_at)"
            " VALUES (?, ?, 'live', ?, ?, ?, 'turn', ?, ?, 'active', ?, ?)",
            (
                character_id,
                spec_version,
                f"{scenario.id} live run",
                scenario.id,
                model,
                user_name,
                character_name,
                session,
                telemetry.timestamp(telemetry.utc_now()),
            ),
        ).lastrowid


def add_message(
    database: db.Database,
    chat_id: int,
    *,
    turn: int,
    speaker: str,
    text: str,
    source: str,
    stopped: bool = False,
    model_call_id: int | None = None,
) -> MessageView:
    text = redact.text(text)
    with database.connect() as conn, db.transaction(conn):
        seq = conn.execute("SELECT COALESCE(MAX(seq), 0) + 1 FROM messages WHERE transcript_id = ?", (chat_id,)).fetchone()[0]
        conn.execute(
            "INSERT INTO messages (transcript_id, seq, turn, speaker, text, source, stopped, model_call_id, created_at)"
            " VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
            (chat_id, seq, turn, speaker, text, source, int(stopped), model_call_id, telemetry.timestamp(telemetry.utc_now())),
        )
    return MessageView(seq=seq, turn=turn, speaker=speaker, text=text, source=source, stopped=stopped, injection=injection.marked(text))


def set_status(database: db.Database, chat_id: int, status: str) -> None:
    with database.connect() as conn:
        conn.execute("UPDATE transcripts SET status = ? WHERE id = ?", (status, chat_id))


def session_runs(database: db.Database, session: str | None) -> int:
    """Live chats this browser session started. Requests that name no session count as one session."""
    with database.connect() as conn:
        return conn.execute(
            "SELECT COUNT(*) FROM transcripts WHERE session IS ? AND kind = 'live'", (session,)
        ).fetchone()[0]


# Reading chats.

_SUMMARY_SQL = (
    "SELECT transcripts.*, characters.slug AS character_slug, characters.name AS character_full_name,"
    " (SELECT COUNT(*) FROM messages WHERE messages.transcript_id = transcripts.id) AS message_count,"
    " (SELECT COUNT(*) FROM messages WHERE messages.transcript_id = transcripts.id AND messages.source = 'script')"
    " AS script_sent"
    " FROM transcripts JOIN characters ON characters.id = transcripts.character_id"
)


def _summary(row, scenarios: dict[str, Scenario], busy: set[int]) -> dict:
    scenario = scenarios.get(row["scenario"]) if row["kind"] == "live" else None
    total = len(scenario.lines) if scenario else 0
    return {
        "id": row["id"],
        "kind": row["kind"],
        "title": row["title"],
        "character": Character(slug=row["character_slug"], name=row["character_full_name"]),
        "spec_version": row["spec_version"],
        "sample": row["sample"],
        "scenario": row["scenario"],
        "model": row["model"],
        "tool": row["tool"],
        "receipt": row["receipt"],
        "numbering": row["numbering"],
        "user_name": row["user_name"],
        "character_name": row["character_name"],
        "status": row["status"],
        "created_at": row["created_at"],
        "message_count": row["message_count"],
        "script_total": total,
        "script_left": max(0, total - row["script_sent"]),
        "script_last_turn": scenario.lines[-1].turn if scenario else None,
        "busy": row["id"] in busy,
    }


def _message_view(row) -> MessageView:
    """A messages row with what its model call says about it: the model, a fallback, an error that cut it off."""
    stopped = bool(row["stopped"])
    return MessageView(
        seq=row["seq"],
        turn=row["turn"],
        speaker=row["speaker"],
        text=row["text"],
        source=row["source"],
        stopped=stopped,
        model=row["model_asked"],
        fallback=bool(row["fallback"]),
        failed=stopped and row["call_status"] == "error",
        injection=injection.marked(row["text"]),
    )


def get_chat(database: db.Database, chat_id: int, *, scenarios: dict[str, Scenario], busy: set[int] = frozenset()) -> ChatView:
    with database.connect() as conn:
        row = conn.execute(f"{_SUMMARY_SQL} WHERE transcripts.id = ?", (chat_id,)).fetchone()
        if row is None:
            raise ChatNotFound(f"There is no chat {chat_id}.")
        messages = conn.execute(
            "SELECT messages.seq, messages.turn, messages.speaker, messages.text, messages.source, messages.stopped,"
            " model_calls.model_asked, model_calls.fallback, model_calls.status AS call_status"
            " FROM messages LEFT JOIN model_calls ON model_calls.id = messages.model_call_id"
            " WHERE messages.transcript_id = ? ORDER BY messages.seq",
            (chat_id,),
        ).fetchall()
    return ChatView(
        **_summary(row, scenarios, busy),
        source=ChatSource.model_validate_json(row["source_json"]),
        messages=[_message_view(message) for message in messages],
    )


def list_chats(database: db.Database, *, scenarios: dict[str, Scenario], busy: set[int] = frozenset()) -> list[ChatSummary]:
    with database.connect() as conn:
        rows = conn.execute(f"{_SUMMARY_SQL} ORDER BY transcripts.id DESC").fetchall()
    return [ChatSummary(**_summary(row, scenarios, busy)) for row in rows]
