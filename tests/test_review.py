"""M4 review tests: the creator's calls on flags. Agree waits for the evidence,
an override needs a reason of at least 3 words and may set the right type,
Undo reopens a flag, and every call and every evidence opening is saved with
its time. The judge is the fake model with scripted answers."""

import re
import typing

import pytest

from conftest import default_model, fake_settings, query
from test_judge import UMBRIDGE, check, import_sample, judge_reply
from workbench.config import load_prompts
from workbench.providers import FakeProvider, FakeReply
from workbench.schemas import FailureType

SESSION = "0f8e5a3c-4b2d-4c1e-9a7f-2d6b8c0e1f3a"


def judged(*replies):
    """The fake model, answering each model call with the next scripted reply."""
    return FakeProvider(fake_settings(), replies=[FakeReply(text=reply) for reply in replies])


def checked(client, sample="cla-f2"):
    """Imports a sample and checks it, and returns the chat's ID."""
    chat_id = import_sample(client, sample)
    check(client, chat_id)
    return chat_id


def ok(response):
    assert response.status_code == 200, response.text
    return response.json()


def review(client):
    return ok(client.get("/api/review"))


def chat_review(client, chat_id):
    return next(item for item in review(client)["chats"] if item["chat"]["id"] == chat_id)


def flag(item, flag_id):
    return next(candidate for candidate in item["flags"] if candidate["id"] == flag_id)


def post(client, flag_id, action, body=None, headers=None):
    return client.post(f"/api/flags/{flag_id}/{action}", json=body, headers=headers)


def events(client):
    """The events that name a flag, oldest first."""
    return query(client, "SELECT * FROM events WHERE flag_id IS NOT NULL ORDER BY id")


@pytest.fixture
def cla_f2(make_client):
    """CLA-F2, checked: (client, chat ID, the rule flag on turn 2, the judge's flag on turn 4)."""
    client = make_client(provider=judged(judge_reply(UMBRIDGE)))
    chat_id = checked(client)
    ids = {(item["source"], item["turn"]): item["id"] for item in chat_review(client, chat_id)["flags"]}
    assert set(ids) == {("rule", 2), ("judge", 4)}
    return client, chat_id, ids[("rule", 2)], ids[("judge", 4)]


def test_agree_before_the_evidence_is_opened_is_refused_and_nothing_is_logged(cla_f2):
    client, chat_id, rule, judge = cla_f2
    logged = len(query(client, "SELECT id FROM events"))
    refused = post(client, rule, "agree")
    assert refused.status_code == 409
    assert "Show in context" in refused.json()["detail"]
    assert len(query(client, "SELECT id FROM events")) == logged
    item = chat_review(client, chat_id)
    assert (flag(item, rule)["call"], flag(item, rule)["evidence_opened"], item["open_calls"]) == (None, False, 2)

    opened = ok(post(client, rule, "evidence"))
    assert flag(opened, rule)["evidence_opened"] is True
    agreed = ok(post(client, rule, "agree"))
    assert flag(agreed, rule)["call"]["verdict"] == "agreed"
    assert agreed["open_calls"] == 1


@pytest.mark.parametrize("reason", ["Looks fine", "  looks   fine  ", ""], ids=["two-words", "two-words-spaced", "empty"])
def test_a_two_word_override_reason_is_refused_and_nothing_is_logged(cla_f2, reason):
    client, chat_id, rule, judge = cla_f2
    refused = post(client, judge, "override", {"reason": reason})
    assert refused.status_code == 422
    assert "at least 3 words" in refused.json()["detail"]
    assert events(client) == []
    assert flag(chat_review(client, chat_id), judge)["call"] is None

    saved = ok(post(client, judge, "override", {"reason": "  The quote is fine.  "}))
    call = flag(saved, judge)["call"]
    assert (call["verdict"], call["reason"], call["type"]) == ("overridden", "The quote is fine.", None)


def test_a_call_survives_a_reload_and_a_restart(cla_f2, make_client):
    client, chat_id, rule, judge = cla_f2
    ok(post(client, rule, "evidence"))
    ok(post(client, rule, "agree"))
    ok(post(client, judge, "override", {"reason": "Harry only guesses here."}))
    first = chat_review(client, chat_id)

    for item in (chat_review(client, chat_id), chat_review(make_client(), chat_id)):
        assert item["flags"] == first["flags"]
        assert item["open_calls"] == 0
        assert flag(item, rule)["evidence_opened"] is True
        assert flag(item, rule)["call"]["verdict"] == "agreed"
        assert flag(item, judge)["call"]["reason"] == "Harry only guesses here."


