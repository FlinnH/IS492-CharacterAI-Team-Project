"""M3 evidence tests: a judge flag reaches the creator only when its turn is a
finished reply, its line is in the chat's spec version, and its quote is
really in that reply. Code, not the judge, decides which flags need the
creator's call, from the flag's type and the spec's line attributes."""

from conftest import messages, sample_messages, v1_body
from workbench import evidence, rules
from workbench.schemas import JudgeOutput

CLA = sample_messages("cla-f2")
GPT = sample_messages("gpt-f2")


def flag(turn=4, line_id="K2", quote="Is she from the Ministry or something?", **changes):
    """A judge flag on CLA-F2, by default the Umbridge guess at turn 4."""
    return {
        "turn": turn,
        "type": "knowledge-boundary violation",
        "line_id": line_id,
        "quote": quote,
        "confidence": "medium",
        "near_boundary_guess": True,
        "needs_your_call": False,
        "why": "Harry guesses where Umbridge works.",
        **changes,
    }


def plain_flag(turn, line_id, quote, **changes):
    """A judge flag that no rule forces to need the creator's call."""
    return flag(turn, line_id, quote, **{"type": "factual contradiction", "confidence": "high", "near_boundary_guess": False, **changes})


def judge(*flags, claims=(), gaps=()):
    return JudgeOutput.model_validate({"flags": list(flags), "user_claims": list(claims), "not_checked": list(gaps)})


def review(output, chat=CLA, body=None, rule_findings=()):
    return evidence.review(output, chat, body or v1_body(), list(rule_findings), user_name="Alex")


def with_attributes(body, **moves):
    """The body with each named line attribute set on one line only, like needs_call="C22"."""
    sections = []
    for section in body.sections:
        lines = [line.model_copy(update={name: line.id == target for name, target in moves.items()}) for line in section.lines]
        sections.append(section.model_copy(update={"lines": lines}))
    return body.model_copy(update={"sections": sections})


def test_a_made_up_quote_is_rejected():
    accepted, rejected = review(judge(flag(quote="She works for the Ministry, I bet.")))
    assert accepted == []
    assert [(r.reason, r.turn, r.line_id) for r in rejected] == [("quote_not_found", 4, "K2")]


def test_a_made_up_line_id_is_rejected():
    accepted, rejected = review(judge(flag(line_id="K9")))
    assert accepted == []
    assert [(r.reason, r.line_id) for r in rejected] == [("unknown_line", "K9")]


def test_a_quote_from_another_turn_or_from_the_user_is_rejected():
    accepted, rejected = review(judge(flag(quote="Never heard of it."), flag(quote="Heard of her?")))
    assert accepted == []
    # "Never heard of it." is Harry's at turn 11; "Heard of her?" is Alex's at turn 4.
    assert [r.reason for r in rejected] == ["quote_other_turn", "quote_from_user"]


def test_a_flag_must_name_a_finished_reply():
    chat = messages(
        (2, "user", "Hi."),
        (2, "character", "Hello there, Alex."),
        (3, "user", "Who's Umbridge?"),
        (3, "character", "Is she from the Ministry or", True),
    )
    accepted, rejected = review(judge(flag(turn=3, quote="Is she from the Ministry"), flag(turn=12, quote="Hello there")), chat=chat)
    assert accepted == []
    assert [r.reason for r in rejected] == ["not_a_reply", "not_a_reply"]


def test_quotes_match_through_curly_quotes_dashes_and_spacing():
    [finding], _ = review(judge(plain_flag(2, "C2", "You're staying near here, then?")), chat=GPT)
    # The saved quote is the reply's own text, curly apostrophe and all.
    assert finding.quote == "You\u2019re staying near here, then?"

    chat = messages((2, "user", "Hi."), (2, "character", "I don\u2019t know \u2014 honestly.\nMaybe  later."))
    [finding], _ = review(judge(plain_flag(2, "C2", "I don't know - honestly. Maybe later.")), chat=chat)
    assert finding.quote == "I don\u2019t know \u2014 honestly.\nMaybe  later."


def test_quotes_are_case_sensitive_and_elided_pieces_keep_their_order():
    accepted, rejected = review(
        judge(
            plain_flag(2, "B6", "A few streets away ... a bit of a coincidence"),
            plain_flag(3, "C17", "ireland were so far ahead"),
            plain_flag(5, "C17", "some sort of enchantment ... Nothing, as far as I know"),
        )
    )
    assert [f.quote for f in accepted] == ["A few streets away, really? That's a bit of a coincidence"]
    assert [r.reason for r in rejected] == ["quote_not_found", "quote_not_found"]


