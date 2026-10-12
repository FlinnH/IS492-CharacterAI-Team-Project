"""M2 prompt tests: the prompt files load, match their recorded hashes, and the
character prompt is the spec alone."""

import hashlib
import shutil
import tomllib

import pytest

from conftest import APP_DIR
from workbench import config
from workbench.config import SPEC_PLACEHOLDER, load_prompts

PROMPTS_DIR = APP_DIR / "prompts"


def test_prompts_load_and_match_the_manifest():
    prompts = load_prompts()
    # models.v2 switched the character to minimal reasoning effort; v1 stays for history.
    assert (prompts.models_version, prompts.character_version) == ("models.v2", "character.v1")

    manifest = tomllib.loads((PROMPTS_DIR / "manifest.toml").read_text(encoding="utf-8"))
    for name, expected in manifest["sha256"].items():
        assert hashlib.sha256((PROMPTS_DIR / name).read_bytes()).hexdigest() == expected, name
    assert set(manifest["current"].values()) <= set(manifest["sha256"])


def copy_prompts(tmp_path):
    folder = tmp_path / "prompts"
    shutil.copytree(PROMPTS_DIR, folder)
    return folder


def test_a_changed_prompt_is_refused(tmp_path):
    folder = copy_prompts(tmp_path)
    with (folder / "character.v1.md").open("a", encoding="utf-8") as file:
        file.write("Stay calm.\n")
    with pytest.raises(RuntimeError, match="character.v1.md changed"):
        load_prompts(folder)


@pytest.mark.parametrize("template", ["No placeholder here.\n", f"{SPEC_PLACEHOLDER}\n{SPEC_PLACEHOLDER}\n"], ids=["none", "twice"])
def test_the_character_prompt_holds_the_spec_exactly_once(tmp_path, template):
    folder = copy_prompts(tmp_path)
    (folder / "character.v1.md").write_text(template, encoding="utf-8")
    manifest = (folder / "manifest.toml").read_text(encoding="utf-8")
    old = tomllib.loads(manifest)["sha256"]["character.v1.md"]
    new = hashlib.sha256(template.encode("utf-8")).hexdigest()
    (folder / "manifest.toml").write_text(manifest.replace(old, new), encoding="utf-8")
    with pytest.raises(RuntimeError, match="exactly once"):
        load_prompts(folder)


def test_character_v1_is_the_spec_alone():
    # The CP2 baseline: the character gets the rendered spec and nothing else.
    assert load_prompts().character_template.strip() == SPEC_PLACEHOLDER


def test_every_model_menu_names_a_model_of_its_provider():
    models = load_prompts().models
    for provider in ("gemini", "ollama", "fake"):
        menu = models.character_models(provider)
        assert menu, provider
        assert all(models.models[model_id].provider == provider for model_id in menu)
    # Temperature is never set: newer Gemini models ignore it.
    assert all("temperature" not in spec.model_dump() for spec in models.models.values())


def test_the_preflight_scenario_exists():
    from workbench import transcripts

    check = load_prompts().models.preflight
    scenario = next(s for s in transcripts.load_scenarios().scenarios if s.id == check.scenario)
    assert len(scenario.lines) >= check.turns


def test_config_is_the_only_reader_of_the_prompts_folder():
    assert config.PROMPTS_DIR == PROMPTS_DIR
