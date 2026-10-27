# Install and run the workbench

The workbench runs on your own computer. `app/run.sh` starts a small local server and opens the app in your web browser. You connect an AI in Settings, inside the app, with no file edits. Editing `app/.env` by hand still works as a fallback.

The 8 steps below are the quick start from the [README](../README.md#how-to-run-the-app), with more detail. For what each screen does, see [docs/use-cases.md](../docs/use-cases.md). For how it fits together, see [docs/architecture.md](../docs/architecture.md).

## What you need

- A Mac or a Linux computer, or Windows with WSL (see [On Windows](#on-windows)).
- Python 3.11 or newer, run as `python3`. run.sh uses the first `python3` on your PATH (the list of folders the terminal looks in for commands) and stops if it is older than 3.11. It never installs another Python.
- git.
- An internet connection the first time, to install the packages, and for live chats with Gemini.
- For live chats, a free Gemini key (step 5), Ollama on this computer, or a key for another OpenAI-compatible service. Without any of them, the app still runs: you can edit the spec, import chats, and try the screens with the fake model.

## Step by step

Each step says what it does in plain words, then gives the exact thing to click or paste, then what you should see.

### Step 1. Open a terminal

A terminal is a window where you type commands to your computer instead of clicking. You'll paste a few lines into it.

- **macOS:** press Cmd+Space, type `Terminal`, and press Return.
- **Linux:** open Terminal from your apps, or press Ctrl+Alt+T on Ubuntu.
- **Windows:** use the Ubuntu window from [On Windows](#on-windows).

To run a line from this page, copy it, click in the terminal, paste it (Cmd+V on macOS, Ctrl+Shift+V on Linux and in Ubuntu on Windows), and press Return.

You should see: a window with a blinking cursor at the end of a line that ends in `%` or `$`.

### Step 2. Check for Python and git

Python is the programming language the app is written in, and the app needs Python 3.11 or newer. Git is a tool that downloads the project's code. Check that you have both:

```bash
python3 --version
```

```bash
git --version
```

You should see: something like `Python 3.12.4` and `git version 2.45.0`.

If Python is older than 3.11, or either one says "command not found":

- **Python:** download it from https://www.python.org/downloads/ and run the installer. Then close the terminal, open a new one, and check again.
- **git on macOS:** `git --version` offers to install Apple's command line tools. Press Install, wait for it to finish, and check again. Or download git from https://git-scm.com/downloads.
- **git on Linux:** download it from https://git-scm.com/downloads, or on Ubuntu run `sudo apt install git`.

### Step 3. Get the code

The code lives in a repo (short for repository): a folder of files that git keeps track of, stored on GitHub. These two lines download your own copy and move the terminal into it:

```bash
git clone https://github.com/FlinnH/IS492-CharacterAI-Team-Project.git
```

```bash
cd IS492-CharacterAI-Team-Project
```

You should see: `Cloning into 'IS492-CharacterAI-Team-Project'...`, then the prompt again. `cd` means "change directory", so the terminal now works inside that folder, the repo root. Run every command below from there.

### Step 4. Start the app

The app is a small server: a program on your own computer that your web browser talks to. This line starts it. The first time, it also makes a virtual environment, a private folder (`app/.venv`) with the exact Python packages the app needs, so nothing else on your computer changes.

```bash
app/run.sh
```

The first run makes `app/.venv` and installs the pinned packages in `app/requirements.txt`. It prints pip's output and can take a minute or two. Later runs start right away, and reinstall only when `requirements.txt` changes. The server's own lines end with `Uvicorn running on http://127.0.0.1:8492`. Once the app answers, run.sh prints:

```
  The workbench is running at http://127.0.0.1:8492
  Your browser should open it now. If it doesn't, copy that address into your browser.
  Keep this window open while you use the app.
  Press Ctrl+C to stop.
```

Then it opens that address in your default browser: with `open` on macOS, `wslview` on WSL, or `xdg-open` on Linux. If none of them works, the second line says to open the address yourself, and the app keeps running. To start without opening the browser, run `app/run.sh --no-browser`.

You should see: the app on the Spec editor. The address 127.0.0.1 means "this computer", so nobody else can reach the app.

### Step 5. Get a free Gemini key

An API key is like a password that lets the app use Google's Gemini AI for you. Google's free tier needs no credit card.

1. Open https://aistudio.google.com/apikey and sign in with a Google account. If Google asks you to accept its terms, accept them.
2. If a key is already listed there (Google makes one for new users), use it. If not, press **Create API key** and follow the prompts.
3. Copy the key.

Keep the key out of every file except `app/.env`, and out of chats, commits, and screenshots. On the free tier, Google may read prompts and use them to improve its products, so never type real personal details into a chat. The free tier allows 15 calls a minute and 500 a day for each Gemini Flash-Lite model, and the count resets at midnight Pacific time.

### Step 6. Connect the key in Settings

1. In the app, press **Settings** in the top bar. Or open the Run a conversation tab: while no AI is connected, it says "No AI is connected yet." and shows **Connect an AI** next to Start run, which opens the same dialog.
2. Under Provider, "Gemini (Google AI Studio)" is already picked. Leave it.
3. Click in **Gemini API key** and paste your key. Show key shows what you pasted.
4. Press **Test**. It sends one tiny message to Harry's model with the settings as you typed them, before anything is saved. It can take up to half a minute. If it works, it says "Connected." with the model's name and how long it took. If not, it says what went wrong and what to do next.
5. If Test says "Gemini had a problem on its side.", Google's servers are busy with that model. Press Test again in a minute. Or, under Models, pick Gemini 3.5 Flash-Lite as Harry's model and press Test again: each model has its own capacity, and the judge's model moves to the other one by itself.
6. Press **Save**. It says "Settings saved." The settings take effect right away, with no restart, and Start run is ready.

Save writes the key to `app/.env`, readable only by your user account, and to nowhere else. The key never comes back to the page: Settings shows only that a key is saved and, for a long key, its last 4 characters. The app logs every Test and Save with its time (never the key), and every model call records the settings it used.

### Step 7. Take a 5-minute first tour

1. On your first visit, a short tour opens. Its 8 steps each point at one part of the screen and say what it's for. Press **Next** and **Back** to move through it, or **Skip tutorial** (or Escape) to close it. The **?** button at the right end of the top bar opens it again any time. The browser remembers that you've seen it, so it opens by itself only once.
2. Open the **Run a conversation** tab. Under **Scenario**, pick **F2: knowledge boundary**, then press **Start run**. You should see Alex's lines and Harry's replies appear one at a time. The script takes a minute or two, since calls start at least 4 seconds apart.
3. When it says "Script finished.", press **Check this chat**. The card counts the seconds while the AI judge reads the whole chat, which can take a minute.
4. Press **Review flags**. Each flag shows a quote from Harry and the spec line it breaks.
5. On a flag, press **Show in context** to see the quote in its turn, then press **Agree**. Agree stays locked until you open the context, so you always look at the evidence first.

A live chat may come back with no flags. Then press **Import a chat**, pick **Sample: Claude (CLA-F2)**, press **Import**, and press **Check this chat** on it. That chat always has at least one flag.

### Step 8. Stop and start again

To stop the app, click in the terminal where it runs and press Ctrl+C (hold Control and press C). The page in your browser stops working until you start the app again. Your specs, chats, and checks stay saved in `app/data/workbench.db`.

To start again later, open a terminal, go back to the repo folder, and run the start line:

```bash
cd IS492-CharacterAI-Team-Project
```

```bash
app/run.sh
```

## On Windows

run.sh is written for bash, the command shell that macOS and Linux use. The easiest way on Windows is WSL (Windows Subsystem for Linux), which runs Ubuntu Linux inside Windows:

1. Press the Windows key, type `PowerShell`, right-click Windows PowerShell, and choose Run as administrator.
2. Install WSL with Ubuntu, and restart Windows when it asks:

   ```powershell
   wsl --install
   ```

3. Open Ubuntu from the Start menu. The first time, it asks you to make a Linux user name and password.
4. In the Ubuntu window, install Python, git, and wslu, which lets run.sh open your Windows browser:

   ```bash
   sudo apt update && sudo apt install -y python3 python3-venv git wslu
   ```

5. Go on with [step 2](#step-2-check-for-python-and-git), typing every command in the Ubuntu window.

Ubuntu 24.04 and later come with Python 3.12. If `python3 --version` says 3.10 or older, update Ubuntu first.

Without WSL, PowerShell works too, but it can't run run.sh, so you type its steps yourself and open the browser by hand. Install Python 3.11 or newer from https://www.python.org/downloads/windows/ (tick "Add python.exe to PATH" in the installer) and git from https://git-scm.com/downloads/win. Then, in PowerShell, get the code, make the virtual environment, and install the packages:

```powershell
git clone https://github.com/FlinnH/IS492-CharacterAI-Team-Project.git
cd IS492-CharacterAI-Team-Project
py -3 -m venv app\.venv
app\.venv\Scripts\python -m pip install -r app\requirements.txt
```

Start the server, then open http://127.0.0.1:8492 in your browser. Ctrl+C stops it.

```powershell
cd app
.\.venv\Scripts\python -m workbench.main
```

To run the tests, from the repo root:

```powershell
app\.venv\Scripts\pytest
```

A few things differ on Windows:

- The repo's `.gitattributes` keeps LF line endings in every checkout, since the prompt manifest records each prompt file's exact bytes. A copy cloned before that file existed may have CRLF endings: then the server refuses to start with "changed after manifest.toml recorded it". Clone the repo again.
- `app/requirements.txt` adds `tzdata` on Windows only, since Python on Windows has no time zone data and the daily count follows Pacific days.
- Windows can't make `app/.env` readable by its owner alone, so keep your user account to yourself.
- The run.sh tests and the two file-mode checks are skipped on Windows.

We checked the Windows steps against the code, but haven't run them on a Windows computer.

## More in Settings

Besides the key, the Settings dialog has:

- **Models.** Harry's model (Gemini 3.1 Flash-Lite by default) and the judge's model (Gemini 3.5 Flash-Lite by default). If one model would do both, a note says the judge would be checking its own replies.
- **Limits.** Calls per minute, the daily cap, and the two session limits, with today's use in the header.
- **Advanced.** Two switches:
  - "Simulate a busy AI service (for demos)" makes every call to the first model fail as if busy, so the fallback model answers, until the server restarts. It doesn't change `app/.env`. While it's on, the Advanced header says "Busy service on".
  - "Decorations", on by default, shows a few faint drawings: a theater-mask mascot on empty screens, a magnifier while a check runs, and a small sparkle when the last flag in a chat gets your call (but not when you agreed with every flag). Switching it off hides them at once, with no Save, and only this browser remembers the choice. Switch it off for a study session. [docs/use-cases.md](../docs/use-cases.md) says where each drawing shows.

If a setting is also set in the shell that started the server, the shell wins, and Settings shows it as locked.

### Other providers

- **Local model (Ollama).** No key, and no internet once the model is downloaded. Install Ollama from https://ollama.com, then run `ollama pull gpt-oss:20b`, a large download. Ollama's default context of 4,096 tokens is too short, since the workbench sends the whole spec on every turn, and a short context cuts the chat off. So start Ollama yourself with a longer one, in its own terminal, and leave that terminal open:

  ```bash
  OLLAMA_CONTEXT_LENGTH=32768 ollama serve
  ```

  If it says `bind: address already in use`, Ollama is already running with its default context. On macOS that's usually the Ollama app, which starts at login: quit it from its icon in the menu bar, then run the command again. On Linux, stop the Ollama service first if the install set one up.

  In Settings, pick "Local model (Ollama)". The Local models section lists what Ollama has installed, and says so if `gpt-oss:20b` isn't there yet. If Ollama isn't running, it says that too, and Check again looks again. One local model both plays Harry and judges, so its flags say "Same model reviewed". Ollama has no fallback model.
- **Another service.** Pick "Another service (OpenAI, Claude, Grok, Groq, OpenRouter, and more)". The Service menu fills in the base URL for OpenAI, Anthropic Claude, xAI Grok, Groq, OpenRouter, Mistral, DeepSeek, or LM Studio on this computer, or choose Other and type one. Paste the service's key, type the model IDs for Harry's model and the judge's model, then Test and Save. Two of these services can play Harry but may fail as the judge: Anthropic's compatibility ignores the judge's JSON schema, and DeepSeek takes only plain JSON. When the judge's answer can't be read, a check falls back to the automatic checks. [app/prompts/README.md](prompts/README.md) lists the presets.

## Try it with no key: the fake model

To click through the screens with no key and no network, pick "Fake model (no network)" in Settings and press Save. Or put the line `WORKBENCH_PROVIDER=fake` in `app/.env` (make the file if there isn't one yet) and restart `app/run.sh`.

Every reply is then "This is a fake reply. No model was called." The fake judge never flags anything, so only the automatic checks flag breaks. That makes it useful for trying the screens, and useless as evidence. **Never use it for the demo.** Settings says so too: "Don't use it for the demo."

## Settings in app/.env (the fallback)

Every setting is listed in `app/.env.example`, with its default and a short note. To change one by hand, copy its line into `app/.env` (make the file if there isn't one yet) and edit it there, then restart `app/run.sh`. Values load from `app/.env.example`, then `app/.env`, then environment variables, and the last one wins. Git ignores `app/.env`.

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

It checks that a key is set and that the service lists each model in the Model menu. Then, for each model and each reasoning effort it compares, it runs the first 3 turns of F2. It prints a table of time to first token and token counts, never chat text, and today's count of calls. That's about 12 free-tier calls and about a minute when Gemini answers quickly. When Google is busy, retries add calls and it can take several minutes. A turn with no first words within 30 seconds shows "no first token in time" in the Error column. It logs its calls, and they count toward the daily cap. It won't run while `WORKBENCH_FORCE_MODEL_ERROR` is on, or with the fake model. It ends with an error when a model in the Model menu, or the judge's model, looks retired or rerouted: the service no longer lists it, or a reply says another model wrote it. Then pick another model in Settings. It also ends with an error when a model fails at the reasoning effort the models file sets for it.

## Reset before a demo

Stop the app first, then run this from the repo root:

```bash
app/.venv/bin/python app/scripts/reset_demo.py
```

It copies the database to `app/data/backups/`, with the date and time in the file name. Then it makes a fresh one: spec v1, and the CLA-F2 and GPT-F2 samples, each with the check saved in `app/samples/judge_snapshot.json`. The snapshot is a real AI judge run made earlier, so Check this chat on a sample shows the same flags every time, with no model call. Nothing else stays: no live runs, calls on flags, model calls, settings history, or events. The reset makes no model calls, takes under a second, and refuses while the app is running. The reset doesn't load the seeded transcript, so load it in Import a chat afterward. To undo a reset, stop the app and copy the backup over `app/data/workbench.db`.

After a reset, the count of calls used today starts over, since the app reads it from the database. Google's own count doesn't.

When the judge's model, reasoning effort, prompt, or schema changes, the reset warns, and each sample whose saved check no longer fits starts unchecked. With no snapshot file at all, both samples start unchecked. Make a new snapshot with 2 judge calls:

```bash
app/.venv/bin/python app/scripts/judge_snapshot.py
```

## Run the tests

From the repo root, after the first run:

```bash
app/.venv/bin/pytest
```

On Windows without WSL, run `app\.venv\Scripts\pytest` instead.

The tests use the fake model and a database in a temporary folder, so they need no key and no network, and they never read `app/.env` or touch `app/data/`.

The screen tests check the page's own files without opening a browser. `tests/test_screens.py` checks that every tour step points at a real part of the page, that the spec field reads Scene, and that the decorations stay faint and move only where they should. It also checks that every message sending you to another screen or to Settings has a button that goes there, that a running check counts its seconds, and that the tab icon is drawn in the page. `tests/test_styles.py` checks that text keeps enough contrast in both themes. `tests/test_smoke.py` runs run.sh's browser opener against a stand-in server, with pretend browsers. We check clicks and keyboard use on the screens by hand in a browser, as [docs/use-cases.md](../docs/use-cases.md) notes.

One live test, skipped unless you ask for it, runs 3 turns of F2 against the provider in `app/.env` and prints the logged call rows. It's the only test that reads `app/.env`. It uses about 3 free-tier calls, more when a busy Gemini makes the app try again:

```bash
app/.venv/bin/pytest tests/test_live.py --live -s
```

While Gemini is busy, this test can fail with an error like `assert 6 == 3` even though every turn got its reply. It expects one logged call per turn, and each retry logs one more. Run it again when Gemini is less busy.

## When something goes wrong

- **`run.sh: python3 not found. Install Python 3.11 or newer, then run this again.`** or **`run.sh: python3 is 3.10.x, and the workbench needs 3.11 or newer.`** Install Python 3.11 or newer (step 2) so that `python3` runs it. Close the terminal, open a new one, go back to the repo folder, and run `app/run.sh` again.
- **`run.sh: the workbench is already running at http://127.0.0.1:8492.`** An `app/run.sh` you started earlier is still running in another terminal window. Open http://127.0.0.1:8492 in your browser and use that one, or press Ctrl+C in that window first, then start it again.
- **The browser didn't open.** Copy the address from the terminal's last lines, like http://127.0.0.1:8492, into your browser. On WSL, install wslu (see [On Windows](#on-windows)) so run.sh can open your Windows browser.
- **`run.sh: app/.env has a missing or wrong value for ...`** The line names the setting. Fix it in `app/.env`, or delete that line to use the default.
- **`run.sh: app/.env.example has a value for GEMINI_API_KEY.`** Move the key to `app/.env` and leave the example empty.
- **A prompt file "changed after manifest.toml recorded it".** Undo the edit to that file in `app/prompts/`, or save it as the next version.
- **The database "was made by a newer version of the workbench".** Switch to the branch that made it, or delete the database file to start fresh, which deletes every saved chat and check.
- **"address already in use" when you start `app/run.sh`.** Another program, not the workbench, has port 8492. Stop that program, or set `WORKBENCH_PORT` in `app/.env` to another port, like 8493.
- **`bind: address already in use` when you start `ollama serve`.** Ollama is already running. Quit the Ollama app (or stop its service), then start it again with the command above.
- **"No AI is connected yet."** Press Connect an AI and follow the steps above.
- **"Gemini had a problem on its side."** (after Test) or **"The model service had a problem. Try again in a minute."** (in a chat). Google's servers are busy and answered with an error. Try again in a minute, or pick the other Gemini model as Harry's model in Settings. During a run, the app already tries again and then asks the other model before it shows this.
- **"Gemini didn't accept this key."** (after Test) or **"The model service didn't accept the key."** (in a chat). The pasted key is incomplete or has something extra, like a space. Copy it again from AI Studio, paste it in Settings, and press Test.
- **"Today's 200 model calls are used up."** Wait for midnight Pacific time, or raise the daily cap under Limits in Settings, up to 500.
- **Old screens after an update.** Reload the page. The server tells the browser to check every file again.
- **The tour opens on every visit.** The browser blocks the page's storage, as some private windows do, so it can't remember the tour, and the Decorations switch starts on again too. Press Skip tutorial. Everything else works the same.

## More docs

- [docs/use-cases.md](../docs/use-cases.md): each flow and edge case, with the tests that cover it.
- [docs/architecture.md](../docs/architecture.md): the parts and how a request moves through them.
- [docs/observability.md](../docs/observability.md): what the database logs, and queries for debugging.
- [docs/safety_privacy.md](../docs/safety_privacy.md): personal data, keys, limits, and what the app doesn't handle.
- [app/prompts/README.md](prompts/README.md): each prompt, schema, and model setting.
