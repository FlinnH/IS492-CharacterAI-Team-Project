"""Character specs: saved versions never change, and a line ID is never reused.

Line IDs, line attributes, and check limits all come from the spec itself
(v1 is app/samples/spec_v1.json), so this code never names a line. Each call
opens its own short connection through db.Database.
"""

import hashlib
import json
import re
from datetime import datetime, timezone
from pathlib import Path

from workbench import db
from workbench.config import APP_DIR
from workbench.schemas import (
    Character,
    SpecBody,
    SpecEdit,
    SpecLine,
    SpecView,
    SpecWarning,
    VersionSummary,
)

SAMPLE_FILE = APP_DIR / "samples" / "spec_v1.json"

SETTING_WARNING = (
    "The setting is empty. Say where and how this conversation happens, "
    "or the character may keep asking how you found them."
)

# A line typed with an ID in front: a capital letter and digits, then "." or
# ":" and a space. The workbench adds IDs itself.
ID_AT_START = re.compile(r"[A-Z][0-9]+[.:]\s")


class SpecNotFound(Exception):
    """No such character, or no such version of its spec."""


class SpecConflict(Exception):
    """The edit started from a version that is no longer the latest."""


class SpecInvalid(Exception):
    """The edit can't be saved as it is. field names the draft field to fix, if one applies."""

    def __init__(self, message: str, field: str | None = None) -> None:
        super().__init__(message)
        self.field = field


def canonical_json(body: SpecBody) -> str:
    """The one way a body is stored and hashed: sorted keys, no defaults, no spaces."""
    return json.dumps(
        body.model_dump(mode="json", exclude_defaults=True),
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
    )


