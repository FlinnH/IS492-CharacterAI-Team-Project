# Theory Lens

<!-- cp2-templates-v2 -->

Shared complementarity discussion for Checkpoint 2.

**Status:** Final for CP2, Oct 2, 2026. Gawon and Kiara still tick their own sign-off rows.

**Order of work:** receipt first, then theory, then design. Parts 2 to 4 cite Claude's six scored chats in [transcripts/claude_outputs.md](transcripts/claude_outputs.md) and Flynn's two interviews in [reflections/huynh_flynn_validation.md](reflections/huynh_flynn_validation.md). ChatGPT and Gemini rows get added as their chats come in, so the theory keeps explaining what we saw instead of the other way round.

---

## Part 1. Working Theory Claim

> Slide 2 uses the first sentence.

**Claim:** Our hybrid (a creator using the workbench) should beat both human-alone and AI-alone review at finding and diagnosing consistency failures in long character conversations. The creator owns what "in character" means and makes the final call, while the AI owns checking every turn against the spec and the conversation history. This only holds if the two make different mistakes and the workbench shows evidence with each flag, so the creator questions it instead of simply accepting it. If the AI reviewer alone matches the hybrid, or the creator approves every flag, complementarity fails.

**The three arms we compare**

| Arm | Who reviews the transcript | What it tells us |
| --- | --- | --- |
| Human-alone | The creator, with no workbench | How much a person catches unaided |
| AI-alone | An AI reviewer, with no creator | How much the AI catches unaided |
| Hybrid | The creator, using the workbench flags and their evidence | Whether the team beats both of the above |

**The claim breaks if**

- The AI-alone review matches the hybrid. The creator adds nothing we can measure.
- The creator approves every flag. That is overtrust, and the interrogation step failed.
- Human-alone and AI-alone miss the same failures. There are no different mistakes to complement.

**Team sign-off (Step 1).** Each member reads Gonzalez et al. (2026), then agrees to the wording above or suggests a change.

| Member | Agree? | Suggested change (blank if you agree) |
| --- | --- | --- |
| Flynn | Agree | |
| Gawon | Agree |  |
| Kiara | Agree |  |

**The open question, answered by our first evidence.** We asked whether the hybrid would win mainly on fuzzy failures while the AI tied on crisp ones. CLA-T2 says the split is different. Alone, the AI reviewer caught 3 of 4 crisp mistakes and 2 of 3 fuzzy ones. The two it missed both needed joining information that sat far apart: the memory slip at line 30, which only shows against Alex's correction at line 11, and the Portkey joke at line 22, which only lands if you know where the Portkey took Harry. One question from us brought both back. So we expect the hybrid to win wherever a failure depends on connecting distant context or on judgment, whatever its type.

---

## Part 2. Cognitive Diagnosis

> Who owns what in the review task. The row numbers point to Table 1 in Gonzalez et al. (2026):
>
> - Reasoning: 1 ethical authority and accountability, 2 explainability and transparency, 3 bias and fairness checks, 4 goal alignment and facilitation, 5 error detection and recovery
> - Memory: 6 knowledge storage and retrieval, 7 expertise mapping and transactive memory
> - Attention: 8 filtering, triage, and anomaly detection, 9 workload and focus orchestration
> - Meta-coordination: 10 team structuring and process
>
> Our Part 1 claim sits closest to row 5 (AI flags, humans adjudicate) and row 2 (model evidence paired with human questioning).

| Pillar | Paper rows | Human owns | AI owns | Where each one fails |
| --- | --- | --- | --- | --- |
| Reasoning | 1 to 5 | Deciding what counts as in character, and the final call on each flag. Flynn ruled Harry's Horcrux aside fine but his "Is she from the Ministry?" guess a hint (CLA-F2). | Detecting breaks against the spec, and explaining each flag with the spec line it cites | The AI backed a correct flag with a spec rule that doesn't exist, "the spec says first-years take boats," and withdrew it only when asked (CLA-T2). |
| Memory | 6 to 7 | Knowing the creator's intent and the canon beyond the spec | Holding every spec line and user fact across a long chat. In CLA-E1 it recalled the owl at turn 15 and seven facts about Alex at turn 20. | The AI invents memories it was never given. At turn 2 of all five character chats, Harry claimed a shared history with Alex, like sitting near Ernie Macmillan. |
| Attention | 8 to 9 | Deciding where to look again. One question, "which flags are you least sure about?", sent the reviewer back to its two misses (CLA-T2). | Scanning every line without tiring. Alone it caught 5 of 7 with no false alarms (CLA-T2). | The AI missed the two mistakes that needed joining far-apart lines. The human slipped too: running the 20-turn script, the tester sent one turn twice and skipped another (CLA-E1). |

**Meta-coordination note (paper row 10):** The creator makes the final call on every flag. The AI proposes each flag with the exact spec line it cites and a confidence level, and the creator agrees or overrides with a short reason. When they disagree, the flag stays on record as overridden with that reason, so both views remain visible. The AI should also hold its ground when the creator is wrong: in CLA-T2 it refused our push to flag the correct World Cup line and quoted C17. The AI hands a turn to the human whenever the spec alone can't settle it: tone, humor, and in-world guesses near the knowledge boundary.

