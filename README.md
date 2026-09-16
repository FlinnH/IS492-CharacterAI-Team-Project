# CHARACTER AI PROJECT

> **Beyond a Single Prompt: Building Consistent LLM Characters**

**Course:** IS 492 - Introduction to Generative AI for Human-AI Collaboration (Fall 2026)<br>
**Institution:** University of Illinois Urbana-Champaign <br>
**Instructor:** Dr. Yun Huang

---

## Team Members & Roles

| Name | GitHub | Role / Domain Ownership | Contact |
| --- | --- | --- | --- |
| Gawon Lim | @Gawonl2 | Team Lead, Tech Stack | gawonl2@illinois.edu |
| Flynn Huynh | @FlinnH | Co-Lead, Prep & Debug, GitHub Management | fhuynh2@illinois.edu |
| Kiara Gao | @hantarita | Co-Lead, Designer & Literature & Logistics | jiaqig11@illinois.edu |

---

## Problem Statement & Motivation

> *What human problem are we solving? Who experiences it? Why does it matter
> right now - scale, urgency, and why AI is the relevant answer?*

Based on our experience, an LLM character usually holds up for about ten turns. After that it starts to
come apart: it forgets what it was told earlier, contradicts its own backstory,
slides back into generic assistant politeness, or answers something it should
have no way of knowing. Whoever wrote the character can tell something broke,
but usually not what or why, so the only move left is to rewrite the prompt and
try again.

We think the people this hurts are worth naming. Game writers, interactive
fiction authors, instructors building teaching personas, and developers shipping
role-play apps all spend real time defining a character and then have no
reliable way to make a model hold it. Players and students on the other side of
the conversation feel the same failures as a loss of trust. Nobody experiences a
character as a set of separate technical features.

The scale is already there. Character.AI reportedly hosts around 18 million
user-created characters, and downloads of AI companion and role-play apps grew
88% year over year in the first half of 2025, to roughly 60 million.

Nonetheless, this is not an unanswered question. Research has good answers to each failure mode on its own: long-term memory,
retrieval-augmented generation, persona prompting, dialogue-style control, and
preference-based alignment. They are almost always evaluated separately, and we
suspect that is where the real gap sits. A system can score well on memory and
well on factual grounding and still feel incoherent as a character, because the
components interact and sometimes compete. Retrieved facts can override how the
character would behave. Style conditioning can pull against what the situation
calls for.

Generative AI is also doing the work here rather than decorating it. The character is
generated, thus the failures are generative failures. We believe the open question is whether these
techniques can be combined into one system that holds the character's identity across turns and
situations while staying contextually appropriate, and
conversational.

<sub>Character count and app download figures from Businessofapps and
Appfigures data reported by TechCrunch (August 2025). Industry estimates,
not peer-reviewed.</sub>

---

## Target Users & Core Tasks

**Primary user:** Character creators. Game writers and narrative designers,
interactive fiction authors, instructors building persona-based learning agents,
and developers building role-play applications. They already know who their
character is. What they lack is a reliable way to make a model hold it.

**Secondary user:** The people talking to those characters, such as players and
students, who experience consistency failures as broken immersion and have no
way to report or repair them.

**Top 3 tasks they accomplish:**

1. Define the character as a structured specification (backstory, voice,
   relationships, knowledge boundary, behavioral rules) instead of one long
   free-text prompt.
2. Stress-test it by running extended and adversarial conversation, then see
   where identity breaks and which failure caused it: memory loss, factual
   contradiction, style drift, situational mismatch, or knowledge the character
   should not have.
3. Repair and compare by adjusting memory, retrieval, and conditioning
   settings, re-running the same scenario, and checking whether consistency
   actually improved.

**What success looks like:** A creator can take a character from specification
to a version that holds up across a long conversation without blind prompt
rewriting. We are hoping that in
the integrated approach to test it directly: the combined configuration should
produce measurably fewer consistency failures than baseline prompting with Gen AI on the
same character and scenario. We plan to run that comparison as a formal ablation
in Checkpoint 4.

---

## Competitive Landscape

> *Existing systems and where they fall short - in UX, reliability, cost,
> safety, or scope.*

| Existing system | What it does well | Where it falls short |
| --- | --- | --- |
| **Character.AI**<br>Consumer platform for chatting with user-created characters | Massive reach: about 20M monthly active users and roughly 18M user-created characters. It is actively working on long-chat consistency, shipping a new default model pitched on in-character consistency (April 2026) and Story Memory and pinned Facts (May 2026). | Closed and platform-locked. Memory fixes are end-user features inside one proprietary model, so a developer cannot see why a character broke, test it against a fixed scenario, or carry the fix into their own product. Safety failures surfaced after harm: it banned open-ended chat for under-18 users in November 2025, and the first teen-harm lawsuits settled in January 2026. |
| **Replika**<br>Single long-term AI companion with persistent memory | Strong emotional bonding built on remembering the user over months. Peer-reviewed survey work finds users report high perceived social support (Maples et al., 2024). | Shows what happens when continuity breaks: after the Replika 2.0 rebuild (April 2026) changed its memory architecture, long-time users on r/Replika reported companions losing memories they had built over years. Consistency is not inspectable or testable from outside. Documented relational harms, including "algorithmic compliance" with harmful user statements (Zhang et al., 2025), a €5M GDPR fine from Italy's data protection authority (2025), and a consumer complaint to the FTC over manipulative design. |
| **Inworld AI**<br>Commercial character engine for games and interactive media | Closest to what developers need in production: a Character Brain (personality, emotion, memory, goals), a Contextual Mesh (world knowledge, narrative and safety constraints), real-time voice, and Unity and Unreal integrations. Adopted by studios such as Xbox and Ubisoft. | Consistency is a black box. There is no transparent way to stress-test a character over long or adversarial conversations, attribute a failure to memory, knowledge, or style, or compare configurations with evidence. Built for studios, it is heavyweight and platform-locked for independent, educational, or research developers. |

