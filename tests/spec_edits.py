"""Helpers that turn a spec view (the API's JSON) into an edit, then change it."""


def edit_payload(view):
    """The edit that would save `view` unchanged."""
    body = view["body"]
    return {
        "parent": view["version"],
        "note": "",
        "preamble": body["preamble"],
        "fields": [{"label": field["label"], "text": field["text"]} for field in body["fields"]],
        "setting": body["setting"],
        "sections": [
            {
                "heading": section["heading"],
                "lines": [{"id": line["id"], "text": line["text"]} for line in section["lines"]],
            }
            for section in body["sections"]
        ],
    }


def set_line(edit, line_id, text):
    for section in edit["sections"]:
        for line in section["lines"]:
            if line["id"] == line_id:
                line["text"] = text
                return
    raise KeyError(line_id)


def drop_line(edit, line_id):
    for section in edit["sections"]:
        section["lines"] = [line for line in section["lines"] if line["id"] != line_id]


def add_line(edit, heading, text):
    """Adds a new line, with no ID, at the end of the section."""
    for section in edit["sections"]:
        if section["heading"] == heading:
            section["lines"].append({"id": None, "text": text})
            return
    raise KeyError(heading)


def line_ids(view):
    return [line["id"] for section in view["body"]["sections"] for line in section["lines"]]


def find_line(view, line_id):
    for section in view["body"]["sections"]:
        for line in section["lines"]:
            if line["id"] == line_id:
                return line
    return None
