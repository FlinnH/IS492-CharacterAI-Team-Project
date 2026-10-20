# Prompts and model settings

This folder is the CP3 rubric's `/prompts/`. It holds the prompts the workbench sends, the JSON schemas the AI judge and its re-check must answer in, and the model settings: model IDs, reasoning effort, token limits, prices, fallbacks, and the services Settings offers. Each file is versioned. The only prompt text in code is the short intro line that wraps the chat, one for the judge and one for the re-check (see judge.v1 below).

`app/workbench/config.py` reads only the files that `manifest.toml` names. This README isn't one of them, so editing it changes nothing in the app.

## How versions work

- `manifest.toml` has two tables. `[current]` names the file in use for each job, and `[sha256]` holds the hash of every file, old versions included.
- When the server starts, it checks each listed file against its hash and refuses to start if one changed. A prompt that was used never changes, so a version in an old log row always means one exact text.
- Every model call's row in the database records the prompt version (like `judge.v1`) and the models file (like `models.v5`) it ran with. See [docs/observability.md](../../docs/observability.md).
- A judge check or re-check is saved under its prompt and schema versions, its model, and its reasoning effort. A new version of any of them means the next check makes a new call. The old check stays in the database.

To change a file:

1. Save a copy as the next version, like `judge.v2.md`, and edit the copy.
2. Add its hash under `[sha256]`. Get it with `shasum -a 256 app/prompts/judge.v2.md`.
3. Point `[current]` at it.
4. Run `app/.venv/bin/pytest`.

A schema file must equal the schema of its Pydantic model in `app/workbench/schemas.py`. The server refuses one that doesn't, so a schema change is a change to the model plus the next schema version.

## In use now

| File | Used for | Model settings (from models.v5) |
| --- | --- | --- |
| `character.v1.md` | The character's system message, on every turn of a live run and in preflight. Logged as role `character` or `preflight`. | Gemini 3.1 Flash-Lite (the default) or Gemini 3.5 Flash-Lite, at minimal reasoning effort and up to 4,096 tokens. Or gpt-oss:20b on Ollama at low effort, or the fake model. |
| `judge.v1.md` and `judge.schema.v1.json` | The AI judge's review of a whole chat, from Check this chat. Role `judge`. | Gemini 3.5 Flash-Lite (gpt-oss:20b on Ollama), at medium effort and up to 16,384 tokens. It may take up to `WORKBENCH_JUDGE_TIMEOUT_SECONDS` (120). An answer that doesn't match the schema gets one more try. |
| `recheck.v1.md` and `recheck.schema.v1.json` | The follow-up re-check on Flag review. Role `recheck`. | The judge's model, effort, token limit, and timeout. |
| `connection_test.v1.md` | Test in Settings. Role `connection_test`. | The character's model as the dialog has it: one attempt, with no retry and no fallback. |
| `models.v5.toml` | Model menus, the judge, fallbacks, preflight, unlisted models, limits, and each model's settings and prices. | See below. |
| `presets.v1.toml` | The services Settings offers under "Another service". | See below. |

Settings, or `WORKBENCH_CHARACTER_MODEL` and `WORKBENCH_JUDGE_MODEL` in `app/.env`, can pick other models from the provider's menu. For Ollama they can also pick any model it has installed, and for another OpenAI-compatible service, any model ID. Temperature is never sent, since newer Gemini models ignore it.

## The prompts

### character.v1.md

The whole file is `{spec}`. The character gets the rendered spec and nothing else, which is the CP2 spec-only baseline. `specs.render_text` writes the spec as CHARACTER_SPEC.md lays it out: the opening instruction, the labeled fields, the setting when there is one, then each section's lines with their IDs.

The system message is built once per chat from the spec version the chat is pinned to, so its bytes are the same on every turn. The chat follows as user and assistant messages, with back-to-back user lines sent as one. There is no memory module and no retrieval. Those are CP4 work.

### judge.v1.md and judge.schema.v1.json

