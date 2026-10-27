# Architecture

How the Character Consistency Workbench fits together for CP3. It runs on one computer: a browser page, one local server, one SQLite file, and the model service the creator picks in Settings. For setup, see [app/INSTALL.md](../app/INSTALL.md). For what each screen does, see [use-cases.md](use-cases.md).

## Diagram

```mermaid
flowchart LR
  subgraph browser["Browser on this computer"]
    screens["Screens in app/static:<br/>Spec editor, Run a conversation,<br/>Flag review, Compare runs, Settings"]
    api["api.js: every request the screens make"]
  end

  subgraph server["FastAPI server: one Uvicorn worker on 127.0.0.1:8492"]
    routes["main.py: the routes"]
    services["Services: specs, transcripts, runtime,<br/>judge with rules and evidence,<br/>recheck, review, app_settings"]
    gateway["gateway.py: daily cap, call spacing,<br/>retries, fallback model, one log row per attempt<br/>(with limiter.py, redact.py, telemetry.py)"]
    providers["providers.py: openai 3.24 on httpx2,<br/>no automatic retries"]
    fake["FakeProvider: canned replies, no network"]
    config["config.py: settings and prompts"]
    dbmod["db.py: the only sqlite3 importer"]
    shared["Shared helpers: schemas.py (every request's<br/>and answer's shape), injection.py (marks lines<br/>that read like instructions to the AI)"]
  end

  files["app/.env.example, app/.env,<br/>app/prompts/"]
  sqlite[("SQLite file:<br/>app/data/workbench.db")]
  gemini["Google Gemini, OpenAI-compatible endpoint:<br/>Gemini 3.1 Flash-Lite plays the character,<br/>Gemini 3.5 Flash-Lite judges and re-checks"]
  ollama["Ollama on this computer (optional):<br/>gpt-oss:20b plays and judges"]
  other["Another OpenAI-compatible service<br/>picked in Settings (optional)"]

  screens --> api
  api -- "HTTP with JSON, server-sent events for live turns" --> routes
  routes --> services
  services --> shared
  services --> gateway
  gateway --> providers
  services --> dbmod
  gateway --> dbmod
  dbmod --> sqlite
  config -- "reads, and Settings writes app/.env" --> files
  providers -- "HTTPS" --> gemini
  providers -. "HTTP on this computer" .-> ollama
  providers -.-> other
  providers -.-> fake
```

There's no vector store: character.v1 sends the whole rendered spec on every turn, and the AI judge reads the whole chat in one call, so nothing needs retrieval yet. Memory and retrieval are CP4 work, to compare against this spec-only baseline.

## The parts

### Browser screens

`app/static/` holds the page: index.html, styles.css, api.js, and app.js. It started as a copy of the CP2 prototype, so it keeps the Material 3 look and the four tabs, one per journey step: Spec editor (Define), Run a conversation (Stress-test), Flag review (Diagnose), and Compare runs (Repair). The Settings dialog opens from the top bar.

- **In:** the creator's clicks and typing, and the server's JSON answers and streamed events.
- **Out:** HTTP requests. Every path lives in api.js, and app.js never calls `fetch`. Each request carries the tab's session ID in an `X-Workbench-Session` header. api.js makes the ID once per tab and keeps it in `sessionStorage`, so the server can apply the session limits and tell sessions apart in the event log.

app.js also runs two things that never talk to the server:

- **The tour.** A first-visit guide in 8 steps, opened again by the ? button in the top bar. It's a native `<dialog>`: a ring outlines each step's target and dims the rest of the page, and a card beside it holds the words. Every step's words and targets are in one list, `TOUR_STEPS`. A target is a `data-tour` element that index.html always has, like the Settings button or a screen's tab, or, once the screen draws it, a part of that screen, like Check this chat.
- **Decorations.** Original drawings, written as inline SVG in app.js: a theater-mask mascot on empty screens, a magnifier while a check runs, a one-time sparkle, and still art in wide side margins. styles.css keeps them faint and still except for those three moving parts, and shows them only while `<html>` has `data-decor="on"`.

The page keeps two preferences in the browser's `localStorage`: `workbench-tour-seen`, set when the tour first opens, and `workbench-decorations`, set by the Decorations switch in Settings. Neither reaches the server or the database. If the browser blocks storage, the tour opens again and decorations start on.

The page loads Roboto and the Material Symbols icons from Google Fonts. Everything else comes from the local server, the drawings included.

### FastAPI server

`app/workbench/main.py` builds the app, serves the screens, and holds the routes. `app/run.sh` starts it as one process with one Uvicorn worker, on 127.0.0.1 port 8492 by default. Once `/api/health` answers, run.sh prints the address and opens it in the default browser (`app/run.sh --no-browser` skips that). If the workbench already answers at that address, run.sh says so and doesn't start a second copy.

