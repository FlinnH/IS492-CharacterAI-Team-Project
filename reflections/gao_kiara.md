# Reading Reflections — Kiara Gao

IS 492 - Fall 2026 - Team Project Checkpoint 1

My three papers cover the three parts of our system that I own: how a character
is defined (SimsChat), how character quality is measured (CharacterEval), and
how character knowledge and speaking style are injected (RoleLLM).

---

## Paper 1 — SimsChat: Crafting Customisable Characters with LLMs

### 1. Full Citation & Link

Yang, B., Liu, D., Xiao, C., Zhao, K., Tang, C., Li, C., Yuan, L., Yang, G., & Lin, C. (2025). Crafting customisable characters with LLMs: A persona-driven role-playing agent framework. In *Findings of the Association for Computational Linguistics: EMNLP 2025* (pp. 20216–20240). Association for Computational Linguistics.

**Link:** https://aclanthology.org/2025.findings-emnlp.1100
**Preprint:** https://arxiv.org/abs/2406.17962
**Code:** https://github.com/Bernard-Yang/SimsChat
**PDF:** open access, saved as `literature/pdfs/yang2025_simschat.pdf`

### 2. Structured Summary (4–6 sentences)

Most role-playing research copies characters that already exist, such as
historical figures or characters from novels, so the personality and knowledge
of the character are fixed and cannot be customised. This paper asks a different
question: can we build a character from scratch out of parts that a creator
chooses? The authors borrow the design of the video game *The Sims* and define
each character with four pre-defined aspects (career, aspiration, traits, skill),
which GPT-4 then expands into eight personal aspects and three social aspects;
each character also gets 20 generated scenes, and every dialogue is generated
with a fixed emotion (out of 16) and topic (out of 18). This produced the
SimsConv dataset of 68 characters, 1,360 scenes and 13,971 multi-turn dialogues
(about 10.3 turns each), which was used to fine-tune LLaMA-3-8B-Instruct into an
agent called SimsChat. SimsChat scored 6.18 on average in automatic evaluation
and 6.08 in human evaluation across five dimensions (memorisation, values,
personality, hallucination, stability), beating GPT-4 (5.91 and 5.55) even though
it is a much smaller model. The ablation study is the most useful result: removing
the pre-defined aspects framework caused the largest drop (−0.79 average), more
than removing scenes (−0.51) or emotion and topic control (−0.48).

### 3. Three Key Insights

1. **Structure matters more than model size.** An 8B model with a structured
   character definition outperformed GPT-4 with a paragraph-long character
   description. This says the way a character is *represented* is a real
   engineering lever, not just a prompt-writing detail.
2. **A character is not only a profile; it also has a per-turn state.** Scene,
   emotion, and topic are passed in at every turn, and removing any of them
   lowers the score. Identity alone is not enough to make a response fit the
   moment.
3. **Ablation is how you prove that an integrated system works.** The paper does
   not just claim that its pipeline is good; it removes one component at a time
   and reports how much each one contributes. This is exactly the argument our
   project needs to make in Checkpoint 4.

### 4. Two Limitations or Risks

1. **It never actually tests long conversations, even though it reports a
   "stability" score.** Dialogues average only 10.3 turns, the context window is
   capped at 4,096 tokens with longer examples truncated, and stability is
   measured with single interview questions rather than a long running
   conversation. Li et al. (2024) found that persona drift starts around eight
   turns, so the setting used here is too short to show whether the character
   would survive a real long session.
2. **GPT-4 generates the data and also grades the results.** The training data,
   the interview questions, and the automatic scores all come from GPT-4, which
   risks self-preference bias. The human check is small (four annotators) and the
   scores are compressed: GPT-3.5, GPT-4o and GPT-4 received 5.51, 5.53 and 5.55,
   which suggests the rating scale does not separate models well. The comparison
   is also confounded, because the baselines only received a paragraph
   description while SimsChat received a structured profile *and* fine-tuning, so
   we cannot tell how much of the gain comes from structure alone.

### 5. One Concrete Inspiration

**A three-layer character specification.** Our character spec should be split
into (1) a fixed identity layer (career, traits, values, skills, knowledge
boundary), (2) a social layer (relationships and how the character treats each
person), and (3) a per-turn state layer (scene, emotion, topic). The runtime
assembles a prompt from all three layers at every turn, and the workbench lets a
developer switch any single layer off so they can see which layer their character
actually depends on — the prompt-level version of this paper's ablation table.

---

## Paper 2 — CharacterEval: A Chinese Benchmark for Role-Playing Conversational Agent Evaluation

### 1. Full Citation & Link

