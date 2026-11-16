# How to finish CP4

Hi Gawon and Kiara. This is the long version of [the start page](TEAM_START_HERE.md). I wrote it so you guys can finish CP4 without me.

Nothing here is an order. Where I suggest something, I say "my suggestion", and the choice is yours. You know your own time and strengths better than I do.

You don't need to read it all. Find your task in the list, and follow that section.

## Contents

1. [Run the app on your laptop](#1-run-the-app-on-your-laptop)
2. [Track B, step by step](#2-track-b-step-by-step)
3. [Track A without new building](#3-track-a-without-new-building)
4. [Ablations](#4-ablations)
5. [The report](#5-the-report)
6. [The slides and the talk](#6-the-slides-and-the-talk)
7. [The package](#7-the-package)
8. [Submitting](#8-submitting)
9. [A day-by-day plan](#9-a-day-by-day-plan)
10. [Troubleshooting](#10-troubleshooting)
11. [What CP2 and CP3 already found](#11-what-cp2-and-cp3-already-found)

## Three things to know first

- **The toolkit doesn't exist yet.** I planned scripts for exports, scoring, and charts, and I ran out of time. If a file named `analysis/README.md` exists, someone built it, so use its commands. If not, every section here has a way by hand.
- **The public link doesn't exist yet either.** If a file named `docs/deployment.md` exists, the link is in it. If not, [section 7](#7-the-package) says what to do.
- **An AI tool can help with one section at a time.** For example, tell it: "Read AGENTS.md and section 2 of docs/cp4/HOW_TO_FINISH_CP4.md, then help me with step 3."

On Nov 15, 2026, the import, check, database, and query steps here were run on a scratch copy of the app on my Mac. The Windows steps were only checked against the code.

## 1. Run the app on your laptop

These are the steps from [app/INSTALL.md](../../app/INSTALL.md), in short form. That file explains each one in more detail. The steps are for a Mac or Linux. Windows is at the end of this section.

1. Open a terminal. On a Mac, press Cmd+Space, type `Terminal`, and press Return.

   You should see: a window with a blinking cursor.

2. Check for Python and git.

   ```bash
   python3 --version
   ```

   ```bash
   git --version
   ```

   You should see: something like `Python 3.12.4` and `git version 2.45.0`. Python must be 3.11 or newer.

3. Get the code. If you already have the repo, go into its folder instead. Then run `git checkout main` and `git pull`.

   ```bash
   git clone https://github.com/FlinnH/IS492-CharacterAI-Team-Project.git
   ```

   ```bash
   cd IS492-CharacterAI-Team-Project
   ```

   You should see: `Cloning into 'IS492-CharacterAI-Team-Project'...`, then the prompt again. If you already had the repo, you should see `Already up to date.` or a list of files. Run every later command from this folder.

4. Start the app.

   ```bash
   app/run.sh
   ```

   You should see: a minute or two of install lines the first time. Then "The workbench is running at http://127.0.0.1:8492", and your browser opens the Spec editor. A short tour opens the first time. Press **Next**, or **Skip tutorial**.

5. Get a free Gemini key. Open https://aistudio.google.com/apikey and sign in with a Google account. Use the key listed there, or press **Create API key**. Copy it.

   You should see: a key you can copy. Treat it like a password. Please each use your own Google account, so you each get your own daily allowance.

6. Connect the key. In the app, press **Settings** in the top bar. "Gemini (Google AI Studio)" is already picked. Paste the key into **Gemini API key**, press **Test**, then press **Save**.

   You should see: "Connected." with the model's name after Test, and "Settings saved." after Save. Save writes the key into `app/.env` for you. Git ignores that file.

   The fallback, by hand: make a file named `app/.env` with one line, `GEMINI_API_KEY=` followed by your key. Then start the app again.

7. Try one test case. Open the **Run Test Cases** tab. Under **Test Case**, pick **F2: knowledge boundary**, and press **Start Test**. When it says "Test case finished.", press **Check this chat**, then **Review flags**.

   You should see: flag cards, each with a quote from Harry and the spec line it breaks. If it says "No flags.", there is no Review flags button. In that case, press **Import a chat** on the same screen. Pick **Sample: Claude (CLA-F2)**, press **Import**, and check that one.

8. Stop and start again. Click in the terminal and press Ctrl+C to stop. Run `app/run.sh` to start again.

   You should see: your chats and checks still there. They are saved in `app/data/workbench.db`.

To run the tests, which need no key and no network:

```bash
app/.venv/bin/pytest
```

You should see: a last line with a count of `passed` and no `failed`.

### On Windows

[app/INSTALL.md](../../app/INSTALL.md#on-windows) has the Windows steps. The easy way is WSL, which runs Ubuntu Linux inside Windows.

1. Open PowerShell as administrator and install WSL. Restart Windows when it asks.

   ```powershell
   wsl --install
   ```

2. Open Ubuntu from the Start menu, and install what the app needs.

   ```bash
   sudo apt update && sudo apt install -y python3 python3-venv git wslu
   ```

3. Do steps 2 to 8 above in the Ubuntu window.

INSTALL.md also has a way with PowerShell alone, without WSL. I checked the Windows steps against the code, but I never ran them on a Windows computer. So please go slowly there.

### The screens

- **Spec editor.** The character, written down one numbered line at a time, like C17. **Edit spec** changes a line and saves a new version.
- **Run Test Cases.** Pick a Test Case and press **Start Test**. The AI writes Alex's lines, and Harry answers live.
- **Free Chat.** Type to Harry yourself, with no script. Gawon added this one after CP3.
- **Flag review.** Each flag shows Harry's quote, the spec line it breaks, and a confidence. You open the evidence, then press **Agree** or **Override**.
- **Compare runs.** Chats of the same test case, side by side. It shows where each one broke.

[docs/use-cases.md](../use-cases.md) walks through every screen.

## 2. Track B, step by step

Track B tests the AI judge with experiments and no participants. It is my pick in [DECISIONS.md](DECISIONS.md#1-track-a-or-track-b), and the choice is yours.

The whole job in five lines:

1. Make about 8 test chats, each with an answer sheet.
2. Run two setups on every chat: a plain prompt (the baseline) and our full judge.
3. Score both against the answer sheets.
4. Change one knob at a time ([section 4](#4-ablations)).
5. Write the error analysis, and make the charts.

Before the first real run, agree on three things. Write them in `docs/study_materials/protocol.md`, a copy of [protocol_TEMPLATE.md](../study_materials/protocol_TEMPLATE.md).

- How many chats, and who makes which.
- What counts as a catch (see step 8).
- The baseline's exact instruction (see step 7).

After the first real run, please don't change the test chats or the answer sheets. A change in the middle makes the runs impossible to compare.

Please also leave the files in `app/prompts/` as they are, at any time. The app checks them, and won't start if one changed.

The numbers in this section are my suggestions from DECISIONS.md: about 8 chats, 4 to 6 mistakes, and 3 to 5 runs. Change them if you like.

### Step 1. Make a test chat

1. Start the app ([section 1](#1-run-the-app-on-your-laptop)), and open **Run Test Cases**.

   You should see: a **Test Case** menu with T1, E1, E2, F1, F2, A1, A2, and Custom.

2. Pick a test case. My suggestion: use different ones across the set, such as F2, E1, A1, and Custom. Custom also needs the **What to test** box filled in.
3. Press **Start Test**.

   You should see: a progress bar while the AI writes the lines. Then Alex's lines and Harry's replies appear one at a time. It ends with "Test case finished."

One test case uses one AI call to write it, plus one call for each reply. A1, A2, and E1 are the long ones. Please leave **Run All Test Cases** alone here. It plays every case, which is about 100 calls.

### Step 2. Get the chat out of the app

The app has no export button, so there are two ways to do this.

**Way 1, copy from the screen.** Select the chat's text on Run Test Cases, and paste it into your file. Then make each message one table row, like `| 1 | Alex | Hi Harry. |`. Number every message from 1, and don't reuse the screen's turn numbers.

**Way 2, the chat as data.** This is my suggestion, because it keeps every line exact.

1. With the app running, open http://127.0.0.1:8492/api/chats in your browser.

   You should see: plain text that lists every chat, newest first. Each one has an `"id"` number and a `"title"`.

2. Open a second terminal window, and run this one line. Change only the `1` right after `/api/chats/` to your chat's id. The newest chat is listed first, so its `"id"` comes first.

   ```bash
   curl -s http://127.0.0.1:8492/api/chats/1 | python3 -c "import json,sys; c=json.load(sys.stdin); [print('|', n, '|', c['character_name'] if m['speaker']=='character' else c['user_name'], '|', ' '.join(m['text'].split()).replace('|','/'), '|') for n, m in enumerate(c['messages'], 1)]"
   ```

   You should see: one table row for each line of the chat, like `| 1 | Alex | Hi Harry. |`. The rows are numbered from 1.

3. Copy [test_chat_TEMPLATE.md](../study_materials/test_chat_TEMPLATE.md) to a file like `docs/study_materials/test_chat_01.md`. Paste the rows under the table's header, in place of the empty rows.

If that long line fails, open http://127.0.0.1:8492/api/chats/1 in the browser and copy each `"text"` by hand.

### Step 3. Plant the mistakes

1. In your test chat file, change 4 to 6 of Harry's lines, so each one breaks one spec line. Leave Alex's lines alone.
2. Read the spec while you do it. It is on the Spec editor screen, and in [CHARACTER_SPEC.md](../../validation/fixtures/CHARACTER_SPEC.md).
3. Mix the kinds. The answer sheet template lists the eight failure types. Make some mistakes obvious and some subtle.
4. Add 1 or 2 decoys. A decoy is a line that looks wrong but is fine.

A real chat can already hold mistakes that nobody planted. Read every one of Harry's lines against the spec, and list those too.

An example: spec line B4 allows 1 to 4 sentences. Rewrite one of Harry's replies to run 6 sentences. Its answer sheet row is that line, `style drift`, B4, and obvious.

Don't build a mistake on an email, a phone number, or a long code. Import replaces those with a label before the judge reads the chat.

### Step 4. Fill in the answer sheet

1. Copy [answer_key_TEMPLATE.md](../study_materials/answer_key_TEMPLATE.md) to a file with the same number, like `answer_key_01.md`.
2. Add one row for each mistake: the line, the type, the spec line's ID, subtle or obvious, and why.
3. Write the type exactly as the template lists it, like `knowledge-boundary violation`. The judge uses the same names.
4. Fill in the Decoys and the Clean lines tables.

For Track B, save both files in `docs/study_materials/`. Nobody takes part, so nothing needs to stay hidden.

### Step 5. Swap and check

1. Send your chat and answer sheet to the other person in a pull request that says "Part of #104". This is for Track B only. Track A's chats stay off GitHub ([section 3](#3-track-a-without-new-building)).
2. The other person checks each row against the chat and the spec. They also read Harry's other lines for mistakes nobody planted.
3. They write their name on the **Checked by** line, with the date.

You should see: every answer sheet with two names on it, **Made by** and **Checked by**.

### Step 6. Run the full judge

1. On **Run Test Cases**, press **Import a chat**.

   You should see: a dialog named "Import a chat".

2. Leave "Paste it, or choose a file" picked. Paste the whole test chat file into the **Chat** box, heading and all. In **Receipt ID (optional)**, type a short name like `TC01`.
3. Check that "Spec version this chat used" shows the version you made the chat with.
4. Press **Preview**.

   You should see: a line like "TC01: 6 messages (lines 1 to 6), pinned to v1." Under it, Alex is "the other speaker" and Harry is "the character". It also says it skipped a few lines that aren't messages. Those are the file's heading and notes, which is fine.

5. Press **Import**.

   You should see: "TC01, imported" in the Chat menu, with an Imported chip above the chat's lines.

6. Press **Check this chat**.

   You should see: a card that counts the seconds. Then a line like "3 flags: 1 from automatic checks and 2 from the AI judge."

7. Press **Review flags**. Each card's title has the line and the type, like "Line 4, style drift". Under the quote is the spec line, like B4. Write down all three for every flag.

My suggestion: don't press Agree or Override during the benchmark. It measures the judge alone, and Kiara's CP3 test did the same.

If the results show "(fallback)" or "AI judge: unavailable", please don't count that run. Redo it later in a fresh database file (step 9).

A faster way to list the flags, if `sqlite3 --version` prints a version on your computer:

```bash
sqlite3 -readonly -box app/data/workbench.db "SELECT t.receipt AS chat, f.turn AS line, f.also_turns AS also_lines, f.source, f.type, f.line_id, f.confidence, f.status FROM flags AS f JOIN transcripts AS t ON t.id = f.transcript_id ORDER BY t.receipt, f.turn;"
```

You should see: a table with one row for each flag. In the source column, `rule` means an automatic check. Skip any row whose status is `withdrawn`.

If it says `-box` is an unknown option, use `-column -header` in its place. In Ubuntu, `sudo apt install -y sqlite3` installs it.

If you changed the database file (step 9), put its name in place of `workbench.db`. If `sqlite3` isn't installed, read the flags off the Flag review screen.

### Step 7. Run the baseline by hand

The baseline is a plain prompt. A model gets the spec and the chat, and lists the lines that break the spec. It has no evidence check and no automatic rules, which is the point of the comparison.

1. Open a free chatbot. My suggestion: Google AI Studio at https://aistudio.google.com. If its model menu lists the judge's model, Gemini 3.5 Flash-Lite, pick that one. If not, pick the closest one.
2. Start a new chat for every test chat and every repeat, so nothing carries over.
3. Paste the fixed instruction below. Under it, paste the spec, then the test chat's table.
4. Write down every line it lists, with the spec line it names.
5. Write down the model's name and the date. The report needs both.

You should see: a short list of line numbers, each with a reason, or "No breaks found."

The instruction below is a starting point, and only my suggestion. Change it as you like before the first run, then keep it word for word.

```
You are reviewing a role-play chat for consistency with a character spec.
Below are the character spec and the chat. Each chat line has a number.
List every line where the character breaks the spec.
For each one, give the line number, the spec line ID it breaks, and one sentence on why.
If no line breaks the spec, say "No breaks found."
```

For the spec, copy the part of [CHARACTER_SPEC.md](../../validation/fixtures/CHARACTER_SPEC.md) between its two horizontal lines.

A baseline by hand is not a perfect match. The chatbot's hidden settings differ from the app's. Please say so in the report's limitations. If `analysis/README.md` exists, the toolkit may run a fairer baseline, so follow that file.

### Step 8. Score

1. Copy [scoring_sheet_TEMPLATE.csv](../study_materials/scoring_sheet_TEMPLATE.csv) to `docs/study_materials/scoring_sheet.csv`. Open the copy in Google Sheets or Excel.
2. Add one row for every flag, and one row for every planted mistake that got no flag.
3. In the result column, write `caught`, `wrong type`, `wrong flag`, or `missed`.

You should see: every flag and every planted mistake on exactly one row, for each setup and each run.

Decide three things before you score, write them in `protocol.md`, and keep them.

- **What a catch is.** In CP3 we counted one only when the line and the type were both right. The plain prompt names no type. So my suggestion is to score both setups by line, and report the type as a second number for the judge.
- **Where `wrong type` rows go.** If they aren't catches, add them to the wrong flags in the precision formula.
- **Flags that cover several lines.** An automatic check can list more lines under "also". Choose one row for the flag, or one for each line.

Then, for each setup:

- Precision = caught / (caught + wrong flags). It says how many flags were right.
- Recall = caught / planted mistakes. It says how many mistakes were found.
- F1 = 2 x precision x recall / (precision + recall). It combines the two.

A made-up example: a chat has 5 planted mistakes. The judge raises 6 flags. Four are planted mistakes, and two are on clean lines. Precision is 4 / 6 = 0.67. Recall is 4 / 5 = 0.80. F1 is 0.73.

Decision 3 also asks for each number by mistake type. The `answer_type` column of the sheet gives you that.

### Step 9. Repeat each setup 3 to 5 times

AI answers vary, so one run can be lucky. But the app keeps a saved check. Once a chat is checked, the app shows that saved check again, with no new model call. So each repeat needs its own database file.

1. Stop the app with Ctrl+C.
2. Open `app/.env` in a text editor, and add this line. Change the name for each run. Put it on a line of its own. On a Mac, `open -e app/.env` opens the file in TextEdit. In Ubuntu, use `nano app/.env`, then Ctrl+O, Return, and Ctrl+X to save and leave.

   ```
   WORKBENCH_DB_PATH=data/eval_run2.db
   ```

3. Start the app with `app/run.sh`.

   You should see: the app with no chats in it. Your key is still connected.

4. Import the test chats again (step 6), and press **Check this chat** on each.
5. Record the flags, with the run's number.

To go back to your usual chats, delete that line from `app/.env` and start the app again.

My suggestion: use a new file for every setup and every run, with a clear name like `data/eval_judge35_run1.db`. Keep all of them until CP4 is graded. They hold the logs behind your numbers, and git ignores that folder.

### Step 10. Cost and speed

The app logs every AI call with its seconds, its tokens, and an estimated cost. This line sums them up for one database file:

```bash
sqlite3 -readonly -box app/data/eval_run2.db "SELECT role, model_asked, COUNT(*) AS calls, ROUND(AVG(latency_ms) / 1000.0, 1) AS avg_seconds, SUM(input_tokens) AS input_tokens, SUM(output_tokens) AS output_tokens, ROUND(SUM(est_cost_usd), 4) AS est_cost_usd FROM model_calls WHERE status = 'ok' GROUP BY role, model_asked;"
```

You should see: one row for each kind of call, like `judge`, with its average seconds and its cost.

The cost is what the calls would cost on a paid key. On the free tier you pay nothing. [docs/observability.md](../observability.md#how-each-number-is-measured) explains each number.

Without `sqlite3`, use the seconds that the check card counts on the screen.

### Step 11. Write the error analysis

This is Track B's "qualitative depth". The rubric wants a sort of the ways the system fails, with reasons.

1. Copy [error_analysis_TEMPLATE.md](../study_materials/error_analysis_TEMPLATE.md) to `docs/study_materials/error_analysis.md`.
2. Take every `missed`, `wrong type`, and `wrong flag` row from the scoring sheet. Write one line on what went wrong.
3. Group them into kinds, and count each kind.
4. Give 2 or 3 examples of each kind, with the chat and the line.

Kiara's [CP3 model test](../cp3_model_test.md) gives two kinds to start from. The judge mixes up style drift and persona drift. A re-check also can't change a flag's type. CP2 also found that AI reviewers miss judgment calls and facts from far back in the chat.

### Step 12. Make the charts

1. In your spreadsheet, make a bar chart of precision, recall, and F1 for each setup.
2. Make a second chart of cost and seconds for each setup. The baseline by hand has no logged cost or seconds, so leave it out and say so.
3. Save each chart as a PNG image in `docs/figures/`.
4. Add a row for each one in [docs/figures/README.md](../figures/README.md).

The rubric asks for scripts that rerun the numbers. A spreadsheet isn't a script. So keep `scoring_sheet.csv` in the repo, and write your formulas in the figures README. Then anyone can redo the math. If `analysis/README.md` exists, use its chart commands.

## 3. Track A without new building

Track A tests the tool with real people. I never built a study mode, so the app has no guided flow for participants. If you pick Track A, one of you runs each session live, on your own laptop, with the app as it is.

### What one session could look like

This is my suggestion, for about 30 minutes. The real plan goes in your copy of [protocol_TEMPLATE.md](../study_materials/protocol_TEMPLATE.md).

1. Consent, 2 minutes. Read the consent text out loud.
2. Introduction, 3 minutes. Say what the tool is, and show the character spec.
3. Task 1, alone, 8 minutes. The person reads a test chat and the spec in a document, and marks each line that breaks the spec.
4. Task 2, with the workbench, 8 minutes. The person reviews the other test chat on the Flag review screen.
5. Survey, 5 minutes. They fill in a Google Form.
6. Thanks, and any last thoughts.

Swap the two chats for every other person, so each chat is used alone and with the tool equally often.

### Before the first session

1. Copy and fill in the templates in [docs/study_materials/](../study_materials/README.md): protocol, consent, task prompts, questionnaire, and recruiting.
2. Make 2 test chats of equal difficulty, with answer sheets ([section 2](#2-track-b-step-by-step), steps 1 to 4).
3. Save those two chats and their answer sheets in a folder named `private/` at the repo root, from the start. Git ignores it. Swap them by private message, not in a pull request. Classmates may take part, so they must not see the chats first.
4. Build one Google Form. Copy the scale's statements word for word from [questionnaire_TEMPLATE.md](../study_materials/questionnaire_TEMPLATE.md). Make the first question the participant's code, like P01. Add your typed-answer questions.
5. Recruit 6 to 10 people, which is my suggestion in decision 1. Start the day you decide. Thanksgiving week makes this hard.
6. Run one practice session with each other.

You should see: a filled-in protocol, a working form, a sign-up list with codes, and one finished practice session.

Names and contact details never go in the repo. Notes use a code like P01.

### Weak spots, and the simplest fixes I found

| Weak spot | Fix |
| --- | --- |
| Flags can differ between runs, so two people could see different flags on one chat | Check each study chat once, before the first session. Then every person sees the same saved flags. Steps are below. |
| The last person's Agree and Override calls stay on the screen | Put the saved database copy back before each session. Steps are below. |
| The first-visit tour opens once in each browser | Press **Skip tutorial** before the person sits down. Or show it to everyone. Pick one and keep it. |
| The faint drawings may distract | In **Settings**, under **Advanced**, switch **Decorations** off. INSTALL.md suggests this for a study. |
| The app doesn't time a task | Use a phone timer, and write the time in the session notes. |
| Gemini may be busy during a session | Checks are saved before the session, so a session needs no live AI call. |
| The **Re-check** button makes a live AI call and can change the flags | My suggestion: leave Re-check out of the tasks, so every session is the same. |

The steps for the first two fixes. Step 1 needs the app running, and the copies in steps 2 to 4 need it stopped. They assume `app/.env` has no `WORKBENCH_DB_PATH` line.

1. Import both study chats, press **Check this chat** on each, then stop the app with Ctrl+C.
2. Keep a copy of the database as your starting point.

   ```bash
   cp app/data/workbench.db app/data/study_start.db
   ```

3. Before each session, put the starting point back, then start the app.

   ```bash
   cp app/data/study_start.db app/data/workbench.db
   ```

   You should see: both chats already checked, and every flag still saying "Needs your call".

4. After each session, stop the app and keep that person's copy. Change the code each time.

   ```bash
   cp app/data/workbench.db app/data/session_P01.db
   ```

That copy holds each call the person made on a flag, with its time. Git ignores `app/data/`, so it stays on your laptop.

For a practice round, `app/scripts/reset_demo.py` gives the two sample chats the same flags every time. [INSTALL.md](../../app/INSTALL.md#reset-before-a-demo) explains it. Those samples are public, so use them for practice, not as study chats. The reset replaces the database the app is using, after it saves a backup.

### After the sessions

1. Score each task against its answer sheet: mistakes caught, wrong calls, and time.
2. Score the survey. The questionnaire template has the formula for each scale.
3. Sort the typed answers into themes with [themes_TEMPLATE.md](../study_materials/themes_TEMPLATE.md).
4. Run the knob tests on the judge ([section 4](#4-ablations)). The rubric asks for an ablation analysis in both tracks.

If the public link exists, I'd still run sessions on your laptop. That way every person sees the same flags.

## 4. Ablations

An ablation changes one thing and keeps everything else the same. If the score moves, that one thing mattered. The rubric asks for an ablation analysis, so please plan at least one knob.

The three knobs come from [decision 3](DECISIONS.md#3-what-we-compare):

| Knob | Values | Can you turn it by hand? |
| --- | --- | --- |
| The follow-up question | None, general, or specific | Yes, on the Flag review screen |
| The judge's model | Gemini 3.5 Flash-Lite, Gemini 3.1 Flash-Lite, or a local model through Ollama | Yes, in Settings |
| The thinking effort | Minimal, medium, or high | No. Toolkit only |

### The follow-up question

1. Check the chat ([section 2](#2-track-b-step-by-step), step 6). Its flags are the "none" result.
2. On **Flag review**, scroll down to the **Follow-up re-check** card.
3. Type the question in "Your question (optional)", and press **Re-check**.

   You should see: "What changed in the re-check", with the flags it added, withdrew, and re-rated. Write the flag list down again. That list is the result for that question.

4. For the other question, use a fresh database file ([section 2](#2-track-b-step-by-step), step 9). Then the two re-checks don't build on each other.

In CP3 the general question was "Does Harry's tone ever clash with what Alex just said?" The specific one was "Does Harry joke about anything painful right after Alex mentions it?" A specific question only fits a chat with that kind of mistake. My suggestion: write your questions before you look at any result, and say so in the report.

### The judge's model

1. Press **Settings**. Under **Models**, open **The judge's model**, and pick the other Gemini model.
2. Press **Test**, then **Save**.

   You should see: "Settings saved." A note may say the same model plays Harry and reviews the chat. That is expected here.

3. Use a fresh database file, import the chats, and check them again.
4. When you finish, set the judge's model back to Gemini 3.5 Flash-Lite, and press **Save**. The choice is saved in `app/.env`, so it follows every database file.

A local model through Ollama also works, and [INSTALL.md](../../app/INSTALL.md#other-providers) has the steps. It is a large download. My suggestion: skip it unless one of you already uses Ollama.

### The thinking effort: toolkit only

The judge's thinking effort is set in `app/prompts/models.v5.toml`. The app has no setting for it, so it can't be changed by hand.

Please never edit `models.v5.toml`. The server checks that file's exact contents, and it refuses to start if they changed. [app/prompts/README.md](../../app/prompts/README.md#how-versions-work) explains why.

If `analysis/README.md` exists, the toolkit can turn this knob, so follow that file. If not, leave this knob out, and say so in the report. Two knobs are still an ablation analysis.

### Why each setup runs 3 to 5 times

AI answers change from run to run, even with the same chat. One run can be lucky or unlucky. With 3 to 5 runs you can report the average, the lowest, and the highest.

### How many calls this takes

One check is one AI call. One re-check is one more.

| What | Calls for 8 chats, 3 runs |
| --- | --- |
| Judge alone, then the general question | 48 |
| Judge alone, then the specific question, in fresh files | 48 |
| The other Gemini model as the judge | 24 |
| All of it | 120 |

The limits to know, all under **Limits** in Settings:

- **Session judge limit** is 20 for each browser tab. Raise it first, or the app stops you after 20 checks.
- **Daily cap** is 200 calls a day. You can raise it to 500.
- Google's free tier allows 500 calls a day for each model, and 15 a minute. The app already spaces the calls.

So the judging fits in a day or two on one key. Making the 8 test chats takes calls too: one to write each chat, plus one for each reply. My suggestion: spread the chat making over two days, or over both your keys.

## 5. The report

The report is [docs/FINAL_REPORT.md](../FINAL_REPORT.md). It is a skeleton now, with every section the course names. Put your name on a section's Owner line in [issue 106](https://github.com/FlinnH/IS492-CharacterAI-Team-Project/issues/106) to take it. The report file has Owner lines too, but the issue is where you claim a section.

| Section | Suggested words | The course asks for | Where the facts already live |
| --- | --- | --- | --- |
| Abstract | 170 | About 150 words | Write it last. Treat 170 as the most. |
| 1. Introduction | 370 | Why the problem matters, and our main contributions | [README.md](../../README.md), [proposal/PROPOSAL.md](../../proposal/PROPOSAL.md) |
| 2. Related work | 500 | Grounding in our CP1 reading list | [literature/BIBLIOGRAPHY.md](../../literature/BIBLIOGRAPHY.md), [reflections/](../../reflections/) |
| 3. Methodology | 610 | The architecture, the AI design, the prompts, and the pipeline | [docs/architecture.md](../architecture.md), [app/prompts/README.md](../../app/prompts/README.md) |
| 4. Evaluation design | 560 | The protocol, the participants or test set, the baselines, and the metrics | Your `protocol.md`, [DECISIONS.md](DECISIONS.md) |
| 5. Results and discussion | 900 | The statistics, the charts, and the qualitative themes | Your scoring sheet, [docs/figures/](../figures/README.md), your error analysis or themes |
| 6. Limitations and ethics | 300 | Safety, bias, hallucinations, and privacy | [docs/safety_privacy.md](../safety_privacy.md), [section 11](#11-what-cp2-and-cp3-already-found) |
| 7. Conclusion | 190 | The key takeaways and future work | Your results |
| References | About 430 | Complete APA references | [literature/BIBLIOGRAPHY.md](../../literature/BIBLIOGRAPHY.md) |
| Appendices | About 220 | The prompts and the questionnaires | [app/prompts/](../../app/prompts/README.md), [docs/study_materials/](../study_materials/README.md) |

The word counts are only my suggestions. They add up to 3,600 for the abstract and sections 1 to 7. With the references and appendices, they come to about 4,250.

Section 3 describes the system as it stands. I wrote most of that code, so I'm sorry to leave this section with you. [docs/architecture.md](../architecture.md) has the diagram, each part, and one check told step by step.

### The word limit

The limit is 3,500 to 4,500 words, and the course calls it hard. I don't know whether the references and appendices count. Please check Canvas or ask the TA. My suggestion: keep the abstract and sections 1 to 7 at 3,500 words or more. Keep everything together at 4,500 or fewer. That is safe either way.

### How to count the words

If `analysis/wordcount.py` exists, use it, and `analysis/README.md` says how.

By hand:

1. Open the report's page on GitHub, where the hidden comments don't show.
2. Select the report's text, and paste it into an empty Google Doc.
3. Use the doc's word count tool, in its Tools menu.

You should see: a number between 3,500 and 4,500.

Please don't use `wc -w` on the file. It also counts the hidden comments and the table marks. Even the empty skeleton reads in the hundreds.

Before you submit, delete the comments, the Owner lines, and the Suggested length lines. The skeleton's first comment says the same.

### References and appendices

- **References.** Use APA style. [BIBLIOGRAPHY.md](../../literature/BIBLIOGRAPHY.md) has a full APA citation for each CP1 paper. If you use SUS or UMUX-Lite, their citations are in the questionnaire template.
- **Appendices.** The course asks for the prompts and the questionnaires. My suggestion: paste short things, like the baseline's instruction and the survey questions. Link to long things, like `app/prompts/judge.v1.md`.
- **AI tools.** If an AI tool helps write a section, add it to the [AI Use Disclosure](../../README.md#ai-use-disclosure) table.

## 6. The slides and the talk

The talk is 8 slides in 8 minutes or less. [CP4_SLIDE_PLAN.md](../../slides/cp4/CP4_SLIDE_PLAN.md) has a row for each slide, with what the course wants on it.

Please plan the talk without me. I may not be back in time.

- **When the slides are due.** The course's general rule is 11:59 PM the day before the presentation. Check Canvas for the day.
- **Who presents.** My suggestion for two people: one takes slides 1 to 4, and the other takes 5 to 8.
- **Where the old decks are.** The CP3 deck and its plan are in `slides/cp3/`, and the CP2 ones are in `slides/cp2/`.
- **The tone.** The course wants what the data shows and honest lessons, not hype. A weak result that you explain well is fine.

### Record the 60-second demo

A recording is safer than a live demo, because Gemini can be busy at the wrong moment.

1. Stop the app. If [section 2](#2-track-b-step-by-step), step 9, added a `WORKBENCH_DB_PATH` line to `app/.env`, delete that line first. Then reset the app to the demo's starting point.

   ```bash
   app/.venv/bin/python app/scripts/reset_demo.py
   ```

   You should see: a line that starts with "Reset", naming spec v1 and the two samples. It ends with how to undo it. You can skip its hint about the seeded transcript.

2. Start the app with `app/run.sh`. If the tour opens, press **Skip tutorial**.
3. Start your screen recorder. On a Mac, press Cmd+Shift+5, choose a recording option, and press **Record**. On Windows, use the screen recorder you already have.
4. Record one pass through the app. My suggestion for the path:
   - **Spec editor:** point at one line ID.
   - **Run Test Cases:** pick "Claude (CLA-F2), imported" in the Chat menu. Its check results are already there. Press **Review flags**.
   - **Flag review:** press **Show in context** on a flag, then **Agree**. Press **Override** on another, and type a reason of 3 words or more.
   - **Compare runs:** show where each chat broke.
5. Stop the recording, and trim it to 60 seconds.

You should see: a video file of about 60 seconds, with no key and no personal details on the screen.

The reset replaces the database the app is using, after it saves a backup in `app/data/backups/`. Your evaluation runs are safe in their own files, once that line is out of `app/.env`.

If the public link exists, you could record the same path there. It also proves the link is real. `docs/deployment.md` would say what works there.

### One timed rehearsal

1. Put the recording inside slide 2.
2. Run the whole talk once, out loud, with a timer.
3. If it runs over 8 minutes, my suggestion is to cut words before slides.

You should see: a full run under 8 minutes.

Before you post the deck, check four things. Slide 1 has the repo link, the live link, and the names. Every number matches the report. No screenshot shows a key. Every AI tool used for the deck is in the disclosure table.

Check Canvas for where the deck goes. My suggestion: also save a copy in `slides/cp4/`, as we did for CP2 and CP3.

## 7. The package

This part is worth 2.0 points. Graders look for clean code, a working public link, test scripts anyone can rerun, and complete docs. They also want charts of latency, ablations, and cost, with scripts that rerun the numbers.

| Piece | Status | Where |
| --- | --- | --- |
| The code and its license | Done | `app/`, [LICENSE](../../LICENSE) |
| Tests anyone can rerun | Done | `app/.venv/bin/pytest`. GitHub also runs them on every push. |
| The setup guide | Done | [README.md](../../README.md#how-to-run-the-app), [app/INSTALL.md](../../app/INSTALL.md) |
| Docs on the design, each screen, the logs, and safety | Done | [architecture](../architecture.md), [use cases](../use-cases.md), [observability](../observability.md), [safety and privacy](../safety_privacy.md) |
| The prompts and model settings | Done | [app/prompts/README.md](../../app/prompts/README.md) |
| Rules for AI coding tools | Done | [AGENTS.md](../../AGENTS.md) |
| The public link | To do | See below |
| Charts in `docs/figures/` | To do | [Section 2](#2-track-b-step-by-step), step 12 |
| A way to rerun the numbers | To do | Your scoring sheet and formulas, or the toolkit if it exists |
| README updates | To do | The two lines from [decision 5](DECISIONS.md#5-two-readme-promises), the folder list, and your AI tools |
| Small tidy-ups | Optional | [Issue 101](https://github.com/FlinnH/IS492-CharacterAI-Team-Project/issues/101) |

### The public link

I planned a public link and didn't get to build it. I'm sorry, because it is part of the grade. The design is in [issue 103](https://github.com/FlinnH/IS492-CharacterAI-Team-Project/issues/103), in case one of you wants to build it.

How to tell if it exists: look for a file named `docs/deployment.md`. If it is there, it names the link.

If the link exists:

- It runs on my Render account, and only I can log in there. So please don't plan on changing anything in Render.
- Fixes go through GitHub, not Render. Merge the fix into `main` with the tests green.
- It can be slow to wake. Free hosting sleeps when nobody visits, so wait a minute and reload.
- Live AI on the link needs the demo code. I sent that code to you privately, and it is never written in this repo.

If the link breaks, or doesn't exist by the deadline:

1. Show the app running on a laptop instead ([section 1](#1-run-the-app-on-your-laptop)), in the recording and in the talk.
2. Tell the TA plainly what happened.
3. Please don't spend your last days on hosting. The evaluation and the report are 9 of the 13 points.

The CP2 prototype is still online at https://is492-characterai-team-project-prot.vercel.app. It is the clickable prototype, not the working app, so label it that way if you show it.

## 8. Submitting

1. Check Canvas for exactly what to hand in, and by what time. I don't have that page, so please trust Canvas over this file.
2. Do the final check on `main`.

   ```bash
   git checkout main
   ```

   ```bash
   git pull
   ```

   ```bash
   app/.venv/bin/pytest
   ```

   You should see: a last line with a count of `passed` and no `failed`.

3. Go through this list:
   - The report is between 3,500 and 4,500 words, with its comments and Owner lines deleted.
   - Every figure in the report is in `docs/figures/`, with a row in its README.
   - The live link opens, or the submission says why it doesn't.
   - [WORK_LOG.md](WORK_LOG.md) and the [AI Use Disclosure](../../README.md#ai-use-disclosure) table are up to date.
4. Tag the version you submit.

   ```bash
   git tag cp4-submitted
   ```

   ```bash
   git push origin cp4-submitted
   ```

   You should see: `* [new tag]         cp4-submitted -> cp4-submitted`.

5. Submit on Canvas. If the public link exists, put the demo code in the submission text, so graders can try the live AI. The code is in the private message I sent you. If there is no public link, say that the app runs on a laptop with `app/INSTALL.md`.
6. Write your contribution reflection. Each person writes their own, so mine is on me. Check Canvas for where it goes.

The tag marks the exact version you handed in. The earlier ones are `cp2-submitted` and `cp3-submitted`. Please never move or delete a tag.

For the reflection, this line counts each person's commits since CP3:

```bash
git shortlog -sn cp3-submitted..HEAD
```

You should see: one line for each person, with a number.

Commits don't show meetings, sessions, or slide work. Add those to [WORK_LOG.md](WORK_LOG.md) first, because the course reads the repo to see what each person did.

## 9. A day-by-day plan

This is only my suggestion, and the Owner column is blank on purpose. I worked backward from Thu Dec 3, with the evaluation first, because it takes longest. If Canvas shows an earlier time, move everything earlier.

| Day | What | Owner |
| --- | --- | --- |
| Sun Nov 15 | I'm away from today. Read the start page and [CP4_REQUIREMENTS.md](CP4_REQUIREMENTS.md). |  |
| Mon Nov 16 | Meet. Settle decisions 1 to 5. Split the work, and assign the issues. Check Canvas. Start the longest job today. |  |
| Tue Nov 17 | Make test chats 1 and 2 each, with answer sheets. Agree on the baseline's instruction and what counts as a catch. |  |
| Wed Nov 18 | Make test chats 3 and 4 each, with answer sheets. |  |
| Thu Nov 19 | Swap, and check each other's answer sheets. |  |
| Fri Nov 20 | Fix what the check found, and merge the test set. Try each setup once on one chat. |  |
| Sat Nov 21 | Run 1: the baseline and the full judge on every chat. |  |
| Sun Nov 22 | Runs 2 and 3. Fill in the scoring sheet as you go. |  |
| Mon Nov 23 | Light. Thanksgiving week. The knob tests, if you feel like it. |  |
| Tue Nov 24 | Light. Any runs still left. |  |
| Wed Nov 25 | Light. Maybe draft report sections 1 to 3, which need no results. |  |
| Thu Nov 26 | Off. Thanksgiving. |  |
| Fri Nov 27 | Off. |  |
| Sat Nov 28 | Score everything: precision, recall, F1, cost, and seconds. |  |
| Sun Nov 29 | The error analysis and the charts. Draft sections 4 and 5. |  |
| Mon Nov 30 | Meet. Pick the charts for the slides, who presents, and the demo. Finish the report draft, and count its words. |  |
| Tue Dec 1 | Build the slides. Record the demo. Read each other's sections. Update the README. |  |
| Wed Dec 2 | Timed rehearsal. Final check. Slides in by 11:59 PM if the talk is Thursday. Reflections. |  |
| Thu Dec 3 | Tag and submit. Present, if the talk is today. Otherwise a spare day. |  |

If you pick Track A, the same shape works. Recruiting starts Mon Nov 16. Sessions run Nov 19 to 22, and again Nov 28 to 30.

## 10. Troubleshooting

| Problem | What to try |
| --- | --- |
| The tests fail after a merge | Run `app/.venv/bin/pytest`, and read the first line that starts with `FAILED`. It names the test and the file. Fix that one thing. If you can't, open the merged pull request on GitHub and press **Revert**. |
| A link test fails | The line names a doc, like `test_every_relative_link_in_the_kit_resolves[docs/cp4/DECISIONS.md]`. A link in that doc points at a file or heading that moved. Fix the link. |
| A merge conflict | Run `git status` to see the files. Open each one, and find the lines with `<<<<<<<`, `=======`, and `>>>>>>>`. Keep the text you want, and delete those three marks. Then run `git add` on the file, and `git commit`. To back out, run `git merge --abort`. |
| "Today's 200 model calls are used up." | In **Settings**, under **Limits**, raise **Daily cap**, up to 500. Google's own limit is 500 a day for each model. It resets at midnight Pacific time. |
| "This browser session has used its 20 AI judge calls" | In **Settings**, under **Limits**, raise **Session judge limit**. |
| "Gemini had a problem on its side." or "The model service had a problem. Try again in a minute." | Google is busy. Try again in a minute. During the benchmark, my suggestion is to wait, and not to switch models. |
| Check results says "(fallback)" | The other model judged this chat, because the first one was busy. Don't count that run. Redo it later in a fresh database file. |
| Check results says "AI judge: unavailable" | The judge's answer couldn't be read, or the judge's model is wrong in Settings. Only the automatic checks ran. Check again in a minute, and don't count that run. |
| "Shown from the saved check, with no new model call." | That is the saved check, not a new run. For a new run, use a fresh database file ([section 2](#2-track-b-step-by-step), step 9). |
| The server won't start, and says a prompt file "changed after manifest.toml recorded it" | A file in `app/prompts/` was edited. Run `git restore app/prompts/` to put it back. |
| The public link is slow to open | If the link exists, free hosting may be asleep. Wait a minute, and reload. |
| The public link is broken | Only I can log in to Render. Show the app on a laptop, and tell the TA. A fix goes through a pull request into `main`. |
| The report is over the word limit | Count each section against its suggested length. Cut background from sections 1 and 2 first. Keep the results. Link to long material from the appendices. |
| You lost the demo code | A demo code only exists if the public link exists. Then it is in the private message I sent you both, so ask each other. It isn't in the repo, and only I can set a new one. The app on a laptop needs no code. |
| An AI coding tool wants to change many files | My suggestion: stop it first. Then ask it to read [AGENTS.md](../../AGENTS.md), then to list each file it wants to change, and why. Say no to `app/prompts/`, `prototype/`, and tests it didn't write. Look at `git status` before you commit. |
| An AI tool already made a mess | `git restore .` puts every tracked file back to your last commit. It throws away uncommitted edits, so be sure first. |
| The app won't start | [INSTALL.md](../../app/INSTALL.md#when-something-goes-wrong) lists each message and its fix. |
| GitHub shows a red Tests check on your pull request | Open the check, and read the failed test's name. Run the tests on your laptop, fix it, and push again. |
| You haven't opened a pull request from a terminal before | Make a branch with `git checkout -b my-branch`. Run `git add` on each file, then `git commit -m "what changed"`. Send it with `git push -u origin my-branch`. GitHub then shows a button to open the pull request. For a small edit to DECISIONS.md or WORK_LOG.md, the pencil button on GitHub is enough. |
| You can't reach me | Please decide together, and go ahead. Nothing here needs my approval. |

## 11. What CP2 and CP3 already found

You can cite all of this. Each line links to where it is written down.

**The claim.** A creator who uses the workbench should beat a creator alone, and an AI alone, at finding consistency failures. It is in [THEORY_LENS.md](../../validation/THEORY_LENS.md#part-1-working-theory-claim), with what would prove it wrong.

**The CP2 pilot.** We ran each arm once on one chat with 7 planted mistakes:

| Who reviewed | Caught |
| --- | --- |
| A person alone (interview INT-KG-2) | 0 of 7 |
| An AI alone: Claude, Gemini, and ChatGPT | 5, 5, and 6 of 7 |
| An AI plus one human question | 7 of 7 for Claude and ChatGPT. Gemini found nothing new. |

**The CP2 prompting study.** We scored 18 chats: 3 tools on 6 scenarios. Each tool held some rules and broke others. The table is in [GAP_ANALYSIS.md](../../validation/GAP_ANALYSIS.md), and the chats are in `validation/transcripts/`.

**The CP2 interviews.** Six speed-dating interviews are in the [roll-up](../../validation/GAP_ANALYSIS.md#speed-dating-roll-up). The themes: people want to see where it broke before they trust a flag. Fixing means rewriting, not repairing. Breaks follow a change of topic or session, not only length.

**What changed since CP1.** [OPPORTUNITY_FRAMING.md](../../validation/OPPORTUNITY_FRAMING.md#hypothesis-evolution) lists each early guess, and what the evidence did to it.

**CP3, our own judge on the same chat.** These are in the [CP3 slide plan](../../slides/cp3/CP3_SLIDE_PLAN.md#results):

| Reviewer | Caught | Wrong flags |
| --- | --- | --- |
| Our free judge alone, Gemini 3.5 Flash-Lite | 4 of 7 | 0 |
| Plus a general follow-up question | 5 of 7 | 0 |
| Plus a specific follow-up question | 6 of 7 | 0 |

The same page has speed and cost. Harry's first word took 0.74 seconds at minimal thinking. A judge call cost about $0.002 at paid rates, and we paid $0 on the free tier.

**Kiara's CP3 model test.** With GPT as the judge, 4 of 7 were caught. With Claude, 6 of 7. Neither raised a wrong flag, and neither follow-up question added or withdrew a flag. [cp3_model_test.md](../cp3_model_test.md) also lists five problems she found in the app.

**Limits to say out loud.** All of these numbers come from one chat, with one run for each arm. So they are pilots, not proof. That chat's answer sheet is public now, so it can't be the CP4 test set. The specific question was written after we saw the miss. These models also know Harry Potter well.

The design choices that came out of this are in [DESIGN_SPEC.md](../../DESIGN_SPEC.md).

Thank you both for carrying this to the end. I know it's a lot.
