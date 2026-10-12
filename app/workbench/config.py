"""Settings and prompts for the workbench.

This module is the only reader of environment variables and of the files in
app/prompts/. Every setting is listed in app/.env.example, and none has a
default in code. Values load from app/.env.example first, then app/.env, then
environment variables, and the last one wins. Model IDs, reasoning effort,
token limits, and prices come from the models file that
app/prompts/manifest.toml names.
"""

import hashlib
import tomllib
from dataclasses import dataclass
from pathlib import Path
from typing import Literal

from dotenv import dotenv_values
from pydantic import Field, PositiveFloat, PositiveInt, SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict

from workbench.schemas import ModelSettings

APP_DIR = Path(__file__).resolve().parent.parent
EXAMPLE_FILE = APP_DIR / ".env.example"
ENV_FILE = APP_DIR / ".env"
PROMPTS_DIR = APP_DIR / "prompts"

# The character prompt holds this once, and the rendered spec replaces it.
SPEC_PLACEHOLDER = "{spec}"


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
    workbench_calls_per_minute: PositiveInt
    workbench_session_run_limit: PositiveInt
    workbench_first_token_timeout_seconds: PositiveFloat
    workbench_max_typed_chars: PositiveInt
    workbench_max_import_chars: PositiveInt
    workbench_seeded_transcript_path: Path


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


def app_path(path: Path) -> Path:
    """A settings path, with a relative one counted from app/, as .env.example says."""
    path = Path(path).expanduser()
    return path if path.is_absolute() else APP_DIR / path


@dataclass(frozen=True)
class Prompts:
    """The prompt files in use. A version is its file name without the extension, like models.v1."""

    models: ModelSettings
    models_version: str
    character_template: str
    character_version: str


def load_prompts(folder: Path = PROMPTS_DIR) -> Prompts:
    """The current prompts from manifest.toml. Refuses a file whose hash changed.

    A prompt that was used never changes, so every call's logged version means
    one exact text. An edit is saved as the next version and added to the manifest.
    """
    manifest = tomllib.loads((folder / "manifest.toml").read_text(encoding="utf-8"))
    hashes = manifest["sha256"]
    for name, expected in hashes.items():
        actual = hashlib.sha256((folder / name).read_bytes()).hexdigest()
        if actual != expected:
            raise RuntimeError(
                f"app/prompts/{name} changed after manifest.toml recorded it. A prompt in use never "
                "changes: undo the edit, or save it as the next version and add that file to the manifest."
            )

    current = manifest["current"]
    for name in current.values():
        if name not in hashes:
            raise RuntimeError(f"app/prompts/manifest.toml uses {name} but has no sha256 for it.")

    models = ModelSettings.model_validate(tomllib.loads((folder / current["models"]).read_text(encoding="utf-8")))
    template = (folder / current["character"]).read_text(encoding="utf-8")
    if template.count(SPEC_PLACEHOLDER) != 1:
        raise RuntimeError(f"app/prompts/{current['character']} must hold {SPEC_PLACEHOLDER} exactly once.")
    return Prompts(
        models=models,
        models_version=Path(current["models"]).stem,
        character_template=template,
        character_version=Path(current["character"]).stem,
    )
