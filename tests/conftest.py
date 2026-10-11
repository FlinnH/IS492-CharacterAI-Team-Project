"""Shared test setup. Tests never read app/.env, so a real key can't reach them."""

import json
import sys
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

REPO_DIR = Path(__file__).resolve().parent.parent
APP_DIR = REPO_DIR / "app"
sys.path.insert(0, str(APP_DIR))

from workbench import db, specs  # noqa: E402
from workbench.config import Settings, example_values  # noqa: E402
from workbench.main import create_app  # noqa: E402

# The frozen CP2 prototype. app/static/data.js is a copy that M4 removes.
PROTOTYPE_DATA = REPO_DIR / "prototype" / "data.js"


def js_literal_to_json(source):
    """Turns the object literal in data.js into JSON: quotes bare keys, drops comments.

    Strings are copied as they are, so apostrophes, \\u2019 escapes, and \\" inside
    them survive. Anything else JSON can't read (single quotes, backticks,
    trailing commas) makes json.loads fail loudly.
    """
    out = []
    i = 0
    while i < len(source):
        char = source[i]
        if char == '"':
            end = i + 1
            while source[end] != '"':
                end += 2 if source[end] == "\\" else 1
            out.append(source[i : end + 1])
            i = end + 1
        elif source.startswith("//", i):
            i = source.index("\n", i)
        elif source.startswith("/*", i):
            i = source.index("*/", i) + 2
        elif char.isalpha() or char == "_":
            end = i
            while end < len(source) and (source[end].isalnum() or source[end] in "_$"):
                end += 1
            word = source[i:end]
            out.append(word if word in ("true", "false", "null") else json.dumps(word))
            i = end
        else:
            out.append(char)
            i += 1
    return "".join(out)


def load_prototype_data():
    """window.WORKBENCH_DATA from prototype/data.js, as Python data."""
    source = PROTOTYPE_DATA.read_text(encoding="utf-8")
    start = source.index("window.WORKBENCH_DATA = ") + len("window.WORKBENCH_DATA = ")
    return json.loads(js_literal_to_json(source[start : source.rindex(";")]))


@pytest.fixture(scope="session")
def prototype_data():
    return load_prototype_data()


@pytest.fixture
def database(tmp_path):
    """A migrated database seeded with v1, in this test's own folder."""
    database = db.Database(tmp_path / "workbench.db")
    with database.connect() as conn:
        db.migrate(conn)
    specs.seed(database)
    return database


@pytest.fixture
def make_client(tmp_path):
    """Builds a test client from the .env.example values plus any overrides.

    The database lives in this test's own folder, so tests never touch app/data.
    Clients built in the same test share it, like restarts of one server.
    """

    def build(**overrides):
        values = {**example_values(), "workbench_db_path": str(tmp_path / "workbench.db"), **overrides}
        # Init values beat environment variables, so the shell can't change a test.
        settings = Settings(_env_file=None, **values)
        assert APP_DIR / "data" not in db.Database(settings.workbench_db_path).path.parents
        return TestClient(create_app(settings))

    return build
