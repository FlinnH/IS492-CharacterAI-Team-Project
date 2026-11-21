# User study plan (Track A)

**Status:** Draft by Kiara, Nov 20, 2026. It assumes we pick Track A in [decision 1](../cp4/DECISIONS.md#1-track-a-or-track-b). Gawon, please review.

## Research question

When creators use our workbench, do they find character breaks more accurately than they do alone, or than the AI does alone? Do they follow the AI blindly? Is the tool easy to use?

| Goal | What we want to know |
| --- | --- |
| **G1 Accuracy** | Person + AI, compared with the person alone and the AI alone |
| **G2 Trust calibration** | People agree with the AI when it's right, and override it when it's wrong |
| **G3 Asking questions** | A Re-check with the person's own question helps them find mistakes the AI missed |
| **G4 Repair and usability** | People can turn a diagnosis into a better spec line, and they find the tool easy to use |

## Participants

- **Who:** people who write or tune AI characters, such as personas, system prompts, or role-play bots. If we can't find enough, we also take classmates who use AI chat tools often.
- **How many:** at least 4, and 8 if we can. With 4 orders (below), 4 people means one per order and 8 means two per order. With fewer than 6, we report the study as a pilot.
- **Who can't take part:** the three of us, and anyone who has seen the CP2 seeded transcript or its answer key.
- **Privacy:** each person gets a code like P01. Names and contact details stay with the recruiter and never go in the repo.

## Materials

| Material | What it is |
| --- | --- |
| Spec | Harry, spec v1 ([CHARACTER_SPEC.md](../../validation/fixtures/CHARACTER_SPEC.md)). It's the only character, and participants don't write their own. |
| Chats A and B | Two new chats, about 30 lines each. Each has 5 planted mistakes and 1 or 2 decoys, which are lines that look wrong but aren't. The two chats match in mistake types and difficulty. Every planted mistake can be judged from the spec alone, without Harry Potter trivia. |
| Answer keys | One for each chat. Someone who didn't make the chat checks it. Chats and keys stay in `private/` until the last session. |
| Failure-type card | The 8 failure types, one line each. Everyone gets it in both review tasks. |
| Pre-survey | Part of the sign-up form (below) |
| Task form | A Google Form for answers the app can't record (below) |
| Post-survey | A Google Form (below) |

## Data we collect

We use only the app's own log and three Google Forms. There's no screen recording, timer, or hand-written notes.

| Source | What it holds |
| --- | --- |
| **App log** (`session_Pxx.db`) | Each opening of a flag's evidence, each Agree, Override (with its reason and any new type), and Undo, each Re-check and its question, the new flags a Re-check adds, and each spec version saved. Every row has a time. See [observability.md](../observability.md). |
| **Pre-survey** | Background and trust before the session |
| **Task form** | T1 answers, and in T2, breaks the AI didn't flag |
| **Post-survey** | Usability, trust, and open answers |

**Logging steps.**

1. **Once, before the first session:** stop the app and run `app/.venv/bin/python app/scripts/reset_demo.py`. This loads spec v1 and the CLA-F2 and GPT-F2 samples with saved flags. Start the app, import chats A and B, and press **Check this chat** on each. Stop the app and run `cp app/data/workbench.db app/data/study_start.db`.
2. **Before each session:** run `cp app/data/study_start.db app/data/workbench.db`, start the app, skip the tour, and turn Decorations off in Settings. Everyone now sees the same flags.
3. **After each session:** stop the app and run `cp app/data/workbench.db app/data/session_P01.db`, with that person's code. Git ignores `app/data/`, so the logs stay on the laptop.

## Pre-survey (in the sign-up form)

People fill this in a few days before their session. Asking about trust right before the tasks could make them more suspicious of the AI than usual.

| # | Question | Answer |
| --- | --- | --- |
| 1 | Your participant code | P01 to P08 (we send it) |
| 2 | How often do you use AI chat tools like ChatGPT, Claude, or Character.AI? | Never / Monthly / Weekly / Daily |
| 3 | Have you written or tuned an AI character, like a persona, a system prompt, or a role-play bot? | No / Once or twice / Often |
| 4 | If yes, about how many, and on which platforms? | Short text |
| 5 | How well do you know Harry Potter? | 1 (not at all) to 5 (very well) |
| 6 | Have you done error-finding work, like editing, proofreading, content moderation, or QA testing? | Yes / No |
| 7 | "In general, I trust judgments made by AI." | 1 (strongly disagree) to 7 (strongly agree) |

We use questions 3 and 5 to spread people evenly across the four orders.

## Session (about 40 minutes, one person at a time)

One of us runs each session on our own laptop, in person or over Zoom with screen sharing and remote control.

| Step | Time | What happens |
| --- | --- | --- |
| Consent | 2 min | Read the consent text ([consent_TEMPLATE.md](consent_TEMPLATE.md)). |
| Intro | 4 min | What the tool is for, Harry's spec, and the failure-type card |
| **T0 Practice** | 3 min | On the CLA-F2 sample: open one flag's evidence, Agree, then Undo. Not scored. |
| **T1 or T2** | 10 min | The first review task, by the person's order |
| **T2 or T1** | 10 min | The other review task |
| **T3 Ask** | 4 min | Re-check on the T2 chat, with the person's own question |
| **T4 Repair** | 5 min | Fix the spec from Compare runs |
| Post-survey | 5 min | Google Form |

**The four orders.** Each condition and each chat comes first equally often, so practice and chat difficulty don't favor either condition.

| Order | First | Second |
| --- | --- | --- |
| 1 | T1 Alone, chat A | T2 Workbench, chat B |
| 2 | T1 Alone, chat B | T2 Workbench, chat A |
| 3 | T2 Workbench, chat A | T1 Alone, chat B |
| 4 | T2 Workbench, chat B | T1 Alone, chat A |

## The tasks

### T1 Review alone

- **What the person does:** reads the spec and one chat in a document, then lists each line where Harry breaks the spec, with its failure type, in the task form.
- **Limit:** 10 minutes.
- **Tests:** G1, the person-alone result.

### T2 Review with the workbench

- **What the person does:** opens the other chat on **Flag review**. For each flag they press **Show in context**, then **Agree** or **Override**. An override needs a reason, and they can pick the right type. They list breaks that have no flag in the task form.
- **Limit:** 10 minutes.
- **Tests:** G1, the person + AI result, and G2.
- **Note:** the app won't let anyone press Agree before opening the evidence, so "opened the evidence" isn't something we measure.

### T3 Ask a question

- **What the person does:** on the same chat, types a question in **Your question**, presses **Re-check**, reads "What changed", and Agrees or Overrides any new flags.
- **Tests:** G3.
- **Note:** Re-check is a live AI call, so each person can get a different answer. We report T3 on its own and don't mix it into G1.

### T4 Repair

- **What the person does:** opens **Compare runs** for the CLA-F2 and GPT-F2 samples. They pick a spec line that broke in both chats, open it, rewrite it to be more specific, and press **Save as v2**.
- **Limit:** 5 minutes.
- **Tests:** G4, repair.

## Post-survey (Google Form)

| Part | Question | Answer |
| --- | --- | --- |
| UMUX-Lite | "This system's capabilities meet my requirements." | 1 to 7 |
| UMUX-Lite | "This system is easy to use." | 1 to 7 |
| Trust | "I trusted the AI's flags." | 1 to 7 |
| Trust | "I could tell when a flag was wrong." | 1 to 7 |
| Usefulness | "The flags pointed me to the right places in the chat." | 1 to 7 |
| Adoption | "I would use this tool to check my own characters." | 1 to 7 |
| Open | When did you agree with a flag, and when didn't you? Why? | Text |
| Open | Was it harder to review alone or with the workbench? Why? | Text |
| Open | What would you change about the workbench? | Text |
| Open | If this were your own character, what would the spec be missing? | Text |

## How each goal is tested

A **catch** means the right line with the right failure type, the same rule as CP2 and CP3. We also report a lenient score, the right line with any type.

### G1 Accuracy

1. **Person alone:** score each person's T1 answers against the answer key. Count catches (out of 5) and wrong calls (marks on decoys or clean lines).
2. **Person + AI:** in the T2 log, every flag the person Agreed with, or retyped with an Override, counts as their answer. Add the breaks they listed in the task form. Score it the same way.
3. **AI alone:** score the saved AI check for chats A and B (in `study_start.db`) against the answer keys. No participant is needed.
4. **Compare:** for each person, take the T2 score minus the T1 score. Show each person's two scores side by side, with the AI-alone score as a reference line.

### G2 Trust calibration

1. Mark each AI flag on chats A and B as right or wrong, using the answer key.
2. From the T2 log, take each person's decision on each flag.
3. Count four outcomes:
   - right flag, Agreed (good)
   - wrong flag, Overridden (good)
   - wrong flag, Agreed (over-trust)
   - right flag, Overridden (under-trust)
4. Compare with the pre-survey trust question and the post-survey trust questions.

### G3 Asking questions

1. From the log, take each person's question and the flags the Re-check added.
2. Check each added flag against the answer key: is it a planted mistake that the first AI check missed?
3. Count how many missed mistakes came back, and how many of those the person then Agreed with.
4. Read the questions: were they general ("Is anything off?") or specific ("Does Harry joke about something painful?")?

### G4 Repair and usability

1. **Repair:** from the log, check whether the person saved a v2 and whether the line they changed was one that broke in both chats. Then rate the rewrite: 0 (no change or worse), 1 (some change), 2 (clearly more specific). Two of us rate it separately and agree on a score.
2. **Usability:** score UMUX-Lite: add the two ratings, subtract 2, divide by 12, and multiply by 100. Also report the SUS-equivalent score, which is 0.65 times that score plus 22.9.
3. **Open answers:** two of us sort them separately into themes (trust, usefulness, and friction) and then agree on the final themes, with short quotes by participant code.

## Analysis

For now we report only the basics:

- G1: catches and wrong calls for each person, in each condition, plus the means and the AI-alone score
- G2: the four outcome counts
- G3: missed mistakes the Re-check brought back, and what the questions were like
- G4: repair success, the rewrite score, the UMUX-Lite mean, and the themes

With 4 to 8 people, these are descriptive numbers, not proof of a general effect, and the report says so.

## If something goes wrong

- **The app crashes:** copy `study_start.db` back, restart, and go on from the task that was running.
- **The AI is busy:** only T3 needs a live AI call. If it fails, skip T3 and say so in the report.
- **A person wants to stop:** stop right away. We keep their data only if they say we may.

## What happens to the data

- Logs stay in `app/data/` on the laptop of whoever ran the session, and git ignores that folder. Form answers stay in our Google account.
- Only the three of us can see them. The report shows only codes and short quotes.
- We delete the logs and form answers once course grades are final.