Tu, Q., Fan, S., Tian, Z., Shen, T., Shang, S., Gao, X., & Yan, R. (2024). CharacterEval: A Chinese benchmark for role-playing conversational agent evaluation. In *Proceedings of the 62nd Annual Meeting of the Association for Computational Linguistics (Volume 1: Long Papers)* (pp. 11836–11850). Association for Computational Linguistics. https://doi.org/10.18653/v1/2024.acl-long.638

**Link:** https://aclanthology.org/2024.acl-long.638
**Preprint:** https://arxiv.org/abs/2401.01275
**Code:** https://github.com/morecry/CharacterEval
**PDF:** open access, saved as `literature/pdfs/tu2024_charactereval.pdf`

### 2. Structured Summary (4–6 sentences)

Role-playing agents were being built faster than they could be compared, because
existing datasets were either fully generated by LLMs or too noisy, which made
evaluation results unreliable. To fix this, the authors built a Chinese
role-playing dataset of 1,785 multi-turn dialogues and 11,376 examples covering
77 leading characters from novels and scripts: GPT-4 split the source text into
complete plots and extracted the dialogue, behaviour and scene, then human
annotators filtered out low-quality dialogues, and character profiles were
crawled from Baidu Baike. They then defined an evaluation system of thirteen
metrics across four dimensions — conversational ability, character consistency,
role-playing attractiveness, and MBTI personality back-testing — and trained
CharacterRM, a reward model built on Baichuan2-13B using scores from twelve
annotators, so these subjective metrics can be scored automatically. CharacterRM
correlates with human judgment better than GPT-4 does (0.631 overall versus 0.375
for GPT-4 with three examples). In the benchmark results, Chinese role-playing
models such as BC-NPC-Turbo and MiniMax beat GPT-4 on Chinese role-play, and
GPT-3.5 performed worst of all because it kept refusing to stay in character and
replying that it is only an AI assistant.

### 3. Three Key Insights

1. **Character knowledge needs three separate metrics, not one.** The paper
   splits it into knowledge exposure (does the character say anything
   substantive?), knowledge accuracy (is it right?), and knowledge hallucination
   (does it stay inside what the character could know?). A model that refuses to
   commit to anything can score well on accuracy while still failing as a
   character, and a single "accuracy" number would hide that.
2. **Safety alignment can break character.** GPT-3.5 scored worst because RLHF
   made it over-cautious, so it answered "I am just an AI assistant and cannot
   perform role-playing." Being helpful and harmless in the assistant sense
   actively works against staying in character, which means our system has to
   treat assistant-voice fallback as one of the failure types we detect.
3. **A small trained judge can beat a big general one.** A 13B reward model
   trained on real human scores tracked human judgment better than GPT-4 did,
   and it is far cheaper to run. Evaluation quality depends on being calibrated
   to humans, not on judge model size.

### 4. Two Limitations or Risks

1. **The automatic judge is weakest exactly where we need it most.** Overall
   correlation with humans is 0.631, which is only moderate, and for
   Knowledge-Accuracy it drops to 0.336 — so the metric that matters most for
   factual grounding is close to unreliable. If we copy this scoring approach,
   we have to hand-label a small set of turns and report how well our judge
   agrees with us instead of trusting the judge's numbers.
2. **The benchmark is Chinese-only, and one of its four dimensions rests on a
   contested instrument.** All 77 characters come from Chinese novels and
   scripts, so results may not transfer to English or Western characters, and
   the personality dimension uses MBTI, whose validity is widely criticised in
   psychometrics, with character MBTI labels taken from a fan database rather
   than from the source works.

### 5. One Concrete Inspiration

**A failure taxonomy with a calibrated judge.** We should collapse these thirteen
metrics into the five failure types in our README (memory loss, factual
contradiction, style drift, situational mismatch, out-of-boundary knowledge) and
have the evaluation layer tag each turn with the failure types it sees, keeping
exposure and hallucination as two separate checks so that a character which
refuses to say anything is not scored as a success. Before we report any number,
we hand-label a sample of turns ourselves and publish the agreement between our
labels and the judge's, the way this paper reports correlation with humans.

---

## Paper 3 — RoleLLM: Benchmarking, Eliciting, and Enhancing Role-Playing Abilities of Large Language Models

### 1. Full Citation & Link

Wang, Z. M., Peng, Z., Que, H., Liu, J., Zhou, W., Wu, Y., Guo, H., Gan, R., Ni, Z., Yang, J., Zhang, M., Zhang, Z., Ouyang, W., Xu, K., Huang, S. W., Fu, J., & Peng, J. (2024). RoleLLM: Benchmarking, eliciting, and enhancing role-playing abilities of large language models. In *Findings of the Association for Computational Linguistics: ACL 2024* (pp. 14743–14777). Association for Computational Linguistics. https://doi.org/10.18653/v1/2024.findings-acl.878

