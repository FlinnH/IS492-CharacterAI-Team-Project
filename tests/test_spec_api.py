"""M1 API tests: the Spec editor's routes, end to end, on a database in each test's own folder."""

import json

import pytest

from spec_edits import add_line, drop_line, edit_payload, find_line, line_ids, set_line

SPECS = "/api/characters/harry/specs"


@pytest.fixture
def client(make_client):
    return make_client()


def post(client, edit):
    # json.dumps escapes every non-ASCII character, so even a lone surrogate
    # reaches the server the way a browser would send it.
    return client.post(SPECS, content=json.dumps(edit), headers={"Content-Type": "application/json"})


def save(client, edit):
    response = post(client, edit)
    assert response.status_code == 201, response.text
    return response.json()


def latest(client):
    response = client.get(f"{SPECS}/latest")
    assert response.status_code == 200, response.text
    return response.json()


def section(view_or_edit, heading):
    sections = view_or_edit["body"]["sections"] if "body" in view_or_edit else view_or_edit["sections"]
    return next(item for item in sections if item["heading"] == heading)


def test_v1_matches_prototype_spec(client, prototype_data):
    assert client.get("/api/characters").json() == [{"slug": "harry", "name": "Harry Potter"}]

    view = client.get(f"{SPECS}/1").json()
    spec = prototype_data["spec"]
    body = view["body"]
    assert (view["version"], view["parent"]) == (1, None)
    assert body["preamble"] == spec["preamble"]
    assert [(field["label"], field["text"]) for field in body["fields"]] == [
        (field["label"], field["text"]) for field in spec["fields"]
    ]
    assert [(item["heading"], [(line["id"], line["text"]) for line in item["lines"]]) for item in body["sections"]] == [
        (item["heading"], [(line["id"], line["text"]) for line in item["lines"]]) for item in spec["sections"]
    ]
    assert body["setting"] == ""


def test_edit_makes_v2_and_v1_stays_the_same(client):
    v1 = latest(client)
    edit = edit_payload(v1)
    set_line(edit, "C2", "He lives with the Dursleys, who treat him badly.")
    edit["setting"] = "Alex knocks on the door of 4 Privet Drive while Harry\u2019s aunt and uncle are out."
    edit["note"] = "Add a setting"
    v2 = save(client, edit)

    assert (v2["version"], v2["parent"], v2["latest"]) == (2, 1, 2)
    assert find_line(v2, "C2")["text"] == "He lives with the Dursleys, who treat him badly."
    assert v2["body"]["setting"] == "Alex knocks on the door of 4 Privet Drive while Harry\u2019s aunt and uncle are out."
    assert v2["note"] == "Add a setting"
    assert [summary["version"] for summary in v2["versions"]] == [2, 1]

    v1_after = client.get(f"{SPECS}/1").json()
    for key in ("body", "sha256", "note", "created_at", "parent", "warnings"):
        assert v1_after[key] == v1[key], key
    assert v1_after["latest"] == 2

    edit = edit_payload(v2)
    set_line(edit, "C3", "He slept in the cupboard under the stairs.")
    v3 = save(client, edit)
    assert (v3["version"], v3["parent"]) == (3, 2)

    v2_after = client.get(f"{SPECS}/2").json()
    for key in ("body", "sha256", "note", "created_at", "parent"):
        assert v2_after[key] == v2[key], key


def test_line_ids_are_never_reused(client):
    edit = edit_payload(latest(client))
    drop_line(edit, "K6")
    add_line(edit, "Canon facts, year 4 (Goblet of Fire)", "He keeps his Firebolt under the floorboards.")
    v2 = save(client, edit)
    assert "K6" not in line_ids(v2)
    assert find_line(v2, "C26")["text"] == "He keeps his Firebolt under the floorboards."

    edit = edit_payload(v2)
    add_line(edit, "Knowledge boundary", "He has never heard of Luna Lovegood.")
    v3 = save(client, edit)
    assert find_line(v3, "K7")["text"] == "He has never heard of Luna Lovegood."
    assert "K6" not in line_ids(v3)

    # Sending K6 back as a kept line is refused, so it can't return that way either.
    edit = edit_payload(v3)
    section(edit, "Knowledge boundary")["lines"].append(
        {"id": "K6", "text": "He does not know he is a character in books or films."}
    )
    response = post(client, edit)
    assert response.status_code == 422
    assert "K6" in response.json()["detail"]
    assert latest(client)["version"] == 3


