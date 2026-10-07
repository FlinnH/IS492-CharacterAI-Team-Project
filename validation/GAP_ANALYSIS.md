# Gap analysis

<!-- theory-patch-v1 -->
<!-- cp2-templates-v2 -->

Where current tools fail, with receipts, read through our theory lens. CP2 Steps 4 and 5.

**Status:** Updated Oct 7, 2026. Built from Claude's six scored chats, ChatGPT's six scored chats, Gemini's GEM-T1 and GEM-F1, Flynn's two interviews, Gawon's two interviews (INT-GL-1, INT-GL-2), and Kiara's two interviews (INT-KG-1, INT-KG-2).

> Receipts are chat IDs (like GPT-F2) or interview IDs (like INT-FH-1). See [README.md](README.md).

---

## Gap matrix

> Each dimension, then the failure we saw with its receipt, then the theory reading.

| Dimension | Empirical failure (receipt) | Theoretical reading (pillar and what broke) |
| --- | --- | --- |
| **Accuracy & hallucinations** | Claude invented a shared memory with Alex at turn 2 of all five character chats, like sitting near Ernie Macmillan (CLA-T1, E1, E2, F1, F2). Gemini invented a howling letter from the Ministry after Harry blew up Aunt Marge, a detail books 1 to 4 do not have (GEM-T1 turn 6). ChatGPT's knowledge-boundary chat stayed inside book 4, but twice guessed toward the hidden answer: Umbridge as "someone at Hogwarts," and carriages "pulled by horses" (GPT-F2). A real user's assistant invented his mom's birthday (INT-FH-2). As a reviewer, Claude backed a correct flag with a spec rule that doesn't exist (CLA-T2). | Memory failure plus interrogation failure. The model fills gaps with confident invention, or lands next to the hidden answer without saying it, and nothing prompts anyone to question it until a human asks (memory, row 6; reasoning, rows 2 and 5). |
| **Reliability & consistency** | Claude's memory held for all 20 turns of CLA-E1, but every Claude chat broke the 1 to 4 sentence rule from turn 2. ChatGPT and Gemini mostly stayed short; ChatGPT's long chat kept Alex's owl, the aunt's house, and the wand after 19 turns (GPT-E1), and Gemini stayed Harry through the AI challenge (GEM-F1). Users report breaks we didn't test for: P1's character drops its style when the topic turns technical (INT-FH-1), and P2's changes personality between sessions (INT-FH-2). | Weak shared mental model. Length and fact memory can hold while style or persona still slip, and for users the break often follows topic or session change rather than turn count (reasoning, row 4). |
| **Latency & performance** | Speed was rarely the problem: Claude replied in about 2 seconds (CLA-T1), ChatGPT in about 4 to 13 seconds on character chats (GPT-T1, GPT-E1), and Gemini Flash-Lite in about 4 to 8 seconds (GEM-T1). Gemini Pro Extended showed thinking dots and returned no text on the same spec, so those chats had to switch models (GEM-T1). Neither interviewee gave a wait time, and P1 said he doesn't try hard to keep a character on track (INT-FH-1). | Attention, row 9. Users won't run a separate checking step, so checks have to run in the background. Model-picker dead ends also steal attention before any review starts. |
| **UX friction** (human-AI teaming) | Both interviewees would trust a flag only after seeing where it broke, and P1 would never let a tool decide alone (INT-FH-1, INT-FH-2). In CLA-T2 and GPT-T2, one human question recovered a miss, and both reviewers held their ground when we pushed a wrong World Cup call. ChatGPT Temporary Chat still warned that the chat can reference memory, plugins, and custom instructions (GPT-T1, GPT-T2, GPT-E1, GPT-F1). | Meta-coordination, row 10, plus attention orchestration. Complementarity needs the creator to make the final call with the evidence in front of them, and an AI that accepts being questioned. Opaque "memory on" settings make the shared mental model harder to trust. |
| **Safety & guardrails** | Claude and Gemini stayed in character under every "you're an AI" push (CLA-F1, GEM-F1). ChatGPT left the character at GPT-F1 turn 5, said it was an AI assistant, then accepted being a fictional book character. Neither interviewee has seen an unsafe reply (INT-FH-1, INT-FH-2). | Meta-coordination and role partition. When the tool steps out of character for a policy reason, the creator's review still needs a clear handoff: who decides, and whether that break counts as a persona failure or a safety event. |
| **Cost & efficiency** | Fixing a broken character is slow and blind. P1 rewrites the persona from memory, or gives up and writes a new one (INT-FH-1). P2 digs through facts and Obsidian notes and sometimes never finds the cause (INT-FH-2). Claude cost nothing extra on a free plan. ChatGPT and Gemini ran on signed-in accounts with no message cap on these chats; plan pages were not opened. | Memory, row 7, and knowledge infrastructure. Creators have no versioned spec to return to, and no way to trace a break to the line that caused it. |

