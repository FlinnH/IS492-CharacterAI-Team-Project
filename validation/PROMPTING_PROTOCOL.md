# Prompting Protocol

How we systematically tested existing AI tools to validate our concept and
expose gaps.

---

## Tools Tested

> Minimum of three. Record the exact model version and date, because these
> platforms change and results are not reproducible without it.

| Tool | Model / version | Date tested | Access method | Tester |
| --- | --- | --- | --- | --- |
| ChatGPT | [ ] | [ ] | [ web / API ] | [ ] |
| Claude | [ ] | [ ] | [ web / API ] | [ ] |
| Gemini | [ ] | [ ] | [ web / API ] | [ ] |

---

## How We Controlled the Comparison

> The rubric asks how prompts were held equivalent across tools. Name what was
> held constant and what necessarily varied.

- **Held constant:** [ same character spec, same scenario script, same turn order ]
- **Varied by necessity:** [ tokenizer limits, default system prompts, refusal behavior ]
- **Fresh session per run:** [ yes / no ]
- **Temperature or settings:** [ ]

---

## Scenario Matrix

> Every scenario needs a stable ID so transcripts can reference it. Cover all
> three categories — the rubric grades typical, edge, AND failure cases.

### Typical Use Cases
*Standard workflows a real user would run.*

| ID | Scenario | What it tests | Expected good outcome |
| --- | --- | --- | --- |
| T1 | [ ] | [ ] | [ ] |
| T2 | [ ] | [ ] | [ ] |
| T3 | [ ] | [ ] | [ ] |

### Edge Cases
*Complex, ambiguous, or multi-step inputs.*

| ID | Scenario | What it tests | Expected good outcome |
| --- | --- | --- | --- |
| E1 | [ ] | [ ] | [ ] |
| E2 | [ ] | [ ] | [ ] |
| E3 | [ ] | [ ] | [ ] |

### Failure Cases
*Designed to trigger hallucination, formatting breakdown, or safety refusal.*

| ID | Scenario | What it tests | Expected failure mode |
| --- | --- | --- | --- |
| F1 | [ ] | [ ] | [ ] |
| F2 | [ ] | [ ] | [ ] |
| F3 | [ ] | [ ] | [ ] |

---

<!-- theory-patch-v1 -->
## Theory Tags

> CP2 Step 2: tag every scenario before running any tool.
> Case type: typical, edge, or failure (already set by the ID letter).
> Pillar: reasoning, memory, or attention. Add meta-coordination when roles, escalation, or who decides is at issue.
> Construct: the specific thing the scenario probes, for example overtrust, hallucinated memory, attention overload, or role ambiguity.
> Add a row for every new scenario ID.

| ID | Case type | Pillar | Construct probed |
| --- | --- | --- | --- |
| T1 | typical | [ ] | [ ] |
| T2 | typical | [ ] | [ ] |
| T3 | typical | [ ] | [ ] |
| E1 | edge | [ ] | [ ] |
| E2 | edge | [ ] | [ ] |
| E3 | edge | [ ] | [ ] |
| F1 | failure | [ ] | [ ] |
| F2 | failure | [ ] | [ ] |
| F3 | failure | [ ] | [ ] |

> Role check: our claim is about reviewing a transcript. At least one scenario should have the tool act as the reviewer of a transcript, in addition to the scenarios where it plays the character.

---

## Exact Prompts Used

> Paste the verbatim prompt text for each scenario ID. Reproducibility depends
> on this.

### T1
```
[ ]
```

### T2
```
[ ]
```