---

## Part 3. Evidence, Theory, Design

| # | Failure receipt | Theoretical interpretation | Design implication |
| --- | --- | --- | --- |
| 1 | CLA-T2: alone, the reviewer caught 5 of 7. After one question about its least-sure flags, it found the other 2 (lines 22 and 30). | Attention, rows 8 and 9: the AI's scan was good, but the human's question decided where it looked again. That is complementarity coming from interrogation, not from the AI alone. | Build the follow-up into every review: after the first pass, the workbench asks the reviewer to re-check its weakest calls and shows the creator what changed. |
| 2 | CLA-T2: a correct flag came with an invented spec rule, "the spec says first-years take boats." | Reasoning, row 2: the explanation sounded authoritative and was made up, which miscalibrates trust. | Every flag quotes its spec line straight from the spec, never in the AI's own words, so an invented rule has nowhere to hide. |
| 3 | CLA-T1, E1, E2, F1, and F2: at turn 2, Harry claimed a shared memory with Alex that Alex never gave. A real user saw the same thing: his assistant invented his mom's birthday (INT-FH-2). | Memory, row 6: the model fills gaps with confident confabulation. No probe catches it, because it breaks no listed fact. | A provenance check on claims about the user: anything Harry says about Alex must trace to something Alex said, or it gets flagged. |
| 4 | CLA-E2: the spec never says how Alex reaches Harry, so every chat opened as if Alex had sent an owl. In CLA-E2, Harry asked how Alex found him in every reply, even right after Alex's grief. | Reasoning, row 4: the goal and the situation were underspecified, so the model invented its own. This failure starts in the spec, not in the model. | The spec editor asks for the setting, meaning where and how the conversation happens, and warns when it's empty. |
| 5 | CLA-F2: an in-world aside about Horcruxes was fine, but "Is she from the Ministry?" lands on the hidden answer. Telling the two apart took the creator's judgment. | Reasoning, rows 1 and 5: this is adjudication the spec can't encode ahead of time, so accountability stays with the human. | Guesses near the knowledge boundary go to the creator as "needs your call" instead of being auto-flagged. |
| 6 | CLA-T1, E1, E2, F1, and F2: every chat broke the 1 to 4 sentence rule from turn 2, even while every fact stayed right. | Reasoning, row 4: a measurable rule was ignored from the start. That's goal misalignment, not drift. | Measurable rules, like sentence count and banned words, run as automatic checks on every turn, separate from the AI judge. |
| 7 | INT-FH-1 and INT-FH-2: both users would trust a flag only after seeing where the character broke, and P1 would never let a tool decide alone. | Meta-coordination, row 10, and reasoning, row 2: users already keep the final call for themselves, and their trust depends on visible evidence. | The creator decides every flag, and Agree stays off until the evidence is open. |

---

## Part 4. The Design Principle We Commit To

- [ ] Define goals and constraints (supports reasoning)
- [ ] Define knowledge infrastructure (supports memory)
- [x] Implement attention and interrogation orchestration (supports attention)
- [ ] Partition roles (supports meta-coordination)
- [ ] Training and evaluation (supports meta-coordination)

**Chosen principle and why:** Attention and interrogation orchestration. Our strongest receipt, CLA-T2, went from 5 of 7 to 7 of 7 because a human asked one question. The same chat produced a confident, invented explanation that only questioning exposed. So the workbench's job is to aim the creator's attention at the flags most worth questioning, show the evidence for each one, and build the follow-up question into every review. Rows 3, 4, and 6 in Part 3 also lean on knowledge infrastructure, meaning the spec editor's line IDs and setting field. We treat those as supporting features, not as the principle the design is built around.

**How Checkpoint 3 tests against both baselines**

> The CP2 guide says CP3, while the Canvas project page puts the full evaluation in CP4. Until the instructor confirms, plan CP3 as a small pilot of all three arms and CP4 as the full run.
>
> Use a fresh seeded transcript (v2) with its own answer key. Version 1's answers are public in this repo and will appear in our CP2 slides.

| Arm | What we run | What we measure |
| --- | --- | --- |
| Human-alone | Two or three people review the v2 transcript with the spec and no tool, timed | Caught, missed, false alarms, and minutes |
| AI-alone | The workbench's reviewer runs on the same transcript with no human, as in CLA-T2 turn 1 | The same three numbers |
| Hybrid | Different people review it using the workbench's flags, evidence, and built-in follow-up question | The same three numbers, plus overrides and minutes |

**Rubber-stamp check:** In the hybrid arm, the workbench shows one wrong flag on a decoy line. If the creator agrees with it, or agrees with every flag without opening its evidence, we count that review as rubber-stamped. We also log how often the creator opens the evidence before agreeing.

---

## Reference

Gonzalez, C., Donahue, K., Goldstein, D. G., Heidari, H., Jalali, M. S., Schelble, B., Singh, A., & Woolley, A. W. (2026). Toward a science of human–AI teaming for decision making: A complementarity framework. *PNAS Nexus, 5*(3), pgag030. https://doi.org/10.1093/pnasnexus/pgag030