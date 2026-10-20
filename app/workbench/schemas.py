"""Shared Pydantic types: spec bodies as stored, edits from the Spec editor,
model settings, chats, the AI judge's answers, flags, and API responses."""

import re
from typing import Annotated, Any, Literal, get_args

from pydantic import BaseModel, ConfigDict, Field, model_validator


class Model(BaseModel):
    model_config = ConfigDict(extra="forbid")


class Removed(Model):
    """What redaction took out of some text before a model or the database saw it (M6)."""

    model_config = ConfigDict(frozen=True)

    emails: int = 0
    phone_numbers: int = 0
    keys: int = 0

    @property
    def total(self) -> int:
        return self.emails + self.phone_numbers + self.keys

    def __add__(self, other: "Removed") -> "Removed":
        return Removed(
            emails=self.emails + other.emails,
            phone_numbers=self.phone_numbers + other.phone_numbers,
            keys=self.keys + other.keys,
        )


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
    # Checked like a stored line's ID, so a made-up one is refused before the edit is read.
    id: str | None = Field(default=None, pattern=r"^[A-Z][1-9][0-9]*$")
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
    # What redaction took out of the edit that saved this version. Zero except in a save's answer.
    removed: Removed = Field(default_factory=Removed)


# Model settings: the models file in app/prompts/ (models.v1.toml).

ProviderName = Literal["gemini", "ollama", "fake", "openai_compatible"]
PROVIDERS: tuple[str, ...] = get_args(ProviderName)

# What Settings accepts (M6.5). A base URL is http or https with no user,
# password, query, or fragment, so no key can hide in it. A model ID and a key
# hold no spaces, quotes, or line breaks, so app/.env can hold them as they are.
BASE_URL = re.compile(r"https?://[A-Za-z0-9.-]+(?::[0-9]{1,5})?(?:/[A-Za-z0-9._~%/-]*)?")
MODEL_ID = re.compile(r"[A-Za-z0-9@][A-Za-z0-9._:/@+-]{0,199}")
API_KEY = re.compile(r"[A-Za-z0-9._~+/=-]{8,512}")

Price = Annotated[float, Field(ge=0)]


class ModelSpec(Model):
    provider: ProviderName
    label: str
    # Left out to use the model's own default.
    reasoning_effort: str | None = None
    # Room for the reply and any thinking tokens.
    max_tokens: int = Field(ge=1)
    # Paid prices in US dollars per 1M tokens, for the estimated cost. The free
    # tier costs nothing. None for a model the models file doesn't list, whose
    # price isn't known, so its calls show no estimated cost.
    input_price: Price | None
    cached_input_price: Price | None
    output_price: Price | None


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


class UnlistedModels(Model):
    """Settings for a model the models file doesn't list (M6.5): one Ollama has
    installed, or one typed for another OpenAI-compatible service."""

    # The providers whose models needn't be listed.
    providers: list[ProviderName]
    max_tokens: int = Field(ge=1)


class LimitBounds(Model):
    """The most Settings lets a creator raise the machine limits to (M6.5). The least is 1."""

    calls_per_minute: int = Field(ge=1)
    daily_call_cap: int = Field(ge=1)


