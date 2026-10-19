"""Settings (M6.5): the dialog where a creator picks the AI provider, pastes a
key, chooses the models, and sets the limits, with no file edits and no restart.

The values in force live in app/.env, which config.save_env writes, and in
memory, so a saved change applies to the next call. Each Save, each Test, each
preflight, and each server start whose settings differ from the last row adds
a dated app_settings row, and every model call's row names the row it ran with.
A key goes to app/.env and nowhere else: no response, row, or log holds it, and
the view says only whether one is saved and, for a long key, its last 4
characters.

Test tries the settings as typed, before they are saved: one tiny call to the
character's model on a trial gateway that shares the call spacing and the
daily count, with no retry and no fallback model. Each outcome comes back in
plain words with what to do next. The busy switch (M6's forced errors) lives
in memory only, so a restart turns it off.
"""

import asyncio
from collections.abc import Callable
from pathlib import Path
from typing import Any

from pydantic import SecretStr

from workbench import config, db, telemetry
from workbench.config import Prompts, Settings
from workbench.gateway import CallResult, CapReached, Gateway
from workbench.providers import Provider, ProviderError
from workbench.schemas import (
    API_KEY,
    BASE_URL,
    MODEL_ID,
    PROVIDERS,
    ConnectionCheck,
    KeyState,
    ModelOption,
    OllamaModels,
    ProviderMenus,
    SettingsDraft,
    SettingsView,
)

ROLE = "connection_test"
# What an app_settings row records, in the table's order. Never a key.
SNAPSHOT = (
    "provider",
    "base_url",
    "character_model",
    "judge_model",
    "calls_per_minute",
    "daily_call_cap",
    "force_model_error",
    "key_set",
    "models_version",
)
# The setting that holds each provider's key. Ollama and the fake model take none.
KEY_FIELDS = {"gemini": "gemini_api_key", "openai_compatible": "openai_compatible_api_key"}
# The settings the dialog changes. A change to the first group builds a new provider.
CONNECTION = ("workbench_provider", "openai_compatible_base_url", *KEY_FIELDS.values())
MANAGED = (
    *CONNECTION,
    "workbench_character_model",
    "workbench_judge_model",
    "workbench_calls_per_minute",
    "workbench_daily_call_cap",
)
# A key shows its last 4 characters only when it is at least this long.
LONG_KEY = 16
OLLAMA_START = "Ollama isn't running. Start it with OLLAMA_CONTEXT_LENGTH=32768 ollama serve, then press Check again."
OLLAMA_SERVE = "Start it with OLLAMA_CONTEXT_LENGTH=32768 ollama serve, then press Test again."
# Host names of a service on this computer.
THIS_COMPUTER = ("localhost", "127.0.0.1")


class SettingsInvalid(Exception):
    """A value in the dialog can't be saved or tested. field names the control to fix."""

    def __init__(self, message: str, field: str) -> None:
        super().__init__(message)
        self.field = field


class SettingsBusy(Exception):
    """A reply streams, or a check or re-check runs, so the settings can't change now."""


class SettingsLocked(Exception):
    """An environment variable sets a setting the save would change, and it wins over app/.env."""


# The app_settings rows.


def base_url(settings: Settings) -> str:
    """Where the provider's calls go. Empty for the fake model, which needs no network."""
    return {
        "gemini": settings.gemini_base_url,
        "ollama": settings.ollama_base_url,
        "openai_compatible": settings.openai_compatible_base_url,
    }.get(settings.workbench_provider, "")


def has_key(settings: Settings) -> bool:
    field = KEY_FIELDS.get(settings.workbench_provider)
    return bool(field and getattr(settings, field).get_secret_value())


def snapshot(settings: Settings, prompts: Prompts) -> dict[str, Any]:
    """The settings a row records: only whether the provider has a key, never the key."""
    models = prompts.models
    return {
        "provider": settings.workbench_provider,
        "base_url": base_url(settings),
        "character_model": config.character_model(settings, models),
        "judge_model": config.judge_model(settings, models),
        "calls_per_minute": settings.workbench_calls_per_minute,
        "daily_call_cap": settings.workbench_daily_call_cap,
        "force_model_error": settings.workbench_force_model_error,
        "key_set": int(has_key(settings)),
        "models_version": prompts.models_version,
    }


def changed_fields(before: dict[str, Any], after: dict[str, Any]) -> list[str]:
    return [field for field in SNAPSHOT if before[field] != after[field]]


