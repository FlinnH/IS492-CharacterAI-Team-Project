"""Evidence checks: every flag from the AI judge is checked against the chat and
the spec before the creator sees it.

Pure: the judge's answer, the chat's messages, its spec body, and the rule
flags in; findings and rejections out, with no AI and no I/O. A flag passes
when its turn is a finished reply from the character, it cites a line ID or a
field label in this chat's spec version, and its quote appears word for word
in that reply. A flag that fails is kept apart with its reason and never
shown; the screen only counts it. Code, not the judge, has the last word on
which flags need the creator's call, from the flag's type and the line
attributes in the spec.
"""

from collections.abc import Sequence
from dataclasses import dataclass

from workbench.schemas import (
    Confidence,
    FailureType,
    Finding,
    JudgeOutput,
    MessageView,
    NeedsCallReason,
    RejectReason,
    SpecBody,
    SpecLine,
    UserClaim,
)

# Curly quotes, dashes, and the ellipsis character in their plain forms, so a
# quote typed with straight quotes still matches a reply that has curly ones.
# Zero-width marks drop out.
PLAIN = {
    "\u2018": "'",
    "\u2019": "'",
    "\u201a": "'",
    "\u201b": "'",
    "\u2032": "'",
    "\u201c": '"',
    "\u201d": '"',
    "\u201e": '"',
    "\u201f": '"',
    "\u2033": '"',
    "\u2010": "-",
    "\u2011": "-",
    "\u2012": "-",
    "\u2013": "-",
    "\u2014": "-",
    "\u2015": "-",
    "\u2212": "-",
    "\u2026": "...",
    "\u200b": "",
    "\ufeff": "",
}
CLAIM_TYPE: FailureType = "invented claim about the user"
CLAIM_CONFIDENCE: Confidence = "medium"


@dataclass(frozen=True)
class Plain:
    """Text in plain form, with whitespace runs as one space, and where each
    plain character came from: starts[i] to ends[i] in the original."""

    text: str
    starts: list[int]
    ends: list[int]


@dataclass(frozen=True)
class Rejection:
    """A flag or claim from the judge that won't be shown, and why."""

    reason: RejectReason
    turn: int
    line_id: str
    quote: str
    raw: dict


def plain(text: str) -> Plain:
    chars, starts, ends = [], [], []
    index = 0
    while index < len(text):
        if text[index].isspace():
            end = index
            while end < len(text) and text[end].isspace():
                end += 1
            chars.append(" ")
            starts.append(index)
            ends.append(end)
            index = end
            continue
        for char in PLAIN.get(text[index], text[index]):
            chars.append(char)
            starts.append(index)
            ends.append(index + 1)
        index += 1
    return Plain("".join(chars), starts, ends)


def find_quote(quote: str, text: str) -> tuple[int, int] | None:
    """Where the quote is in text, as (start, end) in the original text, or None.

    The match is case-sensitive, on the plain forms of both. A quote with "..."
    in it matches when its pieces appear in that order, and the span runs from
    the first piece to the last. Quote marks wrapped around the whole quote
    are dropped if it doesn't match with them.
    """
    target = plain(text)
    wanted = plain(quote).text.strip()
    for candidate in dict.fromkeys([wanted, wanted.strip("\"'").strip()]):
        pieces = [piece.strip() for piece in candidate.split("...")]
        pieces = [piece for piece in pieces if piece]
        if not pieces:
            continue
        position, first, last = 0, None, None
        for piece in pieces:
            found = target.text.find(piece, position)
            if found == -1:
                break
            first = found if first is None else first
            last = position = found + len(piece)
        else:
            return target.starts[first], target.ends[last - 1]
    return None


def citations(body: SpecBody) -> dict[str, str]:
    """Every line ID and field label a flag may cite, keyed for matching: IDs in
    capitals, labels in lowercase. The setting counts as a field when it's set."""
    found = {field.label.casefold(): field.label for field in body.fields}
    if body.setting.strip():
        found["setting"] = "Setting"
    found.update({line.id: line.id for section in body.sections for line in section.lines})
    return found


def cite(line_id: str, body: SpecBody) -> str | None:
    """The line ID or field label as the spec writes it, or None. Case and a
    trailing period or colon don't matter."""
    key = line_id.strip().rstrip(".:").strip()
    known = citations(body)
    return known.get(key.upper()) or known.get(key.casefold())


def line_text(line_id: str, body: SpecBody) -> str:
    """The words of a cited line or field, straight from the spec."""
    for section in body.sections:
        for line in section.lines:
            if line.id == line_id:
                return line.text
    for field in body.fields:
        if field.label == line_id:
            return field.text
    return body.setting if line_id == "Setting" else ""


def _line(line_id: str, body: SpecBody) -> SpecLine | None:
    return next((line for section in body.sections for line in section.lines if line.id == line_id), None)