class ModelSettings(Model):
    # The quota day ends at midnight in this time zone.
    quota_timezone: str
    character: CharacterModels
    judge: JudgeSettings
    preflight: PreflightSettings
    models: dict[str, ModelSpec]
    # The model to ask instead when a call to the model on the left still gets
    # 429 or a 5xx after its retries (M6). A model with no entry has no fallback.
    fallback: dict[str, str] = Field(default_factory=dict)
    unlisted: UnlistedModels
    limits: LimitBounds

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
        for model_id, other in self.fallback.items():
            first, second = self.models.get(model_id), self.models.get(other)
            if first is None or second is None:
                raise ValueError(f"the fallback for {model_id} is {other}, and both need an entry under models")
            if model_id == other or first.provider != second.provider:
                raise ValueError(f"{model_id} must fall back to another model of its own provider, not {other}")
        return self

    def character_models(self, provider: str) -> list[str]:
        """The provider's Model menu. Empty for another OpenAI-compatible service, whose models are typed."""
        return list(getattr(self.character, provider, []))

    def judge_model(self, provider: str) -> str | None:
        """The provider's judge, or None for another OpenAI-compatible service."""
        return getattr(self.judge, provider, None)

    def judge_menu(self, provider: str) -> list[str]:
        """Every model of the provider that the file lists, its judge first."""
        default = self.judge_model(provider)
        others = [model_id for model_id, spec in self.models.items() if spec.provider == provider and model_id != default]
        return ([default] if default else []) + others

    def judge_effort(self, model_id: str) -> str | None:
        """The judge's reasoning effort, or None for a model the file doesn't list, since not every service takes one."""
        return self.judge.reasoning_effort if model_id in self.models else None

    def spec(self, model_id: str, provider: str) -> ModelSpec:
        """The model's settings: its entry under models, or, for a model the file
        doesn't list, the [unlisted] ones, with its ID as its label."""
        listed = self.models.get(model_id)
        if listed is not None:
            return listed
        return ModelSpec(
            provider=provider,
            label=model_id,
            max_tokens=self.unlisted.max_tokens,
            input_price=None,
            cached_input_price=None,
            output_price=None,
        )

    def offers(self, provider: str, model_id: str) -> bool:
        """Whether the provider can answer with this model: one of its own, or any
        model the file doesn't list, for a provider whose models needn't be listed."""
        listed = self.models.get(model_id)
        if listed is not None:
            return listed.provider == provider
        return provider in self.unlisted.providers

    def fallback_for(self, model_id: str) -> str | None:
        return self.fallback.get(model_id)


# Services for "Another OpenAI-compatible service" in Settings (app/prompts/presets.v1.toml).


class Preset(Model):
    id: str = Field(pattern=r"^[a-z0-9]+$")
    label: str
    base_url: str
    # Key prefixes only this service uses, so the Settings screen can suggest it from a pasted key.
    key_prefixes: list[str]
    # The request field that caps a reply's length.
    token_field: Literal["max_tokens", "max_completion_tokens"]
    # Whether a streamed call asks for token counts with stream_options.
    stream_usage: bool
    # Shown under the base URL when this service is picked. Empty for none.
    note: str

    @model_validator(mode="after")
    def base_url_is_one_settings_accepts(self) -> "Preset":
        if not BASE_URL.fullmatch(self.base_url):
            raise ValueError(f"the base URL of {self.id} isn't one Settings accepts")
        return self


class Presets(Model):
    # Keys from Google AI Studio start with one of these, so a pasted one suggests Gemini.
    gemini_key_prefixes: list[str]
    presets: list[Preset] = Field(min_length=1)

    def match(self, base_url: str) -> Preset | None:
        """The service whose base URL this is, ignoring a trailing slash and the case of the host."""
        wanted = _plain_url(base_url)
        return next((preset for preset in self.presets if _plain_url(preset.base_url) == wanted), None)


def _plain_url(url: str) -> str:
    scheme, _, rest = url.strip().partition("://")
    host, slash, path = rest.partition("/")
    return f"{scheme.lower()}://{host.lower()}{slash}{path}".rstrip("/")


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
    # The model whose call wrote this reply, or None for a line no model wrote.
    model: str | None = None
    # The fallback model wrote this reply, after the first model kept failing.
    fallback: bool = False
    # A model error cut this reply off partway, so Try again answers its line again.
    failed: bool = False
    # The line reads like an instruction to the AI: possible prompt injection.
    injection: bool = False


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
    # Every model of the provider by ID, the fallback models too, so a reply can name its model.
    model_labels: dict[str, str]
    default_model: str
    calls_per_minute: int
    daily_cap: int
    used_today: int
    # Runs this browser session has started, and how many one session may start.
    session_runs: int
    session_run_limit: int
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
    # The line reads like an instruction to the AI: possible prompt injection.
    injection: bool


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
    # What redaction took out before anything was saved.
    removed: Removed
    # The numbers of the messages that read like instructions to the AI, in source order.
    injection_numbers: list[int]


