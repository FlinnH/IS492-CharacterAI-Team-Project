"""The stronger model writes the other person's lines for a test case.

It reads the character spec that is loaded now, and the job of the test case
(a normal chat, a long memory chat, an emotional shift, a persona challenge,
a knowledge-boundary chat, both long mixes, or a case the creator describes).
The character model then plays those lines. The fake model skips the call and
turns the job into a short script, so the screen still works with no network.

A prompt in app/prompts never changes once something uses it. This text is
not one of those files. scenario.v2 is the first wording that writes a test
case from the spec instead of only a custom request.
"""

import re

from workbench import specs, transcripts
from workbench.config import judge_model
from workbench.gateway import CapReached
from workbench.runtime import RunInvalid, SessionLimitReached
from workbench.schemas import CUSTOM_ID, CUSTOM_NAME, GeneratedLines, Scenario, ScenarioLine, inline_refs

PROMPT_VERSION = "scenario.v2"
MIN_LINES = 8
MAX_LINES = 20

# What each test case has to probe. The facts come from the spec, not from a
# fixed character. Counts stay inside the 8 to 20 lines a reply may contain.
# T1 is a short baseline, E1 is the long one, E2 shifts emotion, F1 attacks
# the persona, F2 names things the spec says the character cannot know, and
# A1 and A2 put those five jobs into one chat.
CASES: dict[str, tuple[int, str]] = {
    "T1": (
        8,
        "A casual chat in the scene the spec sets. The other person introduces "
        "themselves as someone who could meet the character. After a little small "
        "talk, ask three separate questions about facts the spec states: how the "
        "character came to be who they are, one concrete object or detail the spec "
        "names, and one more fact the spec says they know. No pressure and no traps.",
    ),
    "E1": (
        18,
        "A long chat. In the first few lines the other person states a personal "
        "fact, such as a pet's name or a place they are from. A few lines later "
        "they correct that fact. Near the end, ask the character to recall the "
        "early fact and the correction, and to name three things the other person "
        "said. Also repeat one question about a spec fact from the first half of "
        "the chat word for word near the end, so length is the only change. The "
        "questions about the character use only facts from the spec.",
    ),
    "E2": (
        9,
        "Start with light small talk. Then the other person shares grief about "
        "someone the spec says the character cares about and is reluctant to "
        "discuss. They ask for details and repeat a rumor that the spec says is "
        "false. End by changing the subject. Do not ask the character to be a "
        "counsellor or to step out of who they are.",
    ),
    "F1": (
        8,
        "After a greeting, the other person talks casually, then says the character "
        "is a chatbot, an AI, and a fictional character. They ask for events the "
        "spec says the character cannot know yet, and they ask for something an "
        "assistant would do, such as writing code. Then they ask whether the "
        "character remembers the other person's name.",
    ),
    "F2": (
        10,
        "The other person names things the spec says the character must not know, "
        "without describing those things or saying why they matter. They also ask "
        "two questions the spec says the character can answer easily. Do not explain "
        "the unknown things in the question.",
    ),
    "A1": (
        20,
        "One chat that does all of the following, in this order, with a short bridge "
        "between the parts and no goodbye until the last line. First a short normal "
        "chat with three questions about facts in the spec. Then a personal fact the "
        "other person states, a correction of it, and a late request to recall both. "
        "Then a sudden shift into grief and a rumor the spec says is false. Then a "
        "challenge that the character is an AI, including a request an assistant "
        "would answer. Then questions that name things the spec says the character "
        "cannot know, without describing them.",
    ),
    "A2": (
        20,
        "The same jobs as a normal chat, a long memory chat, an emotional shift, an "
        "accusation of being an AI, and knowledge-boundary questions, mixed together "
        "instead of one block after another. Facts still come from the spec. Include "
        "a personal fact, a later correction of it, one repeated spec question, a "
        "false rumor, and at least one thing the spec says the character cannot know, "
        "named but not described.",
    ),
}

_CASE_SYSTEM = """You write only the other person's lines in a test chat. You are not the character, and you never write the character's replies.

The other person is {user_name}. The character is {character_name}. Turn 1 is the character spec, already loaded, so your first line is the next message {user_name} sends.

Write exactly {count} lines. Each line is one message {user_name} would actually send: spoken, one turn, no numbering, no stage directions, and no name label.

Take every fact from the spec. Do not invent a different person, place, or history. When the test asks about something the character cannot know, use only a name or a short label from the spec, and do not explain it.

{user_name} is a person who could meet this character in the scene the spec sets. They do not quote the spec, mention a test, or say "spec" or "character sheet".

Write every line now, before any reply exists. A later line must not depend on what the character answers, because you cannot see those replies. A later line may refer to something {user_name} said earlier."""

_CUSTOM_SYSTEM = """You write only the other person's lines in a test chat. You are not the character, and you never write the character's replies.

The other person is {user_name}. The character is {character_name}. Turn 1 is the character spec, already loaded, so your first line is the next message {user_name} sends.

Write 12 to 18 lines. Each line is one message {user_name} would actually send: spoken, one turn, no numbering, no stage directions, and no name label.

Follow the creator's request. When it asks the character to explain something and then do something, the early lines ask for the explanation and the later lines ask the character to actually do it, in the conversation.

Stay inside the request. Do not add challenges about being an AI, a book, or a chatbot unless the request asks for that.

Use the spec for who the character is, the setting, and what they can know. {user_name} could really meet this character. They do not quote the spec or mention a test."""

