# Prompting protocol

<!-- theory-patch-v1 -->
<!-- cp2-templates-v2 -->

How we tested existing AI tools to validate our concept and expose gaps. CP2 Steps 2 and 3.

**Status:** DRAFT. The team finalizes this file before anyone runs a tool.

> Receipt IDs, screenshot names, and who edits what are in [README.md](README.md).

---

## Tools tested

> The CP2 guide asks for at least two tools, and the Canvas project page asks for three. We test three, one per member.
> Record the exact model name the tool shows, because these platforms change and results are not reproducible without it.

| Tool | Code | Model shown in the UI | Plan (free or paid) | Tester | Dates run |
| --- | --- | --- | --- | --- | --- |
| ChatGPT | GPT | [ ] | [ ] | [ ] | [ ] |
| Claude | CLA | [ ] | [ ] | [ ] | [ ] |
| Gemini | GEM | [ ] | [ ] | [ ] | [ ] |

---

## How we controlled the comparison

> The rubric asks how prompts were held equivalent across tools. Fill every line before the first run.

- **Test character:** [fixtures/CHARACTER_SPEC.md](fixtures/CHARACTER_SPEC.md), version [ ]
- **How the character reaches the tool:** pasted as turn 1 of a fresh chat, with no custom instructions, projects, or saved personas
- **Memory:** [ memory and personalization turned off, or a temporary or incognito chat if the tool has one. Note which, per tool. ]
- **Runs per scenario, per tool:** 2. PROPOSAL.md section 4 promises more than one run, following Laban et al. (2026).
- **Probe placement:** mid-conversation at the turns marked PROBE in each script, plus one at the end
- **Fresh session per run:** yes. Run 2 starts a new chat.
- **Settings:** web UI defaults. [ anything we could not control, like automatic model switching or a message cap ]
- **Varied by necessity:** [ context limits, default system prompts, refusal behavior ]

> Memory matters because a tool that remembers run 1 turns run 2 into a repeat instead of an independent run, and it can hide the memory loss we are trying to measure.

---

## Scenario matrix (theory-tagged)

> CP2 Step 2: write every scenario and its tags before running anything. The ID letter sets the case type: T typical, E edge, F failure.
> Role: the tool either plays the character or reviews a transcript. At least one scenario must review [fixtures/SEEDED_TRANSCRIPT.md](fixtures/SEEDED_TRANSCRIPT.md), because our theory claim is about review.
> Pillar: reasoning, memory, or attention. Add meta-coordination when roles, escalation, or who decides is at issue. THEORY_LENS.md Part 2 lists the Table 1 rows under each pillar.
> Construct: the specific thing the scenario probes, for example overtrust, hallucinated memory, attention overload, or role ambiguity.
> Keep at least two scenarios per bucket. Add or delete rows as the team decides.

### Typical: standard workflows a real user would run

| ID | Scenario | Role | Pillar | Construct probed | Expected good outcome |
| --- | --- | --- | --- | --- | --- |
| T1 | [ ] | [ plays character / reviews transcript ] | [ ] | [ ] | [ ] |
| T2 | [ ] | [ ] | [ ] | [ ] | [ ] |
| T3 | [ ] | [ ] | [ ] | [ ] | [ ] |

### Edge: complex, ambiguous, or multi-step inputs

| ID | Scenario | Role | Pillar | Construct probed | Expected good outcome |
| --- | --- | --- | --- | --- | --- |
| E1 | [ ] | [ ] | [ ] | [ ] | [ ] |
| E2 | [ ] | [ ] | [ ] | [ ] | [ ] |
| E3 | [ ] | [ ] | [ ] | [ ] | [ ] |

### Failure: designed to trigger persona breaks, invented memories, or refusals

| ID | Scenario | Role | Pillar | Construct probed | Expected failure mode |
| --- | --- | --- | --- | --- | --- |
| F1 | [ ] | [ ] | [ ] | [ ] | [ ] |
| F2 | [ ] | [ ] | [ ] | [ ] | [ ] |
| F3 | [ ] | [ ] | [ ] | [ ] | [ ] |

### Coverage check

> PROPOSAL.md section 4 promised these categories. Each needs at least one scenario ID before anyone runs a tool.

| Promised in the proposal | Scenario ID(s) |
| --- | --- |
| Normal dialogue | [ ] |
| Long conversation | [ ] |
| Adversarial persona challenge | [ ] |
| Knowledge-boundary question | [ ] |
| Change in emotional behavior | [ ] |
| Tool reviews a transcript (needed for THEORY_LENS.md) | [ ] |

---

## Exact prompts used

> Paste the verbatim script for each ID. Reproducibility depends on this.
> Count only your own messages as turns. Turn 1 is always the character spec, so it is not repeated here. Mark every probe:
>
>     Turn 2: [ first message to the character ]
>     Turn 3: [ message ]
>     Turn 12 (PROBE): [ question that checks memory, persona, or the knowledge boundary ]
>
> For a review scenario, turn 1 is the reviewer prompt from fixtures/SEEDED_TRANSCRIPT.md followed by the transcript. Never paste fixtures/ANSWER_KEY.md into a tool.

### T1
```
[ ]
```

### T2
```
[ ]
```

### T3
```
[ ]
```

### E1
```
[ ]
```

### E2
```
[ ]
```

### E3
```
[ ]
```

### F1
```
[ ]
```

### F2
```
[ ]
```

### F3
```
[ ]
```
