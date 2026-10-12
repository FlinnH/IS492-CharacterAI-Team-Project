"""M3 rule tests: sentence counts and banned words, checked by code with no AI,
with every limit taken from the chat's spec version."""

import pytest

from conftest import messages, sample_messages, v1_body
from workbench import evidence, rules

FIVE = "One. Two. Three. Four. Five."


def test_fragments_count_as_sentences():
    assert rules.count_sentences("Oh. Right. Penhallow.") == 3


@pytest.mark.parametrize(
    ("text", "count"),
    [
        ("Ha.", 1),
        ("Mr. Weasley fixed it. Mrs. Weasley didn't.", 2),
        ("Dr. Who? Never heard of him.", 2),
        ("J. K. Rowling wrote it.", 1),
        ("Neither do I. But fine.", 2),
        ("By the Mandrakes... no, that was second year.", 1),
        ("Wait... What?", 2),
        ("Wait\u2026 what was that?", 1),
        ('"Go away!" he said.', 1),
        ('"Go away." Then he left.', 2),
        ("It cost 3.5 Galleons.", 1),
        ("Really?! You're sure?", 2),
        ("First line\nSecond line", 2),
        ("One.\n\nTwo.", 2),
        ("...", 0),
    ],
)
def test_sentences_end_at_marks_and_line_breaks(text, count):
    assert rules.count_sentences(text) == count


def test_the_cp2_chats_count_as_cp3_plan_says():
    cla = {m.turn: rules.count_sentences(m.text) for m in sample_messages("cla-f2") if m.speaker == "character"}
    gpt = {m.turn: rules.count_sentences(m.text) for m in sample_messages("gpt-f2") if m.speaker == "character"}
    assert cla[2] == gpt[2] == 6
    # 9 of CLA-F2's 10 replies run past 4 sentences; only turn 5 stays inside.
    assert sorted(turn for turn, count in cla.items() if count > 4) == [2, 3, 4, 6, 7, 8, 9, 10, 11]


def test_each_rule_gives_one_flag_per_chat_at_the_first_break():
    chat = sample_messages("cla-f2")
    [flag] = rules.check(chat, v1_body())
    assert (flag.source, flag.turn, flag.line_id, flag.type, flag.confidence) == ("rule", 2, "B4", "style drift", "high")
    assert flag.also_turns == (3, 4, 6, 7, 8, 9, 10, 11)
    assert flag.why == "This reply has 6 sentences, and B4 allows at most 4."
    # The quote runs from the fifth sentence to the end of the reply, word for word.
    assert flag.quote == "That's a bit of a coincidence. Look, if you've come to ask what happened in June, I'm not really in the mood."
    assert next(m.text for m in chat if m.speaker == "character" and m.turn == 2).endswith(flag.quote)


def test_the_sentence_limit_comes_from_the_spec():
    body = v1_body()
    sections = [
        section.model_copy(
            update={"lines": [line.model_copy(update={"max_sentences": 6 if line.max_sentences else None}) for line in section.lines]}
        )
        for section in body.sections
    ]
    [flag] = rules.check(sample_messages("cla-f2"), body.model_copy(update={"sections": sections}))
    # At 6, only turn 11 (7 sentences) breaks.
    assert (flag.turn, flag.also_turns) == (11, ())


def test_a_request_for_a_story_skips_the_sentence_check():
    chat = messages(
        (2, "user", "Tell me the story of the dragon."),
        (2, "character", FIVE),
        (3, "user", "And then?"),
        (3, "character", FIVE),
    )
    [flag] = rules.check(chat, v1_body())
    assert (flag.turn, flag.also_turns) == (3, ())


def test_a_banned_word_is_caught_whole_and_in_any_case():
    chat = messages(
        (2, "user", "Hi."),
        (2, "character", "Mom says hi. Just a moment."),
        (3, "user", "Bye."),
        (3, "character", "My turn to go, lol."),
        (4, "user", "Ok."),
        (4, "character", "See you in the moment of truth."),
    )
    [flag] = rules.check(chat, v1_body())
    assert (flag.line_id, flag.turn, flag.quote, flag.also_turns) == ("Voice", 2, "Mom", (3,))
    assert flag.why == 'Uses "Mom", which the Voice field bans.'


def test_an_emoji_is_caught_when_the_field_bans_them():
    chat = messages((2, "user", "Hi."), (2, "character", "Brilliant \U0001F44D lol"))
    [flag] = rules.check(chat, v1_body())
    assert flag.quote == "\U0001F44D"
    assert flag.why == 'Uses an emoji and "lol", which the Voice field bans.'


def test_banned_words_come_from_the_chats_spec_version():
    body = v1_body()
    fields = [
        field.model_copy(update={"banned_words": ["blimey"], "ban_emojis": False}) if field.banned_words else field
        for field in body.fields
    ]
    chat = messages((2, "user", "Hi."), (2, "character", "Blimey, Mom. \U0001F44D"))
    [flag] = rules.check(chat, body.model_copy(update={"fields": fields}))
    assert (flag.quote, flag.why) == ("Blimey", 'Uses "Blimey", which the Voice field bans.')


def test_a_stopped_reply_is_not_checked():
    chat = messages((2, "user", "Hi."), (2, "character", f"{FIVE} lol", True))
    assert rules.check(chat, v1_body()) == []


def test_rule_flags_pass_the_evidence_checks():
    rows = [(m.turn, m.speaker, m.text) for m in sample_messages("cla-f2")]
    chat = messages(*rows, (12, "user", "Hi."), (12, "character", "Mom. \U0001F44D"))
    findings = rules.check(chat, v1_body())
    assert len(findings) == 2
    for flag in findings:
        assert evidence.check_evidence(flag.turn, flag.line_id, flag.quote, chat, v1_body()) == (None, flag.line_id, flag.quote)
