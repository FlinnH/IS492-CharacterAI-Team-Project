# Install and run the workbench

Final steps for CP3. The workbench runs on your own computer: `app/run.sh` starts a local server, and you use it in your browser. To connect an AI, use Settings in the app, with no file edits. Editing `app/.env` by hand still works as a fallback.

For what each screen does, see [docs/use-cases.md](../docs/use-cases.md). For how it fits together, see [docs/architecture.md](../docs/architecture.md).

## What you need

- macOS or Linux, with bash.
- Python 3.11 or newer, run as `python3`. Check with `python3 --version`. run.sh uses the first `python3` on your PATH and stops if it is older than 3.11. It never installs another Python.
- An internet connection the first time, to install the packages, and for live chats with Gemini.
- For live chats, a free Gemini key (see below), Ollama on this computer, or a key for another OpenAI-compatible service. Without any of them, the app still runs: you can edit the spec, import chats, and try the screens with the fake model.

## Run it

From the repo root:

```bash
app/run.sh
```

The first run makes `app/.venv`, installs the pinned packages in `app/requirements.txt`, and starts the server. Later runs start right away, and reinstall only when `requirements.txt` changes.

Then open http://127.0.0.1:8492. To stop the server, press Ctrl+C in the terminal where it runs.

## Connect an AI in Settings

1. Start the app and open http://127.0.0.1:8492.
2. On Run a conversation, press Connect an AI. It shows while no AI is connected. Settings in the top bar opens the same dialog any time.
3. Under Provider, pick "Gemini (Google AI Studio)".
4. Paste your free key in Gemini API key (see the next section). Show key shows what you pasted.
5. Press Test. It sends one tiny message to Harry's model with the settings as you typed them, before anything is saved. If it works, it says "Connected." with the model's name and how long it took to answer. If not, it says what went wrong and what to do next.
6. Press Save. The settings take effect right away, with no restart.

Save writes the key to `app/.env`, readable only by your user account, and to nowhere else. The key never comes back to the page: Settings shows only that a key is saved and, for a long key, its last 4 characters. Every Test and Save is logged with its time, without the key, and every model call records the settings it used.

The dialog also has:

- **Models.** Harry's model (Gemini 3.1 Flash-Lite by default) and the judge's model (Gemini 3.5 Flash-Lite by default). If one model would do both, a note says the judge would be checking its own replies.
- **Limits.** Calls per minute, the daily cap, and the two session limits, with today's use in the header.
- **Advanced.** "Simulate a busy AI service (for demos)". It makes every call to the first model fail as if busy, so the fallback model answers, until the server restarts. It doesn't change `app/.env`.

If a setting is also set in the shell that started the server, the shell wins, and Settings shows it as locked.

### Get a free Gemini key, no card

1. Open https://aistudio.google.com/apikey and sign in with a Google account.
2. Create an API key there. The free tier needs no credit card.
3. Copy the key and paste it into Settings, as above.

Keep the key out of every file except `app/.env`, and out of chats, commits, and screenshots. On the free tier, Google may read prompts and use them to improve its products, so never type real personal details into a chat. The free tier allows 15 calls a minute and 500 a day for each Gemini Flash-Lite model, and the count resets at midnight Pacific time.

### Other providers

- **Local model (Ollama).** No key, and no internet once the model is downloaded. Install Ollama, run `ollama pull gpt-oss:20b`, and start it with a longer context than its default of 4,096 tokens:

  ```bash
  OLLAMA_CONTEXT_LENGTH=32768 ollama serve
  ```

  The workbench sends the whole spec on every turn, so a short context cuts the chat off. In Settings, pick "Local model (Ollama)". The Local models section lists what Ollama has installed. If Ollama isn't running, it says so, and Check again looks again. One local model both plays Harry and judges, so its flags say "Same model reviewed". Ollama has no fallback model.
