"""M6 redaction tests: emails, phone numbers, and key-like strings come out of
text before a model or the database sees it, and ordinary numbers stay.

The test keys are put together from pieces and are shorter than real keys, so
no file in the repo holds anything that looks like a working key."""

import json

import pytest

from conftest import APP_DIR, v1_body
from workbench import redact, specs, transcripts
from workbench.schemas import Removed

AIZA = "AI" + "za" + "SyFakeKeyForTests_0123"
GSK = "gs" + "k_" + "fakeGroqKeyForTests01"
SK = "s" + "k-proj-" + "fakeOpenAiKey0123456"
LONG_TOKEN = "abc123" * 6


@pytest.mark.parametrize(
    ("text", "expected", "removed"),
    [
        ("Write to me at alex.penhallow@example.com, ok?", "Write to me at [email removed], ok?", Removed(emails=1)),
        ("Ring (217) 555-0142 tonight.", "Ring [phone number removed] tonight.", Removed(phone_numbers=1)),
        ("Ring 217-555-0142 or 217.555.0142.", "Ring [phone number removed] or [phone number removed].", Removed(phone_numbers=2)),
        ("Ring +1 217 555 0142.", "Ring [phone number removed].", Removed(phone_numbers=1)),
        ("Ring +44 20 7946 0958 or 020 7946 0958.", "Ring [phone number removed] or [phone number removed].", Removed(phone_numbers=2)),
        ("Ring 555-0142, or 2175550142.", "Ring [phone number removed], or [phone number removed].", Removed(phone_numbers=2)),
        (f"My key is {AIZA}.", "My key is [key removed].", Removed(keys=1)),
        (f"Try {GSK} or {SK}.", "Try [key removed] or [key removed].", Removed(keys=2)),
        (f"Token {LONG_TOKEN} here.", "Token [key removed] here.", Removed(keys=1)),
        (f"https://example.com/?key={AIZA}", "https://example.com/?key=[key removed]", Removed(keys=1)),
    ],
    ids=["email", "phone-parens", "phone-dashes-dots", "phone-plus-1", "phone-uk", "phone-short-and-bare", "aiza-key", "gsk-and-sk-keys", "long-token", "key-in-url"],
)
def test_redaction_catches_emails_phone_numbers_and_keys(text, expected, removed):
    assert redact.scrub(text) == (expected, removed)


@pytest.mark.parametrize(
    "text",
    [
        "Gryffindor won 170 to 160.",
        "Harry was born on 31 July 1980.",
        "Checked on 2026-10-01 at 21:04, then 2026-10-01T21:04:05.123Z, turn 12.",
        "It cost 1,000 Galleons, or 3.1415926535 if you ask Fred.",
        "Platform 9 3/4, Room 101, 4 Privet Drive, and the years 1995 1996 1997.",
        "Write to alex at example dot com.",
    ],
)
def test_ordinary_numbers_and_words_stay(text):
    assert redact.scrub(text) == (text, Removed())


def test_scrubbing_twice_changes_nothing_more():
    once, removed = redact.scrub(f"Mail alex@example.com, call 217-555-0142, key {AIZA}.")
    assert removed == Removed(emails=1, phone_numbers=1, keys=1)
    assert redact.scrub(once) == (once, Removed())


def test_counts_add_up():
    total = Removed(emails=1) + Removed(phone_numbers=2, keys=1)
    assert (total.emails, total.phone_numbers, total.keys, total.total) == (1, 2, 1, 4)


def test_a_label_never_moves_a_row():
    text = "1. Alex: ring 217-555-0142\n2. Harry: No.\n3. Alex: mail a@example.com\n"
    redacted, removed = redact.scrub(text)
    assert removed.total == 2
    assert redacted.split("\n")[1] == "2. Harry: No." and redacted.count("\n") == text.count("\n")


def test_the_spec_scripts_and_samples_pass_through_unchanged():
    texts = [specs.render_text(v1_body())]
    texts += [line.text for scenario in transcripts.load_scenarios().scenarios for line in scenario.lines]
    for name in ("cla-f2", "gpt-f2"):
        chat = json.loads((APP_DIR / "samples" / f"{name}.json").read_text(encoding="utf-8"))
        texts += [message["text"] for message in chat["messages"]]
    assert [text for text in texts if redact.scrub(text) != (text, Removed())] == []
