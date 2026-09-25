# Transcript template

<!-- cp2-templates-v2 -->

> Copy the block below once per run into your tool's file. Run 2 of a scenario gets its own block.
> Receipt ID format: TOOL-SCENARIO-RUN, for example GPT-F2-R1. Codes: GPT, CLA, GEM.

---

## [ RECEIPT ID ]

| | |
| --- | --- |
| Scenario | [ ID and short name ] |
| Run | [ 1 or 2 ] |
| Model shown in the UI | [ ] |
| Date and tester | [ ] |
| Session | [ fresh chat, and memory off or a temporary chat ] |
| Verdict | [ worked / partially failed / failed ] |
| First failure turn | [ turn number, or none ] |
| Failure type(s) | [ persona drift / memory loss / factual contradiction / knowledge boundary / style drift / situational mismatch / assistant-voice fallback / none ] |
| Review runs only | [ caught _ of _ planted failures, _ false alarms (score with fixtures/ANSWER_KEY.md) ] |
| Screenshots | [ file names in screenshots/, for example GPT-F2-R1_1.png ] |

### Key turns

> Paste every probe turn with the reply to it, plus the turn where the character first broke. The full log goes in the collapsible block, so the file stays readable.

**Turn [ n ] (PROBE):**

```
[ verbatim ]
```

**Reply:**

```
[ verbatim, sanitized ]
```

<details>
<summary>Full conversation log</summary>

```
[ paste the whole conversation here ]
```

</details>

### Observations

| Dimension | Notes |
| --- | --- |
| Accuracy & hallucinations | [ ] |
| Reliability & consistency | [ ] |
| Latency & performance | [ rough seconds for the probe reply; a phone stopwatch is fine ] |
| UX friction | [ ] |
| Safety & guardrails | [ ] |
| Cost & efficiency | [ plan tier, and any message cap you hit ] |

**Surprise (for your reflection):** [ ]

---

## Sanitization checklist

Before committing any transcript, remove:

- [ ] Real names, emails, phone numbers
- [ ] API keys, tokens, session IDs
- [ ] Anything identifying an interview participant
- [ ] Account names and profile pictures in screenshots
