# Install and run the workbench

Draft for CP3, updated in milestone M2. The app serves the workbench screens from a local server. The Spec editor saves spec versions, and Run a conversation streams live chats from a model or imports saved chats. Later milestones add the AI judge and the demo steps.

## What you need

- macOS or Linux with bash.
- Python 3.11 or newer, run as `python3`. Check with `python3 --version`. run.sh uses the first python3 on your PATH and stops if it is older than 3.11. It never installs another Python.
- An internet connection the first time, to install the packages, and for live chats with Gemini.
- For live chats, a free Google AI Studio key (see "Model key" below). Without one, the app still runs, and you can use the fake model or import chats.

## Run it

From the repo root:

```bash
app/run.sh
```

The first run makes `app/.venv`, installs the pinned packages in `app/requirements.txt`, and starts the server. Later runs start right away and reinstall only when `requirements.txt` changes.

Then open http://127.0.0.1:8492. To stop the server, press Ctrl+C in the terminal where it runs.

## Settings

`app/.env.example` lists every setting with its default value and a short note. To change one, copy that line into `app/.env` and edit it there. Git ignores `app/.env`. Values in `app/.env` win over `app/.env.example`, and environment variables win over both. A misspelled setting name in `app/.env` stops the server with an error that names it.

Never put a real key in `app/.env.example`. The server refuses to start if the example file holds one.

The limits live in `app/.env` too:

- `WORKBENCH_CALLS_PER_MINUTE` (15) spaces model calls at least 60/15 = 4 seconds apart, under the free per-minute limit.
- `WORKBENCH_DAILY_CALL_CAP` (200) stops model calls for the day once that many are made. The count starts over at midnight Pacific time, when Google's free quota resets.

Model IDs, reasoning effort, token limits, and prices live in `app/prompts/models.v1.toml`, next to the character prompt. A prompt file in use never changes: `app/prompts/manifest.toml` holds each file's hash, and the server refuses to start if one differs. To change a setting there, save the next version (like `models.v2.toml`) and point the manifest at it.

## Model key

Live chats call Gemini Flash-Lite on Google's free tier.

1. Make a key at https://aistudio.google.com/apikey.
2. Put it in `app/.env` as `GEMINI_API_KEY=your-key`. Keep it out of every other file, and out of chat.
3. Restart `app/run.sh`.

On the free tier, Google may read prompts and use them to improve its products, so never type personal details into a chat.

## Model services

`WORKBENCH_PROVIDER` in `app/.env` picks the service:

- `gemini` (the default): needs the key above. The Model menu offers Gemini 3.1 Flash-Lite (the default) and Gemini 3.5 Flash-Lite.
- `ollama`: a local model, `gpt-oss:20b`, with no key and no network. Install Ollama, run `ollama pull gpt-oss:20b`, and start it with a longer context than its default, for example `OLLAMA_CONTEXT_LENGTH=32768 ollama serve`. The workbench sends the whole spec on every turn, so a short context cuts the chat off.
- `fake`: no model and no network. Every reply is "This is a fake reply. No model was called." Use it to try the screens without a key.

## Run a conversation

1. Pick a scenario (T1, E1, E2, F1, or F2) and a model, then press Start run.
2. Each reply streams in as the model writes it. Calls start at least 4 seconds apart, so the screen sometimes says it's waiting.
3. Stop ends the reply and the script. The part already written is saved and marked Stopped.
4. After the script ends, or after Stop, type your own next line in the message box.

Every chat keeps the spec version it started with, even after you save a newer one. If the page reloads mid-run, the reply that was streaming is saved as stopped, and Continue run picks up the script.

## Import a chat

Import a chat on Run a conversation adds a saved chat to the Chat menu:

- **Paste or choose a file.** One message per line ("Alex: Hi."), a receipt log from `validation/transcripts/`, a markdown table with a speaker column, or a workbench chat in JSON. Preview shows how it was read before you import it. A row that can't be read is named by its number.
- **The samples.** CLA-F2 and GPT-F2, the CP2 chats from Claude and ChatGPT.
- **The seeded transcript.** It loads from the path in `WORKBENCH_SEEDED_TRANSCRIPT_PATH`, and only when you pick it.

## Preflight

Before a demo or a live test, check the model setup with real calls. Stop the server first, since call spacing is per process:

```bash
app/.venv/bin/python app/scripts/preflight.py
```

It checks that the key is set and that each model in the Model menu is listed. Then, for each model and each reasoning effort it compares, it runs the first 3 turns of F2. That is about 12 free-tier calls and takes about a minute. It prints time to first token and token counts, never chat text. Its calls are logged and count toward the daily cap.

## Run the tests

From the repo root, after the first run:

```bash
app/.venv/bin/pytest
```

The tests use the fake model, so they need no key and no network, and they never read `app/.env`.

One live test, skipped unless you ask for it, runs 3 turns of F2 against the provider in `app/.env` and prints the logged call rows. It is the only test that reads `app/.env`, and it uses about 3 free-tier calls:

```bash
app/.venv/bin/pytest tests/test_live.py --live -s
```

## Coming in later milestones

- **The AI judge (M3).** Flags on live and imported chats, with the evidence for each.
- **Demo reset (M8).** A script that resets the database to a known state before a demo.
