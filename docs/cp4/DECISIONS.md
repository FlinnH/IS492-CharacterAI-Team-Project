# What we need to decide together

We decide the five items under "Decide first" at our first meeting. After that, each of us can work on our own part without waiting. The recommendations are Flynn's starting points, not decisions. Write your pick on your line before we meet.

## At a glance

| # | Decision | Recommended | Decided |
| --- | --- | --- | --- |
| 1 | Track A (a user study) or Track B (a benchmark) | Track B | |
| 2 | The test set: how many chats, how we make them, who makes them | Real chats from the app, mistakes planted by hand, split three ways | |
| 3 | What we compare | A plain prompt versus our full judge, plus three knob tests | |
| 4 | Who does what, and by when | One chunk and two report sections each | |
| 5 | Two README promises we won't build | Edit those lines | |

We talk about these in [issue 102](https://github.com/FlinnH/IS492-CharacterAI-Team-Project/issues/102).

## Decide first (at our first meeting)

### 1. Track A or Track B?

**The question:** do we test our tool with real people, or test the AI judge with experiments and no people? The rubric asks us to pick one, and this choice affects everything else.

**Option A, a user study:** 6 to 10 classmates or friends each review two short chats, one alone and one with our workbench. We compare how many hidden mistakes they catch each way.

- Good: it tests our main claim, that a person plus the AI catches more than either one alone.
- Good: it matches our README, which promises a user study, and it gives us people's own words.
- Hard: 6 to 10 people must finish by about Nov 17, on their schedules, not ours.
- Hard: a study mode and a private link have to be built first.
- Hard: the people we'd most want, those who make AI characters, are hard to find.

**Option B, a benchmark:** we run the AI judge on about 8 test chats that have answer sheets, compare it with a simpler setup, and change one thing at a time to see what matters.

- Good: no participants, so it runs on our own timeline.
- Good: the rubric lists ablations, cost, and speed under Track B, and our toolkit is built to measure them.
- Hard: it can't show whether people do better with the tool. The report says so in Limitations.
- Hard: it needs about 8 test chats instead of 2, each with an answer sheet.
- Hard: "qualitative depth" becomes an error analysis: sorting what the judge gets wrong, with examples.

- **If we pick A, we also decide:** the survey (SUS or UMUX-Lite), self-guided by link or live sessions, and who recruits.
- **If we pick B, we also decide:** the comparison in decision 3.

**Recommended: Track B.** It fits our 8 days and our own schedules, and it still covers every part of the rubric's evaluation line.

- Flynn:
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

**Recommended: real chats, then plant,** split three ways so each of us makes 2 or 3. Someone who didn't make a chat checks its answer sheet.

- Flynn:
- Gawon:
- Kiara:
- **Decided:**
- **Date:**

### 3. What we compare

**The question:** what do we measure the judge against, and which knobs do we turn?

**If Track B:**

- Systems: (1) a plain prompt, where the same model gets the spec and the chat and lists the lines that break the spec. This is the "baseline prompting" our README promised. (2) Our full judge, with its evidence check and automatic rules. (3) Optional: Claude, ChatGPT, and Gemini by hand, as in CP2.
- Knobs (ablations): the follow-up question (none, general, or specific), the model (Gemini 3.5 Flash-Lite, Gemini 3.1 Flash-Lite, or a free local model through Ollama), and the thinking effort (minimal, medium, or high).
- Measures: precision (how many flags were right), recall (how many mistakes were caught), and F1 (the two combined), each by mistake type, plus cost and seconds per check. Each setup runs 3 to 5 times, because AI answers vary.

**If Track A:** the two arms (alone and with the workbench), the AI alone as a third reference, the measures (mistakes caught, wrong calls, time, and the survey), and the same knob tests on the judge.

**Recommended (if B): the plain prompt versus our full judge, plus the three knobs.** The chatbots by hand only if someone has time.

- Flynn:
- Gawon:
- Kiara:
- **Decided:**
- **Date:**

### 4. Who does what, and by when

**The question:** who owns each chunk, and what are our own deadlines? The chunks match the GitHub issues.

| Chunk | Owner |
| --- | --- |
| Setup: team kit, public link, toolkit | Flynn |
| Test set | |
| Running the evaluation and the analysis | |
| Final report (two sections each) | Everyone |
| Slides, demo recording, and the talk | |
| Final check and submit | Flynn |

**Our deadlines:** test set done by ____, results by ____, report draft by ____, slides by Thu Nov 19 at 11:59 PM. Meeting 2: ____ (around Wed Nov 18).

**Recommended:** each person owns one chunk from start to finish and writes two report sections.

- **Decided:**
- **Date:**

### 5. Two README promises

**The question:** our README says CP4 includes a user study with character creators, and memory and retrieval tested on and off. The app has no memory or retrieval yet, and character creators are hard to find in a week. Do we build them, or edit those lines?

- Build them: memory and retrieval are new features, so that's days of work.
- Edit the lines: five minutes once decision 1 is made, and the report explains what we chose and why.

**Recommended: edit the lines.**

- **Decided:**
- **Date:**

## Decide later (at our second meeting)

- Which results and charts go on the slides
- Who presents which slides
- What the 60-second demo shows
- A last read-through of the report
