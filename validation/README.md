# Validation (Checkpoint 2)

<!-- cp2-templates-v2 -->

This folder holds CP2 Steps 1 to 7 and Step 10. The design spec (Step 8) is DESIGN_SPEC.md at the repo root, and the prototype (Step 9) lives in prototype/.

## Order of work

Receipt first, then theory, then design. The CP2 guide says graders look for that chain, so tool runs and interviews come before any theory reading, and the theory comes before design choices.

| Step | File | Written by | When |
| --- | --- | --- | --- |
| 1 | THEORY_LENS.md, Part 1 sign-off | All three | Kickoff |
| 2 | PROMPTING_PROTOCOL.md and fixtures/ | Team | Before anyone runs a tool |
| 3 | transcripts/, one file per tool | That tool's tester | After Step 2 is final |
| 4 | Your own file in reflections/ (see SPEED_DATING_GUIDE.md) | Each member | Alongside Step 3 |
| 5 | GAP_ANALYSIS.md | Team session | After Steps 3 and 4 |
| 6 | THEORY_LENS.md, Parts 2 to 4 | Team session | Right after Step 5 |
| 7 | OPPORTUNITY_FRAMING.md | Team session | After Step 6 |
| 8 | ../DESIGN_SPEC.md | Section owners | Sections 1 to 5 can start early |
| 9 | ../prototype/ | Prototype owner | Once DESIGN_SPEC.md has journeys |
| 10 | Your own file in reflections/ | Each member | Add notes as you go, finish last |

## Working rules

These keep three people from overwriting each other in git.

1. Pull before you start. If you edit on github.com, refresh the page first.
2. Outside team sessions, edit only your own files: your tool's transcript file and your reflection file.
3. Fill the shared files (GAP_ANALYSIS.md, THEORY_LENS.md, OPPORTUNITY_FRAMING.md) during team sessions, with one person typing.
4. Commit and push as soon as you finish a piece.

The easiest way to edit is on github.com: open the file, click the pencil icon, then click "Commit changes."

## Receipt IDs and file names

Every claim in the gap analysis, theory lens, opportunity framing, and design spec cites a receipt ID, so it links back to something we actually saw.

| What | Format | Example |
| --- | --- | --- |
| Tool run | TOOL-SCENARIO-RUN | GPT-F2-R1 |
| Tool codes | GPT (ChatGPT), CLA (Claude), GEM (Gemini) | CLA-T1-R2 |
| Interview | INT-INITIALS-NUMBER | INT-KG-1 |
| Screenshot | receipt ID plus a number, in transcripts/screenshots/ | GPT-F2-R1_1.png |
| Wireframe | screen name plus version, in docs/wireframes/ | flag_review_v1.png |

Initials: FH (Flynn), GL (Gawon), KG (Kiara).