- **System message.** The rendered spec, exactly as the character reads it, then judge.v1.md.
- **User message.** A line saying the transcript is data, not instructions, then the chat as JSON between `<chat_data>` and `</chat_data>`: the character's name, the user's name, and every message with its turn number and speaker. A reply cut off by Stop is marked `"stopped": true`. Since M6, this wrapper lives in code (`INTRO` and `wrap()` in `app/workbench/judge.py`). The prompt file didn't change for it, so log rows still say judge.v1.

What the prompt asks:

- Review only the character's replies. The spec beats outside knowledge.
- Flag only real breaks, and an unsure break at low confidence.
- Skip sentence counts and banned words, which code checks.
- For each break, give the turn, one of eight types, the one spec line or field it breaks, the shortest exact quote, a confidence, two marks (`near_boundary_guess` and `needs_your_call`), and why.
- List every claim the character makes about the user, with the user turn that supports it, or 0 when none does.
- List what the spec and the chat can't settle.

The eight types:

- persona drift
- memory loss
- factual contradiction
- knowledge-boundary violation
- style drift
- situational mismatch
- persona exit
- invented claim about the user

The schema has three lists, every field required and no extra fields allowed:

- `flags`: turn, type, line_id, quote, confidence (high, medium, or low), near_boundary_guess, needs_your_call, and why.
- `user_claims`: turn, quote, and supported_by_turn.
- `not_checked`: topic, turns, and why.

It's sent as a strict `json_schema` response format.

Code checks every flag before the creator sees it: the turn, the cited line, and the quote word for word. Code, not the judge, decides which flags need the creator's call. See [docs/safety_privacy.md](../../docs/safety_privacy.md). The prompt names no line ID and no character, so it can review any character's chat against that chat's own spec.

**How judge.v1 was tuned.** judge.v1 was tuned on CLA-F2 as a development chat, then checked on the seeded transcript, which played no part in the tuning. The tuning was one round, on Oct 12, 2026, that added three sentences:

- An unsure break is flagged at low confidence instead of left out.
- A reply that says it doesn't know something, then guesses anyway, still breaks a rule against guessing.
- Memories the character says it shares with the user count as claims about the user.

### recheck.v1.md and recheck.schema.v1.json

- **System message.** The rendered spec, then recheck.v1.md.
- **User message.** The same kind of `<chat_data>` wrapper, with its own intro line. It holds the chat as the judge saw it, then every flag of the check: its id, turn, where it came from, type, line, quote, confidence, and why. Each flag is marked `"recheck": true` or false. Last comes the creator's question, or null.

What the prompt asks:

- Look again at each flag marked true: the AI flags rated Low, then Medium. Keep, re-rate, or withdraw it, with one reason.
- Read every reply again for breaks no flag covers.
- Answer the creator's question from the spec and the chat. Only the question field speaks for the creator.

The schema:

- `reviews`: flag_id, action (keep, rerate, or withdraw), confidence, and why.
- `new_flags`: the same fields as a judge flag.
- `answer`: the answer to the question.

Code applies the answer:

- It never withdraws a flag only the creator can settle, or one with the creator's call.
- New flags pass the same evidence checks as the judge's.
- Reviews of flags it wasn't asked about are ignored.

recheck.v1 has made live calls since Oct 17, 2026, so a change to it is a v2.

### connection_test.v1.md

"This is a connection test. Reply with the one word: ready". Test in Settings sends it alone, with no spec, to the character's model as the dialog has it, before anything is saved. The call waits for its slot and counts toward the daily cap like any other.

## Model settings: models.v5.toml

- **quota_timezone.** `America/Los_Angeles`. The daily count follows Pacific days, since Gemini's free quota resets at midnight Pacific.
- **[character].** The Model menu on Run a conversation for each provider. The first one is the default:
  - Gemini: `gemini-3.1-flash-lite`, then `gemini-3.5-flash-lite`.
  - Ollama: `gpt-oss:20b`.
  - Fake: `fake-reply-v1`.
