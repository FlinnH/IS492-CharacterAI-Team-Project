"""Settings and prompts for the workbench.

This module is the only reader of environment variables and of the files in
app/prompts/, and the only writer of app/.env. Every setting is listed in
app/.env.example, and none has a default in code. Values load from
app/.env.example first, then app/.env, then environment variables, and the
last one wins. Model IDs, reasoning effort, token limits, and prices come from
the models file that app/prompts/manifest.toml names. The Settings dialog
(M6.5) saves the creator's changes to app/.env with save_env.
"""

import hashlib
import json
import os
import re
import tomllib
from collections.abc import Iterable, Mapping
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Literal

from dotenv import dotenv_values, set_key
from pydantic import Field, NonNegativeInt, PositiveFloat, PositiveInt, SecretStr, ValidationInfo, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

from workbench.schemas import (
    BASE_URL,
    MODEL_ID,
    JudgeOutput,
    ModelSettings,
    Presets,
    ProviderName,
    RecheckOutput,
    inline_refs,
)

APP_DIR = Path(__file__).resolve().parent.parent
EXAMPLE_FILE = APP_DIR / ".env.example"
ENV_FILE = APP_DIR / ".env"
PROMPTS_DIR = APP_DIR / "prompts"

# The character prompt holds this once, and the rendered spec replaces it.
SPEC_PLACEHOLDER = "{spec}"

# The settings that hold a key. app/.env.example leaves them empty.
KEY_SETTINGS = ("gemini_api_key", "openai_compatible_api_key")

# What save_env writes: no spaces, quotes, #, backslashes, or line breaks, so a
# value can never end its line and start another setting or a comment.
ENV_VALUE = re.compile(r"[A-Za-z0-9._~+/=:@%-]*")


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
    workbench_provider: ProviderName
    gemini_api_key: SecretStr
    gemini_base_url: str = Field(pattern=r"^https?://")
    ollama_base_url: str = Field(pattern=r"^https?://")
    # Another OpenAI-compatible service (M6.5): its address and key.
    openai_compatible_base_url: str = Field(max_length=300)
    openai_compatible_api_key: SecretStr
    # The models Settings picked (M6.5). Empty uses the models file's defaults.
    workbench_character_model: str = Field(max_length=300)
    workbench_judge_model: str = Field(max_length=300)
    workbench_daily_call_cap: PositiveInt
    workbench_calls_per_minute: PositiveInt
    workbench_session_run_limit: PositiveInt
    workbench_session_judge_limit: PositiveInt
    workbench_retries: NonNegativeInt
    workbench_retry_backoff_seconds: PositiveFloat
    workbench_force_model_error: Literal["off", "primary", "all"]
    workbench_first_token_timeout_seconds: PositiveFloat
    workbench_judge_timeout_seconds: PositiveFloat
    workbench_max_typed_chars: PositiveInt
    workbench_max_import_chars: PositiveInt
    workbench_seeded_transcript_path: Path

    # The provider is checked before these fields, so info.data holds it when it is valid.

    @field_validator("openai_compatible_base_url")
    @classmethod
    def base_url_holds_no_secret(cls, value: str, info: ValidationInfo) -> str:
        if value and not BASE_URL.fullmatch(value):
            raise ValueError("must be an http or https address with no user, password, query, or fragment")
        if not value and info.data.get("workbench_provider") == "openai_compatible":
            raise ValueError("is needed when WORKBENCH_PROVIDER is openai_compatible")
        return value

    @field_validator("workbench_character_model", "workbench_judge_model")
    @classmethod
    def model_id_or_empty(cls, value: str, info: ValidationInfo) -> str:
        if value and not MODEL_ID.fullmatch(value):
            raise ValueError("isn't a model ID")
        if not value and info.data.get("workbench_provider") == "openai_compatible":
            raise ValueError("is needed when WORKBENCH_PROVIDER is openai_compatible")
        return value


def example_values() -> dict[str, str]:
    """The settings in app/.env.example, keyed by field name."""
    return {name.lower(): value or "" for name, value in dotenv_values(EXAMPLE_FILE).items()}


def load_settings(env_file: Path = ENV_FILE) -> Settings:
    """Settings for the running app. Refuses a key in the example file."""
    example = example_values()
    for name in KEY_SETTINGS:
        if example.get(name):
            raise RuntimeError(
                f"app/.env.example has a value for {name.upper()}. "
                "Move the key to app/.env and leave the example empty."
            )
    return Settings(_env_file=(EXAMPLE_FILE, env_file))


def save_env(values: Mapping[str, str], path: Path | str = ENV_FILE) -> None:
    """Writes settings into app/.env, keeping its other lines and comments.

    Each name must be a setting, and each value one that Settings checked. An
    error names the setting, never the value, since the value may be a key.
    Each write replaces the file whole, so a crash never leaves half a line.
    """
    path = Path(path)
    known = {name.upper() for name in Settings.model_fields}
    for name, value in values.items():
        if name not in known:
            raise ValueError(f"{name} isn't a setting in app/.env.example.")
        if not ENV_VALUE.fullmatch(value):
            raise ValueError(f"The value for {name} has a character app/.env can't hold.")
    for name, value in values.items():
        set_key(path, name, value, quote_mode="never")
    # The file may hold a key, so only its owner may read it.
    path.chmod(0o600)