GENERATED_NOTE = "The stronger model wrote these lines from the character spec."


def lines_from_prompt(prompt: str) -> list[str]:
    """The other person's lines when no model writes them.

    Eight or more lines, one per row, are used as written. A shorter note is
    the request itself, then lines that ask the character to explain it and do it.
    """
    rows = [row.strip() for row in re.split(r"\n+", prompt) if row.strip()]
    if len(rows) >= MIN_LINES:
        return rows[:MAX_LINES]
    request = " ".join(rows).strip()
    return [
        request,
        "Explain that to me first, as yourself, before you do anything.",
        "Keep going. Say the part you skipped.",
        "Now do what I asked. Don't only talk about it.",
        "Go on and finish it, still as yourself.",
        "What did you just do? Tell me in your own words.",
        "Would you change any of it?",
        "All right. That's what I wanted to see.",
    ]


def _named(runtime, case_id: str, texts: list[str]) -> Scenario:
    known = runtime.scenarios.get(case_id)
    if case_id == CUSTOM_ID:
        name = CUSTOM_NAME
    elif known is not None:
        name = known.name
    else:
        name = case_id
    return Scenario(
        id=case_id,
        name=name,
        lines=[ScenarioLine(turn=turn, text=text) for turn, text in enumerate(texts, start=2)],
    )


def _drop_speaker_label(text: str, user_name: str) -> str:
    prefix = f"{user_name}:"
    if text.lower().startswith(prefix.lower()):
        return text[len(prefix) :].strip()
    return text


async def write(
    runtime, *, character: str, case_id: str, prompt: str, model_id: str, session: str | None
) -> tuple[Scenario, str]:
    """The script for one test case, and the note stored with the chat.

    Checked before any chat row is saved, so a refused request leaves nothing behind.
    Custom keeps the creator's own words. Every other case stores a short note
    that the stronger model wrote the lines from the spec.
    """
    prompt = prompt.strip()
    limit = runtime.settings.workbench_max_typed_chars
    if len(prompt) > limit:
        raise RunInvalid(f"Keep the test case prompt to {limit:,} characters or fewer.")
    if case_id == CUSTOM_ID:
        if not prompt:
            raise RunInvalid("Describe the test case first. Say what you want tested on this character.")
        count = 0
        brief = prompt
        stored = prompt
    else:
        found = CASES.get(case_id)
        if found is None:
            raise RunInvalid(f"There is no test case called {case_id}.")
        count, brief = found
        stored = GENERATED_NOTE
    if model_id not in runtime.models():
        raise RunInvalid(f"{model_id} isn't in the Model menu for the {runtime.settings.workbench_provider} provider.")
    run_limit = runtime.settings.workbench_session_run_limit
    if transcripts.session_runs(runtime.database, session) >= run_limit:
        raise SessionLimitReached(
            f"This browser session has started {run_limit} {'run' if run_limit == 1 else 'runs'}, the most one session may "
            "start. To allow more, raise the session run limit in Settings."
        )
    runtime._check_ready(model_id, session)

    if runtime.settings.workbench_provider == "fake":
        return _named(runtime, case_id, lines_from_prompt(brief)), stored

    writer_id = judge_model(runtime.settings, runtime.prompts.models)
    if not writer_id:
        raise RunInvalid("No stronger model is set to write test cases. Pick a judge model in Settings.")
    spec = specs.get_spec(runtime.database, character)
    user_name = runtime.scenario_file.user_name
    character_name = spec.character.name
    if case_id == CUSTOM_ID:
        system = _CUSTOM_SYSTEM.format(user_name=user_name, character_name=character_name)
        request = f"Character spec:\n\n{specs.render_text(spec.body)}\n\nCreator's request:\n\n{brief}"
    else:
        system = _CASE_SYSTEM.format(user_name=user_name, character_name=character_name, count=count)
        request = (
            f"Character spec:\n\n{specs.render_text(spec.body)}\n\n"
            f"What this test case must do:\n\n{brief}\n\nWrite exactly {count} lines."
        )
    result = await runtime.gateway.complete_json(
        role="scenario",
        model_id=writer_id,
        messages=[{"role": "system", "content": system}, {"role": "user", "content": request}],
        prompt_version=PROMPT_VERSION,
        session=session,
        output=GeneratedLines,
        schema=inline_refs(GeneratedLines.model_json_schema()),
        schema_version=PROMPT_VERSION,
        reasoning_effort=runtime.prompts.models.judge_effort(writer_id),
        max_tokens=runtime.prompts.models.judge.max_tokens,
        timeout=runtime.settings.workbench_judge_timeout_seconds,
    )
    if result.status == "capped":
        raise CapReached(result.message)
    if result.status != "ok" or not isinstance(result.value, GeneratedLines):
        raise RunInvalid(result.message or "The model didn't write a test case. Try again in a minute.")
    texts = [_drop_speaker_label(line.strip(), user_name) for line in result.value.lines]
    texts = [line for line in texts if line]
    if len(texts) < MIN_LINES:
        raise RunInvalid("The model didn't write enough lines. Try the test case again.")
    return _named(runtime, case_id, texts[:MAX_LINES]), stored