- **In:** HTTP requests from the page.
- **Out:** JSON answers whose shape is pinned by the Pydantic models in `schemas.py`, and a stream of server-sent events for each live turn: `user`, `wait`, `delta`, then `done` or `error`.

Routes only call services. A service error becomes a plain message with its status (404, 409, 422, 429, or 503), and a malformed request gets a message that names where it went wrong without echoing the request. The Settings routes answer only a browser on this computer.

At start, the server checks each file the prompt manifest lists against its recorded hash, applies any new database migrations, seeds spec v1, builds the provider, and adds an `app_settings` row if the settings changed since the last one. If something is wrong, run.sh prints one plain line that says what to fix, not a traceback.

### Services

Each service opens its own short database connection.

- **specs.py.** In: an edit from the Spec editor. Out: the next spec version, which never changes once saved. Also the spec as text for the models (`render_text`), and a warning when the setting, which the screens call Scene, is empty. Line IDs, line attributes, and check limits live in the spec itself, not in code.
- **transcripts.py.** In: a pasted chat (a chosen file is read into the paste box in the browser), or a sample. Out: a preview, then a saved chat that keeps the source's own numbering. It also saves each message of a live chat, redacted, and marks lines that read like instructions to the AI.
- **runtime.py.** In: Start run, the next scripted line, a typed line, or Stop. Out: streamed events and saved messages. The system message is character.v1 with the chat's pinned spec version rendered in. It's built once per chat, so its bytes are the same on every turn. One turn runs per chat at a time.
- **judge.py, rules.py, and evidence.py.** In: a saved chat. Out: rule flags from code alone, then the AI judge's flags that pass the evidence checks, a count of hidden flags, and what the judge couldn't check. One judge call covers the whole chat, and the saved check is reused until the chat or the judge settings change.
- **recheck.py.** In: a chat's saved check and the creator's optional question. Out: what changed for each flag it looked at again (kept, re-rated, withdrawn, or added), and the AI's answer.
- **review.py.** In: Show in context, Agree, Override, and Undo on Flag review. Out: one event row per call, and the review state: open calls, the rubber-stamp message, and flags where the re-check disagrees with the creator's call.
- **app_settings.py.** In: the Settings dialog as typed, from Test or Save. Out: Test makes one small call. Save writes the changes to app/.env and puts them in force with no restart. Each one adds an `app_settings` row, never a key.

### Gateway

`gateway.py` is the only path to a model.

- **In:** a role, a model, and messages.
- **Out:** streamed text, or a JSON answer checked against its Pydantic model, plus token counts. Exactly one `model_calls` row for each attempt, however it ends.

Before each attempt it checks the daily cap and waits for its call slot (`limiter.py`). It redacts every message first (`redact.py`). After a 429 or a 5xx before the first token, it tries again after a pause, then once on the fallback model that the models file names. A JSON answer that doesn't match its schema gets one more try. `telemetry.py` writes the rows. For the demo, `WORKBENCH_FORCE_MODEL_ERROR` or the busy switch in Settings makes attempts fail with a 429 without calling the service.

### Providers

`providers.py` is the only module that imports openai or httpx2. `OpenAIProvider` talks to any OpenAI-compatible endpoint: Gemini's, a local Ollama, or another service. `FakeProvider` has the same methods and needs no network.

- **In:** a model ID, messages, a reasoning effort, and a token limit, plus a JSON schema for the judge and the re-check.
- **Out:** chunks of text with the model the service says it used and the latest token counts, or one whole completion. Errors come back as `ProviderError`, with a message the creator can read as it is.

The openai client runs with `max_retries=0`, since the gateway decides when to try again. Temperature is never sent.

### SQLite database

`db.py` opens `WORKBENCH_DB_PATH`, which is `app/data/workbench.db` by default. Git ignores `app/data/`.

- **In:** rows from the services and the gateway.
- **Out:** the saved specs, chats, messages, checks, flags, calls on flags, re-checks, model calls, and settings rows.

Schema changes are numbered SQL files in `app/workbench/migrations/` (001 to 008), applied in order. Triggers keep rows from being changed or deleted, from any connection: spec versions, line IDs, messages, model calls, events, judge runs, hidden flags, not-checked rows, re-checks, flag changes, and settings rows. A flag keeps its evidence, and only its status and confidence change. A chat is never deleted, and only its status changes. The `characters` table has no triggers. [observability.md](observability.md) lists every table and field.

### Prompts and settings

`config.py` is the only reader of the environment and of `app/prompts/`, and the only writer of `app/.env`.

- **In:** `app/.env.example`, then `app/.env`, then environment variables, and the last one wins. Also `app/prompts/manifest.toml` and the files it names.
- **Out:** one `Settings` object and one `Prompts` object.

