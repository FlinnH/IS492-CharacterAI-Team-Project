"""Shared Pydantic types: spec bodies as stored, edits from the Spec editor,
model settings, chats, the AI judge's answer, flags, and API responses."""

from typing import Any, Literal

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


class JudgeSettings(Model):
    """The AI judge, which reviews a whole chat in one call."""

    # The judge's own, never copied from the character's. Its accuracy matters
    # more than its speed, so it is low or higher.
    reasoning_effort: Literal["low", "medium", "high"]
    # The judge answers in one piece after it thinks, so this leaves room for both.
    max_tokens: int = Field(ge=1)
    # The judge model for each provider.
    gemini: str
    ollama: str
    fake: str


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
    judge: JudgeSettings
    preflight: PreflightSettings
    models: dict[str, ModelSpec]

    @model_validator(mode="after")
    def menus_name_known_models(self) -> "ModelSettings":
        for provider in ("gemini", "ollama", "fake"):
            for model_id in getattr(self.character, provider):
                spec = self.models.get(model_id)
                if spec is None or spec.provider != provider:
                    raise ValueError(f"the {provider} menu names {model_id}, which has no {provider} entry under models")
            judge_id = getattr(self.judge, provider)
            spec = self.models.get(judge_id)
            if spec is None or spec.provider != provider:
                raise ValueError(f"the {provider} judge is {judge_id}, which has no {provider} entry under models")
        return self

    def character_models(self, provider: str) -> list[str]:
        return list(getattr(self.character, provider))

    def judge_model(self, provider: str) -> str:
        return getattr(self.judge, provider)


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


# The AI judge's answer. app/prompts/judge.schema.v1.json is this model's JSON
# schema with every $ref written out (inline_refs), since Gemini's structured
# output doesn't list $defs. config refuses to start if the two differ.

FailureType = Literal[
    "persona drift",
    "memory loss",
    "factual contradiction",
    "knowledge-boundary violation",
    "style drift",
    "situational mismatch",
    "persona exit",
    "invented claim about the user",
]
Confidence = Literal["high", "medium", "low"]


class JudgeFlag(Model):
    turn: int = Field(description="The turn number of the character's reply, exactly as the chat numbers it.")
    type: FailureType = Field(description="The kind of break.")
    line_id: str = Field(
        description="The ID of the one spec line the reply breaks, or the label of the spec field it breaks."
    )
    quote: str = Field(description="The shortest exact span of the reply that shows the break, copied word for word.")
    confidence: Confidence = Field(
        description="high when the spec settles it, medium when it probably breaks, low when unsure."
    )
    near_boundary_guess: bool = Field(
        description="True when the reply guesses or hints toward something the character can't know, without naming it."
    )
    needs_your_call: bool = Field(description="True when only the person who wrote the spec can settle it.")
    why: str = Field(description="One plain sentence that says what breaks and why.")


class UserClaim(Model):
    turn: int = Field(description="The turn of the character's reply that makes the claim.")
    quote: str = Field(description="The shortest exact span of the reply that makes the claim, copied word for word.")
    supported_by_turn: int = Field(
        description="The turn of the user line that says it, or 0 if the user never said it before that reply."
    )


class JudgeGap(Model):
    topic: str = Field(description="A short name for what couldn't be checked.")
    turns: list[int] = Field(description="The turns it concerns.")
    why: str = Field(description="Why the spec and the chat can't settle it.")


class JudgeOutput(Model):
    flags: list[JudgeFlag] = Field(description="Every break in the character's replies.")
    user_claims: list[UserClaim] = Field(description="Every claim the character makes about the user.")
    not_checked: list[JudgeGap] = Field(description="What the spec and the chat alone can't settle.")


def inline_refs(schema: dict[str, Any]) -> dict[str, Any]:
    """The schema with each "$ref" replaced by the definition it points to, and no "$defs"."""
    definitions = schema.get("$defs", {})

    def expand(node):
        if isinstance(node, list):
            return [expand(item) for item in node]
        if not isinstance(node, dict):
            return node
        if "$ref" in node:
            target = expand(definitions[node["$ref"].rsplit("/", 1)[-1]])
            return {**target, **{key: expand(value) for key, value in node.items() if key != "$ref"}}
        return {key: expand(value) for key, value in node.items() if key != "$defs"}

    return expand(schema)