def test_empty_setting_returns_warning(client):
    v1 = latest(client)
    assert [warning["field"] for warning in v1["warnings"]] == ["setting"]
    # The screens call the field Scene, so its warning does too.
    message = v1["warnings"][0]["message"].lower()
    assert "scene" in message
    assert "setting" not in message

    edit = edit_payload(v1)
    edit["setting"] = "  \n "
    set_line(edit, "C2", "He lives with the Dursleys.")
    v2 = save(client, edit)
    assert v2["body"]["setting"] == ""
    assert [warning["field"] for warning in v2["warnings"]] == ["setting"]

    edit = edit_payload(v2)
    edit["setting"] = "Alex has come round to 4 Privet Drive on a hot afternoon."
    v3 = save(client, edit)
    assert v3["warnings"] == []


def test_stale_parent_conflicts(client):
    edit = edit_payload(latest(client))
    set_line(edit, "C2", "He lives with the Dursleys.")
    save(client, edit)

    # The same edit again, as a double click or a second tab would send it.
    response = post(client, edit)
    assert response.status_code == 409
    assert "v2" in response.json()["detail"]
    assert [summary["version"] for summary in latest(client)["versions"]] == [2, 1]


def pad_line(edit, line_id):
    """Adds spaces and line breaks that cleaning removes again."""
    for item in edit["sections"]:
        for line in item["lines"]:
            if line["id"] == line_id:
                line["text"] = "  " + line["text"].replace(" ", " \n ") + "\t"


def move_line(edit, line_id, heading):
    """Moves a kept line, ID and all, to the end of another section."""
    for item in edit["sections"]:
        for line in item["lines"]:
            if line["id"] == line_id:
                item["lines"].remove(line)
                section(edit, heading)["lines"].append(line)
                return
    raise KeyError(line_id)


INVALID_EDITS = {
    # name: (change to an unchanged v1 edit, field key the server reports, words in its message)
    "empty-kept-line": (lambda edit: set_line(edit, "C2", "   "), "line-0-1", "C2"),
    "blank-new-line": (lambda edit: add_line(edit, "Relationships", "\n"), "line-5-15", "Relationships"),
    "zero-width-only-line": (lambda edit: set_line(edit, "R1", "\u200b"), "line-5-0", "R1"),
    "id-typed-into-new-line": (
        lambda edit: add_line(edit, "Knowledge boundary", "K7. He has never heard of thestrals."),
        "line-6-6",
        "Leave the ID out",
    ),
    "unknown-id": (
        lambda edit: section(edit, "Relationships")["lines"].append({"id": "R99", "text": "Made up."}),
        "line-5-15",
        "R99",
    ),
    "repeated-id": (
        lambda edit: section(edit, "Relationships")["lines"].append({"id": "R1", "text": "Ron again."}),
        "line-5-15",
        "R1",
    ),
    "renamed-section": (lambda edit: edit["sections"][0].update(heading="Before Hogwarts"), None, "sections"),
    "lone-surrogate": (lambda edit: set_line(edit, "B2", "Don't guess \ud800"), "line-7-1", "B2"),
    "nothing-changed": (lambda edit: None, None, "Nothing changed"),
    "only-whitespace-changed": (lambda edit: pad_line(edit, "C1"), None, "Nothing changed"),
    # The rest of specs.py's checks (M6).
    "renamed-field": (lambda edit: edit["fields"][0].update(label="Full name"), None, "fields changed"),
    "empty-opening-instruction": (lambda edit: edit.update(preamble="  \n "), "preamble", "The opening instruction is empty"),
    "empty-field": (lambda edit: edit["fields"][1].update(text="\u200b"), "field-1", "is empty. Write it before you save."),
    "line-moved-to-another-section": (
        lambda edit: move_line(edit, "C2", "Relationships"),
        "line-5-15",
        "C2 can't move to Relationships",
    ),
    "parent-from-the-future": (lambda edit: edit.update(parent=9), None, "There is no v9 to edit"),
    "lone-surrogate-in-the-note": (
        lambda edit: (set_line(edit, "C2", "He lives with the Dursleys."), edit.update(note="Fixed \ud800")),
        "note",
        "The note has a character that can't be saved",
    ),
}