It refuses to start when a prompt file changed after the manifest recorded its hash, or when `app/.env.example` holds a key. [app/prompts/README.md](../app/prompts/README.md) describes each prompt, schema, and models file.

### Gemini models

The default provider is Google AI Studio, called through Google's OpenAI-compatible endpoint (`GEMINI_BASE_URL`) with the creator's free key.

- **In:** the messages above, over HTTPS.
- **Out:** a streamed reply with token counts on every chunk, or the judge's JSON answer.

Gemini 3.1 Flash-Lite plays the character by default, at minimal reasoning effort. Gemini 3.5 Flash-Lite is the AI judge and the re-check, at medium effort, so by default a chat is reviewed by a different model from the one that wrote it. Each model is the other's fallback, since Google counts the free quota per model.

### Ollama (optional)

With the Ollama provider, `gpt-oss:20b` runs on this computer, with no key and no network.

- **In:** the same messages, over HTTP to `OLLAMA_BASE_URL`.
- **Out:** the same kinds of replies.

One local model both plays the character and judges it, so its flags say "Same model reviewed." Ollama has no fallback model and no cost. Settings also lists the other models Ollama has installed.

### Another OpenAI-compatible service (optional)

In Settings, the creator can pick another service from `app/prompts/presets.v1.toml` (OpenAI, Anthropic Claude, xAI Grok, Groq, OpenRouter, Mistral, DeepSeek, or LM Studio), or type any base URL. They type the two model IDs there too. The preset says which token-limit field to send, and whether to ask for token counts on a stream.

### Fake model

`FakeProvider` streams the reply in `app/samples/fake.v1.json` ("This is a fake reply. No model was called."). Its judge answers with the smallest answer the schema allows: no flags. The tests use it, and it lets someone click through the screens without a key.

### Preflight script

`app/scripts/preflight.py` checks the model setup with real calls before a demo.

- **In:** the provider in `app/.env`.
- **Out:** a printed table of time to first token and token counts for each model and reasoning effort, with no chat text. Its calls are logged with the role `preflight` and count toward the daily cap. It exits with an error when a model looks retired (the service no longer lists it) or rerouted (a reply names another model).

### Demo reset and judge snapshot

`app/scripts/reset_demo.py` copies the database to `app/data/backups/`, then swaps in a fresh one with spec v1 and the CLA-F2 and GPT-F2 samples. It refuses while the server runs. Each sample gets its check from `app/samples/judge_snapshot.json`, real judge answers that `app/scripts/judge_snapshot.py` saved earlier. `Judge.replay` puts each answer through the same evidence checks as a live one and saves it as a judge run with 0 attempts and no model call, under today's cache key, so Check this chat finds it. An answer made with another judge model, reasoning effort, prompt, or schema, or on an edited sample, is skipped with a warning.

## Connectors

The workbench reaches outside itself through two kinds of connectors: data connectors bring chats in, and model connectors reach the AI.

### Data connectors

- **Chat import.** Import a chat, on Run a conversation, takes a pasted chat or a chosen file (.md, .txt, or .json). The browser reads a file into the paste box, so both go the same way. Preview shows what was read, then Import saves it (`POST /api/imports/preview`, then `POST /api/imports`, which answers 201 for a new chat and 200 for one imported before). `transcripts.parse` reads four formats, tried in this order:
  1. The workbench's own JSON (`workbench-chat.v1`), when the text starts with `{`. The samples use it.
  2. A receipt log, like the ones in `validation/transcripts/`: a "Turn N Name:" line with the message indented 4 spaces below it.
  3. A Markdown table with a speaker column, found by its header names or its shape, and maybe a turn column.
  4. One message per line, like "Alex: Hi." Variants like `**Alex:** Hi.`, "Turn 2 Alex: Hi.", "3. Alex: Hi.", and "[3] Alex: Hi." work too. The two names used most are the speakers, and lines after a message continue it.

  A chat keeps the source's own numbering and has two speakers. It can be up to `WORKBENCH_MAX_IMPORT_CHARS` (300000) characters. The server redacts it after parsing and marks lines that read like instructions to the AI.
- **Built-in samples.** `GET /api/samples` lists every file in `app/samples/` in the `workbench-chat.v1` format. Import shows them as "Sample: Claude (CLA-F2)", "Sample: ChatGPT (GPT-F2)", and "Sample: Planted instruction (synthetic)". The other files there are read by the server itself: spec v1 (`spec_v1.json`), the test scripts (`scenarios.v1.json`), the fake model's reply (`fake.v1.json`), and the demo reset's saved checks (`judge_snapshot.json`).
- **The seeded transcript.** `WORKBENCH_SEEDED_TRANSCRIPT_PATH` (default `../validation/fixtures/SEEDED_TRANSCRIPT.md`, relative to `app/`) points to it. Import lists it as "Seeded transcript", with its path, after checking only that the file exists. The server reads it only when the creator picks it. When the file is missing, the choice says so and can't be picked.

