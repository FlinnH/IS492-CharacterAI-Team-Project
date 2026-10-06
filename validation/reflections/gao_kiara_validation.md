# Validation reflection: Kiara Gao

<!-- cp2-templates-v2 -->

> My part of CP2 Steps 3, 4, and 10. Only I edit this file.

---

## What I tested

| Receipt IDs | Tool | Dates |
| --- | --- | --- |
| INT-KG-1, INT-KG-2 (seeded-transcript review task) | No AI tool. Two people reviewed [SEEDED_TRANSCRIPT.md](../fixtures/SEEDED_TRANSCRIPT.md) on their own, as a first human-alone data point | 2026-10-06 |

The ChatGPT chats first assigned to me were run by Gawon, so my part of Step 3 was the human side of the review task. The CLA-T2 numbers are for the AI working alone, and these two runs show what a person catches without any tool.

## What surprised me

Three things surprised me. First, P1 said some out-of-character behavior is exactly what she wants. If she wants to date a villain like Light Yagami, the character has to break canon, so a tool that flags every deviation would be flagging her own choices (INT-KG-1).

Second, P1's character drifted right after she gave it feedback, not after a long chat. When she asked it to be more proactive, it overdid that and lost the rest of the persona (INT-KG-1). I had assumed drift comes from length.

Third, P2 caught none of the seven planted mistakes on his own and called the transcript fine. Once I showed him the answers he agreed with them, including the "google it" line that Harry could not know (INT-KG-2). Claude, working alone, caught 5 of the 7 (CLA-T2).

## Where the tools failed

These are failures the participants reported from their own use, not chats I ran.

- **ChatGPT pulls in memory from other chats.** P1's character invented preferences she never gave it, such as suggesting cake when she doesn't like cake (INT-KG-1).
- **Feedback gets too much weight.** One correction can override the whole persona (INT-KG-1).
- **The base model leaks through.** When the persona doesn't give enough information, P2 sees the base model's own speaking habits come in, and sometimes the language changes mid-reply (INT-KG-2).
- **Detailed canon goes missing.** ChatGPT could play a game character's personality but didn't know the character's old pen name (INT-KG-1).
- **Safety refusals block role-play.** P1 could not get a villain to say violent lines, and ChatGPT stopped a romance scene where both characters were set as high-school students (INT-KG-1). P2 has hit refusals on mental-health and some technical topics (INT-KG-2). I read the minor-related refusal as correct behavior. It matters to us because the tool has to tell a safety refusal apart from a character break.

---

## My speed-dating interviews

> Follow [SPEED_DATING_GUIDE.md](../SPEED_DATING_GUIDE.md). Use P1 and P2 instead of names.
> The CP2 guide asks for notes on all six dimensions. If one does not apply, write one sentence saying why.

### INT-KG-1

| | |
| --- | --- |
| Participant | P1: target user. Uses ChatGPT to role-play characters from games and anime as a companion. Gives it a full persona set in the character's world, and asks it to write actions in parentheses. |
| Date and length | 10/06/2026, about 13 minutes. In-person conversation in Mandarin; notes translated by Kiara. |
| What I showed | The concept sentence and the class storyboard, then the seeded transcript |
| Accuracy & hallucinations | ChatGPT pulls in memory from her other chats and guesses things about her she never said. In one scene it suggested they go eat cake, and she doesn't like cake. Once she corrects a fact, it doesn't repeat it. Knowing too much (like Harry knowing about TikTok) doesn't bother her, because she wants the personality, not the world. Missing knowledge does: it didn't know a game character's old pen name when she joked about it. |
| Reliability & consistency | Yes, and the trigger is her own feedback, not length. When she asks for a change, like "be more proactive with me," it puts too much weight on the new request, overdoes it, and drifts off the persona. It treats small requests as big ones. |
| Latency & performance | She gave no wait time. What she cares about is not being interrupted: a check that pops up mid-chat would pull her out of the "dream," so it should run somewhere else. |
| UX friction (human-AI teaming) | She would trust her own judgment over a flag. Everyone reads a character a little differently and wants a slightly different attitude from it. Some out-of-character behavior is what she wants, like dating a villain. To be useful, a tool would need the character's small details, and it should help rebalance: keep the persona while keeping the relationship changes she asked for. |
| Safety & guardrails | She wanted a villain to say violent lines and never got ChatGPT to do it. It avoids violence and self-harm entirely. It also stopped a romance scene where both characters were set as high-school students, which frustrated her. We see that refusal as correct, and the design point is that a safety refusal must not be counted as a character break. |
| Cost & efficiency | She opens a new chat, asks ChatGPT to recall the earlier prompt and conversation, and starts over. Restarting works better than tuning, because "the more I adjust it, the dumber it gets." |
| What they wanted that we had not considered | Writing the persona is the hard part. A character's personality is hard to put into words, so she asks the AI to reverse-engineer a prompt for her, and that fails for niche characters with little material online. She also said, unprompted, that she really needs a tool like this. |
| Review task (optional) | Not completed. She hasn't read or watched Harry Potter, so she couldn't judge Harry's lines and asked for a character she knows. |

### INT-KG-2

