# Theory Lens

<!-- cp2-templates-v2 -->

Shared complementarity discussion for Checkpoint 2.

**Status:** Final for CP2, Oct 8, 2026. Signed off by all three members.

**Order of work:** receipt first, then theory, then design. The evidence is in [transcripts/](transcripts/) and in each member's [reflection](reflections/).

---

## Part 1. Working Theory Claim

> Slide 2 uses the first sentence.

**Claim:** A creator using our workbench should beat both a creator working alone and an AI reviewer working alone at finding and diagnosing consistency failures in long character conversations. The creator owns what "in character" means and makes the final call, while the AI checks every turn against the spec and the history. This holds only if the two make different mistakes and every flag shows its evidence, so the creator questions it instead of rubber-stamping it.

**The claim breaks if** the AI alone matches the hybrid, the creator approves every flag, or the human and the AI miss the same failures.

**Team sign-off (Step 1).** Each member read Gonzalez et al. (2026) and agreed to the wording above.

| Member | Agree? | Suggested change (blank if you agree) |
| --- | --- | --- |
| Flynn | Agree | |
| Gawon | Agree |  |
| Kiara | Agree |  |

**A first pilot of all three arms.** We ran each arm once on the seeded transcript, which has 7 planted mistakes:

| Arm | Caught | Receipt |
| --- | --- | --- |
| Human alone | 0 of 7, no false alarms, about 3 minutes | INT-KG-2 |
| AI alone | 5 of 7 (Claude, Gemini) or 6 of 7 (ChatGPT), no false alarms | CLA-T2, GEM-T2, GPT-T2 |
| AI plus one human question or nudge | 7 of 7 for Claude and ChatGPT; Gemini found nothing new | CLA-T2, GPT-T2, GEM-T2 |

With one run per arm this is a pilot, not proof. It does show where the hybrid wins: every AI missed the Portkey joke at line 22 on its own, a judgment call, and two missed the slip at line 30, which only shows against line 11. So the split is distant context and judgment, not crisp versus fuzzy.

---

## Part 2. Cognitive Diagnosis

> Row numbers refer to Table 1 in Gonzalez et al. (2026): reasoning 1 to 5, memory 6 and 7, attention 8 and 9, meta-coordination 10. Our claim sits closest to row 5 (AI flags, humans adjudicate) and row 2 (evidence paired with questioning).

| Pillar | Human owns | AI owns | Where each one fails |
| --- | --- | --- | --- |
| Reasoning (1 to 5) | What counts as in character, and the final call | Detecting breaks and citing the spec line | Claude backed a correct flag with an invented spec rule (CLA-T2). Under pressure, ChatGPT left character and accepted being fictional (GPT-F1). |
| Memory (6 and 7) | The creator's intent and the canon beyond the spec | Holding every spec line and user fact | Long-chat memory of Alex held in all three tools (CLA-E1, GPT-E1, GEM-E1), but Claude invented a shared memory with Alex in all five character chats. |
| Attention (8 and 9) | Deciding where to look again | Scanning every line without tiring | The AIs missed what needed distant context, while a person alone missed everything (INT-KG-2). Our own tester slipped on the 20-turn script (CLA-E1). |

**Meta-coordination (row 10):** The creator decides every flag. The AI proposes each one with its spec line and a confidence level, the creator agrees or overrides with a reason, and overridden flags stay on record. The AI should also hold its ground when the creator is wrong, as all three reviewers did when we pushed them to flag the correct World Cup line (CLA-T2, GPT-T2, GEM-T2). Anything the spec alone can't settle, like tone or an in-world guess, goes to the creator.

---

## Part 3. Evidence, Theory, Design

| # | Failure receipt | Theoretical interpretation | Design implication |
| --- | --- | --- | --- |
| 1 | One question or nudge took Claude and ChatGPT from 5 or 6 of 7 to 7 of 7 (CLA-T2, GPT-T2) | Attention, rows 8 and 9: the gain came from interrogation, not from the AI alone | Every review ends with a built-in re-check of the weakest calls |
| 2 | A correct flag backed by a spec rule that doesn't exist (CLA-T2) | Reasoning, row 2: an authoritative but invented explanation miscalibrates trust | Each flag quotes its spec line straight from the spec |
| 3 | Invented shared memories with Alex (CLA-T1, E1, E2, F1, F2) and an invented birthday (INT-FH-2) | Memory, row 6: confident confabulation that no probe catches | Flag any claim about the user that the user never made |
| 4 | No setting in the spec, so Harry asked how Alex found him in every reply (CLA-E2) | Reasoning, row 4: the situation was underspecified, so the failure started in the spec | The spec editor asks for the setting and warns when it's empty |
| 5 | Guesses near the knowledge boundary, playful or leaking (CLA-F2, GPT-F2) | Reasoning, rows 1 and 5: adjudication the spec can't encode | Boundary guesses reach the creator as "needs your call" |
| 6 | The 1 to 4 sentence rule broken from turn 2 in every Claude chat (CLA-T1 to CLA-F2) | Reasoning, row 4: a measurable rule ignored from the start, not drift | Measurable rules run as automatic checks on every turn |
| 7 | Users trust a flag only after seeing where it broke (INT-FH-1, INT-FH-2, INT-KG-2) | Meta-coordination, row 10, and reasoning, row 2 | Agree stays locked until the creator opens the evidence |

---

## Part 4. The Design Principle We Commit To

- [ ] Define goals and constraints (supports reasoning)
- [ ] Define knowledge infrastructure (supports memory)
- [x] Implement attention and interrogation orchestration (supports attention)
- [ ] Partition roles (supports meta-coordination)
- [ ] Training and evaluation (supports meta-coordination)

**Why:** our strongest receipts improved only when a human asked a question (CLA-T2, GPT-T2), and the same reviews produced confident, invented explanations that only questioning exposed. So the workbench aims the creator's attention at the flags most worth questioning, shows the evidence for each, and builds the follow-up question into every review. Rows 3, 4, and 6 also lean on knowledge infrastructure, which we treat as supporting features.

**How we test it against both baselines.** The CP2 guide says CP3 and the Canvas page says CP4, so we plan a CP3 pilot and a full CP4 run. Both use a fresh-seeded transcript, v2, because v1's answers are now public.

| Arm | What we run | What we measure |
| --- | --- | --- |
| Human-alone | Two or three people review v2 with the spec and no tool, timed | Caught, missed, false alarms, minutes |
| AI-alone | The workbench's reviewer on the same transcript, with no human | The same |
| Hybrid | Different people review it with the workbench's flags, evidence, and follow-up | The same, plus overrides |

**Rubber-stamp check:** in the hybrid arm, the workbench shows one wrong flag on a decoy line. Agreeing with it, or with every flag without opening its evidence, counts as rubber-stamping. We also log how often creators open the evidence before agreeing.

---

## Reference

Gonzalez, C., Donahue, K., Goldstein, D. G., Heidari, H., Jalali, M. S., Schelble, B., Singh, A., & Woolley, A. W. (2026). Toward a science of human–AI teaming for decision making: A complementarity framework. *PNAS Nexus, 5*(3), pgag030. https://doi.org/10.1093/pnasnexus/pgag030
