"""M0 smoke tests: the screens load, health hides the key, run.sh checks Python."""

import os
import shutil
import subprocess
from html.parser import HTMLParser
from pathlib import Path

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
        ("data.js", "javascript"),
        ("app.js", "javascript"),
    ]:
        response = client.get(f"/{name}")
        assert response.status_code == 200, name
        assert content_type in response.headers["content-type"], name
        assert response.content == (STATIC_DIR / name).read_bytes(), name


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
