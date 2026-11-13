# AGENTS.md

Rules for any AI coding tool that works in this repo (Cursor, Claude Code, Copilot, Codex, and others), and for the person driving it. Every rule here is already enforced by a test or stated in a doc, and each one names where. If this file and a test disagree, the test is right, so fix this file.

For what CP4 still needs, start at [docs/cp4/TEAM_START_HERE.md](docs/cp4/TEAM_START_HERE.md).

## Run the app and the tests

- **App.** Run `app/run.sh` from the repo root. The first run makes `app/.venv` with the installed `python3` (3.11 or newer) and installs `app/requirements.txt`. Then it serves http://127.0.0.1:8492. `app/run.sh --no-browser` skips opening the browser. [app/INSTALL.md](app/INSTALL.md) has every step and every setting.
- **Tests.** Run `app/.venv/bin/pytest` from the repo root. The tests use a fake model and a database in a temporary folder, so they need no key and no network, and they never read `app/.env` or touch `app/data/`.
- **Run the tests before you push.** GitHub runs them again on every push and every pull request, on Python 3.11 and 3.12 (`.github/workflows/tests.yml`).
- **New tests** go in `tests/`. A test that opens a network connection fails. So does a test that opens `SEEDED_TRANSCRIPT.md` or `ANSWER_KEY.md` in `validation/fixtures/`. Both guards are in `tests/conftest.py`.

## Import layers

Each module in `app/workbench/` has a rank in `LAYERS` in `tests/test_contracts.py`. A module may import only modules ranked below it. A new module needs a rank there, or `test_imports_point_one_way` fails.

| Rank | Modules |
| --- | --- |
| 0 | schemas |
| 1 | config, redact, injection |
| 2 | db |
| 3 | telemetry, limiter, providers |
| 4 | gateway |
| 5 | specs, app_settings, rules, evidence |
| 6 | transcripts |
| 7 | runtime, judge |
| 8 | scenario_gen, recheck |
| 9 | review |
| 10 | main |

## Boundaries

`tests/test_contracts.py` also checks these:

- Only `db.py` imports `sqlite3`.
- Only `providers.py` imports `openai` and `httpx2`.
- Only `config.py` reads environment variables and the files in `app/prompts/`.
- Only `api.js` talks to the server. `app.js` has no `fetch(` and no `/api/` path.
- Every `data-action` in `app.js` and `index.html` has a handler in `actions[...]`.
- No spec line ID, like C17, appears in Python code, a migration, or `api.js`. Line IDs live in the spec.
- No model ID appears in Python code, `api.js`, or `app.js`. Model IDs live in the models file in `app/prompts/`.
- No service address from the presets file in `app/prompts/` appears in code, and no key prefix appears in the screens.
- The code in `app/workbench/` compiles on Python 3.11.
- `FakeProvider` takes the same arguments as `OpenAIProvider` in `stream`, `complete`, `list_models`, and `aclose`.

Other tests pin the screens:

- `index.html` loads `api.js`, then `app.js`, and no other script (`tests/test_smoke.py`).
- Text keeps a contrast of at least 4.5 to 1 in both themes (`tests/test_styles.py`).
- `localStorage` is touched only inside `try` (`tests/test_screens.py`).

[docs/architecture.md](docs/architecture.md) explains each part and why the boundaries are there.

## Versioned files

- **Prompts and model settings.** Every file that `app/prompts/manifest.toml` lists is versioned, like `judge.v1.md` and `models.v5.toml`. The manifest records the sha256 of each one, and the server refuses to start when a listed file's bytes changed. To change one, save a copy as the next version, add its hash under `[sha256]`, point `[current]` at it, and run the tests. [app/prompts/README.md](app/prompts/README.md) has the steps.
- **Schemas.** A schema file in `app/prompts/` must equal the schema of its Pydantic model in `app/workbench/schemas.py` (`tests/test_prompts.py`). So a schema change is a change to the model plus the next schema version.
- **Settings.** `app/.env.example` lists every setting with its default, and no setting has a default in code. A new setting is a new line there. `app/.env` overrides it on each computer.
- **Database.** A schema change is the next numbered file in `app/workbench/migrations/`. The files apply in order, and a database remembers the last number it applied, so a file that already ran never runs again. Pull `main` and take the next free number.

## What never changes

- **`prototype/`.** It is the finished CP2 deliverable, and the README marks it frozen. The tests read `prototype/data.js` to check that spec v1, the two sample chats, and the F2 script still match it (`tests/test_spec_api.py`, `tests/test_transcripts.py`). Copy from it, and never edit it.
- **Every file hashed in `app/prompts/manifest.toml`**, old versions included. A prompt or a models file that was used keeps its bytes, so a version in an old log row always means one exact text.

## No secrets in git

- A key lives only in `app/.env`. `.gitignore` covers it, along with `app/data/` and `private/`.
- `app/.env.example` lists each key's name with an empty value. The server refuses to start if the example file holds a key.
- Never put a key in code, a doc, a test, a fixture, a log line, a commit message, an issue, or a pull request. Tests use a made-up key with the fake model.
- No answer from the server and no database row holds a key (`tests/test_smoke.py`, `tests/test_settings.py`). [docs/safety_privacy.md](docs/safety_privacy.md#keys) has the full list.

## Prose rules

For docs, UI text, code comments, commit messages, issues, and pull requests:

- Plain English.
- Sentence-case headings.
- No em dashes and no en dashes.
- No curly quotes.
- ASCII only.

The tests already hold some text to these rules: the tour's words (`tests/test_screens.py`), and the sample, snapshot, and prompt files that must stay ASCII (`tests/test_transcripts.py`, `tests/test_demo.py`, `tests/test_prompts.py`).

## Before you push

1. Pull `main`, so your change sits on top of what teammates pushed.
2. Run `app/.venv/bin/pytest`, and push only when it passes.
3. Say which AI tools helped. Fill in "AI tools used" in the pull request, keep the tool's `Co-authored-by:` line in the commit message, and check that the tool is in the [AI Use Disclosure](README.md#ai-use-disclosure) table.
