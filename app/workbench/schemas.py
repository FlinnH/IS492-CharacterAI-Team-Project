"""Shared Pydantic types: spec bodies as stored, edits from the Spec editor,
model settings, chats, and API responses."""

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator


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


# Model settings: the models file in app/prompts/ (models.v1.toml).

ProviderName = Literal["gemini", "ollama", "fake"]


class ModelSpec(Model):
    provider: ProviderName
    label: str
    # Left out to use the model's own default.
    reasoning_effort: str | None = None
    # Room for the reply and any thinking tokens.
    max_tokens: int = Field(ge=1)
    # Paid prices in US dollars per 1M tokens, for the estimated cost. The free tier costs nothing.
    input_price: float = Field(ge=0)
    cached_input_price: float = Field(ge=0)
    output_price: float = Field(ge=0)


class CharacterModels(Model):
    """The Model menu on Run a conversation, per provider. The first is the default."""

    gemini: list[str] = Field(min_length=1)
    ollama: list[str] = Field(min_length=1)
    fake: list[str] = Field(min_length=1)


class PreflightSettings(Model):
    # Reasoning efforts that preflight compares on time to first token.
    reasoning_efforts: list[str] = Field(min_length=1)
    # The chat preflight runs: the first turns of this scenario, on this spec version.
    scenario: str
    turns: int = Field(ge=1)
    spec_version: int = Field(ge=1)


class ModelSettings(Model):
    # The quota day ends at midnight in this time zone.
    quota_timezone: str
    character: CharacterModels
    preflight: PreflightSettings
    models: dict[str, ModelSpec]

    @model_validator(mode="after")
    def menus_name_known_models(self) -> "ModelSettings":
        for provider in ("gemini", "ollama", "fake"):
            for model_id in getattr(self.character, provider):
                spec = self.models.get(model_id)
                if spec is None or spec.provider != provider:
                    raise ValueError(f"the {provider} menu names {model_id}, which has no {provider} entry under models")
        return self

    def character_models(self, provider: str) -> list[str]:
        return list(getattr(self.character, provider))


# Scenarios: the fixed test scripts (app/samples/scenarios.v1.json).


class ScenarioLine(Model):
    turn: int = Field(ge=1)
    text: str


class Scenario(Model):
    id: str
    name: str
    lines: list[ScenarioLine] = Field(min_length=1)


class ScenarioFile(Model):
    format: Literal["workbench-scenarios.v1"]
    source: str
    character: str
    user_name: str
    character_name: str
    scenarios: list[Scenario]


# Chats. A saved chat file (the samples, or a pasted JSON chat) uses this format.

Speaker = Literal["user", "character"]
Numbering = Literal["turn", "line"]


class ChatSource(Model):
    """Where a saved chat came from, as its receipt says."""

    date: str = ""
    mode: str = ""
    model: str = ""
    note: str = ""


class SampleMessage(Model):
    turn: int
    speaker: Speaker
    text: str


class SampleChat(Model):
    format: Literal["workbench-chat.v1"]
    title: str
    tool: str = ""
    receipt: str = ""
    scenario: str | None = None
    character: str
    spec_version: int = Field(ge=1)
    user_name: str
    character_name: str
    numbering: Numbering
    source: ChatSource = Field(default_factory=ChatSource)
    messages: list[SampleMessage] = Field(min_length=1)


class FakeSettings(Model):
    """The fake model's defaults (app/samples/fake.v1.json)."""

    format: Literal["workbench-fake.v1"]
    model_reported: str
    reply: str
    chunk_chars: int = Field(ge=1)
    first_token_seconds: float = Field(ge=0)
    chunk_seconds: float = Field(ge=0)
    chars_per_token: int = Field(ge=1)


class MessageView(Model):
    seq: int
    # The source's own number: a turn, or a line when the chat numbers lines.
    turn: int
    speaker: Speaker
    text: str
    source: Literal["script", "typed", "import", "model"]
    stopped: bool


ChatKind = Literal["live", "import", "sample"]
ChatStatus = Literal["active", "script_done", "stopped", "imported"]


class ChatSummary(Model):
    id: int
    kind: ChatKind
    title: str
    character: Character
    spec_version: int
    # The sample a chat was loaded from (cla-f2, gpt-f2, seeded), or None.
    sample: str | None
    scenario: str | None
    model: str | None
    tool: str
    receipt: str
    numbering: Numbering
    user_name: str
    character_name: str
    status: ChatStatus
    created_at: str
    message_count: int
    # Live chats only: how many scripted lines there are, how many are still to
    # send, and the last scripted turn.
    script_total: int
    script_left: int
    script_last_turn: int | None
    # A reply is streaming in this chat right now.
    busy: bool


class ChatView(ChatSummary):
    source: ChatSource
    messages: list[MessageView]


# Requests from the Run screen and the Import dialog.


class StartChat(Model):
    character: str
    scenario: str
    model: str


class TypedLine(Model):
    text: str


class ImportRequest(Model):
    source: Literal["paste", "sample"]
    character: str
    # sample: the sample to load (cla-f2, gpt-f2, seeded).
    sample: str | None = None
    # paste: the chat, as pasted or read from a file.
    text: str | None = None
    # Defaults to the sample's own version, or the latest version for a paste.
    spec_version: int | None = Field(default=None, ge=1)
    # Which speaker label is the character, when the preview had to ask.
    character_label: str | None = None
    tool: str = ""
    receipt: str = ""


# Responses for the Run screen and the Import dialog.


class ScenarioOption(Model):
    id: str
    name: str
    turns: int
    last_turn: int


class ModelOption(Model):
    id: str
    label: str


class RunOptions(Model):
    character: Character
    latest_spec_version: int
    provider: ProviderName
    key_set: bool
    scenarios: list[ScenarioOption]
    models: list[ModelOption]
    default_model: str
    calls_per_minute: int
    daily_cap: int
    used_today: int
    max_typed_chars: int
    max_import_chars: int


class SampleInfo(Model):
    id: str
    label: str
    spec_version: int
    # The file the sample loads from, for the seeded transcript.
    path: str | None
    available: bool


class RowProblem(Model):
    # The line of the pasted text or file where the problem is. Never the text itself.
    row: int
    message: str


class SpeakerCount(Model):
    label: str
    count: int
    role: Speaker | None


class PreviewRow(Model):
    row: int
    number: int
    label: str
    speaker: Speaker | None
    text: str


class ImportPreview(Model):
    format: Literal["json", "table", "receipt", "inline"]
    numbering: Numbering
    message_count: int
    first_number: int | None
    last_number: int | None
    speakers: list[SpeakerCount]
    # True when the preview can't tell which speaker is the character.
    needs_roles: bool
    first_rows: list[PreviewRow]
    last_rows: list[PreviewRow]
    skipped_rows: list[int]
    problems: list[RowProblem]
    spec_version: int
    title: str
    # The saved chat this import would return, when it is already imported.
    duplicate_of: int | None


# Server-sent events for one live turn.


class UserEvent(Model):
    seq: int
    turn: int
    text: str


class WaitEvent(Model):
    seconds: float


class DeltaEvent(Model):
    text: str


class DoneEvent(Model):
    # None when nothing was saved, as when Stop came before the first word.
    message: MessageView | None
    stopped: bool
    status: ChatStatus
    script_left: int
    used_today: int


class ErrorEvent(Model):
    message: str
    retry: bool
    status: ChatStatus
