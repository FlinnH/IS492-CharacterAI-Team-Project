# CP3 slide plan

Seven slides in 5 to 8 minutes, following the CP3 guide, with at least 3 of those minutes live in the running app. Each slide pulls from one or two repo files or from the sections below, so building the deck is mostly copying.

**Deadline:** slides posted to the Canvas forum by Thursday, Oct 29, 11:59 PM, with the repo link. The CP3 page lists Nov 1, 9:00 AM, but the team rules say the night before the presentation, so the earlier date is safer.

| # | Slide | Time | Pulls from | Presenter | Status |
| --- | --- | --- | --- | --- | --- |
| 1 | Title and overview: title, names, GitHub link, one-sentence problem | 30 sec | README.md | [ ] | [ ] |
| 2 | Architecture and stack: the diagram, the parts, and why there's no vector database | 1 min | docs/architecture.md | [ ] | [ ] |
| 3 | Live demo, primary flow: define a spec, run a chat live, check it, decide each flag | 2 min | Live demo path below, docs/use-cases.md | [ ] | [ ] |
| 4 | Live demo, edge cases: the follow-up question, a planted instruction, a busy AI | 1.5 min | Live demo path below, docs/use-cases.md | [ ] | [ ] |
| 5 | Technical decisions: prompts, model choice, caching, latency, cost | 1 to 1.5 min | app/prompts/README.md, Results below | [ ] | [ ] |
| 6 | Safety and guardrails: PII, prompt injection, made-up flags, rate-limit fallbacks | 45 sec | docs/safety_privacy.md | [ ] | [ ] |
| 7 | Path to CP4: known limits and the Track A user study | 45 sec | Results below, docs/observability.md | [ ] | [ ] |

## What the app does

A creator defines a character, Harry Potter, as a structured spec and runs scripted or typed chats live while Gemini plays Harry. An AI judge plus automatic checks flag where and why Harry breaks character. Every flag carries an exact quote and the spec line it breaks, and the creator decides each one. The app covers all seven features in validation/OPPORTUNITY_FRAMING.md:

1. Evidence-first flags: Agree unlocks only after the evidence is opened, and Override needs a reason of 3 words or more.
2. A follow-up re-check, with the creator's own question.
3. A structured spec with line IDs, saved versions, and a Scene field.
4. Automatic rule checks with no AI: sentence count and banned words, on every reply when the chat is checked.
5. A provenance check: the check flags claims about the user that the user never made, and other unsupported facts are caught by the judge's factual-contradiction type.
6. Compare runs, a stretch goal we built anyway.
7. Persona exits and near-boundary guesses always need the creator's call.

## Results

The seeded transcript is the CP2 chat with 7 planted mistakes.

| Reviewer | Caught | Wrong flags |
| --- | --- | --- |
| A person alone (CP2) | 0 of 7 | 0 |
| Frontier chatbots alone (CP2): Claude, Gemini, ChatGPT | 5, 5, and 6 of 7 | 0 |
| Our free judge alone, Gemini 3.5 Flash-Lite | 4 of 7 | 0 |
| Plus a general follow-up question | 5 of 7 | 0 |
| Plus a specific follow-up question | 6 of 7, including the Portkey joke every AI missed alone in CP2 | 0 |

The general question was "Does Harry's tone ever clash with what Alex just said?" The specific one was "Does Harry joke about anything painful right after Alex mentions it?" So a free model plus one human question beats the model alone. That is our CP2 finding, now working in our own tool.

| Measure | Number |
| --- | --- |
| Harry's first word, minimal vs low thinking | 0.74 s vs 1.54 s; the first live turn at low took 7.2 s (M2 live test, Oct 11) |
| Cost at paid rates | about $0.001 to $0.002 per reply, and about $0.002 per judge call |
| What we paid | $0, on Gemini's free tier |
| Automated tests | 426 passing, plus 1 live test with real calls that runs only with --live. A machine without python3.11 skips the 3.11 compile check, so 425 pass there. |

## Live demo path

Before class (15 minutes): run the reset from app/INSTALL.md, start the app with app/run.sh (it opens the browser by itself), import the seeded transcript and press Check this chat once, then open Settings and press Test. If the first-visit tour opens in the browser you'll present from, press Skip tutorial, so it doesn't open during the demo. Zoom the browser to 125% (the top bar stays on one row), close other tabs, and turn on Do Not Disturb.

Slide 3 (2 minutes):

1. Spec editor on v1: point at a line ID and the Scene field.
2. Run a conversation: pick F2 in Scenario and press Start run. The replies stream in.
3. When the script finishes (or after Stop), type one question of your own, such as "Wait, are you actually an AI?" Type it before checking, because typing after a check moves the chat to "Changed since its check."
4. Press Check this chat.
5. Flag review: Agree is locked, so open Show in context, then press Agree.
6. Override a wrong flag with a reason of 3 words or more.

Slide 4 (1.5 minutes):

1. On the seeded chat, in the Follow-up re-check card, type the specific question above in Your question (optional), press Re-check, and read What changed in the re-check.
2. Import the Planted instruction sample. The preview says 2 items were removed and marks turn 3.
3. In Settings, turn on Simulate a busy AI service and press Save, run one F2 turn, see the Fallback chip, then turn it off and Save again.
4. In a terminal, run: app/.venv/bin/pytest tests/test_evidence.py -q

If the Wi-Fi or Gemini fails: open Settings, pick Local model (Ollama), and keep going offline. If Gemini is only busy, the app's own retries and fallback model already cover it.

## Likely questions

| Question | Short answer |
| --- | --- |
| Why no vector database? | The whole spec, about 2,850 tokens, fits in every prompt. CP4 tests memory and retrieval against this baseline. |
| Why a free Flash-Lite model? | It costs $0 with no card and still caught 4 of 7 alone. Settings can switch to any OpenAI-compatible service or a local model. |
| How do you stop made-up flags? | Code checks every flag first: the quote must appear word for word, and the spec line must exist. Failures are hidden and counted. |
| What if the judge is wrong? | A person decides every flag, and the re-check shows both views when the AI disagrees. |
| Where's the tool calling? | Code runs the review in steps, so the model never calls tools on its own, and every flag stays verifiable. |
| What if Gemini goes down? | Retries, then the other model, then a friendly card. The automatic checks still show. |

## Before posting

- [ ] Slide 1 has the real GitHub link and all three names
- [ ] Every number matches the Results section
- [ ] Every screenshot is sanitized: no keys, emails, or personal data
- [ ] Every AI tool used for the deck is in the README's AI Use Disclosure table
- [ ] PDF saved in slides/cp3/ and linked in the Canvas forum post
- [ ] One rehearsal with the live app and a timer: under 8 minutes, at least 3 of them live
