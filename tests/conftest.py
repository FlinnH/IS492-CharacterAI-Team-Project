"""Shared test setup. Tests never read app/.env, so a real key can't reach them."""

import sys
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

REPO_DIR = Path(__file__).resolve().parent.parent
APP_DIR = REPO_DIR / "app"
sys.path.insert(0, str(APP_DIR))

from workbench.config import Settings, example_values  # noqa: E402
from workbench.main import create_app  # noqa: E402


@pytest.fixture
def make_client():
    """Builds a test client from the .env.example values plus any overrides."""

    def build(**overrides):
        # Init values beat environment variables, so the shell can't change a test.
        settings = Settings(_env_file=None, **{**example_values(), **overrides})
        return TestClient(create_app(settings))

    return build
