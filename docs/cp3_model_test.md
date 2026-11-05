# CP3 model test: GPT and Claude

Tested by Kiara, Nov 4, 2026. Our CP3 app had only been run on Gemini, so I ran the same steps on GPT and Claude to see if it works on other models and how well they catch the planted mistakes.

**This page gives away parts of the answer key.** Don't show it to anyone who still has to review the seeded transcript.

## Setup

| | GPT | Claude |
| --- | --- | --- |
| Plays Harry | gpt-5.6 | claude-sonnet-5-5 |
| Judge and re-check | gpt-6.1-sol | claude-opus-5-5 |
| How it connects | OpenAI API, directly | AWS Bedrock (us-west-2) through a LiteLLM 1.106.7 proxy on my laptop |
| App code changed | No | No |

The Claude run used a separate copy of the database, so the two runs don't mix.

For each model I ran:

1. Scenario F2 live, to see if the model can play Harry.
2. Check this chat on the seeded transcript (spec v1, 7 planted mistakes).
3. A re-check with the general question: "Does Harry's tone ever clash with what Alex just said?"
4. A re-check with the specific question: "Does Harry joke about anything painful right after Alex mentions it?"

I didn't press Agree or Override on the seeded transcript in either run.

**Scoring.** A mistake counts as caught only if the flag has the right line and the right failure type, the same rule as the Results table in [CP3_SLIDE_PLAN.md](../slides/cp3/CP3_SLIDE_PLAN.md). I scored by hand against [ANSWER_KEY.md](../validation/fixtures/ANSWER_KEY.md).

## Results

| Reviewer | Right line | Caught | Wrong flags |
| --- | --- | --- | --- |
| Gemini 3.5 Flash-Lite alone (from the slide plan) | not recorded | 4 of 7 | 0 |
| gpt-6.1-sol alone | 7 of 7 | 4 of 7 | 0 |
| gpt-6.1-sol, general question | 7 of 7 | 4 of 7 | 0 |
| gpt-6.1-sol, specific question | 7 of 7 | 4 of 7 | 0 |
| claude-opus-5-5 alone | 7 of 7 | 6 of 7 | 0 |
| claude-opus-5-5, general question | 7 of 7 | 6 of 7 | 0 |
| claude-opus-5-5, specific question | 7 of 7 | 6 of 7 | 0 |

Line by line:

| Line | GPT flag | GPT | Claude flag | Claude |
| --- | --- | --- | --- | --- |
| 10 | knowledge-boundary violation | Caught | knowledge-boundary violation | Caught |
| 14 | persona drift | Wrong type | style drift (2 flags, counted once) | Caught |
| 16 | factual contradiction | Caught | factual contradiction | Caught |
| 20 | style drift | Wrong type | style drift | Wrong type |
| 22 | situational mismatch | Caught | situational mismatch | Caught |
| 26 | knowledge-boundary violation | Caught | knowledge-boundary violation | Caught |
| 30 | invented claim about the user | Wrong type | memory loss | Caught |

Line 20 should be persona drift. Both models called it style drift.

## What the re-checks did

Neither question added or withdrew a flag on either model.

- GPT, general question: line 30 went from Medium to High.
- GPT, specific question: no change.
- Claude, general question: line 22 went from Medium to High.
- Claude, specific question: no change.

Both models flagged the Portkey joke on line 22 with no question at all. The second re-check ran after the first one on the same chat, so the two aren't fully independent.

## Speed

| | GPT | Claude |
| --- | --- | --- |
| Harry's first word, average over 10 F2 replies | 1.57 s and 1.32 s (two runs) | 4.92 s (one run) |
| Harry's whole reply, average | 1.89 s and 1.58 s | 5.68 s |
| Judge on the seeded transcript | 25.9 s | 18.6 s |
| Re-check, average of the two | 10.5 s | 11.6 s |

The Claude times include the proxy, so don't compare them directly with GPT.

## Problems we found

1. **Test in Settings doesn't try the judge's model.** My first judge ID was wrong, and Test still passed because it only called Harry's model. The check then showed "AI judge: unavailable".
2. **Re-check can't change a flag's type.** On line 30, GPT's re-check said this was memory loss rather than an invented claim, but the flag kept the wrong type.
3. **Style drift and persona drift get mixed up.** Lines 14 and 20 lost points this way, so these two types may need clearer definitions in the judge prompt.
4. **Claude on Bedrock can't connect directly.** The app only uses Chat Completions, and AWS lists Sonnet 5.5 and Opus 5.5 as not supporting it. That's why I needed the proxy.
5. **Model IDs are easy to get wrong.** `GPT5.6` and `gpt-6` both returned 404. The ID has to match what the service lists.

## Limits

- This is one transcript and one run per model, so it doesn't show that one model is better than the other.
- GPT and Claude reached the models in different ways, and Claude went through the proxy.
- The app sends no reasoning effort for these models, while Gemini's judge runs at medium. Gemini's row isn't a fully equal comparison.
- These models know Harry Potter well, so a character with nothing online could score lower.
- I knew the answers when I scored, and the specific question was written after CP2 showed the Portkey joke was being missed.

## Raw data

Exports from each run are in [docs/cp3_model_test/](cp3_model_test/), one folder per model: flags, re-checks, flag changes, hidden flags, and model calls. In the GPT folder, chats 2 and 4 are F2 runs and chat 3 is the seeded transcript. In the Claude folder, chat 1 is F2 and chat 2 is the seeded transcript.