def test_undo_reopens_the_flag(cla_f2):
    client, chat_id, rule, judge = cla_f2
    ok(post(client, rule, "evidence"))
    ok(post(client, rule, "agree"))
    undone = ok(post(client, rule, "undo"))
    assert flag(undone, rule)["call"] is None
    assert undone["open_calls"] == 2
    # The opening is still on record, so Agree works again with no new opening.
    assert flag(undone, rule)["evidence_opened"] is True
    again = ok(post(client, rule, "agree"))
    assert flag(again, rule)["call"]["verdict"] == "agreed"
    assert [row["kind"] for row in events(client)] == ["evidence_opened", "agree", "undo", "agree"]

    nothing = post(client, judge, "undo")
    assert nothing.status_code == 409
    assert "no call to undo" in nothing.json()["detail"]


def test_agreeing_with_every_flag_trips_the_rubber_stamp_check(cla_f2):
    client, chat_id, rule, judge = cla_f2
    ok(post(client, rule, "evidence"))
    ok(post(client, judge, "evidence"))
    assert ok(post(client, rule, "agree"))["agreed_with_every"] is False
    assert ok(post(client, judge, "agree"))["agreed_with_every"] is True
    ok(post(client, judge, "undo"))
    assert ok(post(client, judge, "override", {"reason": "Only a guess, not knowledge."}))["agreed_with_every"] is False


def test_the_badge_counts_calls_left_across_every_checked_chat(make_client):
    client = make_client(provider=judged(judge_reply(UMBRIDGE), judge_reply()))
    cla_id = checked(client, "cla-f2")
    gpt_id = checked(client, "gpt-f2")
    pasted = client.post("/api/imports", json={"source": "paste", "character": "harry", "text": "Alex: Hi, Harry.\nHarry: Hi."})
    assert pasted.status_code == 201, pasted.text

    state = review(client)
    assert [item["chat"]["id"] for item in state["chats"]] == [cla_id, gpt_id]
    assert [item["open_calls"] for item in state["chats"]] == [2, 1]
    assert (state["open_calls"], state["changed"]) == (3, [])
    assert state["failure_types"] == list(typing.get_args(FailureType))
    assert (state["min_reason_words"], state["max_reason_chars"]) == (3, 2000)

    rule, judge = (item["id"] for item in state["chats"][0]["flags"])
    ok(post(client, rule, "evidence"))
    ok(post(client, rule, "agree"))
    assert review(client)["open_calls"] == 2
    # The badge counts calls made, not agreements, so an override counts the same.
    ok(post(client, judge, "override", {"reason": "Only a guess, not knowledge."}))
    assert review(client)["open_calls"] == 1
    ok(post(client, rule, "undo"))
    assert review(client)["open_calls"] == 2


def test_an_override_can_set_the_right_type(cla_f2):
    client, chat_id, rule, judge = cla_f2
    own = post(client, judge, "override", {"reason": "It breaks in another way.", "type": "knowledge-boundary violation"})
    assert own.status_code == 422
    assert "other than the flag's own" in own.json()["detail"]
    unknown = post(client, judge, "override", {"reason": "It breaks in another way.", "type": "rudeness"})
    assert unknown.status_code == 422
    assert events(client) == []

    item = ok(post(client, judge, "override", {"reason": "He drifts out of character here.", "type": "persona drift"}))
    call = flag(item, judge)["call"]
    assert (call["verdict"], call["type"]) == ("overridden", "persona drift")
    assert [(row["kind"], row["flag_type"]) for row in events(client)] == [("override", "persona drift")]


def test_retyped_and_overridden_flags_count_differently(cla_f2, make_client):
    client, chat_id, rule, judge = cla_f2
    ok(post(client, rule, "evidence"))
    item = ok(post(client, rule, "override", {"reason": "Six short lines read fine."}))
    assert flag(item, rule)["counts_as_break"] is False
    # A flag with no call yet still counts as a break.
    assert flag(item, judge)["counts_as_break"] is True
    item = ok(post(client, judge, "override", {"reason": "It is persona drift instead.", "type": "persona drift"}))
    assert flag(item, judge)["counts_as_break"] is True
    assert item["first_break"] == 4

    ok(post(client, rule, "undo"))
    ok(post(client, judge, "undo"))
    restarted = make_client()
    # The opening was saved, so after a restart Agree needs no new one.
    item = ok(post(restarted, rule, "agree"))
    assert flag(item, rule)["call"]["verdict"] == "agreed"
    assert item["first_break"] == 2


