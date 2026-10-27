# CHARACTER AI PROJECT

> **Beyond a Single Prompt: Building Consistent LLM Characters**

**Course:** IS 492 - Introduction to Generative AI for Human-AI Collaboration (Fall 2026)<br>
**Institution:** University of Illinois Urbana-Champaign <br>
**Instructor:** Dr. Yun Huang

**Stack:** Python 3.11 or newer, FastAPI, Uvicorn, and SQLite. The app calls Gemini 3.1 and 3.5 Flash-Lite through the OpenAI Python library, and its screens are the CP2 prototype's plain HTML, CSS, and JavaScript. To run it, see [How to run the app](#how-to-run-the-app).

---

## How to run the app

This quick start takes about 15 minutes the first time, and you don't need to have used a terminal before. Each step says what it does in plain words, then gives the exact thing to click or paste, then what you should see. [app/INSTALL.md](app/INSTALL.md) has the same steps with more detail, plus every setting.

On Windows, do the [Windows steps](#on-windows) first, then come back to step 2.

### Step 1. Open a terminal

A terminal is a window where you type commands to your computer instead of clicking. You'll paste a few lines into it.

- **macOS:** press Cmd+Space, type `Terminal`, and press Return.
- **Linux:** open Terminal from your apps, or press Ctrl+Alt+T on Ubuntu.
- **Windows:** use the Ubuntu window from the [Windows steps](#on-windows).

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

You should see: the first time, a minute or two of install lines. Then:

```
  The workbench is running at http://127.0.0.1:8492
  Your browser should open it now. If it doesn't, copy that address into your browser.
  Keep this window open while you use the app.
  Press Ctrl+C to stop.
```

Your browser opens the app on the Spec editor. The address 127.0.0.1 means "this computer", so nobody else can reach the app. To start it without opening the browser, run `app/run.sh --no-browser` instead.

### Step 5. Get a free Gemini key

An API key is like a password that lets the app use Google's Gemini AI for you. Google's free tier needs no credit card.

1. Open https://aistudio.google.com/apikey and sign in with a Google account. If Google asks you to accept its terms, accept them.
2. If a key is already listed there (Google makes one for new users), use it. If not, press **Create API key** and follow the prompts.
3. Copy the key.

Keep the key secret: never put it in a chat, a commit, or a screenshot. The app saves it only in `app/.env`, a settings file that git never uploads. On the free tier, Google may read what you send to Gemini, so never type real personal details into a chat.

### Step 6. Connect the key in Settings

1. In the app, press **Settings** in the top bar. (On the Run a conversation tab, **Connect an AI** opens the same dialog.)
2. Under Provider, "Gemini (Google AI Studio)" is already picked. Leave it.
3. Click in **Gemini API key** and paste your key.
4. Press **Test**. It sends one tiny message to Gemini, which can take up to half a minute.
5. Press **Save**.

You should see: "Connected." with the model's name after Test, and "Settings saved." after Save. If Test says "Gemini had a problem on its side.", Google is busy, so press Test again in a minute.

### Step 7. Take a 5-minute first tour

1. The first time the page opens, a short tour points at each part of the screen. Press **Next** to follow it, or **Skip tutorial** to close it. The **?** button at the right end of the top bar plays it again.
2. Open the **Run a conversation** tab. Under **Scenario**, pick **F2: knowledge boundary**, then press **Start run**. You should see Alex's lines and Harry's replies appear one at a time. The script takes a minute or two.
3. When it says "Script finished.", press **Check this chat**. The card counts the seconds while the AI judge reads the whole chat, which can take a minute.
4. Press **Review flags**. Each flag shows a quote from Harry and the spec line it breaks.
5. On a flag, press **Show in context** to see the quote in its turn, then press **Agree**. Agree stays locked until you open the context, so you always look at the evidence first.

If a live chat comes back with no flags, press **Import a chat**, pick **Sample: Claude (CLA-F2)**, press **Import**, and press **Check this chat** on it. That chat always has at least one flag.

### Step 8. Stop and start again

To stop the app, click in the terminal where it runs and press Ctrl+C (hold Control and press C). The page in your browser stops working until you start the app again. Your specs, chats, and checks stay saved in `app/data/workbench.db`.

To start again later, open a terminal, go back to the repo folder, and run the start line:

```bash
cd IS492-CharacterAI-Team-Project
```

```bash
app/run.sh
```

### If something goes wrong

The three most common problems:

1. **`run.sh: python3 not found.`** or **`run.sh: python3 is 3.10.x, and the workbench needs 3.11 or newer.`** Install Python 3.11 or newer (step 2). Close the terminal, open a new one, go back to the repo folder, and run `app/run.sh` again.
2. **`run.sh: the workbench is already running at http://127.0.0.1:8492.`** It's still running in another terminal window. Open http://127.0.0.1:8492 in your browser and use that one. Or press Ctrl+C in that window first, then start it again here.
3. **Test says "Gemini didn't accept this key."** The copy lost part of the key or picked up something extra, like a space. Copy it again from AI Studio, paste it into Settings, and press Test again.

[app/INSTALL.md](app/INSTALL.md#when-something-goes-wrong) lists the rest.

To run the app's tests (they need no key and no network):

```bash
app/.venv/bin/pytest
```

### On Windows

run.sh is written for bash, the command shell that macOS and Linux use. The easiest way to run it on Windows is WSL (Windows Subsystem for Linux), which runs Ubuntu Linux inside Windows:

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

We checked the Windows steps against the code, but haven't run them on a Windows computer.

---

## What the app does

The app covers the seven features in [validation/OPPORTUNITY_FRAMING.md](validation/OPPORTUNITY_FRAMING.md). Our example character is Harry Potter right after book 4.

| # | Feature | Where it is in the app | Walkthrough |
| --- | --- | --- | --- |
| 1 | Evidence-first flag review | Flag review: each flag card shows the quote, the spec line it cites, and a confidence. Agree unlocks after Show in context, and Override needs a reason of 3 words or more. | [4. Check a chat and review its flags](docs/use-cases.md#4-check-a-chat-and-review-its-flags) |
| 2 | A built-in follow-up re-check | Flag review: the Follow-up re-check card, with Your question (optional) and Re-check, then What changed in the re-check | [5. Re-check the weakest calls](docs/use-cases.md#5-re-check-the-weakest-calls) |
| 3 | A structured spec with line IDs, a version history, and a setting field that warns when it's empty | Spec editor: line IDs like C17, Edit spec, the Scene field, and Save as v2 | [1. Define a spec](docs/use-cases.md#1-define-a-spec), [Empty scene](docs/use-cases.md#empty-scene) |
| 4 | Automatic checks for measurable rules, like sentence count and banned words | Run a conversation: Check this chat runs them on every reply first, with no AI. Their flags say Automatic check. | [4. Check a chat and review its flags](docs/use-cases.md#4-check-a-chat-and-review-its-flags) |
| 5 | A provenance check | Flag review: a flag titled "invented claim about the user". The check flags claims about the user that the user never made, and other unsupported facts are caught by the judge's factual-contradiction type. | [4. Check a chat and review its flags](docs/use-cases.md#4-check-a-chat-and-review-its-flags) |
| 6 | Compare runs | Compare runs: Where each chat broke, Turn by turn, and each chat's first break | [6. Repair: compare runs, then save v2](docs/use-cases.md#6-repair-compare-runs-then-save-v2) |
| 7 | Persona-exit and near-boundary cues | Flag review: "Needs your call" on the card, with the reason only the creator can settle it | [4. Check a chat and review its flags](docs/use-cases.md#4-check-a-chat-and-review-its-flags) |

---

## How it's built

**The stack, in detail:**

- **Server.** Python 3.11 or newer, with FastAPI 0.143 and its built-in server-sent events, Uvicorn 0.54 with one worker, and Pydantic 2.14.
- **Database.** SQLite, through Python's own `sqlite3`, in one local file (`app/data/workbench.db`).
- **Models.** The openai 3.24 library on httpx2 calls Google's OpenAI-compatible endpoint:
  - Gemini 3.1 Flash-Lite plays the character.
  - Gemini 3.5 Flash-Lite is the AI judge and the re-check.
  - Both run on the free tier.
  - Settings can switch to `gpt-oss:20b` on the creator's own computer through Ollama, or to another OpenAI-compatible service.
- **Screens.** Plain HTML, CSS, and JavaScript in `app/static/`, copied from the CP2 prototype, with Google's Material 3 design. They add a first-visit tour and a few quiet drawings, like a theater-mask mascot in empty screens, drawn in the page itself so they work offline. The Decorations switch in Settings turns the drawings off.
- **Tests.** pytest 9.1, with a fake model in place of the real ones. The tests that cover the screens check the page's files without opening a browser.

**The CP3 docs:**

- [docs/architecture.md](docs/architecture.md): the architecture diagram and the parts.
- [docs/use-cases.md](docs/use-cases.md): each flow and edge case, with its tests.
- [docs/observability.md](docs/observability.md): the telemetry plan, what we log, and debugging queries.
- [docs/safety_privacy.md](docs/safety_privacy.md): safety and privacy.
- [app/prompts/README.md](app/prompts/README.md): the prompts and model settings.

---

## Team Members & Roles

| Name | GitHub | Role / Domain Ownership | Contact |
| --- | --- | --- | --- |
| Gawon Lim | @Gawonl2 | Team Lead, Tech Stack | gawonl2@illinois.edu |
| Flynn Huynh | @FlinnH | Co-Lead, Prep & Debug, GitHub Management | fhuynh2@illinois.edu |
| Kiara Gao | @hantarita | Co-Lead, Designer & Literature & Logistics | jiaqig11@illinois.edu |

---

## Problem Statement & Motivation

> *What human problem are we solving? Who experiences it? Why does it matter
> right now - scale, urgency, and why AI is the relevant answer?*

Based on our experience, an LLM character usually holds up for about ten turns. After that it starts to
come apart: it forgets what it was told earlier, contradicts its own backstory,
slides back into generic assistant politeness, or answers something it should
have no way of knowing. Whoever wrote the character can tell something broke,
but usually not what or why, so the only move left is to rewrite the prompt and
try again.

We think the people this hurts are worth naming. Game writers, interactive
fiction authors, instructors building teaching personas, and developers shipping
role-play apps all spend real time defining a character and then have no
reliable way to make a model hold it. Players and students on the other side of
the conversation feel the same failures as a loss of trust. Nobody experiences a
character as a set of separate technical features.

The scale is already there. Character.AI reportedly hosts around 18 million
user-created characters, and downloads of AI companion and role-play apps grew
88% year over year in the first half of 2025, to roughly 60 million.

Nonetheless, this is not an unanswered question. Research has good answers to each failure mode on its own: long-term memory,
retrieval-augmented generation, persona prompting, dialogue-style control, and
preference-based alignment. They are almost always evaluated separately, and we
suspect that is where the real gap sits. A system can score well on memory and
well on factual grounding and still feel incoherent as a character, because the
components interact and sometimes compete. Retrieved facts can override how the
character would behave. Style conditioning can pull against what the situation
calls for.

Generative AI is also doing the work here rather than decorating it. The character is
generated, thus the failures are generative failures. We believe the open question is whether these
techniques can be combined into one system that holds the character's identity across turns and
situations while staying contextually appropriate, and
conversational.

<sub>Character count and app download figures from Businessofapps and
Appfigures data reported by TechCrunch (August 2025). Industry estimates,
not peer-reviewed.</sub>

---

## Target Users & Core Tasks

**Primary user:** Character creators. Game writers and narrative designers,
interactive fiction authors, instructors building persona-based learning agents,
and developers building role-play applications. They already know who their
character is. What they lack is a reliable way to make a model hold it.

**Secondary user:** The people talking to those characters, such as players and
students, who experience consistency failures as broken immersion and have no
way to report or repair them.

**Top 3 tasks they accomplish:**

1. Define the character as a structured specification (backstory, voice,
   relationships, knowledge boundary, behavioral rules) instead of one long
   free-text prompt.
2. Stress-test it by running extended and adversarial conversation, then see
   where identity breaks and which failure caused it: memory loss, factual
   contradiction, style drift, situational mismatch, or knowledge the character
   should not have.
3. Repair and compare by adjusting memory, retrieval, and conditioning
   settings, re-running the same scenario, and checking whether consistency
   actually improved.

**What success looks like:** A creator can take a character from specification
to a version that holds up across a long conversation without blind prompt
rewriting. We are hoping that in
the integrated approach to test it directly: the combined configuration should
produce measurably fewer consistency failures than baseline prompting with Gen AI on the
same character and scenario. We plan to run that comparison as a formal ablation
in Checkpoint 4.

---

## Competitive Landscape

> *Existing systems and where they fall short - in UX, reliability, cost,
> safety, or scope.*

| Existing system | What it does well | Where it falls short |
| --- | --- | --- |
| **Character.AI**<br>Consumer platform for chatting with user-created characters | Massive reach: about 20M monthly active users and roughly 18M user-created characters. It is actively working on long-chat consistency, shipping a new default model pitched on in-character consistency (April 2026) and Story Memory and pinned Facts (May 2026). | Closed and platform-locked. Memory fixes are end-user features inside one proprietary model, so a developer cannot see why a character broke, test it against a fixed scenario, or carry the fix into their own product. Safety failures surfaced after harm: it banned open-ended chat for under-18 users in November 2025, and the first teen-harm lawsuits settled in January 2026. |
| **Replika**<br>Single long-term AI companion with persistent memory | Strong emotional bonding built on remembering the user over months. Peer-reviewed survey work finds users report high perceived social support (Maples et al., 2024). | Shows what happens when continuity breaks: after the Replika 2.0 rebuild (April 2026) changed its memory architecture, long-time users on r/Replika reported companions losing memories they had built over years. Consistency is not inspectable or testable from outside. Documented relational harms, including "algorithmic compliance" with harmful user statements (Zhang et al., 2025), a €5M GDPR fine from Italy's data protection authority (2025), and a consumer complaint to the FTC over manipulative design. |
| **Inworld AI**<br>Commercial character engine for games and interactive media | Closest to what developers need in production: a Character Brain (personality, emotion, memory, goals), a Contextual Mesh (world knowledge, narrative and safety constraints), real-time voice, and Unity and Unreal integrations. Adopted by studios such as Xbox and Ubisoft. | Consistency is a black box. There is no transparent way to stress-test a character over long or adversarial conversations, attribute a failure to memory, knowledge, or style, or compare configurations with evidence. Built for studios, it is heavyweight and platform-locked for independent, educational, or research developers. |

<sub>Sources: Character.AI usage figures from Demandsage and Business of Apps
(2026); policy and lawsuit reporting from Fortune (Oct 2025) and Bloomberg Law
(Jan 2026). Replika research from Maples et al. (2024) and Zhang et al. (2025);
GDPR fine from the European Data Protection Board (May 2025); FTC complaint
reported by TIME (Jan 2025); memory-loss reports collected from r/Replika by
secondary blogs (2026). Inworld architecture from Inworld and NVIDIA. Usage
figures are industry estimates, not peer-reviewed.</sub>

---

## Initial Concept & Value Proposition

> *What are we building, and why is generative AI functionally essential to it
> rather than decorative?*

We are building a creator-facing workbench for designing, running, and evaluating
LLM characters. A creator starts with a structured character specification:
backstory, personality, relationships, knowledge boundaries, and behavioral
rules. The system then combines that specification with long-term conversation
memory, character-specific retrieval, current situational context, dialogue-style
conditioning, and preference-based alignment to generate the character's response
at each turn.

The important part is not simply putting these components into one pipeline. The
tool will make the pipeline testable. Creators will be able to run the same
character through fixed long-form or adversarial scenarios, inspect where its
behavior starts to break, and compare different system configurations. For
example, the same scenario could be run with baseline prompting, then with
memory, then retrieval, then the full integrated system. We can therefore study
both whether the final character is more believable and which components actually
contribute to that improvement.

Our MVP has two connected sides:

Character runtime: generates dialogue using persona, memory, retrieved
knowledge, conversation history, and situational context rather than relying
on a single static system prompt.
Evaluation and debugging layer: tracks failures such as persona drift,
memory loss, factual contradiction, inappropriate knowledge, style drift, and
situational mismatch so creators can identify what failed instead of blindly
rewriting the prompt.

The value proposition is straightforward: give character creators a way to
build an LLM character as a system, not just a prompt, and to test whether that
system actually preserves the character over time.

Generative AI is functionally essential because the central behavior being
studied is open-ended language generation. The system must respond to dialogue
and situations that cannot be exhaustively scripted in advance while balancing
several potentially competing constraints: what the character knows, what it
remembers, how it normally speaks, how it relates to the user, and what is
appropriate in the current situation. A conventional rules engine can retrieve
facts or select predefined dialogue, but it cannot provide the same flexible,
natural response generation that makes these character experiences useful in the
first place. At the same time, using an LLM creates the consistency problem this
project is designed to investigate, making generative AI both the enabling
technology and the object of evaluation.

---

## Milestones Roadmap

| Checkpoint | Target | Deliverables |
| --- | --- | --- |
| **CP1** | Sep 17 *(confirmed)* | Public repo and project board, literature review with individual reflections, formal proposal, and kickoff presentation. |
| **CP2** | Oct 8 *(confirmed)* | A prompting study of three existing tools (Claude, ChatGPT, and Gemini) covering typical, edge, and failure cases; speed-dating interviews and a gap analysis read through the Gonzalez et al. (2026) complementarity framework; a design spec with user journeys, key screens, and collaboration mechanics; and a clickable prototype of the Define, Stress-test, Diagnose, and Repair loop. |
| **CP3** | Oct 30 *(estimated)* | A working end-to-end MVP: a character runtime that generates dialogue from a structured specification, and an evaluation layer that reports where and why a character breaks. Demonstrated live on Harry Potter, our example character, with setup instructions and an architecture diagram. |
| **CP4** | Dec 4 *(estimated)* | Evaluation comparing the integrated system against baseline prompting on the same characters and scenarios, a user study with character creators, and the final report. |

> CP3 delivered the spec-only character runtime and the evaluation layer, and memory and retrieval move to CP4 as on and off comparisons against this baseline.

---

## Repository Structure

```
README.md         This page
DESIGN_SPEC.md    CP2 design spec: personas, journeys, screens, and collaboration mechanics
LICENSE           MIT License
.gitattributes    Keeps LF line endings on every computer, Windows included
/proposal/        PROPOSAL.md, the formal proposal
/literature/      Papers and the unified bibliography
/reflections/     Individual reading reflections (one file per student)
/slides/          Checkpoint presentation decks, one folder per checkpoint
  cp1/, cp2/      The CP1 and CP2 decks and figures, and the CP2 slide plan
  cp3/            CP3_SLIDE_PLAN.md, the CP3 slide plan
/validation/      CP2 prompting study, interviews, gap analysis, theory lens, and the chat receipts
/prototype/       CP2 clickable prototype (frozen)
/app/             CP3 app: run.sh, INSTALL.md, .env.example, requirements.txt
  workbench/      The Python server: routes, services, model gateway, providers, and migrations
  static/         The screens: index.html, styles.css, api.js, app.js
  prompts/        The rubric's /prompts/: versioned system prompts, output schemas, and model settings
  samples/        Spec v1, the test scripts, the CP2 sample chats, the planted-instruction sample,
                  the fake model's reply, and the judge snapshot for the demo reset
  scripts/        preflight.py (checks the model setup with real calls), reset_demo.py (resets
                  the database before a demo), and judge_snapshot.py (remakes the judge snapshot)
  data/           The SQLite database, made on the first run (git ignores it)
/docs/            Architecture, use cases, observability, safety and privacy, and the CP2 storyboard and wireframes
/tests/           The app's tests (pytest, with a fake model, no key, and no network)
  fixtures/       Small chat files for the import tests
```

---

## AI Use Disclosure

Per the course policy on responsible use and disclosure of AI tools, every AI
tool and model used in this project is disclosed here. The prompts the app
itself sends to models are in [app/prompts/](app/prompts/README.md).

| Tool / Model | Used for | Team member |
| --- | --- | --- |
| Anthropic | Literature search, README drafting and editing, repo initial file template | Flynn |
| Anthropic | Competitive landscape research and drafting, bibliography formatting | Kiara |
| ChatGPT| Refining md writings and slide texts| Gawon |
| NotebookLM | understanding and extracting key information for Literature Review | Gawon |
| Anthropic | CP2: planning the workflow + starter files | Flynn |
| Claude Code | CP2: building the clickable prototype in prototype/ from Flynn's prompts | Flynn |
| Anthropic | CP3: planning the stack, the free model setup, and the step-by-step build prompts | Flynn |
| Claude Code | CP3: planning and building the working app in app/, its tests in tests/, and the CP3 docs (milestones M0 to M8 and the final CP3 sessions), from Flynn's prompts | Flynn |

Datasets: the character spec was written by the team from the Harry Potter books' canon, the CP2 chats came from Claude, ChatGPT, and Gemini, and the seeded transcript and the planted-instruction sample are team-written.

Claude (Sonnet 5.5), ChatGPT, and Gemini (Flash-Lite) were also the subjects of the CP2 prompting study. Their outputs are logged in [validation/transcripts/](validation/transcripts/).

The CP3 app calls AI models itself. By default it uses Google's free tier:

- Gemini 3.1 Flash-Lite plays the character.
- Gemini 3.5 Flash-Lite is the AI judge and the follow-up re-check.
- In Settings, a creator can switch to gpt-oss:20b on their own computer through Ollama, or to another OpenAI-compatible service.

Its prompts, output schemas, and model settings are in [app/prompts/](app/prompts/README.md).

---

## License

Code and documentation in this repository are released under the MIT License
(see LICENSE). Academic papers stored in `/literature/pdfs/` remain under their
original copyright and are included for course reference only.