# Server-sent events for one live turn.


class UserEvent(Model):
    seq: int
    turn: int
    text: str
    injection: bool


class WaitEvent(Model):
    seconds: float
    # slot: the call waits for its slot under the per-minute limit. retry: the
    # service was busy, so the call is tried again after a pause. fallback: the
    # fallback model answers instead.
    reason: Literal["slot", "retry", "fallback"] = "slot"
    # What the Run screen shows for a retry or a fallback. Empty for a slot,
    # which the screen words itself.
    message: str = ""


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
    # The part of the reply that came before the error, saved as cut off, or None.
    partial: MessageView | None = None


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


# The follow-up re-check's answer. app/prompts/recheck.schema.v1.json is this
# model's JSON schema written out the same way, and config checks it too.

RecheckAction = Literal["keep", "rerate", "withdraw"]


class RecheckReview(Model):
    flag_id: int = Field(description="The id of a flag marked recheck: true in the request.")
    action: RecheckAction = Field(
        description="keep when the reply breaks the spec as flagged, rerate when it breaks the spec at another"
        " confidence, withdraw when it doesn't break the spec."
    )
    confidence: Confidence = Field(
        description="Your confidence now: high when the spec settles it, medium when it probably breaks, low when"
        " unsure. For withdraw, how sure you are that it isn't a break."
    )
    why: str = Field(description="One plain sentence that says what you decided and why.")


class RecheckOutput(Model):
    reviews: list[RecheckReview] = Field(description="One review for each flag marked recheck: true.")
    new_flags: list[JudgeFlag] = Field(description="Breaks the first pass missed, with the same fields as its flags.")
    answer: str = Field(
        description="Your answer to the creator's question, in plain sentences, or an empty string when there is no question."
    )


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
# rule check (code alone), from the judge, or from its re-check. Code, not the
# judge, sets needs_call, and needs_call_reason says which rule did.

FlagSource = Literal["judge", "rule", "recheck"]
NeedsCallReason = Literal["persona_exit", "near_guess", "unsure_boundary", "line", "judge"]
# Why the evidence checks hid a judge flag. The screen counts these.
HiddenReason = Literal["not_a_reply", "unknown_line", "quote_other_turn", "quote_from_user", "quote_not_found"]
# Flags that repeat another flag are dropped too, but nothing is lost, so the screen doesn't count them.
RejectReason = HiddenReason | Literal["duplicate", "repeats_rule"]


