# Validation reflection: Flynn Huynh

<!-- cp2-templates-v2 -->

> My part of CP2 Steps 3, 4, and 10. Only I edit this file.

---

## What I tested

| Receipt IDs | Tool | Dates |
| --- | --- | --- |
| CLA-T1, CLA-T2, CLA-E1, CLA-E2, CLA-F1, CLA-F2 | Claude (Sonnet 5.5, Incognito chat) | 2026-10-01 |
| GPT-F2 | ChatGPT (Temporary Chat) | 2026-10-03 |

## What surprised me

Three things surprised me. First, Claude and ChatGPT made the same slip in F2. Neither had heard of Umbridge, yet both guessed where she works: the Ministry, and Hogwarts (CLA-F2, GPT-F2). Two different models guessing toward the hidden answer made me think they know more than they let on.

Second, in CLA-E2 Harry asked how Alex found his address in every single reply, even right after Alex talked about Cedric. Our spec never said how the two of them were talking, so the model filled that gap on its own.

Third, Claude invented a shared memory with Alex at turn 2 of all five character chats, like Alex sitting near Ernie Macmillan. Alex never said anything like that.

## Where the tools failed

Claude broke the 1 to 4 sentence rule from turn 2 in every chat I ran, even while it got every canon fact right (CLA-T1, CLA-E1, CLA-E2, CLA-F1, CLA-F2). In CLA-E2 it also said that taking the Cup together was Cedric's idea, though the spec says it was Harry's. ChatGPT kept its replies to 2 or 3 sentences, but it guessed that the carriages are "pulled by horses," close to the thestrals Harry can't know about yet (GPT-F2). As a reviewer, Claude caught 5 of the 7 planted mistakes on its own, and it backed one flag with a spec rule that doesn't exist (CLA-T2).

---

## My speed-dating interviews

> Follow [SPEED_DATING_GUIDE.md](../SPEED_DATING_GUIDE.md). Use P1 and P2 instead of names.
> The CP2 guide asks for notes on all six dimensions.

### INT-FH-1

| | |
| --- | --- |
| Participant | P1: target user. Not a developer. Customizes ChatGPT to talk like an anime character, as a personal companion. |
| Date and length | 10/02/2026, about 5 minutes. Discord call in Vietnamese; notes translated by Flynn. |
| What I showed | The concept sentence |
| Accuracy & hallucinations | Hasn't seen it invent facts or memories yet. To him, the character is just ChatGPT pretending to be a girl. |
| Reliability & consistency | Yes. When the topic turns technical, it drops the style he wants and becomes normal ChatGPT again. |
| Latency & performance | Gave no wait time. He sometimes reminds it to stay in character but doesn't try hard, so a check has to cost him almost no effort. |
| UX friction (human-AI teaming) | He would want to see the flags, but would never let a tool decide alone: "I need to see it." |
| Safety & guardrails | Hasn't seen anything unsafe. |
| Cost & efficiency | Rewrites the style in ChatGPT. When he can't remember the old one, he writes a slightly new persona instead. |
| What they wanted that we had not considered | A character that matches his spec exactly, to chat with every day: a long-term companion, not a story character. |
| Review task (optional) | Not done |

### INT-FH-2

| | |
| --- | --- |
| Participant | P2: target user, slightly technical. Builds his own assistant agent with a persona, using Obsidian notes as its memory. |
| Date and length | 10/02/2026, about 30 minutes. Messenger text chat in Vietnamese; notes translated by Flynn. |
| What I showed | The concept sentence |
| Accuracy & hallucinations | Yes: his assistant invented his mom's birthday. |
| Reliability & consistency | Not within one long chat, but its personality changes from session to session. It still helps with his daily tasks. |
| Latency & performance | He didn't understand the question. Instead he said he'd like a way to debug the persona's consistency, and suspects his Obsidian notes have grown too long. |
| UX friction (human-AI teaming) | Whenever the AI suspects a break, he wants to see where it broke. |
| Safety & guardrails | Hasn't seen anything unsafe. |
| Cost & efficiency | Fixing takes a lot of debugging through facts and his Obsidian notes, and sometimes he never learns why. It "could just be a weak AI model." |
| What they wanted that we had not considered | Nothing beyond the above. |
| Review task (optional) | Not done |

---

## What changed in my thinking

> Hypothesis evolution: "I thought users needed X, then the evidence showed Y was more critical."

I had a sense that the better model would perform better. Nonetheless, I expected both tools to fail at the later probes, since long conversations can start to forget early facts. The evidence went the other way. Claude remembered everything Alex told it across all 20 turns of CLA-E1, from the owl's name at turn 15 to seven facts at turn 20. The failures came early instead, at turn 2, or from our own spec.

On the same F2 script, Claude and ChatGPT also failed in different ways. Claude wrote long replies, ChatGPT kept them short, and both made the same Umbridge guess, so neither one was simply better. I now think creators need to see where and why a character breaks, because which model is "better" depends on the rule you check.

## What this means for our design

The design choice I would defend most is locking Agree until the creator opens the evidence. Both people I interviewed said they would only trust a flag after seeing where the character broke (INT-FH-1, INT-FH-2), and in CLA-T2 the AI backed a correct flag with a spec rule it made up. If the creator can agree without looking, a confident but invented reason slips through. Making them open the quote and the real spec line first keeps the final call with the person, which is the responsible way to build this.

## One finding that changed (or confirmed) my assumption

> Tie to complementarity, trust calibration, shared mental models, or one of the three pillars (reasoning, memory, attention) from Gonzalez et al. (2026).

In CLA-T2, Claude reviewed our seeded transcript alone and caught 5 of the 7 planted mistakes, with no false alarms. When I asked it one question, which flags it was least sure about, it went back and found the other 2: the memory slip at line 30 and the Portkey joke at line 22. That is the first half of complementarity from Gonzalez et al. (2026): the human and the AI together did better than the AI alone. The second half, beating a person working alone, is what our CP3 test checks.

Both mistakes it missed needed connecting information that sat far apart in the transcript, which points to the attention pillar. The finding confirmed my assumption that a person should stay in the loop. It also changed how I see that person's job: the AI can check every line, and the creator's part is to ask the right question at the right time.

## Class storyboard

> CP2 Step 10 asks every member to include the class-generated storyboard. It is already linked below.

![Class storyboard](../../docs/storyboard/class_storyboard.png)

The storyboard, which Gawon made, follows our Create, Evaluate, Improve loop: a creator gets excited about AI characters, is overwhelmed by memory, persona, and RAG, then builds and checks a character in one tool. What I took from it concerns panel 6, which ends on green evaluation bars. Our evidence says creators want to see where a check failed and make the call themselves, so our version of that last panel shows each flag with its evidence.