# Flags. A finding is a flag that passed its checks, before it is saved: from a
# rule check (code alone) or from the judge. Code, not the judge, sets
# needs_call, and needs_call_reason says which rule did.

FlagSource = Literal["judge", "rule", "recheck"]
NeedsCallReason = Literal["persona_exit", "near_guess", "unsure_boundary", "line", "judge"]
# Why the evidence checks hid a judge flag. The screen counts these.
HiddenReason = Literal["not_a_reply", "unknown_line", "quote_other_turn", "quote_from_user", "quote_not_found"]
# Flags that repeat another flag are dropped too, but nothing is lost, so the screen doesn't count them.
RejectReason = HiddenReason | Literal["duplicate", "repeats_rule"]


class Finding(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    source: Literal["judge", "rule"]
    turn: int
    # A rule flag's other broken turns, after the first.
    also_turns: tuple[int, ...] = ()
    type: FailureType
    # A line ID or a field label, exactly as the spec writes it.
    line_id: str
    # An exact span of the reply, so the screen can mark it.
    quote: str
    confidence: Confidence
    near_boundary_guess: bool = False
    needs_call: bool = False
    needs_call_reason: NeedsCallReason | None = None
    why: str


# Check results, for Run a conversation.


class CheckFlag(Model):
    id: int
    source: FlagSource
    turn: int
    also_turns: list[int]
    type: FailureType
    line_id: str
    # The cited line's own words, from the chat's spec version, so a flag never
    # restates its rule in the AI's words.
    line_text: str
    quote: str
    confidence: Confidence
    near_boundary_guess: bool
    needs_call: bool
    needs_call_reason: NeedsCallReason | None
    # The judge reviewed a turn its own model wrote.
    same_model: bool
    why: str


class HiddenCount(Model):
    reason: HiddenReason
    count: int


class NotCheckedTopic(Model):
    topic: str
    turns: list[int]
    why: str


class JudgeRunView(Model):
    status: Literal["ok", "failed"]
    model: str
    model_label: str
    reasoning_effort: str | None
    prompt_version: str
    schema_version: str
    same_model: bool
    # For the creator when the judge's flags are missing. Empty when it worked.
    note: str
    checked_at: str


class CheckView(Model):
    chat_id: int
    spec_version: int
    # True when this came from a saved check, with no new model call.
    cached: bool
    judge: JudgeRunView
    flags: list[CheckFlag]
    hidden: list[HiddenCount]
    not_checked: list[NotCheckedTopic]


class CheckState(Model):
    # A check of this chat is running now.
    running: bool
    # The saved check of the chat as it is now, or None.
    result: CheckView | None


# Flag review: the creator's call on each flag of a saved check.

Verdict = Literal["agreed", "overridden"]


class FlagCall(Model):
    verdict: Verdict
    # Why the creator overrode the flag. None for an agree.
    reason: str | None
    # The type an override says is right, when it changes the flag's type. The
    # flag then still counts as a break, of this type.
    type: FailureType | None
    made_at: str


class ReviewFlag(CheckFlag):
    # The creator has opened the flag's evidence at least once, which unlocks Agree.
    evidence_opened: bool
    # The creator's standing call, or None while the flag needs one.
    call: FlagCall | None
    # True unless the creator overrode the flag without giving another type.
    counts_as_break: bool


class ReviewChat(Model):
    chat: ChatView
    spec_version: int
    judge: JudgeRunView
    flags: list[ReviewFlag]
    hidden: list[HiddenCount]
    not_checked: list[NotCheckedTopic]
    # Flags with no call yet.
    open_calls: int
    # The earliest turn with a flag that counts as a break, or None.
    first_break: int | None
    # Every flag has a call, and every call is Agree: the rubber-stamp check.
    agreed_with_every: bool
    # The newest event on this chat's flags, or 0, so the screen can tell an older answer from a newer one.
    last_event_id: int


class ReviewState(Model):
    # The override rules, so the screen checks what the server checks.
    min_reason_words: int
    max_reason_chars: int
    # The types an override may give.
    failure_types: list[FailureType]
    # Flags with no call yet, in every chat below.
    open_calls: int
    # Every checked chat whose saved check covers it as it stands, oldest first.
    chats: list[ReviewChat]
    # Checked chats that changed after their check, so their flags wait for a new one.
    changed: list[ChatSummary]


class OverrideCall(Model):
    reason: str
    # The right type, when the flag's own type is wrong. None means it isn't a break.
    type: FailureType | None = None
