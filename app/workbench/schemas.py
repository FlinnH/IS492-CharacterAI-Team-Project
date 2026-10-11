"""Shared Pydantic types: spec bodies as stored, edits from the Spec editor, and API responses."""

from pydantic import BaseModel, ConfigDict, Field


class Model(BaseModel):
    model_config = ConfigDict(extra="forbid")


# A stored spec body. Saved JSON leaves out attributes at their defaults, so
# adding an attribute with a default later doesn't change a saved version's hash.


class SpecLine(Model):
    id: str = Field(pattern=r"^[A-Z][1-9][0-9]*$")
    text: str
    # Flags that cite this line always need the creator's call (M3).
    needs_call: bool = False
    # A claim about the user that the user never made is flagged on this line (M3).
    provenance: bool = False
    # Rule check: the most sentences a reply may have (M3).
    max_sentences: int | None = Field(default=None, ge=1)


class SpecField(Model):
    label: str
    text: str
    # Rule check: words a reply must not use, and whether emojis count too (M3).
    banned_words: list[str] = Field(default_factory=list)
    ban_emojis: bool = False


class SpecSection(Model):
    heading: str
    # Every line ID in this section starts with this letter.
    prefix: str = Field(pattern=r"^[A-Z]$")
    lines: list[SpecLine]


class SpecBody(Model):
    preamble: str
    fields: list[SpecField]
    setting: str
    sections: list[SpecSection]


# An edit from the Spec editor. Kept lines carry their ID and new lines carry
# none. The server numbers new lines and carries every attribute forward.


class LineEdit(Model):
    id: str | None = None
    text: str


class FieldEdit(Model):
    label: str
    text: str


class SectionEdit(Model):
    heading: str
    lines: list[LineEdit]


class SpecEdit(Model):
    parent: int = Field(ge=1)
    note: str = ""
    preamble: str
    fields: list[FieldEdit]
    setting: str
    sections: list[SectionEdit]


# API responses.


class Character(Model):
    slug: str
    name: str


class SpecWarning(Model):
    field: str
    message: str


class VersionSummary(Model):
    version: int
    parent: int | None
    note: str
    created_at: str


class SpecView(Model):
    character: Character
    version: int
    latest: int
    parent: int | None
    note: str
    created_at: str
    sha256: str
    body: SpecBody
    warnings: list[SpecWarning]
    # Newest first.
    versions: list[VersionSummary]
