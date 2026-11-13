# Study materials

What the CP4 evaluation needs on paper. For a user study (Track A), the CP4 instructions ask for the protocol, a consent script if one is needed, the materials, and the analysis (basic statistics and themes). For a benchmark (Track B), they ask for clear datasets, baselines, and metrics.

Every file here is a blank template until the team decides. The decisions are in [docs/cp4/DECISIONS.md](../cp4/DECISIONS.md).

| Template | What it becomes | Used for |
| --- | --- | --- |
| [protocol_TEMPLATE.md](protocol_TEMPLATE.md) | The study protocol: who takes part, the setup, and each step of a session. For Track B: the test set, the systems, the knobs, and the measures | Both tracks |
| [consent_TEMPLATE.md](consent_TEMPLATE.md) | The consent text a participant reads or hears before starting | Track A |
| [task_prompts_TEMPLATE.md](task_prompts_TEMPLATE.md) | The exact words of each task | Track A |
| [questionnaire_TEMPLATE.md](questionnaire_TEMPLATE.md) | The questions after the tasks, with SUS and UMUX-Lite both written out | Track A |
| [recruiting_TEMPLATE.md](recruiting_TEMPLATE.md) | The invitation and the sign-up list | Track A |
| [session_notes_TEMPLATE.md](session_notes_TEMPLATE.md) | The notes from one session | Track A |
| [themes_TEMPLATE.md](themes_TEMPLATE.md) | Themes in what people said: trust, usefulness, and friction | Track A |
| [test_chat_TEMPLATE.md](test_chat_TEMPLATE.md) | One chat of the test set, line by line | Both tracks |
| [answer_key_TEMPLATE.md](answer_key_TEMPLATE.md) | The answer sheet for one test chat: its planted mistakes, decoys, and clean lines | Both tracks |

## How to use a template

1. Copy it to a file without `_TEMPLATE` in its name, like `protocol.md`, and fill in the copy. The template stays as it is.
2. Fill in every blank. Where a part isn't used, write "not used" and one line that says why.
3. Open a pull request, like any other task.

## What stays out of this folder

This repo is public, and classmates may take part in the study.

- Names, emails, and anything else that says who a participant is. Use a code like P01.
- If we pick Track A: any test chat or answer sheet that participants shouldn't see before their session. Keep it in a folder named `private/` at the repo root, which git ignores, until the study ends. If we pick Track B, there are no participants, so the test chats and answer sheets are saved here.
- Recordings of a session.

The report's appendices point here, so the filled-in files are part of what we submit.
