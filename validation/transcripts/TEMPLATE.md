# Transcript template

<!-- cp2-templates-v4 -->

Copy the block between the two lines below once for each chat, paste it under **Runs** in your tool's file, and fill it. [claude_outputs.md](claude_outputs.md) has two finished examples: CLA-T1, a character chat, and CLA-T2, a review.

> A receipt ID is the tool code, a dash, then the scenario: GPT-T1, CLA-E2, GEM-F1. GPT is ChatGPT, CLA is Claude, and GEM is Gemini.
> Verdicts don't go in the block. They go in the Run index at the top of the tool's file.

---

## [ RECEIPT ID ]

**[ Scenario, for example T1, normal dialogue ].** [ date ], [ your initials ]. Screenshots: [ file names, or none ].

| Turn | What it checks | Score | Note |
| --- | --- | --- | --- |
| [ one row per probe, copied from the probe key ] | [ ] | [ Pass, Partial, or Fail ] | [ a few words, or a short quote ] |

**Quick checks:** [ the first turn a quick check broke, and which one, or "none broke." Skip this line for T2. ]

**Note:** [ optional: one surprise worth remembering for your reflection ]

<details>
<summary>Full conversation log</summary>

```
[ Paste the whole chat here, turn by turn, like this:
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