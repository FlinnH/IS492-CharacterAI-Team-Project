"""Team kit checks (CP4 F1).

The report skeleton has every section, every relative link in the kit's files
resolves, the tests workflow parses, and the questionnaire template holds SUS
and UMUX-Lite in full. These read the kit's own files, with no key and no network.
"""

import json
import os
import re
from pathlib import Path
from urllib.parse import unquote

import pytest

REPO_DIR = Path(__file__).resolve().parent.parent
REPORT = REPO_DIR / "docs" / "FINAL_REPORT.md"
QUESTIONNAIRE = REPO_DIR / "docs" / "study_materials" / "questionnaire_TEMPLATE.md"
WORKFLOW = REPO_DIR / ".github" / "workflows" / "tests.yml"
ANSWER_KEY_TEMPLATE = REPO_DIR / "docs" / "study_materials" / "answer_key_TEMPLATE.md"
JUDGE_SCHEMA = REPO_DIR / "app" / "prompts" / "judge.schema.v1.json"

# The Markdown files the team kit added.
KIT_FILES = [
    "AGENTS.md",
    "docs/FINAL_REPORT.md",
    "docs/cp4/TEAM_START_HERE.md",
    "docs/cp4/DECISIONS.md",
    "docs/cp4/WORK_LOG.md",
    "docs/study_materials/README.md",
    "docs/study_materials/protocol_TEMPLATE.md",
    "docs/study_materials/consent_TEMPLATE.md",
    "docs/study_materials/task_prompts_TEMPLATE.md",
    "docs/study_materials/questionnaire_TEMPLATE.md",
    "docs/study_materials/recruiting_TEMPLATE.md",
    "docs/study_materials/session_notes_TEMPLATE.md",
    "docs/study_materials/themes_TEMPLATE.md",
    "docs/study_materials/test_chat_TEMPLATE.md",
    "docs/study_materials/answer_key_TEMPLATE.md",
    "docs/figures/README.md",
    "slides/cp4/CP4_SLIDE_PLAN.md",
    ".github/pull_request_template.md",
    ".github/ISSUE_TEMPLATE/task.md",
    ".github/ISSUE_TEMPLATE/decision.md",
]

# The sections the CP4 instructions name, in their order.
REPORT_SECTIONS = [
    "Abstract",
    "1. Introduction",
    "2. Related work",
    "3. Methodology",
    "4. Evaluation design",
    "5. Results and discussion",
    "6. Limitations and ethics",
    "7. Conclusion",
    "References",
    "Appendices",
]

# The System Usability Scale, word for word (Brooke, 1996).
SUS_ITEMS = [
    "I think that I would like to use this system frequently.",
    "I found the system unnecessarily complex.",
    "I thought the system was easy to use.",
    "I think that I would need the support of a technical person to be able to use this system.",
    "I found the various functions in this system were well integrated.",
    "I thought there was too much inconsistency in this system.",
    "I would imagine that most people would learn to use this system very quickly.",
    "I found the system very cumbersome to use.",
    "I felt very confident using the system.",
    "I needed to learn a lot of things before I could get going with this system.",
]

# UMUX-Lite, word for word (Lewis, Utesch, and Maher, 2013).
UMUX_LITE_ITEMS = [
    "This system's capabilities meet my requirements.",
    "This system is easy to use.",
]

HEADING = re.compile(r"^(#{1,6})\s+(.+?)\s*$", re.M)
LINK = re.compile(r"\[[^\]]*\]\(\s*<?([^)\s>]+)>?(?:\s+\"[^\"]*\")?\s*\)")


def without_blocks(text):
    """The text with HTML comments and fenced code taken out."""
    text = re.sub(r"<!--.*?-->", "", text, flags=re.S)
    return re.sub(r"^```.*?^```[^\n]*$", "", text, flags=re.S | re.M)


def headings(path):
    """(level, words) for each heading in a Markdown file, in order."""
    text = without_blocks(path.read_text(encoding="utf-8"))
    return [(len(marks), words) for marks, words in HEADING.findall(text)]


def anchors(path):
    """Every anchor GitHub makes from a file's headings.

    An anchor is the heading in lowercase, with punctuation dropped and spaces
    turned into hyphens. A repeated heading gets -1, -2, and so on.
    """
    seen, found = {}, set()
    for _level, words in headings(path):
        name = re.sub(r"[^\w\- ]", "", words.lower()).replace(" ", "-")
        found.add(f"{name}-{seen[name]}" if name in seen else name)
        seen[name] = seen.get(name, 0) + 1
    return found


def exists_with_this_spelling(path):
    """True when the path is inside the repo and exists with exactly these letters.

    A Mac finds docs/readme.md when the file is docs/README.md, and GitHub doesn't.
    """
    path = Path(os.path.normpath(path))
    if path != REPO_DIR and REPO_DIR not in path.parents:
        return False
    here = REPO_DIR
    for part in path.relative_to(REPO_DIR).parts:
        if part not in os.listdir(here):
            return False
        here = here / part
    return True


def test_the_report_skeleton_has_every_section():
    found = headings(REPORT)
    assert len([words for level, words in found if level == 1]) == 1, "one title"
    # Each named section appears once, in the instructions' order. Other headings are fine.
    sections = [words for level, words in found if level == 2]
    assert [words for words in sections if words in REPORT_SECTIONS] == REPORT_SECTIONS


