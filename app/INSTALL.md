# Install and run the workbench

Draft for CP3 milestone M0. In M0 the app serves the CP2 prototype's screens from a local server and makes no AI calls. Later milestones add the model key, the database, and the demo steps.

## What you need

- macOS or Linux with bash.
- Python 3.11 or newer, run as `python3`. Check with `python3 --version`. run.sh uses the first python3 on your PATH and stops if it is older than 3.11. It never installs another Python.
- An internet connection the first time, to install the packages.

## Run it

From the repo root:

```bash
app/run.sh
```

The first run makes `app/.venv`, installs the pinned packages in `app/requirements.txt`, and starts the server. Later runs start right away and reinstall only when `requirements.txt` changes.

Then open http://127.0.0.1:8492. You should see the four workbench screens, just like the prototype. To stop the server, press Ctrl+C in the terminal where it runs.

## Settings

`app/.env.example` lists every setting with its default value and a short note. To change one, copy that line into `app/.env` and edit it there. Git ignores `app/.env`. Values in `app/.env` win over `app/.env.example`, and environment variables win over both. A misspelled setting name in `app/.env` stops the server with an error that names it.

Never put a real key in `app/.env.example`. The server refuses to start if the example file holds one.

## Run the tests

From the repo root, after the first run:

```bash
app/.venv/bin/pytest
```

The tests need no key and never read `app/.env`.

## Coming in later milestones

- **Model key (M2).** A free Google AI Studio key goes in `app/.env` as `GEMINI_API_KEY`. On the free tier, Google may read prompts and use them to improve its products, so never type personal details into a chat.
- **Ollama (M2).** A local option. Ollama's `gpt-oss:20b` starts with a 4,096-token context, so these steps will set `OLLAMA_CONTEXT_LENGTH` before you start Ollama.
- **Demo reset and preflight (M8).** Scripts that reset the database to a known state and check the model setup before a demo.
