"""Smoke tests: the screens load, health hides the key, run.sh checks Python, and a refusal to start is one plain line."""

import os
import shutil
import subprocess
from html.parser import HTMLParser
from pathlib import Path

import pytest

APP_DIR = Path(__file__).resolve().parent.parent / "app"
RUN_SH = APP_DIR / "run.sh"
STATIC_DIR = APP_DIR / "static"


class TabFinder(HTMLParser):
    """Collects the data-screen of every element with role="tab"."""

    def __init__(self):
        super().__init__()
        self.screens = []

    def handle_starttag(self, tag, attrs):
        attrs = dict(attrs)
        if attrs.get("role") == "tab":
            self.screens.append(attrs.get("data-screen"))


class ScriptFinder(HTMLParser):
    """Collects the src of every script tag, in page order."""

    def __init__(self):
        super().__init__()
        self.sources = []

    def handle_starttag(self, tag, attrs):
        if tag == "script":
            self.sources.append(dict(attrs).get("src"))


def test_root_serves_four_tabs(make_client):
    client = make_client()

    response = client.get("/")
    assert response.status_code == 200
    assert response.headers["content-type"].startswith("text/html")
    finder = TabFinder()
    finder.feed(response.text)
    assert finder.screens == ["define", "run", "diagnose", "compare"]

    for name, content_type in [
        ("styles.css", "text/css"),
        ("api.js", "javascript"),
        ("app.js", "javascript"),
    ]:
        response = client.get(f"/{name}")
        assert response.status_code == 200, name
        assert content_type in response.headers["content-type"], name
        assert response.content == (STATIC_DIR / name).read_bytes(), name

    # M4 moved every screen onto the server's data, so the CP2 data.js is gone.
    assert client.get("/data.js").status_code == 404


def test_scripts_load_in_order(make_client):
    # app.js uses api.js as soon as it runs.
    finder = ScriptFinder()
    finder.feed(make_client().get("/").text)
    assert finder.sources == ["api.js", "app.js"]


def test_health_never_echoes_key(make_client):
    fake_key = "fake-test-key-7f3a9c1e5b2d"
    response = make_client(gemini_api_key=fake_key).get("/api/health")
    assert response.status_code == 200
    assert response.json()["key_set"] is True
    assert fake_key not in response.text
    assert fake_key[-6:] not in response.text

    response = make_client(gemini_api_key="").get("/api/health")
    assert response.status_code == 200
    assert response.json()["key_set"] is False


def test_run_sh_refuses_python_older_than_3_11(tmp_path):
    assert os.access(RUN_SH, os.X_OK), "app/run.sh must be executable"

    # Run a copy, so nothing can touch the real app/.venv.
    app_copy = tmp_path / "app"
    app_copy.mkdir()
    shutil.copy2(RUN_SH, app_copy / "run.sh")
    fake_bin = tmp_path / "bin"
    fake_bin.mkdir()
    fake_python = fake_bin / "python3"
    fake_python.write_text("#!/bin/sh\necho 3.10.14\n")
    fake_python.chmod(0o755)

    result = subprocess.run(
        [shutil.which("bash") or "/bin/bash", str(app_copy / "run.sh")],
        env={"PATH": os.pathsep.join([str(fake_bin), "/usr/bin", "/bin"]), "HOME": str(tmp_path)},
        capture_output=True,
        text=True,
        timeout=30,
    )

    assert result.returncode != 0
    assert "3.10.14" in result.stderr
    assert "3.11" in result.stderr
    assert not (app_copy / ".venv").exists()


def test_a_refusal_to_start_is_one_plain_line(monkeypatch, capsys, tmp_path):
    from conftest import settings_for
    from workbench import db
    from workbench import main as entry

    # A database from a newer workbench: create_app refuses it.
    settings = settings_for(tmp_path)
    with db.Database(settings.workbench_db_path).connect() as conn:
        conn.execute("PRAGMA user_version = 99")
    monkeypatch.setattr(entry, "load_settings", lambda: settings)
    with pytest.raises(SystemExit) as stopped:
        entry.main()
    assert stopped.value.code == 1
    err = capsys.readouterr().err
    assert err.startswith("run.sh: ") and err.count("\n") == 1
    assert "made by a newer version of the workbench" in err and "Traceback" not in err


def test_a_wrong_setting_is_named_in_one_line(monkeypatch, capsys, tmp_path):
    from conftest import settings_for
    from workbench import main as entry

    monkeypatch.setattr(entry, "load_settings", lambda: settings_for(tmp_path, workbench_port="not a port"))
    with pytest.raises(SystemExit):
        entry.main()
    assert capsys.readouterr().err == (
        "run.sh: app/.env has a missing or wrong value for WORKBENCH_PORT. app/.env.example lists every setting.\n"
    )