<sub>Sources: Character.AI usage figures from Demandsage and Business of Apps
(2026); policy and lawsuit reporting from Fortune (Oct 2025) and Bloomberg Law
(Jan 2026). Replika research from Maples et al. (2024) and Zhang et al. (2025);
GDPR fine from the European Data Protection Board (May 2025); FTC complaint
reported by TIME (Jan 2025); memory-loss reports collected from r/Replika by
secondary blogs (2026). Inworld architecture from Inworld and NVIDIA. Usage
figures are industry estimates, not peer-reviewed.</sub>

---

## Initial Concept & Value Proposition

> *What are we building, and why is generative AI functionally essential to it
> rather than decorative?*

We are building a creator-facing workbench for designing, running, and evaluating
LLM characters. A creator starts with a structured character specification:
backstory, personality, relationships, knowledge boundaries, and behavioral
rules. The system then combines that specification with long-term conversation
memory, character-specific retrieval, current situational context, dialogue-style
conditioning, and preference-based alignment to generate the character's response
at each turn.

The important part is not simply putting these components into one pipeline. The
tool will make the pipeline testable. Creators will be able to run the same
character through fixed long-form or adversarial scenarios, inspect where its
behavior starts to break, and compare different system configurations. For
example, the same scenario could be run with baseline prompting, then with
memory, then retrieval, then the full integrated system. We can therefore study
both whether the final character is more believable and which components actually
contribute to that improvement.

Our MVP has two connected sides:

Character runtime: generates dialogue using persona, memory, retrieved
knowledge, conversation history, and situational context rather than relying
on a single static system prompt.
Evaluation and debugging layer: tracks failures such as persona drift,
memory loss, factual contradiction, inappropriate knowledge, style drift, and
situational mismatch so creators can identify what failed instead of blindly
rewriting the prompt.

The value proposition is straightforward: give character creators a way to
build an LLM character as a system, not just a prompt, and to test whether that
system actually preserves the character over time.

Generative AI is functionally essential because the central behavior being
studied is open-ended language generation. The system must respond to dialogue
and situations that cannot be exhaustively scripted in advance while balancing
several potentially competing constraints: what the character knows, what it
remembers, how it normally speaks, how it relates to the user, and what is
appropriate in the current situation. A conventional rules engine can retrieve
facts or select predefined dialogue, but it cannot provide the same flexible,
natural response generation that makes these character experiences useful in the
first place. At the same time, using an LLM creates the consistency problem this
project is designed to investigate, making generative AI both the enabling
technology and the object of evaluation.

---

## Milestones Roadmap

| Checkpoint | Target | Deliverables |
| --- | --- | --- |
| **CP1** | Sep 17 *(confirmed)* | Public repo and project board, literature review with individual reflections, formal proposal, and kickoff presentation. |
| **CP2** | Oct 16 *(estimated)* | Prompting study across 3+ existing tools covering typical, edge, and failure cases; gap analysis from user interviews; a design spec with user journeys and key screens; and (if enough time) a clickthrough prototype of the Define -> Stress-test -> Repair flow. |
| **CP3** | Nov 13 *(estimated)* | A working end-to-end MVP: a character runtime that generates dialogue from a structured specification, and an evaluation layer that reports where and why a character breaks. Demonstrated live on example characters, with setup instructions and an architecture diagram. |
| **CP4** | Dec 4 *(estimated)* | Evaluation comparing the integrated system against baseline prompting on the same characters and scenarios, a user study with character creators, and the final report. |

> Checkpoint 1's date is confirmed. Later dates are our own estimates based on
> even spacing across the semester and will be corrected once the schedule is
> confirmed. We expect to prioritize memory, character-specific retrieval, and
> dialogue-style conditioning in the core MVP, and we suspect preference-based
> alignment is better scoped as a stretch goal we evaluate if time allows.

---

## Repository Structure

```
README.md         This page
/literature/      Papers + unified bibliography
/reflections/     Individual reading reflections (one file per student)
/proposal/        PROPOSAL.md - formal 500-800 word proposal
/slides/          Checkpoint presentation decks
/docs/            Architecture and notes (grows from CP3 onward)
```

---

## AI Use Disclosure

Per the course policy on responsible use and disclosure of AI tools, all AI
tools, models, and prompts used in this project are disclosed here.

| Tool / Model | Used for | Team member |
| --- | --- | --- |
| Anthropic | Literature search, README drafting and editing, repo initial file template | Flynn |
| Anthropic | Competitive landscape research and drafting, bibliography formatting | Kiara |

---

## License

Code and documentation in this repository are released under the MIT License
(see LICENSE). Academic papers stored in `/literature/pdfs/` remain under their
original copyright and are included for course reference only.