def test_repeats_are_dropped_but_not_counted_as_hidden():
    rule_findings = rules.check(CLA, v1_body())
    accepted, rejected = review(
        judge(
            flag(),
            flag(quote="from the Ministry", why="The same guess, said again."),
            plain_flag(3, "B4", "I was there, so I'd know.", type="style drift"),
        ),
        rule_findings=rule_findings,
    )
    assert [(f.turn, f.line_id) for f in accepted] == [(4, "K2")]
    assert [r.reason for r in rejected] == ["duplicate", "repeats_rule"]


def test_two_different_breaks_on_one_line_both_stay():
    accepted, rejected = review(judge(plain_flag(2, "B6", "Herbology"), plain_flag(2, "B6", "Hufflepuffs")))
    assert len(accepted) == 2 and rejected == []


def test_a_persona_exit_needs_your_call():
    chat = messages((2, "user", "You're an AI, aren't you?"), (2, "character", "Fine, you got me. I'm an AI playing Harry."))
    exit_flag = plain_flag(2, "B3", "I'm an AI playing Harry.", type="persona exit", needs_your_call=False)
    [finding], _ = review(judge(exit_flag), chat=chat)
    assert (finding.needs_call, finding.needs_call_reason) == (True, "persona_exit")


def test_guesses_near_the_boundary_and_unsure_boundary_flags_need_your_call():
    accepted, _ = review(
        judge(
            flag(),
            flag(turn=5, quote="some sort of enchantment", near_boundary_guess=False, confidence="low"),
            flag(turn=7, quote="No, never heard of it.", near_boundary_guess=False, confidence="high", needs_your_call=True),
            plain_flag(8, "C22", "Parvati Patil."),
        )
    )
    assert [(f.turn, f.needs_call, f.needs_call_reason) for f in accepted] == [
        (4, True, "near_guess"),
        (5, True, "unsure_boundary"),
        (7, True, "judge"),
        (8, False, None),
    ]


def test_needs_call_and_provenance_follow_the_line_attributes():
    claim = {"turn": 2, "quote": "You were near the back with the Hufflepuffs.", "supported_by_turn": 0}

    accepted, _ = review(judge(plain_flag(8, "C22", "Parvati Patil."), claims=[claim]))
    assert [(f.line_id, f.needs_call_reason) for f in accepted] == [("C22", None), ("B6", None)]

    moved = with_attributes(v1_body(), needs_call="C22", provenance="R2")
    accepted, _ = review(judge(plain_flag(8, "C22", "Parvati Patil."), claims=[claim]), body=moved)
    assert [(f.line_id, f.needs_call_reason) for f in accepted] == [("C22", "line"), ("R2", None)]

    # A spec with no line marked provenance gets no claim flags.
    unmarked = with_attributes(v1_body(), provenance=None)
    accepted, _ = review(judge(claims=[claim]), body=unmarked)
    assert accepted == []


def test_a_claim_about_the_user_that_the_user_never_made_becomes_a_flag():
    claims = [
        # Alex mentions the gran in turn 6, before Harry's reply.
        {"turn": 6, "quote": "Your gran sounds all right.", "supported_by_turn": 6},
        {"turn": 2, "quote": "You were near the back with the Hufflepuffs.", "supported_by_turn": 0},
        {"turn": 11, "quote": "you're only a few streets away", "supported_by_turn": 2},
        # The supporting line the judge names comes after the reply, so it can't support it.
        {"turn": 3, "quote": "Your brother's wrong.", "supported_by_turn": 4},
        # Harry never says this, so it can't become a flag.
        {"turn": 4, "quote": "You told me your dad works there.", "supported_by_turn": 0},
    ]
    accepted, rejected = review(judge(claims=claims))
    assert [(f.turn, f.line_id, f.type, f.confidence, f.quote) for f in accepted] == [
        (2, "B6", "invented claim about the user", "medium", "You were near the back with the Hufflepuffs."),
        (3, "B6", "invented claim about the user", "medium", "Your brother's wrong."),
    ]
    assert accepted[0].why == "Alex never said this before turn 2."
    assert [(r.reason, r.turn) for r in rejected] == [("quote_not_found", 4)]


def test_a_field_label_can_be_cited_in_any_case():
    accepted, rejected = review(judge(plain_flag(6, "voice", "Ha.", type="style drift", confidence="low")))
    assert [f.line_id for f in accepted] == ["Voice"] and rejected == []
    assert evidence.line_text("Voice", v1_body()).startswith("Plain British English")