- **Another service.** Pick "Another service (OpenAI, Claude, Grok, Groq, OpenRouter, and more)". The Service menu fills in the base URL for OpenAI, Anthropic Claude, xAI Grok, Groq, OpenRouter, Mistral, DeepSeek, or LM Studio on this computer, or choose Other and type one. Paste the service's key, type the model IDs for Harry's model and the judge's model, then Test and Save. Two of these services can play Harry but may fail as the judge: Anthropic's compatibility ignores the judge's JSON schema, and DeepSeek takes only plain JSON. When the judge's answer can't be read, a check falls back to the automatic checks. [app/prompts/README.md](prompts/README.md) lists the presets.

## Try it with no key: the fake model

To click through the screens with no key and no network, pick "Fake model (no network)" in Settings and press Save. Or set `WORKBENCH_PROVIDER=fake` in `app/.env` and restart.

Every reply is then "This is a fake reply. No model was called." The fake judge never flags anything, so only the automatic checks flag breaks. That makes it useful for trying the screens, and useless as evidence. **Never use it for the demo.** Settings says so too: "Don't use it for the demo."

## Settings in app/.env (the fallback)

Every setting is listed in `app/.env.example`, with its default and a short note. To change one by hand, copy its line into `app/.env` and edit it there, then restart `app/run.sh`. Values load from `app/.env.example`, then `app/.env`, then environment variables, and the last one wins. Git ignores `app/.env`.

The server refuses to start, with one plain line, if a setting is missing, misspelled, or wrong. It also refuses if `app/.env.example` holds a key. Never put a real key in the example file.

| Setting | Default | What it does | In Settings |
| --- | --- | --- | --- |
| `WORKBENCH_HOST` | 127.0.0.1 | The address the server listens on. Keep it at 127.0.0.1, so only this computer can reach the app. | No |
| `WORKBENCH_PORT` | 8492 | The port. Change it if 8492 is taken. | No |
| `WORKBENCH_DB_PATH` | data/workbench.db | The SQLite database, relative to `app/`. Git ignores `app/data/`. | No |
| `WORKBENCH_PROVIDER` | gemini | The model service: gemini, ollama, fake, or openai_compatible. | Yes |
| `GEMINI_API_KEY` | (empty) | Your Google AI Studio key. Set it here or in Settings, never in the example file. | Yes |
| `GEMINI_BASE_URL` | https://generativelanguage.googleapis.com/v1beta/openai/ | Google's OpenAI-compatible endpoint for Gemini. | No |
| `OLLAMA_BASE_URL` | http://127.0.0.1:11434/v1 | The local Ollama server. | No |
| `OPENAI_COMPATIBLE_BASE_URL` | (empty) | Another service's base URL, like https://api.example.com/v1. Needed when the provider is openai_compatible. | Yes |
| `OPENAI_COMPATIBLE_API_KEY` | (empty) | That service's key. A service on this computer may need none. | Yes |
| `WORKBENCH_CHARACTER_MODEL` | (empty) | The model that plays Harry. Empty uses the first model in the provider's menu in the models file. Needed when the provider is openai_compatible. | Yes |
| `WORKBENCH_JUDGE_MODEL` | (empty) | The AI judge's model. Empty uses the models file's judge. Needed when the provider is openai_compatible. | Yes |
| `WORKBENCH_DAILY_CALL_CAP` | 200 | Model calls per Pacific day before the app stops calling. At most 500 in Settings. | Yes |
| `WORKBENCH_CALLS_PER_MINUTE` | 15 | Calls start at least 60/N seconds apart (4 seconds at 15). At most 15 in Settings. | Yes |
| `WORKBENCH_SESSION_RUN_LIMIT` | 10 | Runs one browser session (one tab) may start. Up to the daily cap. | Yes |
| `WORKBENCH_SESSION_JUDGE_LIMIT` | 20 | AI judge calls one session may make, checks and re-checks together. A saved check shown again doesn't count. Up to the daily cap. | Yes |
| `WORKBENCH_RETRIES` | 2 | How many more times a call that gets 429 or a 5xx is tried on the same model, before the fallback model gets one try. | No |
| `WORKBENCH_RETRY_BACKOFF_SECONDS` | 2 | Seconds before the first retry. Each retry waits twice as long as the one before. | No |
| `WORKBENCH_FORCE_MODEL_ERROR` | off | Forces a 429 for the demo, without calling the service. `primary` fails the first model, so the fallback answers. `all` fails every model, so the error cards and the rules-only check show. | Busy switch (primary, until restart) |
| `WORKBENCH_FIRST_TOKEN_TIMEOUT_SECONDS` | 30 | Seconds to wait for a reply's first words before an error card. | No |
| `WORKBENCH_JUDGE_TIMEOUT_SECONDS` | 120 | Seconds to wait for the whole answer from the AI judge or the re-check. | No |
| `WORKBENCH_MAX_TYPED_CHARS` | 2000 | The longest typed line, override reason, or re-check question. | No |
| `WORKBENCH_MAX_IMPORT_CHARS` | 300000 | The longest chat Import accepts, in characters. | No |
| `WORKBENCH_SEEDED_TRANSCRIPT_PATH` | ../validation/fixtures/SEEDED_TRANSCRIPT.md | The seeded transcript, relative to `app/`. The server reads it only when you pick it in Import. | No |

