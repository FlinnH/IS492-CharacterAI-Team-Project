"""Preflight: checks the model setup with real calls, before a demo or a live test.

Run it from the repo root with the server stopped (call spacing is per process):

    app/.venv/bin/python app/scripts/preflight.py

For each model in the Model menu of the provider in app/.env, it checks that
the service lists the model, then runs the first turns of the preflight
scenario as one chat for each reasoning effort in the models file. Earlier
replies go back as plain assistant text, the way the Run screen sends them.
Every call is logged in the database like any other (role "preflight") and
counts toward the daily cap. It prints no chat text. It exits 1 if a model
fails with the reasoning effort the models file sets for it, and when a model
in the Model menu, or the AI judge's model, looks retired or rerouted: the
service no longer lists it, or a reply says another model wrote it. A busy
model is retried like any call, but never swapped for its fallback model, so
each model's numbers stay its own.
"""

import asyncio
import statistics
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from workbench import app_settings, db, specs, transcripts  # noqa: E402
from workbench.config import SPEC_PLACEHOLDER, judge_model, load_prompts, load_settings  # noqa: E402
from workbench.gateway import CapReached, Gateway, Wait  # noqa: E402
from workbench.limiter import Limiter  # noqa: E402
from workbench.providers import ProviderError, build  # noqa: E402

ROLE = "preflight"


def table(rows: list[list[str]]) -> str:
    widths = [max(len(row[i]) for row in rows) for i in range(len(rows[0]))]
    lines = ["  ".join(cell.ljust(width) for cell, width in zip(row, widths)).rstrip() for row in rows]
    lines.insert(1, "  ".join("-" * width for width in widths))
    return "\n".join(lines)


def model_problems(model_ids, listed: set[str] | None, reported: dict[str, set[str]]) -> list[str]:
    """A plain line for each model that looks retired or rerouted.

    listed is None when the service's model list couldn't be read, so nothing
    is said about it. reported maps a model to the names its replies gave. A
    name that only adds to the one asked for, like a dated version, is the
    same model. Any other name means the service sends the model's calls to
    another one, as Google did when it rerouted gemini-3.5-flash to 3.6.
    """
    problems = []
    for model_id in model_ids:
        if listed is not None and model_id not in listed:
            problems.append(f"{model_id} isn't in the service's model list any more, so it may be retired.")
        for name in sorted(reported.get(model_id, ())):
            if not name.startswith(model_id):
                problems.append(f"{model_id} was answered by {name}, so the service reroutes it.")
    return problems


async def run_chat(gateway, prompts, system, lines, model_id, effort) -> dict:
    """One chat of the preflight turns. Stops at the first turn that fails."""
    messages = [{"role": "system", "content": system}]
    outcome = {"ok": 0, "ttft": [], "input": 0, "output": 0, "thinking": 0, "reported": set(), "error": ""}
    for line in lines:
        messages.append({"role": "user", "content": line.text})
        call = gateway.call(
            role=ROLE,
            model_id=model_id,
            messages=messages,
            prompt_version=prompts.character_version,
            session=None,
            stop=asyncio.Event(),
            turn=line.turn,
            reasoning_effort=effort,
            allow_fallback=False,
        )
        async for event in call.events():
            if isinstance(event, Wait) and event.reason == "retry":
                print(f"  the model is busy, trying again in {event.seconds:.1f} s", flush=True)
            elif isinstance(event, Wait):
                print(f"  waiting {event.seconds:.1f} s for the next call slot", flush=True)
        result = call.result
        if result.status != "ok":
            outcome["error"] = result.detail or result.status
            break
        outcome["ok"] += 1
        if result.ttft_ms is not None:
            outcome["ttft"].append(result.ttft_ms)
        if result.usage is not None:
            outcome["input"] += result.usage.input_tokens
            outcome["output"] += result.usage.output_tokens
            outcome["thinking"] += result.usage.reasoning_tokens
        if result.model_reported:
            outcome["reported"].add(result.model_reported)
        messages.append({"role": "assistant", "content": result.text})
    return outcome