def record(database: db.Database, values: dict[str, Any], *, source: str, session: str | None, changed: list[str]) -> int:
    """Adds one dated row and returns its ID."""
    marks = ", ".join("?" for _ in SNAPSHOT)
    with database.connect() as conn:
        return conn.execute(
            f"INSERT INTO app_settings (saved_at, session, source, changed, {', '.join(SNAPSHOT)}) VALUES (?, ?, ?, ?, {marks})",
            (telemetry.timestamp(telemetry.utc_now()), session, source, ", ".join(changed), *(values[field] for field in SNAPSHOT)),
        ).lastrowid


def latest(database: db.Database) -> dict[str, Any] | None:
    """The newest row that was in force, so any row but a Test's."""
    with database.connect() as conn:
        row = conn.execute("SELECT * FROM app_settings WHERE source != ? ORDER BY id DESC LIMIT 1", (ROLE,)).fetchone()
    return dict(row) if row is not None else None


def ensure_row(database: db.Database, settings: Settings, prompts: Prompts, source: str) -> int:
    """The newest row, when it holds these settings, or else a new one.

    A server start and preflight use it, so a hand edit of app/.env between
    runs gets a row of its own, while a plain restart adds none.
    """
    values = snapshot(settings, prompts)
    last = latest(database)
    if last is not None and not changed_fields(last, values):
        return last["id"]
    return record(database, values, source=source, session=None, changed=[] if last is None else changed_fields(last, values))


def _value(value: Any) -> str:
    """A setting as app/.env writes it."""
    return value.get_secret_value() if isinstance(value, SecretStr) else str(value)


def _seconds(value: float | None) -> str:
    if value is None:
        return "no time"
    return f"{value:g} {'second' if value == 1 else 'seconds'}"


def _host(url: str) -> str:
    return url.split("://", 1)[-1].split("/", 1)[0].split(":", 1)[0].lower()