@pytest.mark.parametrize("case", INVALID_EDITS)
def test_invalid_edits_are_rejected(client, case):
    change, field, words = INVALID_EDITS[case]
    edit = edit_payload(latest(client))
    change(edit)

    response = post(client, edit)
    assert response.status_code == 422
    error = response.json()
    assert isinstance(error["detail"], str)
    assert words in error["detail"]
    assert error.get("field") == field
    assert latest(client)["version"] == 1


@pytest.mark.parametrize(
    "line_id",
    ["R1'; DROP TABLE spec_versions; --", "\ud800", "r1", "R0", "R1 "],
    ids=["sql", "lone-surrogate", "lowercase", "zero", "trailing-space"],
)
def test_a_made_up_line_id_gets_a_plain_422(client, line_id):
    # Checked like a stored line's ID before the edit is read, so a crafted one
    # can't reach a message that echoes it, as a lone surrogate once did with a 500.
    edit = edit_payload(latest(client))
    section(edit, "Relationships")["lines"].append({"id": line_id, "text": "Made up."})
    response = post(client, edit)
    assert response.status_code == 422
    assert response.json() == {"detail": "The request has a missing or wrong value at sections.5.lines.15.id."}
    assert latest(client)["version"] == 1


def test_malformed_request_gets_one_plain_message(client):
    response = post(client, {"parent": 1, "preamble": "words only the creator typed"})
    assert response.status_code == 422
    assert isinstance(response.json()["detail"], str)
    assert "words only the creator typed" not in response.text


@pytest.mark.parametrize(
    ("path", "named"),
    [
        ("/api/characters/nobody/specs/latest", "nobody"),
        (f"{SPECS}/9", "v9"),
        (f"{SPECS}/99999999999999999999", "v99999999999999999999"),
    ],
    ids=["unknown-character", "unknown-version", "huge-version"],
)
def test_unknown_character_or_version_is_404(client, path, named):
    response = client.get(path)
    assert response.status_code == 404
    # The message names what is missing, unlike the plain 404 for a missing file.
    assert named in response.json()["detail"]


def test_versions_survive_a_restart(make_client):
    first = make_client()
    edit = edit_payload(latest(first))
    set_line(edit, "C2", "He lives with the Dursleys.")
    save(first, edit)

    # A second app on the same database file, as after app/run.sh restarts.
    view = latest(make_client())
    assert view["version"] == 2
    assert [summary["version"] for summary in view["versions"]] == [2, 1]


def test_emptied_section_keeps_its_prefix(client):
    edit = edit_payload(latest(client))
    section(edit, "Knowledge boundary")["lines"] = []
    v2 = save(client, edit)
    knowledge = section(v2, "Knowledge boundary")
    assert (knowledge["prefix"], knowledge["lines"]) == ("K", [])

    edit = edit_payload(v2)
    add_line(edit, "Knowledge boundary", "He knows nothing that happened after June 1995.")
    v3 = save(client, edit)
    assert [line["id"] for line in section(v3, "Knowledge boundary")["lines"]] == ["K7"]
