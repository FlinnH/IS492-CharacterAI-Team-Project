# Speed-dating guide

<!-- cp2-templates-v2 -->

How each of us runs two short interviews for CP2 Step 4. Each one takes about 10 minutes.

Speed dating is an HCI method for testing a concept with people before building it (Davidoff et al., 2007): you show a storyboard or a short concept and collect quick reactions. Participants can be target users (people who write characters or build with LLMs), classmates, or teammates. The Canvas project page allows documented team discussions.

---

## Before

1. Open the class storyboard, [docs/storyboard/class_storyboard.png](../docs/storyboard/class_storyboard.png), on your laptop or phone.
2. Open your reflection file and find the INT table for this interview.
3. Ask: "Is it okay if I take notes? I won't write down your name."

## During

**Show (1 minute).** Say: "We're building a workbench that tests whether an AI character stays in character over a long conversation, and shows the creator where and why it broke." Then show the storyboard.

**Ask (6 to 7 minutes).** One question per dimension. If a question clearly does not fit this person, skip it and note why.

| Dimension | Question |
| --- | --- |
| Accuracy & hallucinations | "Have you seen an AI character invent facts or memories? What happened?" |
| Reliability & consistency | "Has a character ever drifted or started acting differently in a long chat? How long before you noticed?" |
| Latency & performance | "How long would you wait for a check like this before giving up on it?" |
| UX friction (human-AI teaming) | "If a tool flagged a line as out of character, would you trust the flag? What would you need to see first?" |
| Safety & guardrails | "Has a character ever said something unsafe, or crossed a line because it was staying in character?" |
| Cost & efficiency | "What do you do today when a character breaks, and how long does fixing it take?" |

**Close (1 minute).** Ask: "What did we miss that you would want?"

## Optional: a 3-minute review task

If the participant has three extra minutes, show them [fixtures/SEEDED_TRANSCRIPT.md](fixtures/SEEDED_TRANSCRIPT.md) and ask them to point out every line where the character slips. Time it, then score it later against fixtures/ANSWER_KEY.md. Never show them the answer key.

This gives us human-alone data for the theory claim at almost no extra cost.

## After (about 5 minutes)

1. Finish your INT table while it is fresh.
2. Copy one summary row into the speed-dating roll-up in [GAP_ANALYSIS.md](GAP_ANALYSIS.md).
3. Commit your reflection file.

---

Davidoff, S., Lee, M. K., Dey, A. K., & Zimmerman, J. (2007). Rapidly exploring application design through speed dating. In J. Krumm et al. (Eds.), *UbiComp 2007: Ubiquitous Computing* (LNCS 4717, pp. 429–446). Springer.
