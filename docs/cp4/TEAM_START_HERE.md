# CP4: start here

Hi Gawon and Kiara. I'm away from Sun Nov 15, 2026, for a family matter, and I may not be back before the talk. I'm sorry to leave in the middle of it.

Before I left, I finished the working app (CP3), this team kit, a step-by-step guide, and the public link. Everything you need is in this repo, so nothing has to wait for me. Where I suggest something, it is only a suggestion. Every decision is yours.

## CP4 in five lines

- **What it is:** the last checkpoint, worth 13 points. We evaluate the app, write a report, put the app online, and present.
- **When it's due:** Thu Dec 3, 2026, after Thanksgiving break. Check Canvas for the time.
- **The four graded parts:** the evaluation (4.5), the final report (4.5), the package and public link (2.0), and the talk (2.0).
- **The full ask:** [CP4_REQUIREMENTS.md](CP4_REQUIREMENTS.md).
- **How to do each part:** [HOW_TO_FINISH_CP4.md](HOW_TO_FINISH_CP4.md), the how-to.

## Where things stand

| Piece | Status | Notes and links |
| --- | --- | --- |
| Team kit | Done | This page, [the how-to](HOW_TO_FINISH_CP4.md), the templates, and the 8 issues. [The map](#the-map) lists them. |
| Public link | Done | https://character-consistency-workbench.onrender.com. Live AI there needs the demo code, which I sent you privately. See [the how-to, section 7](HOW_TO_FINISH_CP4.md#7-the-package). |
| Toolkit | To do | Not built. Every step in [the how-to](HOW_TO_FINISH_CP4.md#three-things-to-know-first) has a way by hand. |
| Package polish | To do | [The how-to, section 7](HOW_TO_FINISH_CP4.md#7-the-package) lists what is left. |
| Decisions | Ready to use | My picks are in [DECISIONS.md](DECISIONS.md). Yours decide. [Issue 102][102]. |
| Test set | To do | The templates are ready. [Section 2](HOW_TO_FINISH_CP4.md#2-track-b-step-by-step), [issue 104][104]. |
| Evaluation | To do | Sections [2](HOW_TO_FINISH_CP4.md#2-track-b-step-by-step), [3](HOW_TO_FINISH_CP4.md#3-track-a-without-new-building), and [4](HOW_TO_FINISH_CP4.md#4-ablations). [Issue 105][105]. |
| Report | To do | The skeleton is ready: [FINAL_REPORT.md](../FINAL_REPORT.md). [Section 5](HOW_TO_FINISH_CP4.md#5-the-report), [issue 106][106]. |
| Slides | To do | The [slide plan](../../slides/cp4/CP4_SLIDE_PLAN.md) is ready. [Section 6](HOW_TO_FINISH_CP4.md#6-the-slides-and-the-talk), [issue 107][107]. |
| Talk | To do | One timed rehearsal. [Section 6](HOW_TO_FINISH_CP4.md#6-the-slides-and-the-talk). |
| Reflections | To do | One each. [Section 8](HOW_TO_FINISH_CP4.md#8-submitting). |
| Submission | To do | [Section 8](HOW_TO_FINISH_CP4.md#8-submitting), [issue 108][108]. |

## Your first five steps

1. Read [CP4_REQUIREMENTS.md](CP4_REQUIREMENTS.md). It takes about five minutes.

   You should see: the four graded parts, the two tracks, and the 8 slides.

2. Check Canvas for the deadline's time and the presentation day. Write both on the "Our deadlines" line of [decision 4](DECISIONS.md#4-who-does-what-and-by-when).

   You should see: a time for Thu Dec 3, and a day for the talk.

3. Decide the track together, in [decision 1](DECISIONS.md#1-track-a-or-track-b).

   You should see: its Decided line filled in.

4. Split the work with [decision 4](DECISIONS.md#4-who-does-what-and-by-when). Then open each issue on GitHub, and pick yourself under Assignees.

   You should see: a name on every issue from 104 to 108.

5. Start the longest job the same day. That is the test set for Track B, or recruiting for Track A.

   You should see: the first test chat, or the first invitation, by that evening. [Section 1](HOW_TO_FINISH_CP4.md#1-run-the-app-on-your-laptop) of the how-to gets the app running.

The how-to has a [day-by-day plan](HOW_TO_FINISH_CP4.md#9-a-day-by-day-plan) you can start from.

## The map

| File or folder | What it's for | When you'll need it |
| --- | --- | --- |
| [CP4_REQUIREMENTS.md](CP4_REQUIREMENTS.md) | What the course asks | First, and before you submit |
| [HOW_TO_FINISH_CP4.md](HOW_TO_FINISH_CP4.md) | The steps for every part | Every working day |
| [DECISIONS.md](DECISIONS.md) | Five choices, with my picks | Your first meeting |
| [WORK_LOG.md](WORK_LOG.md) | Work that git can't show | After a meeting or a session |
| [docs/FINAL_REPORT.md](../FINAL_REPORT.md) | The report's skeleton | While writing |
| [docs/study_materials/](../study_materials/README.md) | Templates for the test set, the scoring, and a study | While you make and score the test set |
| [docs/figures/](../figures/README.md) | The charts, each with how it was made | After scoring |
| [slides/cp4/CP4_SLIDE_PLAN.md](../../slides/cp4/CP4_SLIDE_PLAN.md) | The 8 slides | The last week |
| [AGENTS.md](../../AGENTS.md) | Rules for AI coding tools | Before a tool edits anything |
| `.github/` | Issue and pull request templates, and the tests GitHub runs | They work by themselves |
| [The CP4 milestone](https://github.com/FlinnH/IS492-CharacterAI-Team-Project/milestone/4) | The 8 issues, each with a checklist | To take and tick off work |
| [app/INSTALL.md](../../app/INSTALL.md) | Installing the app, and every setting | When the app misbehaves |
| [docs/deployment.md](../deployment.md) | How the public link works, its limits, and how to check it | If the link misbehaves |
| `analysis/` | The toolkit | Only if it exists. It didn't when I left. |

## House rules

Five habits I'd suggest:

- **Run the tests before you push.** The command is `app/.venv/bin/pytest`. GitHub runs them again on every pull request.
- **Don't edit prompt files once the test chats exist.** That means everything in `app/prompts/`. A change there makes old and new runs impossible to compare. The app also won't start if one of those files changes.
- **Nothing secret in git.** No key, no demo code, and no participant's name. A key lives only in `app/.env`.
- **A pull request names its issue.** Write "Part of #104", with the issue's own number. Write "Closes" only on the last one.
- **Work that git can't show goes in [WORK_LOG.md](WORK_LOG.md).** A meeting, a study session, or slide work counts.

## If something breaks

The [troubleshooting table](HOW_TO_FINISH_CP4.md#10-troubleshooting) lists the likely problems and their fixes. If yours isn't there, please decide together and go ahead. Nothing needs my approval.

Thank you both for taking this on.

[102]: https://github.com/FlinnH/IS492-CharacterAI-Team-Project/issues/102
[103]: https://github.com/FlinnH/IS492-CharacterAI-Team-Project/issues/103
[104]: https://github.com/FlinnH/IS492-CharacterAI-Team-Project/issues/104
[105]: https://github.com/FlinnH/IS492-CharacterAI-Team-Project/issues/105
[106]: https://github.com/FlinnH/IS492-CharacterAI-Team-Project/issues/106
[107]: https://github.com/FlinnH/IS492-CharacterAI-Team-Project/issues/107
[108]: https://github.com/FlinnH/IS492-CharacterAI-Team-Project/issues/108
