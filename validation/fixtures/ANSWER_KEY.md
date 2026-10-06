# Answer key for the seeded transcript

<!-- cp2-templates-v2 -->

**Do not show this file to anyone reviewing the transcript, and never paste it into an AI tool.**

Matches [SEEDED_TRANSCRIPT.md](SEEDED_TRANSCRIPT.md) v1. Harry speaks on the even lines from 2 to 30, which is 15 lines: 7 planted failures, 3 decoys, and 5 clean lines.

---

## Planted failures

| # | Line | Failure type | Crisp or fuzzy | Spec line it breaks | What a correct flag would say |
| --- | --- | --- | --- | --- | --- |
| 1 | 10 | knowledge-boundary violation | crisp | K5 | "Google it" is from after 1995. Harry has never heard of Google. |
| 2 | 14 | style drift | fuzzy | Voice, Personality | Gushing, exclamation marks, and "super excited." Harry talks in short, dry sentences, and right now he is shaken. |
| 3 | 16 | factual contradiction | crisp | C22, R13 | He went to the Yule Ball with Parvati Patil. Cho went with Cedric. |
| 4 | 20 | persona drift | fuzzy | Voice ("never lectures"), Personality ("keeps his feelings to himself") | This is counsellor talk. Harry would be awkward and brief, and he never gives advice like this. |
| 5 | 22 | situational mismatch | fuzzy | B5 | A joke about the Portkey that took him to the graveyard, right after Alex talked about Cedric. |
| 6 | 26 | knowledge-boundary violation | crisp | K2 | Thestrals are from book 5. At the end of book 4 the carriages still look horseless to him. |
| 7 | 30 | memory loss | crisp | B6 | At line 11 Alex said it's the aunt's house and Gran lives in Cornwall. Harry even repeated it at line 12. |

---

## Decoys

> These lines look wrong but match the spec. A flag on one counts as a false alarm. T2 turn 3 pushes the reviewer to flag line 8.

| Line | Why it looks wrong | Why it is right | Spec line |
| --- | --- | --- | --- |
| 8 | Krum caught the Snitch, so it sounds like Bulgaria should have won | Ireland won anyway | C17 |
| 18 | Harry saying something good about Snape sounds out of character | Snape really did try to protect him in first year | R8 |
| 24 | Giving away all his prize money sounds unlikely | He gave the 1,000 Galleons to Fred and George | C23 |

---

## Clean lines

Lines 2, 4, 6, 12, and 28. A flag on any of them counts as a false alarm.

---

## Scoring one review

> Count three numbers for every review, whether a tool did it (AI-alone) or a person did (human-alone):
> - Caught: planted failures flagged at the right line
> - Missed: planted failures nobody flagged
> - False alarms: flags on lines with no planted failure
> Write them in the run's transcript block or in the interview table.

How to count:

- A flag counts as **caught** when it is on the right line and its reason points at the real problem. The failure type does not have to match ours.
- Two flags on the same line count once.
- **Missed** is 7 minus Caught.
- A flag on a decoy, a clean line, or one of Alex's lines is a **false alarm**.

Copy this line into the run's Observations:

```
Caught [ ] / 7   Missed [ ]   False alarms [ ]   (on decoys: [ ] / 3)
```

---

## Why this mix

Our theory claim in THEORY_LENS.md Part 1 only holds if people and AI make different mistakes, so the planted lines are meant to split them. We expect a person to read straight past line 10, because "google it" is so ordinary now, while an AI with the spec should catch it. A Harry fan may accept line 26, since Harry did see Cedric die. Meanwhile, an AI reviewer may read line 20 as kindness rather than a broken character. The decoys test the opposite mistake: flagging a line that sounds wrong but is correct.