**Link:** https://aclanthology.org/2024.findings-acl.878
**Preprint:** https://arxiv.org/abs/2310.00746
**Code:** https://github.com/InteractiveNLP-Team/RoleLLM-public
**PDF:** open access, saved as `literature/pdfs/wang2024_rolellm.pdf`

### 2. Structured Summary (4–6 sentences)

Open-source models are trained for general use and are not optimised for
role-play, while strong closed models like GPT-4 cannot be fine-tuned, cost a lot
per call, and force every piece of character information into the prompt. The
authors propose RoleLLM, a four-stage framework: build profiles for 100
fine-grained characters selected from 916 English and 24 Chinese scripts; use
RoleGPT to imitate speaking style through few-shot *dialogue* engineering;
use Context-Instruct to pull role-specific knowledge out of long profiles as
question-confidence-answer triples; and fine-tune LLaMA and ChatGLM2 on the
resulting 168,093-sample RoleBench dataset to get RoleLLaMA and RoleGLM. They
separate two design targets that are usually mixed together — speaking style
(lexical consistency plus dialogic fidelity) and role knowledge (script-based
memories plus script-agnostic expertise) — and evaluate with Rouge-L, GPT-4
judging, and human judging. The ablations are the most informative part:
formatting few-shot examples as real dialogue turns beat putting them in one
prompt (63.3% versus 29.8% win rate), a system instruction beat retrieval
augmentation for role customisation (38.1 versus 36.7), and adding role knowledge
through training clearly beat retrieving it (38.1 versus 19.1). Larger models
also role-played better, with scores rising steadily from 7B to 13B to 33B.

### 3. Three Key Insights

1. **Retrieval can make a character worse.** When the character's source material
   is sparse and noisy, retrieval-augmented role customisation scored *below*
   using no retrieval at all (19.1 versus 21.4), because retrieved fragments
   distract smaller models. This is direct evidence for our team's claim that
   these components can compete with each other rather than simply add up.
2. **How you place information in the prompt can matter more than what you
   place.** With the same character information, presenting examples as a real
   multi-turn dialogue history nearly doubled the win rate compared with
   presenting them inside a single prompt. Prompt structure is part of the
   system design, not cosmetic.
3. **Character knowledge has two different sources and should be handled
   separately.** Script-based knowledge is what the character personally
   experienced, while script-agnostic knowledge is the general expertise their
   role implies. They fail in different ways, so a character spec should keep
   them apart instead of pouring everything into one "background" field.

### 4. Two Limitations or Risks

1. **The whole framework is single-turn, which is the opposite of our problem.**
   The authors state in their limitations that RoleLLM is designed for
   single-turn question answering, so it cannot say anything about whether a
   character holds together over a long conversation — the exact failure our
   project targets. Its retrieval findings should also be read with care for us:
   they come from noisy script profiles and small fine-tuned models, and a clean,
   purpose-written character document might behave differently.
2. **The metrics are weak for what they claim to measure, and the data is
   model-generated.** Rouge-L only counts n-gram overlap, which is a poor proxy
   for speaking style, and the remaining judgments come from GPT-4 plus three
   graduate students. On top of that, GPT-4 and GPT-3.5 generated the profiles,
   the instructions and the responses in RoleBench, and the quality review found
   only 77% of samples correctly embodied the role's style, personality and
   knowledge.

### 5. One Concrete Inspiration

**A retrieval inspector with an on/off switch.** Because retrieval can hurt as
well as help, our workbench should show, for every turn, which passages were
retrieved and whether the response actually used them, and let the developer
re-run the same scenario with retrieval disabled and with the same facts moved
into the character spec instead. That turns this paper's finding into a feature:
the tool answers "is retrieval helping this character, or distracting it?" with
a side-by-side comparison rather than a guess.

---

## Cross-paper note

Read together, these three papers give our project its argument. SimsChat shows
that a structured character definition is the single most valuable component,
which justifies making the specification, not the prompt, the thing a developer
edits. RoleLLM shows that components interact and can work against each other,
since retrieval reduced performance when the source was noisy, which is why the
components have to be evaluated together rather than one at a time. CharacterEval
shows what to measure and how cautious to be about it, especially that automatic
judges agree with humans least on knowledge accuracy. All three also share one
gap: none of them really tests long conversations. RoleLLM is single-turn,
CharacterEval averages 9.28 turns, and SimsChat averages 10.3, while Li et al.
(2024) report that persona drift begins at around eight turns. Newer work has
started moving in this direction — CoSER (ICML 2025) evaluates characters acting
inside book scenes, and multi-turn benchmarks such as RMTBench are appearing —
but a developer still has no tool that runs their own character through a long
conversation, says which failure occurred, and shows whether a configuration
change fixed it. That is the space our MVP is built for.
