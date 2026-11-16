# What CP4 asks for

CP4 is the last checkpoint and the biggest: 13 points. We evaluate our app with real data and write a 3,500 to 4,500 word final report. We also put a working version online and give a talk of 8 minutes or less. The course's motto for it is "data and evidence over sales pitches": an honest result with good evidence beats a glowing claim.

This page is only what the course asks. For what to do about it, go back to [the start page](TEAM_START_HERE.md) or open [the how-to](HOW_TO_FINISH_CP4.md).

## When it's due

- CP4 is due Thu Dec 3, 2026. The date is confirmed, and it comes after a one-week Thanksgiving break (the week of Nov 23).
- The course's general rule says slides are due at 11:59 PM the day before the presentation.
- Check Canvas for the exact time, and for the presentation day.

## How it's graded

| Part | Points | What earns them |
| --- | --- | --- |
| Evaluation | 4.5 | A sound study (Track A) or benchmark (Track B), with numbers, real qualitative insight, and an ablation analysis |
| Final report | 4.5 | [docs/FINAL_REPORT.md](../FINAL_REPORT.md): 3,500 to 4,500 words, clearly structured, academically rigorous, tied to our CP1 reading list, with APA references and appendices |
| Package and deployment | 2.0 | Clean open-source code, a working public link, test scripts anyone can rerun, and complete documentation |
| Talk | 2.0 | A professional talk of 8 minutes or less, with clear findings, demo highlights, and honest engineering lessons |

## The evaluation: pick one track

Track A, a tool or user study, uses real target users:
- a realistic set of tasks
- numbers: task success, time on task, SUS or UMUX-Lite usability scores, and satisfaction ratings
- a thematic analysis of what people said about trust, usefulness, and friction
- materials: the protocol, the consent text, and the task prompts

Track B, algorithmic research, runs benchmark experiments on the models and the pipeline:
- a test set, and baselines to compare against
- numbers: accuracy, F1, win rates, token cost, and response latency
- ablations: prompt variants, model choices, and other one-change comparisons
- an error analysis: a deep sort of the ways the system fails

## What must be in the repo

- [docs/FINAL_REPORT.md](../FINAL_REPORT.md), the report
- [docs/study_materials/](../study_materials/README.md), the study protocols and surveys, or the benchmark test set
- [docs/figures/](../figures/README.md), the charts, latency plots, and architecture diagrams
- [app/](../../app/), clean code that anyone can deploy
- a live public link to the working app

The package also needs charts of latency, ablations, and cost, and scripts that rerun the numbers.

## The report's sections

- Title, authors, and an abstract of about 150 words
- 1 Introduction: why the problem matters, and our main contributions
- 2 Related work: grounded in our CP1 reading list
- 3 Methodology: the system's architecture, the AI design, the prompts, and the pipeline
- 4 Evaluation design: the protocol, the participants or test set, the baselines, and the metrics
- 5 Results and discussion: the statistics, the charts, and the qualitative themes
- 6 Limitations and ethics: safety, bias, hallucinations, and privacy
- 7 Conclusion: the key takeaways and future work
- References and appendices: complete APA references, the prompts, and the questionnaires

## The talk: 8 slides, 8 minutes or less

| Slide | Topic | Time | What to cover |
| --- | --- | --- | --- |
| 1 | Title and deployed link | about 30 seconds | Title, team names, the GitHub repo link, the live URL |
| 2 | System and 60-second demo | about 1.5 minutes | The problem in a sentence, then a highlight reel of the app working |
| 3 | Evaluation setup | about 1 minute | Track A: participants, tasks, protocol. Track B: test set, baselines, ablation variables, metrics |
| 4 | Quantitative results | 1.5 to 2 minutes | The core findings: charts, success rates, usability scores, ablation tables, or cost and latency curves |
| 5 | Qualitative insights | 1 to 1.5 minutes | Track A: themes from what people said, trust, workarounds, friction. Track B (our adaptation): what the system gets wrong and why |
| 6 | Limitations and ethics | about 1 minute | Honest limits, edge-case failures, hallucination risk, privacy, bias |
| 7 | Engineering lessons | about 1 minute | What worked and what failed, prompt design, handling run-to-run variation, human-AI interaction insights |
| 8 | Future work and conclusion | about 30 seconds | What's next, and the one-line conclusion |

The talk should focus on what the data shows and on honest lessons, not hype.

## Also due: each person's contribution reflection

As in CP3, each of us writes an individual contribution reflection, and the course runs the same AI contribution audit on the repo. Work that git can't show goes in [docs/cp4/WORK_LOG.md](WORK_LOG.md).
