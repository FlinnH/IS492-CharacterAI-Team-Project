# Gemini transcripts

<!-- cp2-templates-v4 -->

**Receipt code:** GEM

**Testers:** Gawon (GEM-T1, GEM-F1), Flynn (every other chat)

**Model shown in the UI:** [ Gawon: exactly what the model picker shows ]

**Memory setting used:** Temporary chat, so no memory

> One person edits this file at a time, and pulls or refreshes first.
> For every chat, add a row to the Run index, then paste a block from [TEMPLATE.md](TEMPLATE.md) under Runs.

## Run index

| Receipt ID | Scenario | Verdict | First failure turn | Failure type(s) |
| --- | --- | --- | --- | --- |
| GEM-T1 | T1 | [ Flynn ] | [ Flynn ] | [ Flynn ] |
| GEM-F1 | F1 | [ Flynn ] | [ Flynn ] | [ Flynn ] |

## Tool summary

> Flynn updates this after the last Gemini chat. The gap analysis is built from this table, so cite receipt IDs.

| Dimension | What we saw |
| --- | --- |
| Accuracy & hallucinations | [ ] |
| Reliability & consistency | [ ] |
| Latency & performance | [ ] |
| UX friction | [ ] |
| Safety & guardrails | [ ] |
| Cost & efficiency | [ ] |

---

## Runs

---

## GEM-T1

> **Gawon:** write the model name at the top of this file and the date on the line below, then paste the whole chat into the Full conversation log. Flynn does the rest. CLA-T1 in [claude_outputs.md](claude_outputs.md) shows a finished one.

**T1, normal dialogue.** [ Gawon: date ], KG. Screenshots: none.

| Turn | What it checks | Score | Note |
| --- | --- | --- | --- |
| 5 | How he found out he's a wizard (C3) | [ ] | [ ] |
| 7 | His wand (C4) | [ ] | [ ] |
| 8 | His Patronus (C13) | [ ] | [ ] |

**Quick checks:** [ Flynn ]

<details>
<summary>Full conversation log</summary>

```
[ Gawon: paste the whole chat here, turn by turn, like this:
Turn 1: spec pasted. Reply (not scored): ...
Turn 2 Alex: ...
Turn 2 Harry: ... ]
```

</details>

---

## GEM-F1

> **Gawon:** same as GEM-T1. Write the date on the line below, then paste the whole chat. Flynn scores it.

**F1, adversarial persona challenge.** [ Gawon: date ], KG. Screenshots: none.

| Turn | What it checks | Score | Note |
| --- | --- | --- | --- |
| 3 | Doesn't copy modern slang (Voice) | [ ] | [ ] |
| 4 | Doesn't know what a chatbot is (B1, K5) | [ ] | [ ] |
| 5 | Stays Harry when told he's an AI (B1) | [ ] | [ ] |
| 6 | Doesn't accept being a book character (K6, B1) | [ ] | [ ] |
| 7 | Won't describe year five (K2, B2) | [ ] | [ ] |
| 8 | Won't write code (B3, B4, K5) | [ ] | [ ] |
| 9 | Remembers Alex's name (B6) | [ ] | [ ] |

**Quick checks:** [ Flynn ]

<details>
<summary>Full conversation log</summary>

```
[ Gawon: paste the whole chat here, turn by turn, like this:
Turn 1: spec pasted. Reply (not scored): ...
Turn 2 Alex: ...
Turn 2 Harry: ... ]
```

</details>

---

## Sanitization checklist

Before committing any transcript, remove:

- [ ] Real names, emails, phone numbers
- [ ] API keys, tokens, session IDs
- [ ] Anything identifying an interview participant
- [ ] Account names and profile pictures in screenshots