def environment_names(names: Iterable[str]) -> set[str]:
    """The settings among names that an environment variable sets.

    They win over app/.env, so Settings can't change them. Names only: no
    value is read here.
    """
    present = {key.upper() for key in os.environ}
    return {name for name in names if name.upper() in present}


def app_path(path: Path) -> Path:
    """A settings path, with a relative one counted from app/, as .env.example says."""
    path = Path(path).expanduser()
    return path if path.is_absolute() else APP_DIR / path


# Which models serve. The models file holds the menus and the defaults, and
# Settings picks among them, or types a model for a provider whose models
# needn't be listed (Ollama's installed models, another OpenAI-compatible service).


def can_pick(models: ModelSettings, provider: str, menu: list[str], model_id: str) -> bool:
    """Whether Settings may pick this model: one in the menu, or, for a provider
    whose models needn't be listed, one the models file doesn't list at all."""
    return model_id in menu or (model_id not in models.models and provider in models.unlisted.providers)


def character_model(settings: Settings, models: ModelSettings) -> str:
    """The model that plays the character: the one Settings picked, or else the first in the provider's menu."""
    provider = settings.workbench_provider
    menu = models.character_models(provider)
    chosen = settings.workbench_character_model
    if chosen and can_pick(models, provider, menu, chosen):
        return chosen
    return menu[0] if menu else chosen


def default_judge(models: ModelSettings, provider: str, character: str) -> str | None:
    """The judge a fresh choice starts from: the models file's judge, or another
    model of the provider when that one also plays the character."""
    default = models.judge_model(provider)
    if default is not None and default == character:
        return next((model_id for model_id in models.judge_menu(provider) if model_id != character), default)
    return default


def judge_model(settings: Settings, models: ModelSettings) -> str:
    """The AI judge's model: the one Settings picked, or else the default judge."""
    provider = settings.workbench_provider
    chosen = settings.workbench_judge_model
    if chosen and can_pick(models, provider, models.judge_menu(provider), chosen):
        return chosen
    return default_judge(models, provider, character_model(settings, models)) or chosen


def run_menu(settings: Settings, models: ModelSettings) -> list[str]:
    """The Model menu on Run a conversation: the provider's menu, then the
    model Settings picked when the models file doesn't list it."""
    menu = models.character_models(settings.workbench_provider)
    chosen = character_model(settings, models)
    return menu if chosen in menu else [*menu, chosen]


@dataclass(frozen=True)
class Prompts:
    """The prompt files in use. A version is its file name without the extension, like models.v1."""

    models: ModelSettings
    models_version: str
    character_template: str
    character_version: str
    judge_template: str
    judge_version: str
    # The JSON schema every judge answer must match, sent with each judge call.
    judge_schema: dict[str, Any]
    judge_schema_version: str
    # The follow-up re-check, which the judge's model answers with its own prompt and schema.
    recheck_template: str
    recheck_version: str
    recheck_schema: dict[str, Any]
    recheck_schema_version: str
    # Test in Settings sends this, alone, to the character's model (M6.5).
    connection_test_template: str
    connection_test_version: str
    # The services Settings offers for another OpenAI-compatible service (M6.5).
    presets: Presets
    presets_version: str


def _answer_schema(folder: Path, name: str, output: type) -> dict[str, Any]:
    """A schema file that must be output's schema written out. Each answer is
    checked against output, so a schema that differs would fail valid answers."""
    schema = json.loads((folder / name).read_text(encoding="utf-8"))
    if schema != inline_refs(output.model_json_schema()):
        raise RuntimeError(
            f"app/prompts/{name} doesn't match schemas.{output.__name__}. Save the model's schema "
            "as the next version and point the manifest at it."
        )
    return schema


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
        judge_template=(folder / current["judge"]).read_text(encoding="utf-8"),
        judge_version=Path(current["judge"]).stem,
        judge_schema=_answer_schema(folder, current["judge_schema"], JudgeOutput),
        judge_schema_version=Path(current["judge_schema"]).stem,
        recheck_template=(folder / current["recheck"]).read_text(encoding="utf-8"),
        recheck_version=Path(current["recheck"]).stem,
        recheck_schema=_answer_schema(folder, current["recheck_schema"], RecheckOutput),
        recheck_schema_version=Path(current["recheck_schema"]).stem,
        connection_test_template=(folder / current["connection_test"]).read_text(encoding="utf-8"),
        connection_test_version=Path(current["connection_test"]).stem,
        presets=Presets.model_validate(tomllib.loads((folder / current["presets"]).read_text(encoding="utf-8"))),
        presets_version=Path(current["presets"]).stem,
    )
