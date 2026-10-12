"""M2 and M3 prompt tests: the prompt files load and match their recorded
hashes, the character prompt is the spec alone, and the judge's prompt,
schema, and reasoning effort are its own."""

import hashlib
import json
import re
import shutil
import tomllib

import pytest

from conftest import APP_DIR
from workbench import config
from workbench.config import SPEC_PLACEHOLDER, load_prompts
from workbench.schemas import JudgeOutput, inline_refs

PROMPTS_DIR = APP_DIR / "prompts"


def test_prompts_load_and_match_the_manifest():
    prompts = load_prompts()
    # models.v2 switched the character to minimal reasoning effort, and models.v3
    # added the judge; v1 and v2 stay for history.
    assert (prompts.models_version, prompts.character_version) == ("models.v3", "character.v1")
    assert (prompts.judge_version, prompts.judge_schema_version) == ("judge.v1", "judge.schema.v1")

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


def test_the_judge_schema_file_is_the_models_schema_written_out():
    text = (PROMPTS_DIR / "judge.schema.v1.json").read_text(encoding="utf-8")
    assert json.loads(text) == inline_refs(JudgeOutput.model_json_schema()) == load_prompts().judge_schema
    # Gemini's structured output doesn't list $defs, so nothing points elsewhere.
    assert "$ref" not in text and "$defs" not in text
    assert text.isascii()


def test_a_judge_schema_that_drifts_from_the_model_is_refused(tmp_path):
    folder = copy_prompts(tmp_path)
    schema = json.loads((folder / "judge.schema.v1.json").read_text(encoding="utf-8"))
    del schema["properties"]["not_checked"]
    changed = json.dumps(schema, indent=2) + "\n"
    (folder / "judge.schema.v1.json").write_text(changed, encoding="utf-8")
    manifest = (folder / "manifest.toml").read_text(encoding="utf-8")
    old = tomllib.loads(manifest)["sha256"]["judge.schema.v1.json"]
    new = hashlib.sha256(changed.encode("utf-8")).hexdigest()
    (folder / "manifest.toml").write_text(manifest.replace(old, new), encoding="utf-8")
    with pytest.raises(RuntimeError, match="doesn't match schemas.JudgeOutput"):
        load_prompts(folder)


def test_the_judge_prompt_names_no_line_and_no_character():
    # The judge reviews any character's chat against that chat's own spec.
    text = load_prompts().judge_template
    spec = json.loads((APP_DIR / "samples" / "spec_v1.json").read_text(encoding="utf-8"))
    line_ids = [line["id"] for section in spec["body"]["sections"] for line in section["lines"]]
    assert [line_id for line_id in line_ids if re.search(rf"\b{line_id}\b", text)] == []
    assert not re.search(r"Harry|Alex|Hogwarts|Umbridge", text)
    assert SPEC_PLACEHOLDER not in text


def test_the_judge_has_its_own_effort_low_or_higher():
    raw = tomllib.loads((PROMPTS_DIR / f"{load_prompts().models_version}.toml").read_text(encoding="utf-8"))
    # Set in the judge's own section, never borrowed from a character model.
    assert raw["judge"]["reasoning_effort"] in ("low", "medium", "high")
    models = load_prompts().models
    for provider in ("gemini", "ollama", "fake"):
        assert models.models[models.judge_model(provider)].provider == provider