def needs_call(
    flag_type: str, near_boundary_guess: bool, confidence: str, judge_says: bool, line: SpecLine | None
) -> NeedsCallReason | None:
    """Why a flag needs the creator's call, or None when it doesn't.

    Persona exits and guesses near the knowledge boundary always do, and so
    does a knowledge-boundary flag the judge isn't sure of, and any flag on a
    line the spec marks needs_call. Otherwise the judge's own mark decides.
    """
    if flag_type == "persona exit":
        return "persona_exit"
    if near_boundary_guess:
        return "near_guess"
    if flag_type == "knowledge-boundary violation" and confidence != "high":
        return "unsure_boundary"
    if line is not None and line.needs_call:
        return "line"
    return "judge" if judge_says else None


def _replies(messages: Sequence[MessageView], turn: int) -> list[MessageView]:
    return [m for m in messages if m.speaker == "character" and m.turn == turn and not m.stopped and m.text.strip()]


def check_evidence(turn: int, line_id: str, quote: str, messages: Sequence[MessageView], body: SpecBody):
    """(reason, cited line, exact quote) for a flag: the turn is a finished reply, the
    line is in the spec, and the quote is in that reply. The reason is None when all pass."""
    replies = _replies(messages, turn)
    if not replies:
        return "not_a_reply", None, None
    cited = cite(line_id, body)
    if cited is None:
        return "unknown_line", None, None
    for reply in replies:
        span = find_quote(quote, reply.text)
        if span is not None:
            return None, cited, reply.text[span[0] : span[1]]
    if any(find_quote(quote, m.text) for m in messages if m.speaker == "character" and m.turn != turn):
        return "quote_other_turn", cited, None
    if any(find_quote(quote, m.text) for m in messages if m.speaker == "user"):
        return "quote_from_user", cited, None
    return "quote_not_found", cited, None


def _repeat(finding: Finding, accepted: Sequence[Finding], rule_findings: Sequence[Finding]) -> RejectReason | None:
    """repeats_rule when a rule flag covers the same line and turn; duplicate when an
    earlier flag has the same turn, line, and type and one quote holds the other."""
    for rule in rule_findings:
        if rule.line_id == finding.line_id and finding.turn in (rule.turn, *rule.also_turns):
            return "repeats_rule"
    for other in accepted:
        if (other.turn, other.line_id, other.type) == (finding.turn, finding.line_id, finding.type) and (
            other.quote in finding.quote or finding.quote in other.quote
        ):
            return "duplicate"
    return None


def _supported(claim: UserClaim, messages: Sequence[MessageView]) -> bool:
    """True when a user line with the claim's supporting number comes before the reply that makes it."""
    if claim.supported_by_turn <= 0:
        return False
    replies = _replies(messages, claim.turn)
    if not replies:
        return False
    return any(m.speaker == "user" and m.turn == claim.supported_by_turn and m.seq < replies[0].seq for m in messages)


def review(
    output: JudgeOutput,
    messages: Sequence[MessageView],
    body: SpecBody,
    rule_findings: Sequence[Finding],
    *,
    user_name: str,
    number_word: str = "turn",
) -> tuple[list[Finding], list[Rejection]]:
    """The judge's flags and claims about the user that pass every check, and the rest with their reasons.

    A claim about the user that no earlier user line supports becomes a flag
    on the line the spec marks provenance, if one is marked.
    """
    accepted: list[Finding] = []
    rejected: list[Rejection] = []

    def consider(raw: dict, turn: int, line_id: str, quote: str, make) -> None:
        reason, cited, exact = check_evidence(turn, line_id, quote, messages, body)
        if reason is None:
            finding = make(cited, exact)
            reason = _repeat(finding, accepted, rule_findings)
            if reason is None:
                accepted.append(finding)
                return
        rejected.append(Rejection(reason=reason, turn=turn, line_id=line_id, quote=quote, raw=raw))

    for flag in output.flags:

        def make(cited: str, exact: str, flag=flag) -> Finding:
            reason = needs_call(flag.type, flag.near_boundary_guess, flag.confidence, flag.needs_your_call, _line(cited, body))
            return Finding(
                source="judge",
                turn=flag.turn,
                type=flag.type,
                line_id=cited,
                quote=exact,
                confidence=flag.confidence,
                near_boundary_guess=flag.near_boundary_guess,
                needs_call=reason is not None,
                needs_call_reason=reason,
                why=" ".join(flag.why.split()),
            )

        consider(flag.model_dump(), flag.turn, flag.line_id, flag.quote, make)

    provenance = next((line for section in body.sections for line in section.lines if line.provenance), None)
    if provenance is not None:
        for claim in output.user_claims:
            if _supported(claim, messages):
                continue

            def make(cited: str, exact: str, claim=claim) -> Finding:
                reason = needs_call(CLAIM_TYPE, False, CLAIM_CONFIDENCE, False, provenance)
                return Finding(
                    source="judge",
                    turn=claim.turn,
                    type=CLAIM_TYPE,
                    line_id=cited,
                    quote=exact,
                    confidence=CLAIM_CONFIDENCE,
                    needs_call=reason is not None,
                    needs_call_reason=reason,
                    why=f"{user_name} never said this before {number_word} {claim.turn}.",
                )

            consider(claim.model_dump(), claim.turn, provenance.id, claim.quote, make)
    return accepted, rejected
