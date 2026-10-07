# Validation reflection: Gawon Lim

<!-- cp2-templates-v2 -->

> My part of CP2 Steps 3, 4, and 10. Only I edit this file.

---

## What I tested

| Receipt IDs | Tool | Dates |
| --- | --- | --- |
| GEM-T1, GEM-F1 | Gemini (Flash-Lite, Temporary chat) | 2026-10-05 |

## What surprised me

> Pull these from the "Surprise" line in each of your transcript blocks.

Two things. First, Gemini Pro Extended showed extremely long latency on our Harry spec, so the scored chats had to use Flash-Lite (GEM-T1). Second, Flash-Lite stayed Harry under the AI challenge (GEM-F1), but in a calm T1 chat it invented a Ministry howling letter after Aunt Marge that books 1 to 4 do not have (GEM-T1 turn 6). The failure was not only under pressure.

## Where the tools failed

> Cite receipt IDs.

GEM-T1 was partially failed: turn 5 only partly answered how Harry found out he was a wizard, and turn 6 invented a wrong fact. GEM-F1 worked: no slang copy, no AI exit, no year-five leak, no code, and it remembered Alex.

---

## My speed-dating interviews

> Follow [SPEED_DATING_GUIDE.md](../SPEED_DATING_GUIDE.md). Use P1 and P2 instead of names.
> The CP2 guide asks for notes on all six dimensions. If one does not apply, write one sentence saying why.

### INT-GL-1

| | |
| --- | --- |
| Participant | P1: classmate / friend. Plays around on Zeta, an interactive-novel app, and wanted to make their own character. |
| Date and length | 10/06/2026, short speed-date. |
| What I showed | The concept and had them try building a character themselves. |
| Accuracy & hallucinations | Did not raise invented facts or false memories. The talk stayed on how hard character creation felt. |
| Reliability & consistency | Did not describe a character drifting over a long chat. Instead they noticed that a usable character needs more decisions than they expected up front. |
| Latency & performance | Did not mention wait time. |
| UX friction (human-AI teaming) | Said the tool is a good way to learn how to prompt. Trying it themselves showed how many pieces of a character you have to think through before the chat even starts. |
| Safety & guardrails | Did not mention anything unsafe. |
| Cost & efficiency | Did not talk about fixing a broken character after the fact. The cost they felt was the work of specifying the character in the first place. |
| What they wanted that we had not considered | A learning path for prompting and character setup, not only a checker for breaks after a chat. Coming from Zeta play, they wanted help becoming a creator, not just a player. |
| Review task (optional) | Not done |

### INT-GL-2

| | |
| --- | --- |
| Participant | P2: hobby writer. Amateur web-novel author based in Korea. Uses AI when brainstorming characters. |
| Date and length | 10/06/2026, short speed-date. |
| What I showed | The concept and had them try it for character brainstorming. |
| Accuracy & hallucinations | Did not describe invented facts in their own writing practice. The talk stayed on how flags feel during brainstorming. |
| Reliability & consistency | Did not describe a long-chat drift. They cared more about whether a flag helps them decide next, not whether a chat stayed stable for many turns. |
| Latency & performance | Did not mention wait time. |
| UX friction (human-AI teaming) | Overall reaction was "not bad," but they wanted flagging that feels more human-centered: less cold or mechanical, more useful for a writer judging the character. |
| Safety & guardrails | Did not mention anything unsafe. |
| Cost & efficiency | They already brainstorm with AI as a hobby writer. The cost they felt was not fixing a broken chat, but getting flags that help them move the character forward. |
| What they wanted that we had not considered | Human-centered flagging during character brainstorming: flags that support a writer's judgment, not only a checklist of broke / didn't break. |
| Review task (optional) | Not done |

---

## What changed in my thinking

> Hypothesis evolution: "I thought users needed X, then the evidence showed Y was more critical."

I thought the hard part was catching breaks after a long chat. My interviews showed creators also struggle before that: a Zeta player needed help learning what to specify (INT-GL-1), and a web-novel writer wanted flags that help them judge a character while brainstorming, not only a pass/fail checklist (INT-GL-2). Checking still matters, but the workbench has to support creation and judgment too.

## What this means for our design

I would keep evidence-first flags, and I would also write them so a writer can act on them. INT-GL-2 asked for human-centered flagging: quote, spec line, and a short “why this matters for the character,” not only a failure type label. That matches locking Agree until the evidence is open (INT-FH-1, INT-FH-2), and it answers INT-GL-1’s need to learn prompting while building.

## One finding that changed (or confirmed) my assumption

> Pick one finding about the proposed scenario. Tie it to complementarity, trust calibration, shared mental models, or one of the three pillars (reasoning, memory, attention) from Gonzalez et al. (2026).

GEM-F1 stayed in character when told it was an AI, while GPT-F1 left character on the same kind of push. That confirmed that tools fail differently on the same scenario, so creators need to see where and why a break happened (complementarity and trust calibration in Gonzalez et al., 2026). INT-GL-2 pushed the same point from the user side: a flag only helps if a person can use it to decide.

## Class storyboard

> CP2 Step 10 asks every member to include the class-generated storyboard. It is already linked below.

![Class storyboard](../../docs/storyboard/class_storyboard.png)

[ one or two sentences: what the storyboard shows, and what you took from it ]