def sha256_hex(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def clean_text(text: str, field: str, where: str) -> str:
    """Drops zero-width marks, trims, and turns every run of whitespace into one space.

    where names the text in a message, like "the setting" or a line ID.
    """
    try:
        text.encode("utf-8")
    except UnicodeEncodeError:
        message = f"{where[0].upper()}{where[1:]} has a character that can't be saved. Retype it."
        raise SpecInvalid(message, field) from None
    return " ".join(text.replace("\u200b", "").replace("\ufeff", "").split())


def warnings_for(body: SpecBody) -> list[SpecWarning]:
    if body.setting.strip():
        return []
    return [SpecWarning(field="setting", message=SETTING_WARNING)]


def next_line_id(prefix: str, used: set[str]) -> str:
    """The prefix plus one more than the highest number ever issued with it."""
    pattern = re.compile(rf"{re.escape(prefix)}([0-9]+)")
    numbers = [int(match[1]) for line_id in used if (match := pattern.fullmatch(line_id))]
    return f"{prefix}{max(numbers, default=0) + 1}"


def _required(text: str, field: str, where: str, empty_message: str) -> str:
    cleaned = clean_text(text, field, where)
    if not cleaned:
        raise SpecInvalid(empty_message, field)
    return cleaned


def _line_text(text: str, field: str, where: str, empty_message: str) -> str:
    cleaned = _required(text, field, where, empty_message)
    if ID_AT_START.match(cleaned):
        raise SpecInvalid(f"Leave the ID out of {where}. The workbench adds IDs.", field)
    return cleaned


def apply_edit(parent: SpecBody, edit: SpecEdit, used: set[str]) -> tuple[SpecBody, list[str]]:
    """The body this edit makes from parent, and the IDs it issues, in document order.

    used holds every line ID ever issued for the character, so new lines skip
    removed IDs too. Attributes and limits come from the parent, never the edit.
    """
    if [field.label for field in edit.fields] != [field.label for field in parent.fields]:
        raise SpecInvalid("The spec's fields changed. Reload the page and try again.")
    if [section.heading for section in edit.sections] != [section.heading for section in parent.sections]:
        raise SpecInvalid("The spec's sections changed. Reload the page and try again.")

    preamble = _required(
        edit.preamble, "preamble", "the opening instruction", "The opening instruction is empty. Write it before you save."
    )
    fields = [
        old.model_copy(
            update={"text": _required(new.text, f"field-{i}", new.label, f"{new.label} is empty. Write it before you save.")}
        )
        for i, (old, new) in enumerate(zip(parent.fields, edit.fields))
    ]
    setting = clean_text(edit.setting, "setting", "the setting")

    parent_lines = {line.id: line for section in parent.sections for line in section.lines}
    used = set(used)
    kept: set[str] = set()
    new_ids: list[str] = []
    sections = []
    for s, (old_section, new_section) in enumerate(zip(parent.sections, edit.sections)):
        heading = new_section.heading
        lines = []
        for i, line in enumerate(new_section.lines):
            field = f"line-{s}-{i}"
            if line.id is None:
                text = _line_text(
                    line.text, field, f"the new line in {heading}", f"A new line in {heading} is empty. Write it or delete it."
                )
                line_id = next_line_id(old_section.prefix, used)
                used.add(line_id)
                new_ids.append(line_id)
                lines.append(SpecLine(id=line_id, text=text))
                continue
            if line.id not in parent_lines:
                raise SpecInvalid(f"{line.id} is not in the version you edited.", field)
            if line.id in kept:
                raise SpecInvalid(f"{line.id} appears twice.", field)
            if not re.fullmatch(rf"{old_section.prefix}[0-9]+", line.id):
                raise SpecInvalid(f"{line.id} can't move to {heading}.", field)
            kept.add(line.id)
            text = _line_text(line.text, field, line.id, f"{line.id} is empty. Write the line or delete it.")
            lines.append(parent_lines[line.id].model_copy(update={"text": text}))
        sections.append(old_section.model_copy(update={"lines": lines}))

    body = SpecBody(preamble=preamble, fields=fields, setting=setting, sections=sections)
    return body, new_ids


def _now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _character(conn: db.Connection, slug: str):
    row = conn.execute("SELECT id, slug, name FROM characters WHERE slug = ?", (slug,)).fetchone()
    if row is None:
        raise SpecNotFound(f"There is no character called {slug}.")
    return row


def _latest(conn: db.Connection, character_id: int) -> int:
    return conn.execute("SELECT MAX(version) FROM spec_versions WHERE character_id = ?", (character_id,)).fetchone()[0]


def _version_row(conn: db.Connection, character_id: int, version: int):
    return conn.execute(
        "SELECT version, parent, body, sha256, note, created_at FROM spec_versions"
        " WHERE character_id = ? AND version = ?",
        (character_id, version),
    ).fetchone()


def seed(database: db.Database, sample_file: Path = SAMPLE_FILE) -> None:
    """Adds the sample character and its v1, once. Refuses a database whose v1 differs."""
    sample = json.loads(sample_file.read_text(encoding="utf-8"))
    body = SpecBody.model_validate(sample["body"])
    body_json = canonical_json(body)
    slug = sample["character"]["slug"]

    with database.connect() as conn, db.transaction(conn):
        row = conn.execute(
            "SELECT spec_versions.sha256 FROM characters"
            " JOIN spec_versions ON spec_versions.character_id = characters.id"
            " WHERE characters.slug = ? AND spec_versions.version = 1",
            (slug,),
        ).fetchone()
        if row is not None:
            if row["sha256"] != sha256_hex(body_json):
                raise RuntimeError(
                    f"{database.path} holds a different spec v1 than {sample_file}. "
                    "Delete the database file to start fresh. Its saved spec versions go with it."
                )
            return

        character_id = conn.execute(
            "INSERT INTO characters (slug, name) VALUES (?, ?)", (slug, sample["character"]["name"])
        ).lastrowid
        conn.execute(
            "INSERT INTO spec_versions (character_id, version, parent, body, sha256, note, created_at)"
            " VALUES (?, 1, NULL, ?, ?, ?, ?)",
            (character_id, body_json, sha256_hex(body_json), sample["note"], _now()),
        )
        conn.executemany(
            "INSERT INTO line_ids (character_id, line_id, first_version) VALUES (?, ?, 1)",
            [(character_id, line.id) for section in body.sections for line in section.lines],
        )


def list_characters(database: db.Database) -> list[Character]:
    with database.connect() as conn:
        rows = conn.execute("SELECT slug, name FROM characters ORDER BY id").fetchall()
    return [Character(slug=row["slug"], name=row["name"]) for row in rows]


def get_spec(database: db.Database, slug: str, version: int | None = None) -> SpecView:
    """One version of a character's spec (the latest if version is None)."""
    with database.connect() as conn:
        character = _character(conn, slug)
        latest = _latest(conn, character["id"])
        # Checked here, before any query, so a huge number can't overflow SQLite.
        if version is None:
            version = latest
        elif not 1 <= version <= latest:
            raise SpecNotFound(f"{character['name']} has no spec v{version}.")
        row = _version_row(conn, character["id"], version)
        history = conn.execute(
            "SELECT version, parent, note, created_at FROM spec_versions WHERE character_id = ? ORDER BY version DESC",
            (character["id"],),
        ).fetchall()

    body = SpecBody.model_validate_json(row["body"])
    return SpecView(
        character=Character(slug=character["slug"], name=character["name"]),
        version=version,
        latest=latest,
        parent=row["parent"],
        note=row["note"],
        created_at=row["created_at"],
        sha256=row["sha256"],
        body=body,
        warnings=warnings_for(body),
        versions=[
            VersionSummary(version=item["version"], parent=item["parent"], note=item["note"], created_at=item["created_at"])
            for item in history
        ],
    )


def save_edit(database: db.Database, slug: str, edit: SpecEdit) -> SpecView:
    """Saves the edit as the next version. Only the latest version can be edited."""
    with database.connect() as conn, db.transaction(conn):
        character = _character(conn, slug)
        latest = _latest(conn, character["id"])
        if edit.parent > latest:
            raise SpecInvalid(f"There is no v{edit.parent} to edit. Reload the page and try again.")
        if edit.parent < latest:
            raise SpecConflict(
                f"A newer version (v{latest}) was saved while you were editing. "
                "Copy anything you want to keep, then reload."
            )

        parent_row = _version_row(conn, character["id"], latest)
        used = {row["line_id"] for row in conn.execute("SELECT line_id FROM line_ids WHERE character_id = ?", (character["id"],))}
        body, new_ids = apply_edit(SpecBody.model_validate_json(parent_row["body"]), edit, used)
        body_json = canonical_json(body)
        if body_json == parent_row["body"]:
            raise SpecInvalid("Nothing changed, so there's nothing to save.")

        version = latest + 1
        note = clean_text(edit.note, "note", "the note")
        try:
            conn.execute(
                "INSERT INTO spec_versions (character_id, version, parent, body, sha256, note, created_at)"
                " VALUES (?, ?, ?, ?, ?, ?, ?)",
                (character["id"], version, latest, body_json, sha256_hex(body_json), note, _now()),
            )
            conn.executemany(
                "INSERT INTO line_ids (character_id, line_id, first_version) VALUES (?, ?, ?)",
                [(character["id"], line_id, version) for line_id in new_ids],
            )
        except db.IntegrityError as error:
            # Only another save racing this one can get here.
            raise SpecConflict(
                "A newer version was saved while you were editing. Copy anything you want to keep, then reload."
            ) from error

    return get_spec(database, slug, version)
