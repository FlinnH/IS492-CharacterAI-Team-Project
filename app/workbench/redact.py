"""Redaction: emails, phone numbers, and key-like strings never reach a model or the database.

scrub() swaps each one for a label, like [email removed], and counts what it
took out. It runs on each message of an import and on every message before it
is saved, on spec edits, on logged reasons and errors, and on every message a
model is sent. A label holds no digit and no @, so scrubbing text twice
changes nothing more. Pure: no I/O.

The patterns leave ordinary numbers alone, like "170 to 160", "31 July 1980",
"1,000", turn numbers, and dates like 2026-10-01.
"""

import re

from workbench.schemas import Removed

EMAIL_LABEL = "[email removed]"
KEY_LABEL = "[key removed]"
PHONE_LABEL = "[phone number removed]"

EMAIL = re.compile(
    r"(?<![A-Za-z0-9._%+\-])[A-Za-z0-9._%+\-]+@[A-Za-z0-9\-]+(?:\.[A-Za-z0-9\-]+)*\.[A-Za-z]{2,}(?![A-Za-z0-9\-])"
)

# A key-like string is a whole token: one that starts the way a service's keys
# start (Google's AIza, Groq's gsk_, and OpenAI, Anthropic, GitHub, Slack, and
# AWS), or a run of 32 or more letters and digits with both in it.
_TOKEN = r"[A-Za-z0-9_\-]"
KEY = re.compile(
    rf"(?<!{_TOKEN})(?:"
    rf"AIza{_TOKEN}*"
    rf"|gsk_{_TOKEN}*"
    rf"|sk-{_TOKEN}{{16,}}"
    rf"|gh[pousr]_[A-Za-z0-9]{{20,}}"
    rf"|github_pat_{_TOKEN}{{20,}}"
    rf"|xox[abposr]-{_TOKEN}{{10,}}"
    rf"|AKIA[0-9A-Z]{{16}}"
    rf"|(?=[A-Za-z_\-]*[0-9])(?=[0-9_\-]*[A-Za-z]){_TOKEN}{{32,}}"
    rf")(?!{_TOKEN})"
)

# Phone numbers, in the shapes people write them. A space, a dot, or a hyphen
# may split the digits, never a line break, so a pasted chat keeps its rows.
_SEP = r"[ .\-]"
PHONE = re.compile(
    r"(?<![\w+@.\-/])(?:"
    # +44 20 7946 0958, +1 (217) 555-0142, +12175550142
    rf"\+\d{{1,3}}(?:{_SEP}?\(?\d{{1,4}}\)?){{2,5}}"
    # (217) 555-0142, 1 (217) 555-0142
    rf"|(?:1{_SEP}?)?\(\d{{3}}\){_SEP}?\d{{3}}{_SEP}?\d{{4}}"
    # 217-555-0142, 217.555.0142, 217 555 0142, 1-217-555-0142
    rf"|(?:1{_SEP})?\d{{3}}{_SEP}\d{{3}}{_SEP}\d{{4}}"
    # 020 7946 0958
    rf"|0\d{{2,4}}{_SEP}\d{{3,4}}{_SEP}?\d{{3,4}}"
    # 555-0142
    r"|\d{3}-\d{4}"
    # 2175550142
    r"|\d{10,15}"
    r")(?![\w\-])"
)
SHORT_PHONE = re.compile(r"\d{3}-\d{4}")


def _is_phone(found: str) -> bool:
    """Whether a match has a phone number's count of digits."""
    digits = sum(char.isdigit() for char in found)
    if found.startswith("+"):
        return 8 <= digits <= 15
    if SHORT_PHONE.fullmatch(found):
        return True
    return 10 <= digits <= 15


def scrub(text: str) -> tuple[str, Removed]:
    """The text with each email, key-like string, and phone number swapped for a label, and the counts."""
    counts = {"emails": 0, "keys": 0, "phone_numbers": 0}

    def swap(kind: str, label: str):
        def replace(match: re.Match) -> str:
            if kind == "phone_numbers" and not _is_phone(match[0]):
                return match[0]
            counts[kind] += 1
            return label

        return replace

    text = EMAIL.sub(swap("emails", EMAIL_LABEL), text)
    text = KEY.sub(swap("keys", KEY_LABEL), text)
    text = PHONE.sub(swap("phone_numbers", PHONE_LABEL), text)
    return text, Removed(**counts)


def text(value: str) -> str:
    """The text with nothing a label would replace, for places that don't count."""
    return scrub(value)[0]


def optional(value: str | None) -> str | None:
    return None if value is None else text(value)