### Model connectors

`providers.py` holds the only model connectors. `WORKBENCH_PROVIDER` picks one, and Settings can change it:

| `WORKBENCH_PROVIDER` | In Settings | Address | Key | Models | Fallback |
| --- | --- | --- | --- | --- | --- |
| `gemini` | Gemini (Google AI Studio) | `GEMINI_BASE_URL`, default https://generativelanguage.googleapis.com/v1beta/openai/ | `GEMINI_API_KEY` | `gemini-3.1-flash-lite` plays the character, and `gemini-3.5-flash-lite` judges and re-checks | Each falls back to the other |
| `ollama` | Local model (Ollama) | `OLLAMA_BASE_URL`, default http://127.0.0.1:11434/v1 | None | `gpt-oss:20b`, or another model Ollama has installed, plays and judges | None |
| `openai_compatible` | Another service (OpenAI, Claude, Grok, Groq, OpenRouter, and more) | `OPENAI_COMPATIBLE_BASE_URL`, from a preset in `app/prompts/presets.v1.toml` or typed | `OPENAI_COMPATIBLE_API_KEY` | `WORKBENCH_CHARACTER_MODEL` and `WORKBENCH_JUDGE_MODEL`, typed in Settings | None |
| `fake` | Fake model (no network) | None | None | `fake-reply-v1` and `fake-judge-v1` | Each falls back to the other |

The first three are model endpoints that speak the same OpenAI-compatible API, so one class, `OpenAIProvider`, talks to all of them through the openai library. It calls two paths under the base URL:

- `POST /chat/completions`, streamed for the character's replies, or with a JSON schema for the judge and the re-check.
- `GET /models`, for the models Ollama has installed in Settings, and for preflight's check that each model is still listed.

Model IDs, reasoning efforts, token limits, prices, and fallbacks live in `app/prompts/models.v5.toml`, the models file `manifest.toml` names. No model ID appears in code (`test_no_model_id_in_code`). A preset says which token-limit field its service takes, and whether to ask for token counts on a stream. `FakeProvider` has the same methods and needs no network.

### No tool calling

Code runs the review in steps: the automatic checks, one judge call, the evidence check, then the optional re-check. So the model never calls tools on its own, and every flag stays verifiable. Each model call is a single request with a fixed prompt, and the judge and the re-check answer in a JSON schema that code reads, checks, and saves.

## One live turn, step by step

1. The page sends `POST /api/chats/{id}/next`, or `/messages` for a typed line.
2. runtime saves the user's line, redacted, and builds the messages: the system message with the pinned spec, then the chat so far.
3. The gateway checks the daily cap, waits for the call slot, redacts the messages, and asks the provider to stream.
4. Each piece of text goes back to the page as a `delta` event as it arrives.
5. When the reply ends, or the creator presses Stop, runtime saves the reply (marked stopped if it was cut off), and the gateway writes the `model_calls` row.

## One check, step by step

1. The page sends `POST /api/chats/{id}/check`.
2. The rule checks run first, with no AI.
3. If no saved judge run covers this chat as it stands, the gateway makes one judge call. The rendered spec and judge.v1 go in the system message, and the chat goes in as JSON between `<chat_data>` tags.
4. Every judge flag passes the evidence checks or is saved apart as hidden, with its reason.
5. The check is saved, and Flag review reads it from the database.

## Boundaries the tests enforce

Imports point one way, from the bottom up: schemas; then config, redact, and injection; then db; then telemetry, limiter, and providers; then the gateway; then specs, app_settings, rules, and evidence; then transcripts; then runtime and judge; then recheck; then review; and main last. `tests/test_contracts.py` holds the ranks (`LAYERS`), and `test_imports_point_one_way` fails when a module imports one at its own rank or above. The same file checks 10 more boundaries:

- only db.py imports sqlite3
- only providers.py imports openai and httpx2
- only config.py reads the environment and the prompts
- only api.js talks to the server
- every `data-action` in the screens has a handler
- no line ID appears in code
- no model ID appears in code
- no preset address appears in code, and no key prefix appears in the screens
- the app's code compiles on Python 3.11
- `FakeProvider` has the same methods as the real provider

`tests/test_screens.py` reads the screens' own files, with no browser. It checks that every tour step points at an element index.html has, that the spec field reads Scene on screen, that `localStorage` is only touched inside `try`, and that decorations keep their limits: background art at most 12% opacity and still, and only the mascot, the magnifier, and the sparkle animated, with transform and opacity alone.
