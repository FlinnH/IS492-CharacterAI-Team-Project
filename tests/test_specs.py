"""M1 spec service tests: v1 is the CP2 spec, and edits keep the data later checks rely on."""

import hashlib
import json
import re
from pathlib import Path

import pytest

from spec_edits import add_line, drop_line, edit_payload, set_line
from workbench import specs
from workbench.schemas import SpecEdit

REPO_DIR = Path(__file__).resolve().parent.parent
# Named exactly: the other files in validation/fixtures are a hidden test set.
CHARACTER_SPEC = REPO_DIR / "validation" / "fixtures" / "CHARACTER_SPEC.md"


def edit_of(view):
    """An edit that would save this SpecView unchanged."""
    return edit_payload(view.model_dump(mode="json"))


def save(database, edit):
    return specs.save_edit(database, "harry", SpecEdit.model_validate(edit))


def lines_by_id(view):
    return {line.id: line for section in view.body.sections for line in section.lines}


def test_v1_matches_character_spec_md(database):
    # The spec is the text between the file's two horizontal rules, with the
    # markdown symbols removed.
    markdown = CHARACTER_SPEC.read_text(encoding="utf-8").split("\n---\n")[1]
    body = specs.get_spec(database, "harry", 1).body

    def plain(text):
        return text.replace("*", "")

    assert markdown.strip().splitlines()[0] == body.preamble
    assert [(label, plain(text)) for label, text in re.findall(r"^\*\*(.+?):\*\* (.+)$", markdown, re.M)] == [
        (field.label, field.text) for field in body.fields
    ]
    assert re.findall(r"^\*\*(.+?):\*\*$", markdown, re.M) == [section.heading for section in body.sections]
    assert [(line_id, plain(text)) for line_id, text in re.findall(r"^- ([A-Z][0-9]+)\. (.+)$", markdown, re.M)] == [
        (line.id, line.text) for section in body.sections for line in section.lines
    ]


def test_line_attributes_and_limits_are_data(database):
    view = specs.get_spec(database, "harry", 1)
    lines = lines_by_id(view)

    assert sorted(line_id for line_id, line in lines.items() if line.needs_call) == ["B1", "K6"]
    assert [line_id for line_id, line in lines.items() if line.provenance] == ["B6"]
    assert {line_id: line.max_sentences for line_id, line in lines.items() if line.max_sentences is not None} == {
        "B4": 4
    }
    assert [(field.label, field.banned_words, field.ban_emojis) for field in view.body.fields if field.banned_words or field.ban_emojis] == [
        ("Voice", ["mom", "vacation", "lol", "ngl", "rn"], True)
    ]


def test_edits_keep_attributes_and_new_lines_get_defaults(database):
    edit = edit_of(specs.get_spec(database, "harry"))
    set_line(edit, "B1", "Stay Harry, always.")
    set_line(edit, "B4", "Keep replies short.")
    set_line(edit, "B6", "Remember what the user says.")
    add_line(edit, "Behavioral rules", "Never sing.")
    v2 = save(database, edit)

    lines = lines_by_id(v2)
    assert (lines["B1"].text, lines["B1"].needs_call) == ("Stay Harry, always.", True)
    assert (lines["B4"].text, lines["B4"].max_sentences) == ("Keep replies short.", 4)
    assert (lines["B6"].text, lines["B6"].provenance) == ("Remember what the user says.", True)
    assert (lines["B7"].text, lines["B7"].needs_call, lines["B7"].provenance, lines["B7"].max_sentences) == (
        "Never sing.",
        False,
        False,
        None,
    )
    voice = next(field for field in v2.body.fields if field.label == "Voice")
    assert (voice.banned_words, voice.ban_emojis) == (["mom", "vacation", "lol", "ngl", "rn"], True)

    edit = edit_of(v2)
    drop_line(edit, "B6")
    v3 = save(database, edit)
    assert [line_id for line_id, line in lines_by_id(v3).items() if line.provenance] == []


def test_v1_hash_holds(database):
    def v1_row():
        with database.connect() as conn:
            return tuple(conn.execute("SELECT body, sha256 FROM spec_versions WHERE version = 1").fetchone())

    before = v1_row()
    for text in ("First change.", "Second change."):
        edit = edit_of(specs.get_spec(database, "harry"))
        set_line(edit, "C2", text)
        save(database, edit)

    body, sha256 = v1_row()
    assert (body, sha256) == before
    assert hashlib.sha256(body.encode("utf-8")).hexdigest() == sha256
    assert json.loads(body)["sections"][0]["lines"][1]["text"].startswith("He lives with his aunt Petunia")


@pytest.mark.parametrize(
    ("prefix", "used", "expected"),
    [
        ("K", {"K1", "K2", "K3", "K4", "K5", "K6"}, "K7"),
        ("K", {"K1", "K2", "K9"}, "K10"),
        ("C", {"C25", "K6"}, "C26"),
        ("S", set(), "S1"),
    ],
    ids=["after-the-last", "past-a-gap", "ignores-other-prefixes", "first-of-a-prefix"],
)
def test_next_line_id_skips_every_issued_number(prefix, used, expected):
    assert specs.next_line_id(prefix, used) == expected


def test_clean_text_collapses_whitespace_and_zero_width_marks():
    assert specs.clean_text(" a\n\n b\u00a0c ", "setting", "the setting") == "a b c"
    assert specs.clean_text("\u200b\ufeff", "line-0-0", "C1") == ""


def test_clean_text_rejects_characters_it_cannot_store():
    with pytest.raises(specs.SpecInvalid, match="can't be saved") as caught:
        specs.clean_text("Half a pair: \ud800", "line-2-1", "the new line in Relationships")
    assert caught.value.field == "line-2-1"
    assert str(caught.value).startswith("The new line in Relationships")


def test_seed_refuses_a_different_v1(tmp_path, database):
    sample = json.loads(specs.SAMPLE_FILE.read_text(encoding="utf-8"))
    sample["body"]["sections"][0]["lines"][0]["text"] = "A different first line."
    other_sample = tmp_path / "other_spec_v1.json"
    other_sample.write_text(json.dumps(sample), encoding="utf-8")

    with pytest.raises(RuntimeError, match="workbench.db"):
        specs.seed(database, other_sample)
    # The real sample still matches, so seeding again is a no-op.
    specs.seed(database)
    assert [summary.version for summary in specs.get_spec(database, "harry").versions] == [1]


def test_render_text_is_the_cp2_paste_without_italics(database):
    # The character gets the spec in CHARACTER_SPEC.md's own layout. Only the
    # italics differ, since spec bodies are stored without markdown.
    markdown = CHARACTER_SPEC.read_text(encoding="utf-8").split("\n---\n")[1]
    without_italics = re.sub(r"(?<!\*)\*(?!\*)", "", markdown).strip()
    assert specs.render_text(specs.get_spec(database, "harry", 1).body) == without_italics


def test_render_text_puts_the_setting_after_the_fields(database):
    body = specs.get_spec(database, "harry", 1).body.model_copy(update={"setting": "Alex knocks at 4 Privet Drive."})
    text = specs.render_text(body)
    voice = next(field for field in body.fields if field.label == "Voice")
    first_heading = body.sections[0].heading
    assert f"**Voice:** {voice.text}\n\n**Setting:** Alex knocks at 4 Privet Drive.\n\n**{first_heading}:**" in text
    # The same body always renders the same text.
    assert specs.render_text(body) == text