def test_every_call_and_evidence_opening_is_logged_with_its_time(cla_f2):
    client, chat_id, rule, judge = cla_f2
    headers = {"x-workbench-session": SESSION}
    marks = [ok(post(client, rule, action, headers=headers))["last_event_id"] for action in ("evidence", "evidence", "agree")]
    rows = events(client)
    assert [row["kind"] for row in rows] == ["evidence_opened", "evidence_opened", "agree"]
    assert {(row["flag_id"], row["transcript_id"], row["session"]) for row in rows} == {(rule, chat_id, SESSION)}
    assert all(re.fullmatch(r"\d{4}-\d\d-\d\dT\d\d:\d\d:\d\d\.\d{3}Z", row["created_at"]) for row in rows)
    assert marks == [row["id"] for row in rows]


def test_a_flag_has_one_call_at_a_time(cla_f2):
    client, chat_id, rule, judge = cla_f2
    ok(post(client, rule, "evidence"))
    ok(post(client, rule, "agree"))
    again = post(client, rule, "agree")
    assert again.status_code == 409
    assert "already has your call" in again.json()["detail"]
    assert post(client, rule, "override", {"reason": "I changed my mind."}).status_code == 409
    assert [row["kind"] for row in events(client)] == ["evidence_opened", "agree"]


def test_a_chat_that_changes_after_its_check_moves_to_changed(make_client):
    # Six sentences on turn 2 break the sentence limit, so the check has a rule flag.
    client = make_client(provider=judged("One. Two. Three. Four. Five. Six."))
    chat = client.post("/api/chats", json={"character": "harry", "scenario": "F2", "model": default_model()}).json()
    client.post(f"/api/chats/{chat['id']}/next")
    check(client, chat["id"])
    [rule] = chat_review(client, chat["id"])["flags"]
    assert (rule["source"], rule["turn"]) == ("rule", 2)
    ok(post(client, rule["id"], "evidence"))
    ok(post(client, rule["id"], "agree"))

    client.post(f"/api/chats/{chat['id']}/next")
    state = review(client)
    assert [item["id"] for item in state["changed"]] == [chat["id"]]
    assert (state["chats"], state["open_calls"]) == ([], 0)
    logged = len(events(client))
    for action in ("evidence", "agree", "undo"):
        refused = post(client, rule["id"], action)
        assert refused.status_code == 409
        assert "older check" in refused.json()["detail"]
    assert len(events(client)) == logged
    assert post(client, 999, "evidence").status_code == 404


def test_calls_stay_when_the_judge_settings_change(cla_f2, make_client):
    client, chat_id, rule, judge = cla_f2
    ok(post(client, rule, "evidence"))
    ok(post(client, rule, "agree"))

    # Another provider means another judge model, so no saved run matches today's settings.
    other = make_client(workbench_provider="gemini")
    assert other.get(f"/api/chats/{chat_id}/check").json()["result"] is None
    item = chat_review(other, chat_id)
    assert item["judge"]["model"] == load_prompts().models.judge_model("fake")
    assert flag(item, rule)["call"]["verdict"] == "agreed"
    assert flag(ok(post(other, judge, "evidence")), judge)["evidence_opened"] is True


def test_a_judge_retry_keeps_the_calls_on_rule_flags(make_client):
    provider = judged("No breaks found.", '{"flags": "none"}')
    client = make_client(provider=provider)
    chat_id = checked(client)
    [rule] = chat_review(client, chat_id)["flags"]
    ok(post(client, rule["id"], "evidence"))
    ok(post(client, rule["id"], "agree"))

    provider.replies.append(FakeReply(text=judge_reply(UMBRIDGE)))
    check(client, chat_id)
    item = chat_review(client, chat_id)
    assert [(found["id"], found["source"]) for found in item["flags"]][0] == (rule["id"], "rule")
    assert flag(item, rule["id"])["call"]["verdict"] == "agreed"
    [judge] = [found for found in item["flags"] if found["source"] == "judge"]
    assert judge["call"] is None
    assert item["open_calls"] == 1


def test_a_reason_over_the_typed_limit_is_refused(cla_f2):
    client, chat_id, rule, judge = cla_f2
    refused = post(client, judge, "override", {"reason": "word " * 401})
    assert refused.status_code == 422
    assert "2,000 characters" in refused.json()["detail"]
    assert events(client) == []