| | |
| --- | --- |
| Participant | P2: peer, technically fluent. Writes personas and system prompts for AI characters and story writing, and thinks in terms of base models, model size, and context length. |
| Date and length | 10/06/2026, about 18 minutes. Recorded conversation in Mandarin; notes translated by Kiara. |
| What I showed | The concept sentence and the class storyboard, then the seeded transcript |
| Accuracy & hallucinations | Yes. When the persona or story outline doesn't give enough information, the model fills the gap with elements that were never in the plan. The base model's own speaking habits come in, or the language switches, and the reply jumps out of character. |
| Reliability & consistency | Yes. When it starts depends on how long the persona is and how big the model is: often around turns 5 or 6, but with a long persona on a small model, at turn 1. Sometimes the first half of a reply is fine and the second half is not. |
| Latency & performance | For in-character chat he wants fast answers, not a long "thinking" pause. A check can't slow the conversation down. |
| UX friction (human-AI teaming) | He would probably trust the flags after spot-checking a few himself. Two things build that trust: a run of correct flags, and a reason under each flag with the tool's confidence. |
| Safety & guardrails | He hasn't seen a character cross a line in role-play, because he hasn't tried a villain. Outside role-play, older models refused to continue on mental-health topics and on some technical topics. |
| Cost & efficiency | He adds more constraint words to the persona or identity definition, and tells the model to follow the given context, persona, and background strictly. He puts that in the system prompt so it's injected every turn. A fix takes a few minutes to a few tens of minutes, because he has to change the configuration. |
| What they wanted that we had not considered | Sub-agents. Each reply would come from separate agents, one for tone, one that looks up the knowledge base, and one for memory, with an orchestrator that merges their results before the character answers. |
| Review task (optional) | Caught 0 of 7, 0 false alarms, about 3 minutes. He knows the films well but not the books. He called the transcript fine, only asking when the story is set. Once shown the answers, he agreed with line 10 ("google it"). He noted line 26 depends on knowing the story stops at book 4, which he wasn't told, and saw line 30 only after being pointed back to line 11. |

---

## What changed in my thinking

> Hypothesis evolution: "I thought users needed X, then the evidence showed Y was more critical."

I thought drift mainly came from long conversations, so the tool's main job would be to find the turn where a long chat broke. My interviews showed something else. For P1, drift starts right after she corrects the character, because the model gives her newest request too much weight (INT-KG-1). For P2, it depends on the persona's length and the model's size, and can start at turn 1 (INT-KG-2). I also thought "in character" was a fixed target set by the source material. P1 showed that each user defines it for themselves, and sometimes the break is the point.

So I now think users need two things more than a long-chat detector. They need a way to change how a character treats them without losing who the character is. And they need a tool that checks against their own version of the character, not against canon.

## What this means for our design

1. **The creator owns the definition of "in character."** P1 wants some breaks, so an override needs a reason like "intended," and that kind of override should teach the spec instead of being counted as an error. This supports our rule that the creator makes the final call on every flag.
2. **Separate the relationship from the identity.** P1's drift came from relationship feedback swamping the persona. In CP1 I proposed a three-layer spec from SimsChat: identity, social, and per-turn state. Her case is the reason for the social layer: "be more proactive with me" belongs there, so it can change without rewriting the identity.
3. **Review happens outside the chat.** Both participants care about the chat staying smooth: P1 doesn't want to be interrupted, and P2 doesn't want to wait. That fits our design of a separate workbench rather than warnings inside the chat.
4. **Each flag shows its reason and confidence.** P2 asked for exactly that, which matches the evidence-first flag review (OPPORTUNITY_FRAMING feature 1).
5. **Sub-agents are a CP4 idea, not a CP2 change.** P2's tone, knowledge, and memory agents line up with our failure types, and could become a way to trace which component caused a break. I'm noting it for later.

## One finding that changed (or confirmed) my assumption

> Pick one finding about the proposed scenario. Tie it to complementarity, trust calibration, shared mental models, or one of the three pillars (reasoning, memory, attention) from Gonzalez et al. (2026).

I expected a person who knows Harry Potter to spot most of the planted mistakes. P2 has watched the films many times and still caught 0 of 7 on his own (INT-KG-2), while Claude alone caught 5 of 7 (CLA-T2). P1 could not attempt the task at all, because she doesn't know the character (INT-KG-1). This changed my assumption: a human reviewer without the spec in front of them is weak at line-by-line checking.

Seen through Gonzalez et al. (2026), this is the human-alone baseline, and it fails mostly on memory and attention. P2 missed line 26 because he didn't know the story stops at book 4, which is knowledge infrastructure the spec holds and he didn't have. He missed line 30 because it only shows against line 11, the same far-apart link the AI missed. So the person shouldn't do the scanning. The AI scans, and the person decides what each flag means, which is the division of roles in our theory claim. My data is two people, so it's only a first point. It also tells us CP3's human-alone arm has to recruit people who know the character and give them the spec, or the baseline will look worse than it really is.

## Class storyboard

> CP2 Step 10 asks every member to include the class-generated storyboard. It is already linked below.

![Class storyboard](../../docs/storyboard/class_storyboard.png)

The storyboard follows a creator from excitement about AI characters, through confusion about memory, persona, and RAG, to building a character in one structured tool and ending on green evaluation bars. What I took from it is the last panel: my participants wouldn't accept a green bar on its own. P1 wants to decide what counts as in character, and P2 wants a reason and a confidence behind each check, so our version of panel 6 should show flags the creator can question, not just scores.