class Finding(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    source: FlagSource
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
    id: int
    status: Literal["ok", "failed"]
    model: str
    model_label: str
    reasoning_effort: str | None
    prompt_version: str
    schema_version: str
    same_model: bool
    # The fallback model answered, after the judge's own model kept failing.
    fallback: bool
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


# The follow-up re-check. A flag it added, withdrew, re-rated, or kept, with
# its one-line reason. kept_because is set when it asked to withdraw a flag
# that stayed: only the creator can settle the flag, or it has their call.

FlagChangeKind = Literal["added", "withdrawn", "rerated", "kept"]
KeptBecause = Literal["needs_call", "your_call"]


class FlagRecheck(Model):
    """The latest re-check's word on one flag."""

    change: FlagChangeKind
    from_confidence: Confidence
    to_confidence: Confidence
    kept_because: KeptBecause | None
    why: str
    made_at: str


class FlagChange(FlagRecheck):
    """One line of What changed. A withdrawn flag isn't in the review anymore, so its evidence comes along."""

    flag_id: int
    turn: int
    type: FailureType
    line_id: str
    quote: str


class RecheckRequest(Model):
    # The creator's own question, or None.
    question: str | None = None


class RecheckView(Model):
    """The latest re-check of a chat's check, for the What changed panel."""

    id: int
    status: Literal["ok", "failed"]
    # For the creator when the re-check didn't finish. Empty when it worked.
    note: str
    model_label: str
    checked_at: str
    question: str | None
    # The AI's answer to the question, in its own words. Empty without a question.
    answer: str
    # How many flags it looked at again.
    picked: int
    changes: list[FlagChange]
    # Its new flags that failed the evidence checks.
    hidden: list[HiddenCount]


class ReviewFlag(CheckFlag):
    # The creator has opened the flag's evidence at least once, which unlocks Agree.
    evidence_opened: bool
    # The creator's standing call, or None while the flag needs one.
    call: FlagCall | None
    # True unless the creator overrode the flag without giving another type.
    counts_as_break: bool
    # The latest re-check's word on this flag, or None.
    recheck: FlagRecheck | None
    # The re-check looked again at this flag and disagrees with its standing
    # on whether it is a break, so the screen shows both views.
    disputed: bool


class ReviewChat(Model):
    chat: ChatView
    spec_version: int
    judge: JudgeRunView
    flags: list[ReviewFlag]
    hidden: list[HiddenCount]
    not_checked: list[NotCheckedTopic]
    # The latest re-check of this check, or None.
    recheck: RecheckView | None
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


# Settings (M6.5): the dialog opened from the top bar. A key goes in only, in
# SettingsDraft.api_key, and never comes back in any response.


class KeyState(Model):
    # Whether app/.env, or the shell, holds a key for the provider.
    saved: bool
    # The key's last 4 characters, for a key of 16 or more. Never more of it.
    last4: str | None
    # An environment variable sets it, so Settings can't change it.
    locked: bool


class ProviderMenus(Model):
    """One provider's model menus in Settings, and the models a fresh choice starts from."""

    provider: ProviderName
    character_models: list[ModelOption]
    judge_models: list[ModelOption]
    # None for another OpenAI-compatible service, whose models are typed.
    default_character: str | None
    # A different model than default_character when the provider has one.
    default_judge: str | None


class SettingsView(Model):
    # The character's first name, for "Harry's model".
    character_name: str
    provider: ProviderName
    providers: list[ProviderMenus]
    # Another OpenAI-compatible service's address, or "".
    base_url: str
    presets: list[Preset]
    gemini_key_prefixes: list[str]
    # By provider: gemini and openai_compatible, the two that take a key.
    keys: dict[str, KeyState]
    character_model: str
    judge_model: str
    calls_per_minute: int
    daily_call_cap: int
    max_calls_per_minute: int
    max_daily_call_cap: int
    # Runs, and AI judge calls, one browser session may make. Each may be 1 up to the daily cap.
    session_run_limit: int
    session_judge_limit: int
    used_today: int
    # M6's forced errors. all can only come from app/.env.
    simulate_busy: bool
    force_mode: Literal["off", "primary", "all"]
    # Setting names an environment variable sets, which Settings can't change.
    locked: list[str]
    # The app_settings row in force, and when it was saved.
    settings_id: int
    saved_at: str


class SettingsDraft(Model):
    provider: ProviderName
    base_url: str = Field(default="", max_length=300)
    # A newly pasted key, or None to keep the saved one.
    api_key: str | None = Field(default=None, max_length=600)
    character_model: str = Field(max_length=300)
    judge_model: str = Field(max_length=300)
    calls_per_minute: int
    daily_call_cap: int
    session_run_limit: int
    session_judge_limit: int
    simulate_busy: bool = False


class ConnectionCheck(Model):
    """What Test found, in plain words: what happened, then what to do next."""

    ok: bool
    message: str
    next: str
    model: str
    model_label: str
    # How long the call took, or None when no call was made.
    seconds: float | None


class OllamaModels(Model):
    running: bool
    # The models Ollama has installed.
    models: list[str]
    # Ollama models the models file lists that Ollama hasn't installed.
    missing: list[str]
    message: str
