# What we need to decide together

**A note from Flynn, Nov 15, 2026.** I'm away from Sun Nov 15, so the two of you decide these and plan the work. My picks are on my lines below. They are only suggestions, so please choose whatever suits you two.

The five items under "Decide first" are for your first meeting. After that, each of you can work on your own part without waiting. The recommendations are Flynn's starting points, not decisions. Write your pick on your line before you meet.

## At a glance

| # | Decision | Recommended | Decided |
| --- | --- | --- | --- |
| 1 | Track A (a user study) or Track B (a benchmark) | Track B | |
| 2 | The test set: how many chats, how we make them, who makes them | Real chats from the app, mistakes planted by hand, about 4 each | |
| 3 | What we compare | A plain prompt versus our full judge, plus three knob tests | |
| 4 | Who does what, and by when | About 4 test chats and half the report each | |
| 5 | Two README promises we won't build | Edit those lines | |

The place to talk about these is [issue 102](https://github.com/FlinnH/IS492-CharacterAI-Team-Project/issues/102).

## Decide first (at our first meeting)

### 1. Track A or Track B?

**The question:** do we test our tool with real people, or test the AI judge with experiments and no people? The rubric asks us to pick one, and this choice affects everything else.

**Option A, a user study:** 6 to 10 classmates or friends each review two short chats, one alone and one with our workbench. We compare how many hidden mistakes they catch each way. Study mode won't be built, so Track A would now mean moderated sessions. One of you runs each session live, with the app as it is. [The how-to, section 3](HOW_TO_FINISH_CP4.md#3-track-a-without-new-building) has the steps.

- Good: it tests our main claim, that a person plus the AI catches more than either one alone.
- Good: it matches our README, which promises a user study, and it gives us people's own words.
- Hard: 6 to 10 people must finish by about Mon Nov 30, on their schedules, with Thanksgiving break in the middle.
- Hard: study mode was never built, so every session needs one of you there to run it.
- Hard: the people we'd most want, those who make AI characters, are hard to find.

**Option B, a benchmark:** we run the AI judge on about 8 test chats that have answer sheets, compare it with a simpler setup, and change one thing at a time to see what matters.

- Good: no participants, so it runs on our own timeline.
- Good: the rubric lists ablations, cost, and speed under Track B. The toolkit isn't built, but [the how-to](HOW_TO_FINISH_CP4.md#2-track-b-step-by-step) measures each one by hand.
- Hard: it can't show whether people do better with the tool. The report says so in Limitations.
- Hard: it needs about 8 test chats instead of 2, each with an answer sheet.
- Hard: "qualitative depth" becomes an error analysis: sorting what the judge gets wrong, with examples.

- **If we pick A, we also decide:** the survey (SUS or UMUX-Lite) and who recruits. Sessions would be live, since no study mode exists for a self-guided link.
- **If we pick B, we also decide:** the comparison in decision 3.

**Recommended: Track B.** It fits the time left and your own schedules. The deadline is Thu Dec 3, with Thanksgiving week in the middle. It still covers every part of the rubric's evaluation line.

- Flynn: Track B. It needs no participants, so other people's schedules can't hold it up.
- Gawon:
- Kiara:
- **Decided:**
- **Date:**

### 2. The test set

**The question:** which chats do we test on, and who makes them? Both tracks need chats with hidden mistakes and an answer sheet. The old seeded chat can't be used, because its answer sheet is public in validation/fixtures/.

**How many:** Track A needs 2 chats of equal difficulty. Track B needs about 8.

**Three ways to make them:**

- Real chats, then plant: run a test case in the app (Gawon's all-in-one or a custom one), edit a few of Harry's lines to plant mistakes, and fill in the answer sheet. It keeps Harry's real voice and uses our own feature. A real chat can also contain mistakes that nobody planted, so a second person checks every line.
- Claude drafts, we edit: Claude writes each chat and its answer sheet, and a teammate fixes them. It's the fastest, but AI-written mistakes may be easier for the AI judge to find, and the report must say AI helped.
- From scratch: we write everything by hand, like the old chat. It's fully human-made, and the slowest.

**Recommended: real chats, then plant,** split between the two of you, about 4 each. Each of you checks the other's answer sheets.

- Flynn: real chats, then plant.
- Gawon:
- Kiara:
- **Decided:**
- **Date:**

### 3. What we compare

**The question:** what do we measure the judge against, and which knobs do we turn?

**If Track B:**

- Systems: (1) a plain prompt, where the same model gets the spec and the chat and lists the lines that break the spec. This is the "baseline prompting" our README promised. (2) Our full judge, with its evidence check and automatic rules. (3) Optional: Claude, ChatGPT, and Gemini by hand, as in CP2.
- Knobs (ablations): the follow-up question (none, general, or specific), the model (Gemini 3.5 Flash-Lite, Gemini 3.1 Flash-Lite, or a free local model through Ollama), and the thinking effort (minimal, medium, or high). The thinking effort can't be changed by hand. It needs the toolkit, which isn't built.
- Measures: precision (how many flags were right), recall (how many mistakes were caught), and F1 (the two combined), each by mistake type, plus cost and seconds per check. Each setup runs 3 to 5 times, because AI answers vary.

**If Track A:** the two arms (alone and with the workbench), the AI alone as a third reference, the measures (mistakes caught, wrong calls, time, and the survey), and the same knob tests on the judge.

**Recommended (if B): the plain prompt versus our full judge, plus the three knobs.** The chatbots by hand only if someone has time.

- Flynn: the plain prompt versus the full judge, plus the three knobs. Drop the thinking-effort knob if the toolkit isn't there.
- Gawon:
- Kiara:
- **Decided:**
- **Date:**

### 4. Who does what, and by when

**The question:** who owns each chunk, and what are our own deadlines? The chunks match the GitHub issues.

The owners are now Gawon and Kiara. Where a cell is filled in, it is only Flynn's suggestion.

| Chunk | Owner |
| --- | --- |
| Setup: the team kit | Flynn. Done. |
| Setup: the public link and the toolkit | Not built. Open, if one of you wants to build either. |
| Test set | Both, about 4 chats each |
| Running the evaluation and the analysis | Gawon or Kiara: ____ |
| Final report (half each) | Both |
| Slides, demo recording, and the talk | Gawon or Kiara: ____ |
| Final check and submit | Whoever submits: ____ |

**Our deadlines:** CP4 is due Thu Dec 3, 2026, at ____ (the time on Canvas). The talk is on ____. Test set done by ____, results by ____, report draft by ____, slides by 11:59 PM the day before the talk. Meeting 2: ____ (Flynn's suggestion: around Mon Nov 30).

The how-to has a [day-by-day plan](HOW_TO_FINISH_CP4.md#9-a-day-by-day-plan) with suggested dates.

**Recommended:** about 4 test chats each and half the report each. Every other chunk has one owner from start to finish.

- **Decided:**
- **Date:**

### 5. Two README promises

**The question:** our README says CP4 includes a user study with character creators, and memory and retrieval tested on and off. The app has no memory or retrieval yet, and character creators are hard to find in the time left. Do we build them, or edit those lines?

- Build them: memory and retrieval are new features, so that's days of work.
- Edit the lines: five minutes once decision 1 is made, and the report explains what we chose and why.

**Recommended: edit the lines.**

- Flynn: edit the lines.
- **Decided:**
- **Date:**

## Decide later (at our second meeting)

- Which results and charts go on the slides
- Who presents which slides
- What the 60-second demo shows
- A last read-through of the report
