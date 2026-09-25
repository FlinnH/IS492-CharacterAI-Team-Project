# Theory Lens

Shared complementarity discussion for Checkpoint 2. Aim for 1 to 2 pages once filled in.

**Status:** DRAFT. Part 1 is the working wording from Step 1 and still needs the team's agreement.

**Order of work:** receipt first, then theory, then design. Parts 3 and 4 stay empty until the transcripts and interviews exist, so the theory explains what we saw and the evidence is never bent to fit it.

---

## Part 1. Working Theory Claim

> 2 to 3 sentences: what must be true for the hybrid to beat both baselines?
> Slide 2 uses the first sentence.

**(Flynn's draft claim)** Our hybrid (creator + workbench) should beat human-alone review and AI-alone review at finding and diagnosing consistency failures in long character conversations, because humans own what "in character" means and the final call, and AI owns checking every turn against the spec and history. This only holds if the two make different mistakes and the workbench shows evidence with each flag, so the creator questions it instead of accepting it. If the AI reviewer alone matches the hybrid, or the creator just approves every flag, complementarity fails.

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

<!-- cp2-templates-v2 -->
**Team sign-off (Step 1).** Each member reads Gonzalez et al. (2026), then agrees to the wording above or suggests a change. Slide 2 uses the first sentence once all three agree.

| Member | Agree? | Suggested change (blank if you agree) |
| --- | --- | --- |
| Flynn | [ ] | [ ] |
| Gawon | [ ] | [ ] |
| Kiara | [ ] | [ ] |

> Open question for the sign-off: the paper expects the biggest gains where humans and AI make different kinds of errors, and it says AI alone often does best on well-defined, structured tasks (see its "Task characteristics" section). Do we expect the hybrid to win on every failure type, or mainly on fuzzy ones (persona drift, style drift, situational mismatch) while the AI reviewer ties on crisp ones (factual contradiction, knowledge boundary)?

---

## Part 2. Cognitive Diagnosis

> Who owns what in the review task. The row numbers point to Table 1 in Gonzalez et al. (2026).
> Fill the Human and AI cells from what we saw in the transcripts and interviews.
>
> Table 1 rows, so nobody needs the paper open:
>
> - Reasoning: 1 ethical authority and accountability, 2 explainability and transparency, 3 bias and fairness checks, 4 goal alignment and facilitation, 5 error detection and recovery
> - Memory: 6 knowledge storage and retrieval, 7 expertise mapping and transactive memory
> - Attention: 8 filtering, triage, and anomaly detection, 9 workload and focus orchestration
> - Meta-coordination: 10 team structuring and process
>
> Our Part 1 claim sits closest to row 5 (AI flags, humans adjudicate) and row 2 (model evidence paired with human questioning).

| Pillar | Paper rows | Human owns | AI owns | Where each one fails |
| --- | --- | --- | --- | --- |
| Reasoning | 1 to 5 | [ ] | [ ] | [ ] |
| Memory | 6 to 7 | [ ] | [ ] | [ ] |
| Attention | 8 to 9 | [ ] | [ ] | [ ] |

**Meta-coordination note (paper row 10):** who makes the final call on a flag, when the creator can override, what happens when creator and AI disagree, and when the AI hands a turn to the human.

[ ]

---

## Part 3. Evidence, Theory, Design

> At least 3 rows. Start each row from something we actually saw (a scenario ID, a transcript quote, or an interview), then the theory reading, then what we change in the design.
> Vocabulary from the CP2 guide: hallucination is a memory plus interrogation failure; inconsistent advice is a weak shared mental model or trust calibration; long prompts are an attention orchestration failure; unclear who overrides is a meta-coordination or role partition gap.

| # | Failure receipt (scenario ID or interview) | Theoretical interpretation (pillar and what broke) | Design implication |
| --- | --- | --- | --- |
| 1 | [ ] | [ ] | [ ] |
| 2 | [ ] | [ ] | [ ] |
| 3 | [ ] | [ ] | [ ] |

---

## Part 4. The Design Principle We Commit To

> Pick one. The options are the design principles in Gonzalez et al. (2026).

- [ ] Define goals and constraints (supports reasoning)
- [ ] Define knowledge infrastructure (supports memory)
- [ ] Implement attention and interrogation orchestration (supports attention)
- [ ] Partition roles (supports meta-coordination)
- [ ] Training and evaluation (supports meta-coordination)

**Chosen principle and why:**

[ ]

**How Checkpoint 3 tests against both baselines**

> The CP2 guide says CP3, while the Canvas project page puts the full evaluation in CP4. Until the instructor confirms, plan CP3 as a small pilot of all three arms and CP4 as the full run.

| Arm | What we run | What we measure |
| --- | --- | --- |
| Human-alone | [ ] | [ ] |
| AI-alone | [ ] | [ ] |
| Hybrid | [ ] | [ ] |

**Rubber-stamp check:** [ how we will notice the creator approving every flag ]

---

## Reference

Gonzalez, C., Donahue, K., Goldstein, D. G., Heidari, H., Jalali, M. S., Schelble, B., Singh, A., & Woolley, A. W. (2026). Toward a science of human–AI teaming for decision making: A complementarity framework. *PNAS Nexus, 5*(3), pgag030. https://doi.org/10.1093/pnasnexus/pgag030
