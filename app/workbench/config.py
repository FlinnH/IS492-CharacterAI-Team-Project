"""Settings for the workbench.

This module is the only reader of environment variables. Every setting is
listed in app/.env.example, and none has a default in code. Values load from
app/.env.example first, then app/.env, then environment variables, and the
last one wins. Model settings live in app/prompts/ from M2 on.
"""

from pathlib import Path
from typing import Literal

from dotenv import dotenv_values
from pydantic import Field, PositiveFloat, PositiveInt, SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict

APP_DIR = Path(__file__).resolve().parent.parent
EXAMPLE_FILE = APP_DIR / ".env.example"
ENV_FILE = APP_DIR / ".env"


class Settings(BaseSettings):
    """One field per line in app/.env.example. A field is its env name in lowercase."""

    model_config = SettingsConfigDict(
        env_file=(EXAMPLE_FILE, ENV_FILE),
        extra="forbid",
        frozen=True,
    )

    workbench_host: str = Field(min_length=1)
    workbench_port: int = Field(ge=1, le=65535)
    workbench_db_path: Path
    workbench_provider: Literal["gemini", "ollama", "fake"]
    gemini_api_key: SecretStr
    gemini_base_url: str = Field(pattern=r"^https?://")
    ollama_base_url: str = Field(pattern=r"^https?://")
    workbench_daily_call_cap: PositiveInt
    workbench_session_run_limit: PositiveInt
    workbench_first_token_timeout_seconds: PositiveFloat


def example_values() -> dict[str, str]:
    """The settings in app/.env.example, keyed by field name."""
    return {name.lower(): value or "" for name, value in dotenv_values(EXAMPLE_FILE).items()}


def load_settings() -> Settings:
    """Settings for the running app. Refuses a key in the example file."""
    if example_values().get("gemini_api_key"):
        raise RuntimeError(
            "app/.env.example has a value for GEMINI_API_KEY. "
            "Move the key to app/.env and leave the example empty."
        )
    return Settings()