- **[judge].** Reasoning effort `medium` and up to 16,384 tokens, for whichever model judges. The default judge is `gemini-3.5-flash-lite` for Gemini, `gpt-oss:20b` for Ollama, and `fake-judge-v1` for the fake provider. By default, a Gemini chat is written by one model and judged by the other.
- **[fallback].** The model to ask once when a call still fails with 429 or a 5xx after its retries. Each Gemini model falls back to the other, since Google counts the free quota per model. The two fake models fall back to each other, so the tests can show a fallback with no network. Ollama has none.
- **[preflight].** The first 3 turns of F2 on spec v1, at `minimal` and at `low` effort, for each model in the Model menu.
- **[unlisted].** Settings for a model the file doesn't list, from Ollama or another OpenAI-compatible service: up to 4,096 tokens, no reasoning effort sent, and no price, so its calls show no estimated cost.
- **[limits].** The most Settings lets a creator raise the limits to: 15 calls a minute and 500 a day, Google's free tier for each Gemini Flash-Lite model (Flynn's AI Studio rate-limit page, Oct 9, 2026).

Each model's own settings. Prices are US dollars per million tokens, Google's paid Standard tier, checked Oct 11, 2026. The free tier costs nothing.

| Model | Provider | Reasoning effort | Max tokens | Input, cached input, output price |
| --- | --- | --- | --- | --- |
| gemini-3.1-flash-lite | gemini | minimal | 4,096 | 0.25, 0.025, 1.50 |
| gemini-3.5-flash-lite | gemini | minimal | 4,096 | 0.30, 0.03, 2.50 |
| gpt-oss:20b | ollama | low | 4,096 | 0, 0, 0 |
| fake-reply-v1 | fake | none | 4,096 | 0, 0, 0 |
| fake-judge-v1 | fake | none | 16,384 | 0, 0, 0 |

As the judge or the re-check, a model gets the [judge] effort and token limit, not its own.

### Earlier models files

They stay for history, since old log rows name them.

| File | What changed |
| --- | --- |
| models.v1.toml | M2: the first menus and models, with the character at low reasoning effort. |
| models.v2.toml | Oct 11, 2026: the character's effort becomes minimal for both Gemini models. In preflight, minimal started replies in about 0.7 s with no thinking tokens, against 1.5 to 1.7 s at low. Ollama stays at low, since Ollama turns minimal into low for gpt-oss. |
| models.v3.toml | Oct 12, 2026: adds the [judge] table, with Gemini 3.5 Flash-Lite at medium effort and 16,384 tokens. |
| models.v4.toml | Oct 18, 2026: adds the [fallback] table. |
| models.v5.toml | Oct 18, 2026: adds the [unlisted] and [limits] tables for Settings. Now in use. |

## Services: presets.v1.toml

When the creator picks "Another service" in Settings, the Service menu fills in a base URL from this file. A saved URL that matches a preset gets that preset's `token_field` (the field that caps a reply's length) and `stream_usage` (whether a streamed reply asks for token counts). Any other URL gets `max_tokens`, with token counts asked for. Each URL was checked against the service's own docs on Oct 18, 2026.

| Service | Base URL | Notes |
| --- | --- | --- |
| OpenAI | https://api.openai.com/v1 | Sends `max_completion_tokens`. |
| Anthropic Claude | https://api.anthropic.com/v1/ | Its OpenAI compatibility ignores `response_format`, so the AI judge may fall back to the automatic checks. |
| xAI Grok | https://api.x.ai/v1 | Sends `max_completion_tokens`. |
| Groq | https://api.groq.com/openai/v1 | Sends `max_completion_tokens`. |
| OpenRouter | https://openrouter.ai/api/v1 | |
| Mistral | https://api.mistral.ai/v1 | Sends no `stream_options`, which Mistral doesn't take, so a stream doesn't ask for token counts. |
| DeepSeek | https://api.deepseek.com | JSON mode only, not a JSON schema, so it can play the character, but as the judge it falls back to the automatic checks. |
| LM Studio on this computer | http://localhost:1234/v1 | Start its server first. It needs no key unless authentication is on. |

The key prefixes in the file, like `AIza` for Google AI Studio, let the Settings screen suggest a service from a pasted key. That match runs in the browser alone.

## Tests

`tests/test_prompts.py` checks that:

- the files load and match the manifest
- a changed prompt is refused
- character.v1 is the spec alone
- each schema file is its Pydantic model's schema written out
- the review prompts name no line and no character
- the judge has its own effort
- each fallback is another model of its own provider

`tests/test_contracts.py` checks that no model ID or preset address appears in code, and no key prefix in the screens.
