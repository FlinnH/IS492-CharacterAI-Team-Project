# Opportunity framing

<!-- theory-patch-v1 -->
<!-- cp2-templates-v2 -->

The product requirements our tool must meet that existing tools do not. CP2 Step 7.

**Status:** In progress, Oct 2, 2026. Built from GAP_ANALYSIS.md, THEORY_LENS.md Part 3, Claude's six scored chats, and Flynn's two interviews. ChatGPT and Gemini evidence gets added as it comes in.

---

## Hypothesis evolution

> Slide 2 needs "we thought X, then found Y." If the evidence confirmed an assumption, we say so and cite the receipt.

| We assumed at CP1 | Where we said it | Evidence that challenged or confirmed it (receipt) | What we believe now |
| --- | --- | --- | --- |
| A character holds up for about ten turns, then breaks | README, problem statement | Challenged. Claude's memory held all 20 turns of CLA-E1, yet every chat broke the 1 to 4 sentence rule from turn 2 (CLA-T1 to CLA-F2). Users see breaks after topic changes (INT-FH-1) and between sessions (INT-FH-2). | Breaks don't wait for turn ten. Rule-following can fail at once while facts and memory hold, and for users, breaks follow topic and session changes, not just length. |
| Creators can tell something broke, but not what or why | README, problem statement | Confirmed. P2 debugs facts and notes and sometimes never learns the cause (INT-FH-2). P1 rewrites the persona instead of fixing it (INT-FH-1). | Confirmed, and the "why" is the expensive part. Without it, users rewrite instead of repairing. |
| The failures fit our list: memory loss, factual contradiction, style drift, situational mismatch, out-of-boundary knowledge | README, core tasks | Mostly confirmed, with two additions. Invented claims about the user appeared in all five Claude character chats and in a real user's assistant (INT-FH-2). P1's character falls back into normal assistant talk on technical topics (INT-FH-1). | Add "invented claims about the user" and "assistant-voice fallback" to the list. Some failures also start in an underspecified spec, not in the model (CLA-E2). |
| Creators want a structured spec instead of one long free-text prompt | README, core tasks | Confirmed, with a twist. P2 suspects his long Obsidian notes cause breaks (INT-FH-2), and P1 can't get back to his old persona (INT-FH-1). Our own spec had no setting, which derailed CLA-E2. | The spec needs structure, a version history, and a setting field, so creators can return to a known-good version and see which line a break touches. |
| The primary user is the character creator | README, target users | Broadened. Both interviewees shape a personal companion or assistant for daily use, not characters for a story (INT-FH-1, INT-FH-2). | "Creator" includes everyday users who shape a daily companion. Their needs match a writer's: consistency, evidence, and a fast fix. |
| The AI reviewer would tie the hybrid on crisp failures and lose only on fuzzy ones | THEORY_LENS Part 1, open question | Challenged. Alone, Claude's reviewer missed one crisp and one fuzzy mistake, and one human question recovered both (CLA-T2). | The split isn't crisp versus fuzzy. The hybrid wins where a failure depends on connecting distant context, or on judgment. |

---

## Prioritized features

> Every feature has the full sentence: "Evidence X shows complementarity break Y; principle Z addresses it."
> P0 means the CP3 demo must show it. P1 means CP3 if time allows. P2 means CP4 or stretch.

| # | Feature | Priority | Justification: "Evidence X shows complementarity break Y; principle Z addresses it." | Target |
| --- | --- | --- | --- | --- |
| 1 | Evidence-first flag review: each flag shows the quote, the exact spec line it cites, and a confidence level. The creator agrees or overrides with a reason, and Agree stays off until the evidence is opened. | P0 | Evidence from CLA-T2, where the reviewer backed a correct flag with an invented spec rule, and from INT-FH-1 and INT-FH-2, where both users refused to trust a flag they couldn't see, shows a trust-calibration break; attention and interrogation orchestration addresses it. | CP3 |
| 2 | A built-in follow-up: after the first pass, the reviewer re-checks its weakest calls, and the creator sees what changed. | P0 | Evidence from CLA-T2, where one human question took the reviewer from 5 of 7 to 7 of 7, shows that complementarity breaks whenever nobody asks; attention and interrogation orchestration addresses it. | CP3 |
| 3 | A structured spec with line IDs, a version history, and a setting field that warns when it's empty | P0 | Evidence from CLA-E2, where a spec with no setting made Harry ask how Alex found him in every reply, and from INT-FH-1, who can't get back to his old persona, shows a broken shared mental model between creator and model; knowledge infrastructure addresses it. | CP3 |
| 4 | Automatic checks for measurable rules, like sentence count and banned words, on every turn | P1 | Evidence from CLA-T1 to CLA-F2, which all broke the 1 to 4 sentence rule from turn 2 while getting every fact right, shows a goal-alignment break the AI judge doesn't catch; defining goals and constraints addresses it. | CP3 |
| 5 | A provenance check that flags any claim about the user the user never made | P1 | Evidence from the invented shared memories in all five Claude character chats and the invented birthday in INT-FH-2 shows a memory break no probe catches; knowledge infrastructure addresses it. | CP3 |
| 6 | Compare runs: the same script across sessions, tools, or system versions, side by side, with the first break marked | P2 | Evidence from INT-FH-2, whose assistant changes personality between sessions, and from the same Harry script scoring differently across tools, shows an unreliability that a single run hides; training and evaluation addresses it. This also serves the CP4 ablation study. | CP4 |

---

## Explicitly out of scope

> Naming what we are not building protects us at CP3, where every proposed feature has to be demonstrated.

- Preference-based alignment, meaning tuning a character from creator feedback. It stays a stretch goal.
- Hosting characters for the public, or chats with several users at once.
- Scenes with more than one AI character.
- Safety moderation beyond what each underlying model already does. No unsafe replies showed up in our evidence.