# CHARACTER AI PROJECT

> **Tagline:** [ One sentence - who it helps and what it does. ]

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
| [ ] | [ ] | [ ] |
| [ ] | [ ] | [ ] |
| [ ] | [ ] | [ ] |

---

## Initial Concept & Value Proposition

> *What are we building, and why is generative AI functionally essential to it
> rather than decorative?*

[ ]

---

## Milestones Roadmap

| Checkpoint | Deliverable | Due | Owners |
| --- | --- | --- | --- |
| CP1 | Repo, literature review, proposal, kickoff presentation | Sep 17 | All |
| CP2 | Prompting study across 3+ tools, gap analysis, design spec, prototype | TBD | All |
| CP3 | Working end-to-end tool + live demo | TBD | All |
| CP4 | Evaluation study + final report (3,500–4,500 words) | TBD | All |

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
| [ ] | [ ] | [ ] |

---

## License

Code and documentation in this repository are released under the MIT License
(see LICENSE). Academic papers stored in `/literature/pdfs/` remain under their
original copyright and are included for course reference only.
