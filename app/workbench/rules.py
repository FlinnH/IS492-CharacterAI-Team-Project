"""Rule checks: the spec's measurable rules, checked by code with no AI.

Pure: a chat's messages and its spec body in, findings out, with no I/O. The
limits come from the spec itself (a line's max_sentences, a field's
banned_words and ban_emojis), so this code names no line. Each rule gives at
most one flag per chat, at its first break, and lists the other turns that
broke it. Only the character's finished replies are checked, never a reply
cut off by Stop.
"""

import re
from collections.abc import Iterator, Sequence

from workbench.schemas import Finding, MessageView, SpecBody, SpecField, SpecLine

# A run of sentence-ending marks, with any closing quotes or brackets after it,
# before a space or the end. Every line break ends a sentence too.
SENTENCE_END = re.compile(r"[.!?\u2026]+[\"'\u2019\u201d)\]]*(?=\s|$)")
# A period after one of these doesn't end a sentence.
TITLES = {"Mr", "Mrs", "Ms", "Dr"}
WORD_BEFORE = re.compile(r"([A-Za-z]+)$")
# The user asked for a story, so a longer reply is allowed.
STORY_REQUEST = re.compile(r"\bstor(?:y|ies)\b", re.IGNORECASE)
# The main emoji blocks. A skin tone, a variation selector, or a joined part
# stays with its emoji, so the quote holds the whole emoji.
_EMOJI = "\U0001F000-\U0001FAFF\u2600-\u27bf\u2b00-\u2bff\u231a\u231b\u23e9-\u23fa"
EMOJI = re.compile(rf"[{_EMOJI}][\ufe0f\U0001F3FB-\U0001F3FF]?(?:\u200d[{_EMOJI}][\ufe0f\U0001F3FB-\U0001F3FF]?)*")


def _keeps_going(line: str, end: re.Match) -> bool:
    """True when the marks at end don't end the sentence: a lowercase word comes
    next, or the period follows a title like Mr. or an initial like the J. in J. K."""
    after = line[end.end() :].lstrip()
    if after[:1].islower():
        return True
    if end.group().rstrip("\"'\u2019\u201d)]") != ".":
        return False
    word = WORD_BEFORE.search(line, 0, end.start())
    if word is None:
        return False
    name = word[1]
    return name in TITLES or (len(name) == 1 and name.isupper() and name != "I")


def sentences(text: str) -> list[tuple[int, int]]:
    """(start, end) of each sentence in a reply, without the spaces around it.

    Fragments like "Oh." count. A piece with no letter or digit, like "...",
    doesn't.
    """
    spans = []
    offset = 0
    for line in text.split("\n"):
        start = 0
        for end in SENTENCE_END.finditer(line):
            if not _keeps_going(line, end):
                spans.append((offset + start, offset + end.end()))
                start = end.end()
        spans.append((offset + start, offset + len(line)))
        offset += len(line) + 1

    found = []
    for start, end in spans:
        piece = text[start:end]
        if not re.search(r"[^\W_]", piece):
            continue
        found.append((start + len(piece) - len(piece.lstrip()), end - (len(piece) - len(piece.rstrip()))))
    return found


def count_sentences(text: str) -> int:
    return len(sentences(text))


def replies(messages: Sequence[MessageView]) -> Iterator[tuple[MessageView, str]]:
    """Each finished reply from the character, with the user's lines it answers."""
    asked: list[str] = []
    for message in messages:
        if message.speaker == "user":
            asked.append(message.text)
            continue
        if not message.stopped and message.text.strip():
            yield message, "\n".join(asked)
        asked = []


def _flag(breaks: list, make) -> list[Finding]:
    """One finding at the first break, listing the other broken turns after it."""
    if not breaks:
        return []
    first = breaks[0]
    others = sorted({message.turn for message, *_ in breaks[1:]} - {first[0].turn})
    return [make(*first).model_copy(update={"also_turns": tuple(others)})]


def sentence_findings(messages: Sequence[MessageView], line: SpecLine) -> list[Finding]:
    """Replies with more sentences than the line allows. A reply to a request for a story may run long."""
    limit = line.max_sentences
    breaks = []
    for message, asked in replies(messages):
        if STORY_REQUEST.search(asked):
            continue
        spans = sentences(message.text)
        if len(spans) > limit:
            breaks.append((message, spans))

    def make(message: MessageView, spans: list[tuple[int, int]]) -> Finding:
        return Finding(
            source="rule",
            turn=message.turn,
            type="style drift",
            line_id=line.id,
            # From the first sentence over the limit to the end of the reply.
            quote=message.text[spans[limit][0] :].rstrip(),
            confidence="high",
            needs_call=line.needs_call,
            needs_call_reason="line" if line.needs_call else None,
            why=f"This reply has {len(spans)} sentences, and {line.id} allows at most {limit}.",
        )

    return _flag(breaks, make)


def _listed(items: list[str]) -> str:
    if len(items) <= 2:
        return " and ".join(items)
    return f"{', '.join(items[:-1])}, and {items[-1]}"


def banned_findings(messages: Sequence[MessageView], field: SpecField) -> list[Finding]:
    """Replies that use a word the field bans, or an emoji when it bans those. Case doesn't matter."""
    words = re.compile(rf"\b(?:{'|'.join(re.escape(word) for word in field.banned_words)})\b", re.IGNORECASE)
    breaks = []
    for message, _ in replies(messages):
        hits = []
        if field.banned_words:
            hits += [(match.start(), match.group(), False) for match in words.finditer(message.text)]
        if field.ban_emojis:
            hits += [(match.start(), match.group(), True) for match in EMOJI.finditer(message.text)]
        if hits:
            breaks.append((message, sorted(hits)))

    def make(message: MessageView, hits: list[tuple[int, str, bool]]) -> Finding:
        named = []
        for _, text, emoji in hits:
            name = "an emoji" if emoji else f'"{text}"'
            if name not in named:
                named.append(name)
        return Finding(
            source="rule",
            turn=message.turn,
            type="style drift",
            line_id=field.label,
            quote=hits[0][1],
            confidence="high",
            why=f"Uses {_listed(named)}, which the {field.label} field bans.",
        )

    return _flag(breaks, make)


def check(messages: Sequence[MessageView], body: SpecBody) -> list[Finding]:
    """Every rule in the spec, in spec order: sentence limits on lines, then bans on fields."""
    findings = []
    for section in body.sections:
        for line in section.lines:
            if line.max_sentences is not None:
                findings += sentence_findings(messages, line)
    for field in body.fields:
        if field.banned_words or field.ban_emojis:
            findings += banned_findings(messages, field)
    return findings
