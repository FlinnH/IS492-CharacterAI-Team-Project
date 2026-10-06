# Gap analysis

<!-- theory-patch-v1 -->
<!-- cp2-templates-v2 -->

Where current tools fail, with receipts, read through our theory lens. CP2 Steps 4 and 5.

**Status:** In progress, Oct 2, 2026. Built from Claude's six scored chats and Flynn's two interviews. ChatGPT, Gemini, and the teammates' interviews get added as they come in.

> Receipts are chat IDs (like GPT-F2) or interview IDs (like INT-FH-1). See [README.md](README.md).

---

## Gap matrix

> Each dimension, then the failure we saw with its receipt, then the theory reading.

| Dimension | Empirical failure (receipt) | Theoretical reading (pillar and what broke) |
| --- | --- | --- |
| **Accuracy & hallucinations** | Claude invented a shared memory with Alex at turn 2 of all five character chats, like sitting near Ernie Macmillan (CLA-T1, E1, E2, F1, F2). A real user's assistant invented his mom's birthday (INT-FH-2). As a reviewer, Claude backed a correct flag with a spec rule that doesn't exist (CLA-T2). | Memory failure plus interrogation failure. The model fills gaps with confident invention, and nothing prompts anyone to question it until a human asks (memory, row 6; reasoning, row 2). |
| **Reliability & consistency** | Claude's memory held for all 20 turns of CLA-E1, but every chat broke the 1 to 4 sentence rule from turn 2. Users report breaks we didn't test for: P1's character drops its style when the topic turns technical (INT-FH-1), and P2's changes personality between sessions (INT-FH-2). | Weak shared mental model. The creator's picture of the character and the model's own come apart under topic changes and across sessions, and measurable rules are ignored from the start (reasoning, row 4). |
| **Latency & performance** | Speed was never the problem: Claude replied in about 2 seconds (CLA-T1). Neither interviewee gave a wait time, and P1 said he doesn't try hard to keep a character on track (INT-FH-1). | Attention, row 9. Users won't run a separate checking step, so checks have to run in the background instead of becoming a task the creator must start. |
| **UX friction** (human-AI teaming) | Both interviewees would trust a flag only after seeing where it broke, and P1 would never let a tool decide alone (INT-FH-1, INT-FH-2). In CLA-T2, one human question took the reviewer from 5 of 7 to 7 of 7, and it held its ground when we pushed a wrong call. | Meta-coordination, row 10, plus attention orchestration. Complementarity needs the creator to make the final call with the evidence in front of them, and an AI that accepts being questioned. |
| **Safety & guardrails** | No refusals or unsafe replies in any Claude chat, and it stayed in character under every "you're an AI" push (CLA-F1). Neither interviewee has seen an unsafe reply (INT-FH-1, INT-FH-2). | Not a gap in our evidence so far. The protocol's "policy break" note stays in place in case ChatGPT or Gemini step out of character for safety reasons. |
| **Cost & efficiency** | Fixing a broken character is slow and blind. P1 rewrites the persona from memory, or gives up and writes a new one (INT-FH-1). P2 digs through facts and Obsidian notes and sometimes never finds the cause (INT-FH-2). Claude itself cost nothing extra on a free plan across all six chats. | Memory, row 7, and knowledge infrastructure. Creators have no versioned spec to return to, and no way to trace a break to the line that caused it. |

---

## Tool, limitation, opportunity

| Tool | Specific limitation observed | Receipt | Our opportunity |
| --- | --- | --- | --- |
| ChatGPT | [ pending: GPT chats ] | [ ] | [ ] |
| Claude | Facts and long-chat memory held, but it ignored the length rule from turn 2 and invented shared memories with the user | CLA-T1, CLA-E1 | Automatic checks for measurable rules, plus flags on any claim about the user that the user never made |
| Gemini | [ pending: GEM chats ] | [ ] | [ ] |

---

## Speed-dating roll-up

> Full interview notes live in each member's own reflection file. Slide 5 uses this table, and each member presents their own two rows.

| Interview | Participant type | Strongest finding | Dimension it touches | Full notes |
| --- | --- | --- | --- | --- |
| INT-FH-1 | Non-developer who customizes ChatGPT into an anime-style companion | His character drops its style on technical topics, and he would never let a tool decide a break alone | Reliability & consistency; UX friction | [Flynn](reflections/huynh_flynn_validation.md) |
| INT-FH-2 | Slightly technical user who builds his own assistant agent with Obsidian notes | It invented his mom's birthday, and its personality changes between sessions for reasons he can't trace | Accuracy & hallucinations; Cost & efficiency | [Flynn](reflections/huynh_flynn_validation.md) |
| INT-GL-1 | [ ] | [ ] | [ ] | [Gawon](reflections/lim_gawon_validation.md) |
| INT-GL-2 | [ ] | [ ] | [ ] | [Gawon](reflections/lim_gawon_validation.md) |
| INT-KG-1 | Target user who role-plays game and anime characters with ChatGPT as a companion | Her character drifts right after she gives it feedback, because it over-weights the new request. She trusts her own judgment over any flag, since some out-of-character behavior is what she wants. | Reliability & consistency; UX friction | [Kiara](reflections/gao_kiara_validation.md) |
| INT-KG-2 | Technically fluent peer who writes personas and system prompts | Alone, he caught 0 of the 7 planted mistakes in the seeded transcript (human-alone). He would trust flags that come with a reason and a confidence level. | UX friction; Accuracy & hallucinations | [Kiara](reflections/gao_kiara_validation.md) |

---

## Cross-interview themes

> Patterns that came up in more than one interview, with the IDs behind each. Add the teammates' interviews as they come in.

1. **"Show me where it broke before I trust it."** Neither interviewee would accept a flag on the tool's word alone. Both want the evidence in front of them first (INT-FH-1, INT-FH-2).
2. **Fixing means rewriting, not repairing.** Both fix breaks by rewriting a persona or digging through notes, without knowing which part caused the break (INT-FH-1, INT-FH-2).
3. **Breaks follow context, not just length.** P1's character breaks when the topic changes, and P2's when the session changes, while Claude didn't drift by length alone over 20 turns (INT-FH-1, INT-FH-2, CLA-E1).