class SettingsService:
    def __init__(
        self,
        database: db.Database,
        prompts: Prompts,
        gateway: Gateway,
        settings: Settings,
        *,
        env_file: Path,
        build_provider: Callable[[Settings], Provider],
        apply: Callable[[Settings, Provider], None],
        busy: Callable[[], bool],
        character_name: str,
    ) -> None:
        self.database = database
        self.prompts = prompts
        self.gateway = gateway
        # The settings in force. apply puts new ones in force in every service.
        self.settings = settings
        self.env_file = env_file
        self.build_provider = build_provider
        self.apply = apply
        self.busy = busy
        self.character_name = character_name

    def start(self) -> None:
        """Logs the settings the server starts with, when they differ from the last row."""
        self.gateway.app_settings_id = ensure_row(self.database, self.settings, self.prompts, "startup")

    # Reading.

    def _option(self, model_id: str, provider: str) -> ModelOption:
        return ModelOption(id=model_id, label=self.prompts.models.spec(model_id, provider).label)

    def _menus(self, provider: str, character: str, judge: str) -> ProviderMenus:
        """A provider's menus. The provider in force also lists its models when the models file doesn't."""
        models = self.prompts.models
        character_menu = models.character_models(provider)
        judge_menu = models.judge_menu(provider)
        default_character = character_menu[0] if character_menu else None
        default_judge = config.default_judge(models, provider, default_character) if default_character else None
        if provider == self.settings.workbench_provider:
            character_menu += [] if character in character_menu else [character]
            judge_menu += [] if judge in judge_menu else [judge]
        return ProviderMenus(
            provider=provider,
            character_models=[self._option(model_id, provider) for model_id in character_menu],
            judge_models=[self._option(model_id, provider) for model_id in judge_menu],
            default_character=default_character,
            default_judge=default_judge,
        )

    def view(self) -> SettingsView:
        settings, models = self.settings, self.prompts.models
        character = config.character_model(settings, models)
        judge = config.judge_model(settings, models)
        locked = config.environment_names(field.upper() for field in MANAGED)
        keys = {}
        for provider, field in KEY_FIELDS.items():
            key = getattr(settings, field).get_secret_value()
            keys[provider] = KeyState(saved=bool(key), last4=key[-4:] if len(key) >= LONG_KEY else None, locked=field.upper() in locked)
        with self.database.connect() as conn:
            row = conn.execute("SELECT saved_at FROM app_settings WHERE id = ?", (self.gateway.app_settings_id,)).fetchone()
        presets = self.prompts.presets
        return SettingsView(
            character_name=self.character_name,
            provider=settings.workbench_provider,
            providers=[self._menus(provider, character, judge) for provider in PROVIDERS],
            base_url=settings.openai_compatible_base_url,
            presets=presets.presets,
            gemini_key_prefixes=presets.gemini_key_prefixes,
            keys=keys,
            character_model=character,
            judge_model=judge,
            calls_per_minute=settings.workbench_calls_per_minute,
            daily_call_cap=settings.workbench_daily_call_cap,
            max_calls_per_minute=models.limits.calls_per_minute,
            max_daily_call_cap=models.limits.daily_call_cap,
            used_today=self.gateway.used_today(),
            simulate_busy=settings.workbench_force_model_error != "off",
            force_mode=settings.workbench_force_model_error,
            locked=sorted(locked),
            settings_id=self.gateway.app_settings_id or 0,
            saved_at=row["saved_at"] if row is not None else "",
        )

    # Checking what the dialog sends.

    def _changes(self, draft: SettingsDraft) -> dict[str, Any]:
        """The settings the draft sets, checked, by field name. Raises SettingsInvalid naming the control to fix."""
        models = self.prompts.models
        provider = draft.provider
        changes: dict[str, Any] = {"workbench_provider": provider}
        if provider == "openai_compatible":
            url = draft.base_url.strip()
            if not url:
                raise SettingsInvalid("Pick a service, or type its base URL, like https://api.example.com/v1.", "base_url")
            if not BASE_URL.fullmatch(url):
                raise SettingsInvalid(
                    "That base URL won't work. It starts with https://, or http:// for a service on this computer, "
                    "and holds no password, key, ?, or #.",
                    "base_url",
                )
            changes["openai_compatible_base_url"] = url
        key = (draft.api_key or "").strip()
        if key and provider in KEY_FIELDS:
            if not API_KEY.fullmatch(key):
                raise SettingsInvalid("That key has a space or a character keys don't use. Copy the key again and paste it.", "api_key")
            changes[KEY_FIELDS[provider]] = SecretStr(key)

        roles = (
            ("character_model", draft.character_model.strip(), models.character_models(provider), f"{self.character_name}'s model"),
            ("judge_model", draft.judge_model.strip(), models.judge_menu(provider), "the judge's model"),
        )
        for field, value, menu, name in roles:
            if not value:
                verb = "Type" if provider == "openai_compatible" else "Pick"
                raise SettingsInvalid(f"{verb} {name}.", field)
            if value not in models.models and not MODEL_ID.fullmatch(value):
                raise SettingsInvalid("That model ID has a space or a character model IDs don't use.", field)
            if not config.can_pick(models, provider, menu, value):
                raise SettingsInvalid(f"Pick {name} from its menu.", field)
            changes[f"workbench_{field}"] = value

        bounds = models.limits
        if not 1 <= draft.calls_per_minute <= bounds.calls_per_minute:
            raise SettingsInvalid(
                f"Calls per minute can be 1 to {bounds.calls_per_minute}. Gemini's free tier allows {bounds.calls_per_minute}.",
                "calls_per_minute",
            )
        if not 1 <= draft.daily_call_cap <= bounds.daily_call_cap:
            raise SettingsInvalid(
                f"The daily cap can be 1 to {bounds.daily_call_cap}, Google's daily limit for each model.", "daily_call_cap"
            )
        changes["workbench_calls_per_minute"] = draft.calls_per_minute
        changes["workbench_daily_call_cap"] = draft.daily_call_cap
        return changes

    def _to_write(self, changes: dict[str, Any]) -> dict[str, Any]:
        """The changes app/.env needs: the values that differ from the settings in force.

        The two models are written only when the provider or either model
        changes, and then both, so a save of the limits never pins a model
        that was a default.
        """
        current, models = self.settings, self.prompts.models
        written = {
            field: value
            for field, value in changes.items()
            if field not in ("workbench_character_model", "workbench_judge_model") and _value(getattr(current, field)) != _value(value)
        }
        now = (current.workbench_provider, config.character_model(current, models), config.judge_model(current, models))
        wanted = (changes["workbench_provider"], changes["workbench_character_model"], changes["workbench_judge_model"])
        if wanted != now:
            for field in ("workbench_character_model", "workbench_judge_model"):
                if getattr(current, field) != changes[field]:
                    written[field] = changes[field]
        return written

    def _force(self, simulate_busy: bool) -> str:
        """M6's forced-error mode for the busy switch: primary when it's on, or all when app/.env set that."""
        if not simulate_busy:
            return "off"
        current = self.settings.workbench_force_model_error
        return current if current != "off" else "primary"

    # Saving.

    async def save(self, draft: SettingsDraft, session: str | None) -> SettingsView:
        """Writes the changes to app/.env and puts them in force, then logs a row."""
        if self.busy():
            raise SettingsBusy("A reply or a check is running. Save when it ends, or press Stop first.")
        changes = self._changes(draft)
        written = self._to_write(changes)
        locked = sorted(config.environment_names(field.upper() for field in written))
        if locked:
            one = len(locked) == 1
            raise SettingsLocked(
                f"{' and '.join(locked)} {'is' if one else 'are'} set in the shell that started the server, which wins "
                f"over Settings. Change {'it' if one else 'them'} there, or unset {'it' if one else 'them'} and restart app/run.sh."
            )
        force = self._force(draft.simulate_busy)
        if not written and force == self.settings.workbench_force_model_error:
            return self.view()

        if written:
            config.save_env({field.upper(): _value(value) for field, value in written.items()}, self.env_file)
        before = snapshot(self.settings, self.prompts)
        settings = self.settings.model_copy(update={**written, "workbench_force_model_error": force})
        old = self.gateway.provider
        provider = self.build_provider(settings) if any(field in written for field in CONNECTION) else old
        self.apply(settings, provider)
        self.settings = settings
        if provider is not old:
            await old.aclose()
        after = snapshot(settings, self.prompts)
        changed = changed_fields(before, after) + (["key"] if any(field in written for field in KEY_FIELDS.values()) else [])
        self.gateway.app_settings_id = record(self.database, after, source="settings", session=session, changed=changed)
        return self.view()

    # Testing.

    async def test(self, draft: SettingsDraft, session: str | None) -> ConnectionCheck:
        """One tiny call to the character's model with the settings as typed. Saves nothing but its row."""
        models = self.prompts.models
        changes = self._changes(draft)
        # The busy switch is left out, so the test shows the real connection.
        trial = self.settings.model_copy(update={**changes, "workbench_force_model_error": "off"})
        provider_name = trial.workbench_provider
        model_id = config.character_model(trial, models)
        label = models.spec(model_id, provider_name).label
        if provider_name == "gemini" and not trial.gemini_api_key.get_secret_value():
            return ConnectionCheck(
                ok=False,
                message="There's no Gemini key yet.",
                next="Get a free key at aistudio.google.com, paste it here, and press Test again.",
                model=model_id,
                model_label=label,
                seconds=None,
            )

        before = {**snapshot(self.settings, self.prompts), "force_model_error": "off"}
        after = snapshot(trial, self.prompts)
        key_field = KEY_FIELDS.get(provider_name)
        new_key = key_field in changes and _value(changes[key_field]) != _value(getattr(self.settings, key_field))
        changed = changed_fields(before, after) + (["key"] if new_key else [])
        row_id = record(self.database, after, source=ROLE, session=session, changed=changed)
        provider = self.build_provider(trial)
        try:
            call = self.gateway.trial(trial, provider, row_id).call(
                role=ROLE,
                model_id=model_id,
                messages=[{"role": "user", "content": self.prompts.connection_test_template.strip()}],
                prompt_version=self.prompts.connection_test_version,
                session=session,
                stop=asyncio.Event(),
                allow_fallback=False,
                retries=0,
            )
            async for _ in call.events():
                pass
        except CapReached as error:
            return ConnectionCheck(
                ok=False,
                message=str(error),
                next="Raise the daily cap under Limits and save, or test again after midnight Pacific time.",
                model=model_id,
                model_label=label,
                seconds=None,
            )
        finally:
            if provider is not self.gateway.provider:
                await provider.aclose()
        return self._outcome(trial, call.result, model_id, label, unsaved=bool(changed))

    def _service(self, settings: Settings) -> str:
        """The provider's name at the start of a sentence."""
        provider = settings.workbench_provider
        if provider == "openai_compatible":
            preset = self.prompts.presets.match(settings.openai_compatible_base_url)
            return preset.label if preset is not None else "The service"
        return {"gemini": "Gemini", "ollama": "Ollama", "fake": "The fake model"}[provider]

    def _outcome(self, trial: Settings, result: CallResult, model_id: str, label: str, *, unsaved: bool) -> ConnectionCheck:
        """What the test found, and what to do next, in plain words."""
        provider = trial.workbench_provider
        service = self._service(trial)
        seconds = None if result.latency_ms is None else round(result.latency_ms / 1000, 1)

        def check(ok: bool, message: str, next_step: str) -> ConnectionCheck:
            return ConnectionCheck(ok=ok, message=message, next=next_step, model=model_id, model_label=label, seconds=seconds)

        if result.status == "ok":
            if provider == "fake":
                return check(
                    True,
                    f"The fake model answered in {_seconds(seconds)}, with no network.",
                    "Press Save to use it. Runs then get canned replies, and the AI judge finds nothing."
                    if unsaved
                    else "It's the model in use now.",
                )
            return check(
                True,
                f"Connected. {label} answered in {_seconds(seconds)}.",
                "Press Save to use these settings." if unsaved else "These are the settings in use now.",
            )
        if result.status == "timeout" or result.kind == "timeout":
            return check(
                False,
                f"{service} didn't start answering within {trial.workbench_first_token_timeout_seconds:g} seconds.",
                "Press Test again in a minute. A local model can take longer the first time it loads.",
            )
        if result.status == "empty":
            return check(False, f"{label} answered with nothing.", "Press Test again, or pick another model.")

        kind = result.kind
        if kind == "auth":
            if provider == "gemini":
                return check(
                    False,
                    "Gemini didn't accept this key.",
                    "Copy the key again from aistudio.google.com, with nothing extra like a space, paste it here, and press Test again.",
                )
            return check(
                False,
                f"{service} didn't accept this key.",
                "Copy the key again from the service's website, paste it here, and press Test again.",
            )
        if kind == "rate_limited":
            if provider == "gemini":
                return check(
                    False,
                    "Gemini says its free limit was reached.",
                    "Wait a minute and press Test again. If it keeps happening, today's free quota may be used up. "
                    "It starts over at midnight Pacific time.",
                )
            return check(False, f"{service} says its limit was reached.", "Wait a minute and press Test again.")
        if kind == "not_found":
            if provider == "ollama":
                return check(
                    False,
                    f"Ollama doesn't have {model_id} installed.",
                    f"Install it with ollama pull {model_id}, or pick a model Ollama has installed.",
                )
            if provider == "openai_compatible":
                return check(
                    False,
                    f"{service} doesn't know the model {model_id}.",
                    "Check the model ID on the service's website, type it again, and press Test again.",
                )
            return check(False, f"{service} doesn't know {model_id}.", "Pick another model and press Test again.")
        if kind == "connection":
            if provider == "ollama":
                return check(False, "Ollama isn't running.", OLLAMA_SERVE)
            if provider == "openai_compatible":
                address = trial.openai_compatible_base_url
                if _host(address) in THIS_COMPUTER:
                    return check(False, f"Couldn't reach {address}.", "Check that the service is running on this computer, then press Test again.")
                return check(False, f"Couldn't reach {address}.", "Check the address and the internet connection, then press Test again.")
            return check(False, "Couldn't reach Google.", "Check the internet connection and press Test again.")
        if kind == "server":
            return check(False, f"{service} had a problem on its side.", "Press Test again in a minute.")
        if kind == "bad_request":
            status = (result.detail or "").split(":", 1)[0] or "an error"
            if provider == "openai_compatible":
                return check(
                    False,
                    f"{service} refused the request ({status}).",
                    "Check the base URL, which usually ends in /v1, and the model ID, then press Test again.",
                )
            return check(False, f"{service} refused the request ({status}).", "Press Test again. If it keeps failing, pick another model.")
        return check(False, f"{service} sent an error partway through.", "Press Test again.")

    # Ollama's installed models.

    async def ollama_models(self) -> OllamaModels:
        """What Ollama has installed, at OLLAMA_BASE_URL. It lists models and makes no model call."""
        provider = self.build_provider(self.settings.model_copy(update={"workbench_provider": "ollama"}))
        try:
            installed = sorted(set(await provider.list_models()))
        except ProviderError as error:
            if error.kind in ("connection", "timeout"):
                return OllamaModels(running=False, models=[], missing=[], message=OLLAMA_START)
            return OllamaModels(
                running=False,
                models=[],
                missing=[],
                message="Ollama didn't list its models. Check that it's up to date, then press Check again.",
            )
        finally:
            if provider is not self.gateway.provider:
                await provider.aclose()
        missing = [model_id for model_id in self.prompts.models.character_models("ollama") if model_id not in installed]
        if not installed:
            message = "Ollama is running, but it has no models installed yet."
        else:
            message = f"Ollama is running with {len(installed)} installed {'model' if len(installed) == 1 else 'models'}."
        return OllamaModels(running=True, models=installed, missing=missing, message=message)