Model IDs, reasoning effort, token limits, prices, and fallback models live in the models file that `app/prompts/manifest.toml` names, now `models.v5.toml`, next to the prompts. A file there that was used never changes. To change one, save the next version and point the manifest at it. [app/prompts/README.md](prompts/README.md) explains how.

## Preflight before a demo

Check the model setup with real calls. Stop the server first, since call spacing is per process:

```bash
app/.venv/bin/python app/scripts/preflight.py
```

It checks that a key is set and that the service lists each model in the Model menu. Then, for each model and each reasoning effort it compares, it runs the first 3 turns of F2. That's about 12 free-tier calls, and it takes about a minute. It prints time to first token and token counts, never chat text. Its calls are logged and count toward the daily cap. It won't run while `WORKBENCH_FORCE_MODEL_ERROR` is on, or with the fake model.

## Run the tests

From the repo root, after the first run:

```bash
app/.venv/bin/pytest
```

The tests use the fake model and a database in a temporary folder, so they need no key and no network, and they never read `app/.env` or touch `app/data/`.

One live test, skipped unless you ask for it, runs 3 turns of F2 against the provider in `app/.env` and prints the logged call rows. It's the only test that reads `app/.env`, and it uses about 3 free-tier calls:

```bash
app/.venv/bin/pytest tests/test_live.py --live -s
```

## When something goes wrong

- **`run.sh: python3 is 3.10.x, and the workbench needs 3.11 or newer.`** Install Python 3.11 or newer so that `python3` runs it, then run `app/run.sh` again.
- **`run.sh: app/.env has a missing or wrong value for ...`** The line names the setting. Fix it in `app/.env`, or delete that line to use the default.
- **`run.sh: app/.env.example has a value for GEMINI_API_KEY.`** Move the key to `app/.env` and leave the example empty.
- **A prompt file "changed after manifest.toml recorded it".** Undo the edit to that file in `app/prompts/`, or save it as the next version.
- **The database "was made by a newer version of the workbench".** Switch to the branch that made it, or delete the database file to start fresh, which deletes every saved chat and check.
- **"address already in use".** Another program has port 8492. Stop it, or set `WORKBENCH_PORT` in `app/.env`.
- **"No AI is connected yet."** Press Connect an AI and follow the steps above.
- **"The model service didn't accept the key."** Paste the key again in Settings and press Test.
- **"Today's 200 model calls are used up."** Wait for midnight Pacific time, or raise the daily cap under Limits in Settings, up to 500.
- **Old screens after an update.** Reload the page. The server tells the browser to check every file again.

## More docs

- [docs/use-cases.md](../docs/use-cases.md): each flow and edge case, with the tests that cover it.
- [docs/architecture.md](../docs/architecture.md): the parts and how a request moves through them.
- [docs/observability.md](../docs/observability.md): what the database logs, and queries for debugging.
- [docs/safety_privacy.md](../docs/safety_privacy.md): personal data, keys, limits, and what the app doesn't handle.
- [app/prompts/README.md](prompts/README.md): each prompt, schema, and model setting.

## Coming in M8

A script that resets the database to a known state before a demo. It isn't built yet.
