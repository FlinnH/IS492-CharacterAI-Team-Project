# CP4: start here

One page for the whole team. CP4 is the last checkpoint: evaluate the workbench, write the final report, package it with a live link, and present.

**Due:** Fri Nov 20, 2026 at 9:00 AM, to be confirmed on Canvas.

**Start with the [At a glance table in DECISIONS.md](DECISIONS.md#at-a-glance).** It lists the five choices we make together first.

## What CP4 requires

| Part | Points |
| --- | --- |
| The evaluation: a user study or a benchmark, with numbers, what people said, and an ablation analysis | 4.5 |
| The report: [docs/FINAL_REPORT.md](../FINAL_REPORT.md), 3,500 to 4,500 words | 4.5 |
| The package and a live link: clean code, scripts that reproduce the results, and complete docs | 2.0 |
| The talk: 8 slides in 8 minutes or less | 2.0 |

## The 8 issues

All CP4 work is in 8 issues in the [CP4 milestone](https://github.com/FlinnH/IS492-CharacterAI-Team-Project/milestone/4). Each one has a checklist.

| Issue | What it is | Who |
| --- | --- | --- |
| [102, Decide together: CP4's 5 big choices][102] | The five choices we make at our first meeting | Everyone |
| [103, Setup: team kit, public link, toolkit][103] | This kit, a web address for the app, and scripts for the evaluation | Flynn |
| [104, Test set: chats and answer sheets][104] | The chats we test on, each with a checked answer sheet | Open |
| [105, Run the evaluation and analyze it][105] | The runs or the study, then the numbers and charts | Open |
| [106, Final report][106] | One line for each section of the report | Open, one owner for each section |
| [107, Slides, demo recording, and the talk][107] | The 8 slides, the 60-second recording, and a rehearsal | Open |
| [108, Final check and submit][108] | The last audit, the tag, and the Canvas submission | Flynn |
| [101, Optional tidy-ups before the final package][101] | Small things for each file's owner to decide | Each file's owner |

## How to take a task

1. Pick a line in an issue's checklist, and comment on the issue to say you are taking it.
2. Work on your own branch.
3. Open a pull request into `main` that says "Part of #N", with the issue's number in place of N. The tests run on it by themselves.
4. After the merge, tick your line. Write "Closes #N" only in the pull request that finishes the last line, because that closes the whole issue.

## What the app already does

1. **Spec editor.** A character spec with line IDs, a Scene field, and saved versions. Spec v1 is Harry Potter right after book 4.
2. **Run Test Cases and Free Chat.** Live chats with the character: a test case the AI writes from the spec (T1, E1, E2, F1, F2, A1, A2, or Custom), free typing, or an imported chat.
3. **Check this chat and Flag review.** Automatic checks and an AI judge flag each break, with a quote and the spec line it breaks. The creator opens the evidence, then agrees or overrides with a reason. A follow-up re-check looks again.
4. **Compare runs.** Where each chat broke, side by side.
5. **Under the screens.** Settings for the AI service and its limits, a log in SQLite of every model call and every call on a flag, and tests that run with a fake model.

[docs/use-cases.md](../use-cases.md) explains each screen step by step.

## Where every template is

| What | Where |
| --- | --- |
| What we need to decide together: 5 choices, each with a recommendation and a blank Decided line | [DECISIONS.md](DECISIONS.md) |
| The final report, as a skeleton | [docs/FINAL_REPORT.md](../FINAL_REPORT.md) |
| Study materials: protocol, consent, task prompts, questionnaire, recruiting, session notes, themes, a test chat, and its answer sheet | [docs/study_materials/](../study_materials/README.md) |
| Figures, each with the script that makes it | [docs/figures/](../figures/README.md) |
| The slide plan | [slides/cp4/CP4_SLIDE_PLAN.md](../../slides/cp4/CP4_SLIDE_PLAN.md) |
| Work that git can't show | [WORK_LOG.md](WORK_LOG.md) |
| Rules for AI coding tools | [AGENTS.md](../../AGENTS.md) |
| New issues and pull requests | `.github/ISSUE_TEMPLATE/` and `.github/pull_request_template.md`. GitHub offers them when you open one. |

## Run the app and the tests

- **The app.** Run `app/run.sh` from the repo root. It opens http://127.0.0.1:8492 in your browser.
  The first run installs what it needs. The [README](../../README.md#how-to-run-the-app) has every step, the free Gemini key included.
- **The tests.** Run `app/.venv/bin/pytest` from the repo root, after the app has run once.
  They use a fake model, so they need no key and no network. GitHub runs them too, on every push and pull request.

## What must stay private

This repo is public, and classmates may take part in a study.

- **Keys.** An API key lives only in `app/.env`, which git ignores. Never put one in code, a doc, an issue, a pull request, a screenshot, or a chat with an AI tool.
- **Test chats the team wants unseen before a study.** If we pick Track A, keep every test chat and answer sheet in a folder named `private/` at the repo root, which git ignores, until the study ends.
- **Who the participants are.** Keep names and contact details out of the repo. Notes use a code like P01.

[101]: https://github.com/FlinnH/IS492-CharacterAI-Team-Project/issues/101
[102]: https://github.com/FlinnH/IS492-CharacterAI-Team-Project/issues/102
[103]: https://github.com/FlinnH/IS492-CharacterAI-Team-Project/issues/103
[104]: https://github.com/FlinnH/IS492-CharacterAI-Team-Project/issues/104
[105]: https://github.com/FlinnH/IS492-CharacterAI-Team-Project/issues/105
[106]: https://github.com/FlinnH/IS492-CharacterAI-Team-Project/issues/106
[107]: https://github.com/FlinnH/IS492-CharacterAI-Team-Project/issues/107
[108]: https://github.com/FlinnH/IS492-CharacterAI-Team-Project/issues/108