async def main() -> int:
    settings = load_settings()
    prompts = load_prompts()
    provider_name = settings.workbench_provider
    if provider_name == "fake":
        print("WORKBENCH_PROVIDER is fake, so there is no model service to check.")
        return 0
    if settings.workbench_force_model_error != "off":
        print("WORKBENCH_FORCE_MODEL_ERROR is on in app/.env. Set it to off first: preflight times real calls.")
        return 1

    provider = build(settings, prompts.presets)
    print(f"Provider: {provider_name}. Key set: {'yes' if provider.ready else 'no'}.")
    if not provider.ready:
        print("There's no Gemini key yet. Add one in Settings in the workbench first.")
        return 1

    database = db.Database(settings.workbench_db_path)
    with database.connect() as conn:
        db.migrate(conn)
    specs.seed(database)
    limiter = Limiter(settings.workbench_calls_per_minute, settings.workbench_daily_call_cap, prompts.models.quota_timezone)
    gateway = Gateway(database, settings, prompts, provider, limiter)
    # Its calls name the settings they ran with, like the server's.
    gateway.app_settings_id = app_settings.ensure_row(database, settings, prompts, "preflight")

    check = prompts.models.preflight
    scenarios = transcripts.load_scenarios()
    scenario = next(s for s in scenarios.scenarios if s.id == check.scenario)
    lines = scenario.lines[: check.turns]
    spec = specs.get_spec(database, scenarios.character, check.spec_version)
    system = prompts.character_template.replace(SPEC_PLACEHOLDER, specs.render_text(spec.body)).strip()
    model_ids = prompts.models.character_models(provider_name)
    # The judge's model is listed too, since a reset's judge snapshot and every check depend on it.
    checked_ids = [model_id for model_id in dict.fromkeys([*model_ids, judge_model(settings, prompts.models)]) if model_id]

    try:
        listed = set(await provider.list_models())
    except ProviderError as error:
        print(f"Listing models failed: {error.detail}")
        listed = None
    for model_id in checked_ids:
        state = "unknown" if listed is None else ("listed" if model_id in listed else "NOT LISTED")
        print(f"Model {model_id}: {state}.")

    print(
        f"\nRunning {check.scenario} turns {lines[0].turn} to {lines[-1].turn} on spec v{check.spec_version}, "
        f"once per model and effort. Calls start {60 / settings.workbench_calls_per_minute:g} s apart.",
        flush=True,
    )
    rows = [["Model", "Effort", "Turns OK", "Median TTFT", "Tokens in/out/thinking", "Model reported", "Error"]]
    failed_configured = False
    reported: dict[str, set[str]] = {}
    try:
        for model_id in model_ids:
            configured = prompts.models.models[model_id].reasoning_effort
            for effort in check.reasoning_efforts:
                print(f"{model_id}, {effort}:", flush=True)
                outcome = await run_chat(gateway, prompts, system, lines, model_id, effort)
                reported.setdefault(model_id, set()).update(outcome["reported"])
                median = f"{statistics.median(outcome['ttft']):.0f} ms" if outcome["ttft"] else "-"
                label = f"{effort} (configured)" if effort == configured else effort
                rows.append(
                    [
                        model_id,
                        label,
                        f"{outcome['ok']} of {len(lines)}",
                        median,
                        f"{outcome['input']}/{outcome['output']}/{outcome['thinking']}",
                        ", ".join(sorted(outcome["reported"])) or "-",
                        outcome["error"] or "-",
                    ]
                )
                if effort == configured and outcome["ok"] < len(lines):
                    failed_configured = True
    except CapReached as error:
        print(str(error))
        return 1
    finally:
        await provider.aclose()

    print()
    print(table(rows))
    print(f"\nCalls today on {provider_name}, counting these: {gateway.used_today()} of {settings.workbench_daily_call_cap}.")
    problems = model_problems(checked_ids, listed, reported)
    for problem in problems:
        print(problem)
    if problems:
        print("Pick another model in Settings, or save a models version that drops it.")
    if failed_configured:
        print("A model failed with the reasoning effort the models file sets for it.")
    return 1 if failed_configured or problems else 0


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
