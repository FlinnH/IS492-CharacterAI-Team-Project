"""Contract tests from CP3_PLAN section 1: the boundaries between modules hold."""

import ast
import json
import re
import shutil
import subprocess
from pathlib import Path

import pytest

APP_DIR = Path(__file__).resolve().parent.parent / "app"
WORKBENCH_DIR = APP_DIR / "workbench"
STATIC_DIR = APP_DIR / "static"


def v1_line_ids():
    sample = json.loads((APP_DIR / "samples" / "spec_v1.json").read_text(encoding="utf-8"))
    return [line["id"] for section in sample["body"]["sections"] for line in section["lines"]]


def test_no_line_id_in_code():
    # Line IDs, their attributes, and check limits live in the spec, so the
    # code keeps working when a creator edits or replaces the spec.
    files = [*WORKBENCH_DIR.rglob("*.py"), *(WORKBENCH_DIR / "migrations").glob("*.sql"), STATIC_DIR / "api.js"]
    found = [
        f"{path.relative_to(APP_DIR)}: {line_id}"
        for path in files
        for line_id in v1_line_ids()
        if re.search(rf"\b{line_id}\b", path.read_text(encoding="utf-8"))
    ]
    assert found == []


def test_only_db_imports_sqlite3():
    importers = set()
    for path in WORKBENCH_DIR.rglob("*.py"):
        for node in ast.walk(ast.parse(path.read_text(encoding="utf-8"))):
            if isinstance(node, ast.Import):
                modules = [alias.name for alias in node.names]
            elif isinstance(node, ast.ImportFrom):
                modules = [node.module or ""]
            else:
                continue
            if any(module.split(".")[0] == "sqlite3" for module in modules):
                importers.add(path.name)
    assert importers == {"db.py"}


def test_only_api_js_talks_to_the_server():
    app_js = (STATIC_DIR / "app.js").read_text(encoding="utf-8")
    api_js = (STATIC_DIR / "api.js").read_text(encoding="utf-8")
    assert "fetch(" not in app_js
    assert "/api/" not in app_js
    assert "fetch(" in api_js
    assert "/api/" in api_js


def test_every_data_action_has_a_handler():
    # A button whose action has no handler does nothing when pressed. Whole-line
    # comments are dropped first, since one shows data-action="name" as an example.
    app_js = re.sub(r"^\s*//.*$", "", (STATIC_DIR / "app.js").read_text(encoding="utf-8"), flags=re.M)
    markup = app_js + (STATIC_DIR / "index.html").read_text(encoding="utf-8")
    used = set(re.findall(r'data-action="([a-z-]+)"', markup))
    handled = set(re.findall(r'actions\["([a-z-]+)"\]', app_js))
    assert used - handled == set()


def find_python_3_11():
    for name in ("python3.11", "python3"):
        python = shutil.which(name)
        if not python:
            continue
        result = subprocess.run(
            [python, "-c", "import sys; print(*sys.version_info[:2])"], capture_output=True, text=True, timeout=30
        )
        if result.returncode == 0 and result.stdout.split() == ["3", "11"]:
            return python
    return None


def test_app_code_compiles_on_python_3_11():
    # app/.venv may be newer, but run.sh accepts any python3 from 3.11 up.
    python = find_python_3_11()
    if python is None:
        pytest.skip("no Python 3.11 on PATH")
    check = (
        "import pathlib, sys\n"
        "for path in pathlib.Path(sys.argv[1]).rglob('*.py'):\n"
        "    compile(path.read_text(encoding='utf-8'), str(path), 'exec')\n"
    )
    result = subprocess.run([python, "-B", "-c", check, str(WORKBENCH_DIR)], capture_output=True, text=True, timeout=60)
    assert result.returncode == 0, result.stderr