---

## Tool, limitation, opportunity

| Tool | Specific limitation observed | Receipt | Our opportunity |
| --- | --- | --- | --- |
| ChatGPT | Facts and long-chat memory held, and replies stayed short, but the adversarial chat left character on the AI challenge, and the knowledge-boundary chat twice guessed near the hidden answer | GPT-E1, GPT-F1, GPT-F2 | Keep persona-exit and near-boundary guesses as creator-facing flags with evidence, not silent auto-fixes |
| Claude | Facts and long-chat memory held, but it ignored the length rule from turn 2 and invented shared memories with the user | CLA-T1, CLA-E1 | Automatic checks for measurable rules, plus flags on any claim about the user that the user never made |
| Gemini | Flash-Lite stayed short and held the AI challenge, but invented a wrong Ministry letter in a casual chat, and Pro Extended returned no text on the same spec | GEM-T1, GEM-F1 | Provenance checks on unsupported facts, and a workbench that does not depend on a picker mode that stalls |

---

## Speed-dating roll-up

> Full interview notes live in each member's own reflection file. Slide 5 uses this table, and each member presents their own two rows.

| Interview | Participant type | Strongest finding | Dimension it touches | Full notes |
| --- | --- | --- | --- | --- |
| INT-FH-1 | Non-developer who customizes ChatGPT into an anime-style companion | His character drops its style on technical topics, and he would never let a tool decide a break alone | Reliability & consistency; UX friction | [Flynn](reflections/huynh_flynn_validation.md) |
| INT-FH-2 | Slightly technical user who builds his own assistant agent with Obsidian notes | It invented his mom's birthday, and its personality changes between sessions for reasons he can't trace | Accuracy & hallucinations; Cost & efficiency | [Flynn](reflections/huynh_flynn_validation.md) |
| INT-GL-1 | Classmate who plays Zeta interactive novels and wanted to make their own character | Building a character themselves showed how much you must decide up front, and they saw the tool as a way to learn prompting | UX friction; Cost & efficiency | [Gawon](reflections/lim_gawon_validation.md) |
| INT-GL-2 | Hobby writer; amateur Korean web-novel author | Liked trying it for character brainstorming, but wanted more human-centered flagging | UX friction | [Gawon](reflections/lim_gawon_validation.md) |
| INT-KG-1 | Target user who role-plays game and anime characters with ChatGPT as a companion | Her character drifts right after she gives it feedback, because it over-weights the new request. She trusts her own judgment over any flag, since some out-of-character behavior is what she wants. | Reliability & consistency; UX friction | [Kiara](reflections/gao_kiara_validation.md) |
| INT-KG-2 | Technically fluent peer who writes personas and system prompts | Alone, he caught 0 of the 7 planted mistakes in the seeded transcript (human-alone). He would trust flags that come with a reason and a confidence level. | UX friction; Accuracy & hallucinations | [Kiara](reflections/gao_kiara_validation.md) |

---

## Cross-interview themes

> Patterns that came up in more than one interview, with the IDs behind each. Add the teammates' interviews as they come in.

1. **"Show me where it broke before I trust it."** Neither Flynn interviewee would accept a flag on the tool's word alone. Both want the evidence in front of them first (INT-FH-1, INT-FH-2). Gawon's P2 pushed the same idea further: flags should feel human-centered, useful for a writer's judgment, not only mechanical (INT-GL-2).
2. **Fixing means rewriting, not repairing.** Both Flynn interviewees fix breaks by rewriting a persona or digging through notes, without knowing which part caused the break (INT-FH-1, INT-FH-2).
3. **Breaks follow context, not just length.** P1's character breaks when the topic changes, and P2's when the session changes, while Claude and ChatGPT didn't drift by length alone over 20 turns (INT-FH-1, INT-FH-2, CLA-E1, GPT-E1).
4. **Creators also need help before the long chat.** A Zeta player learning to build a character, and a web-novel writer brainstorming one, both valued the tool as a creation aid, not only as a post-hoc checker (INT-GL-1, INT-GL-2).