@pytest.mark.parametrize("name", KIT_FILES)
def test_every_relative_link_in_the_kit_resolves(name):
    path = REPO_DIR / name
    text = re.sub(r"`[^`\n]*`", "", without_blocks(path.read_text(encoding="utf-8")))
    broken = []
    for target in LINK.findall(text):
        if re.match(r"[A-Za-z][A-Za-z0-9+.-]*:", target):
            continue  # https:, mailto:, and other full addresses
        file_part, _, anchor = target.partition("#")
        linked = path.parent / unquote(file_part) if file_part else path
        if not exists_with_this_spelling(linked):
            broken.append(target)
        elif anchor and linked.is_file() and linked.suffix == ".md" and anchor not in anchors(linked):
            broken.append(target)
    assert broken == []


def read_plain_yaml(text):
    """Reads the plain YAML the tests workflow is written in.

    The app has no YAML library, and the workflow needs only nested maps,
    lists, and one-line values. Anything else (a tab, a comment after a value,
    block text, an unquoted version number) fails here, so the file stays simple.
    """
    lines = []
    for raw in text.splitlines():
        assert "\t" not in raw, f"a tab in: {raw!r}"
        if raw.strip() and not raw.lstrip().startswith("#"):
            lines.append((len(raw) - len(raw.lstrip(" ")), raw.strip()))
    value, end = read_block(lines, 0)
    assert end == len(lines), f"can't place: {lines[end][1]!r}"
    return value


def read_block(lines, start):
    """The map or list that starts at lines[start], and the index of the line after it."""
    indent = lines[start][0]
    index = start
    if lines[start][1].startswith("- "):
        items = []
        while index < len(lines) and lines[index][0] == indent:
            words = lines[index][1]
            assert words.startswith("- "), f"expected a list item: {words!r}"
            words = words[2:].strip()
            if re.match(r"[\w-]+:(\s|$)", words):
                # A map inside the list. Its first key sits two columns in, in line with its other keys.
                lines[index] = (indent + 2, words)
                item, index = read_block(lines, index)
            else:
                item, index = read_value(words), index + 1
            items.append(item)
        return items, index
    mapping = {}
    while index < len(lines) and lines[index][0] == indent:
        match = re.fullmatch(r"([\w-]+):(?:\s+(.+))?", lines[index][1])
        assert match, f"expected key: value in: {lines[index][1]!r}"
        key, words = match.groups()
        assert key not in mapping, f"{key} appears twice"
        index += 1
        if words is not None:
            mapping[key] = read_value(words)
        elif index < len(lines) and lines[index][0] > indent:
            mapping[key], index = read_block(lines, index)
        else:
            mapping[key] = None
    return mapping, index


def read_value(words):
    """A one-line value: quoted text, a [list], true or false, a whole number, or plain text."""
    if words[0] in "\"'":
        assert len(words) > 1 and words[-1] == words[0] and words[0] not in words[1:-1], f"odd quotes in: {words!r}"
        return words[1:-1]
    if words[0] == "[":
        assert words[-1] == "]", f"a list must close on its own line: {words!r}"
        inside = words[1:-1].strip()
        return [read_value(part.strip()) for part in inside.split(",")] if inside else []
    assert not re.search(r"^[|>&*!%@`{]|\s#|:\s|:$", words), f"not plain YAML: {words!r}"
    assert not re.fullmatch(r"[-+]?\d*\.\d+", words), f"quote this, or YAML reads it as a decimal: {words!r}"
    assert words.lower() not in ("yes", "no", "on", "off", "null", "~"), f"quote this word: {words!r}"
    if words in ("true", "false"):
        return words == "true"
    return int(words) if re.fullmatch(r"-?\d+", words) else words


def test_the_tests_workflow_parses_and_runs_pytest_on_python_3_11_and_3_12():
    text = WORKFLOW.read_text(encoding="utf-8")
    workflow = read_plain_yaml(text)

    # Every push and every pull request, with no branch or path filter on either.
    assert "push" in workflow["on"] and workflow["on"]["push"] is None
    assert "pull_request" in workflow["on"] and workflow["on"]["pull_request"] is None
    # The tests use the fake model, so the workflow asks for no secret.
    assert "secrets." not in text

    jobs = [job for job in workflow["jobs"].values() if any("pytest" in step.get("run", "") for step in job["steps"])]
    assert len(jobs) == 1
    job = jobs[0]
    assert workflow["name"] and job["name"], "the check needs a clear name"
    assert job["strategy"]["matrix"]["python-version"] == ["3.11", "3.12"]

    steps = job["steps"]
    assert any(step.get("uses", "").startswith("actions/checkout@") for step in steps)
    setup = [step for step in steps if step.get("uses", "").startswith("actions/setup-python@")]
    assert len(setup) == 1
    assert setup[0]["with"]["python-version"] == "${{ matrix.python-version }}"
    runs = [step.get("run", "") for step in steps]
    install = next(index for index, run in enumerate(runs) if "pip install -r app/requirements.txt" in run)
    tests = next(index for index, run in enumerate(runs) if re.search(r"\bpytest\b", run))
    assert install < tests


def test_the_questionnaire_template_holds_all_of_sus_and_umux_lite():
    text = " ".join(QUESTIONNAIRE.read_text(encoding="utf-8").split())
    assert len(SUS_ITEMS) == 10 and len(UMUX_LITE_ITEMS) == 2
    assert [item for item in SUS_ITEMS + UMUX_LITE_ITEMS if item not in text] == []


def test_the_answer_sheet_template_lists_the_judges_failure_types():
    # Scoring by mistake type needs the answer sheet and the judge to use the same names.
    schema = json.loads(JUDGE_SCHEMA.read_text(encoding="utf-8"))
    types = schema["properties"]["flags"]["items"]["properties"]["type"]["enum"]
    listed = re.findall(r"^- (.+)$", ANSWER_KEY_TEMPLATE.read_text(encoding="utf-8"), flags=re.M)
    assert [item for item in listed if not item.startswith("**")] == types
