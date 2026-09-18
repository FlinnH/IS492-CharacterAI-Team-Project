Paper 1 — HER: Human-like Reasoning and Reinforcement Learning for LLM Role-playing

1. Full Citation & Link

Du, C., Wang, X., Chen, A., Li, W., Xu, R., Liu, J., Huang, Z., Tian, R., Sun, Z., Li, Y., Feng, L., Ding, D., Zhao, P., & Xiao, Y. (2026). HER: Human-like reasoning and reinforcement learning for LLM role-playing. In M. Liakata, V. P. Moreira, J. Zhang, & D. Jurgens (Eds.), Findings of the Association for Computational Linguistics: ACL 2026 (pp. 25725–25762). Association for Computational Linguistics. https://doi.org/10.18653/v1/2026.findings-acl.1283

2. Structured Summary (4–6 sentences)

HER addresses a key limitation of current role-playing LLMs: they can imitate a character's surface-level tone and knowledge, but often lack consistent reasoning about the character's internal motivations and the surrounding narrative context. The authors introduce a dual-layer thinking framework that separates the LLM's hidden third-person planning ("system thinking") from the character's first-person internal reasoning ("role thinking"), and construct reasoning-augmented role-play data for supervised fine-tuning. They then build a role-play Generative Reward Model using human-aligned, context-dependent evaluation principles and pairwise preference judgments, and use it to further optimize a Qwen3-32B-based model with reinforcement learning from human feedback. HER-RL improves the Qwen3-32B baseline by 30.26 points on CoSER and 14.97 points on the MiniMax Role-Play Bench, while also improving over the HER-SFT model, showing that preference-based RL provides additional gains beyond supervised fine-tuning. Overall, the paper suggests that strong role-playing behavior depends not only on teaching a model how a character should speak, but also on giving it structured reasoning and a reward signal that evaluates whether a response makes sense for that specific character and situation.

3. Three Key Insights

Separate model planning from character thinking. The dual-layer design is useful because the LLM can reason strategically about persona, scene, and narrative constraints without treating that meta-level reasoning as if it were the character's own thoughts.

Role-play rewards should be context-dependent rather than based on one fixed rubric. HER's reward model selects principles relevant to the current character and dialogue situation and compares candidate responses pairwise, which is better suited to subjective role-playing quality than assigning an absolute score to each response.

RL complements, rather than replaces, strong supervised role-play training. HER-SFT already produces a large improvement over the base model, while HER-RL adds further gains; this suggests that the quality of the reasoning data and reward model is at least as important as the choice to apply RL itself.

4. Two Limitations or Risks

The reward signal still depends heavily on model-generated judgments. The preference data and Generative Reward Model rely on strong teacher/judge LLMs, and the reported teacher-to-expert agreement is 80.5%, meaning subjective disagreements and judge biases can still propagate into the final policy.

Benchmark improvements do not guarantee reliable long-term behavior in a deployed character system. CoSER and MiniMax provide useful role-playing evaluations, but a real application may involve persistent memory, changing relationships, world-state updates, player-specific history, and much longer interactions; failures in these settings may not be fully captured by the reported benchmarks.

5. One Concrete Inspiration

Context-Adaptive Pairwise Character Judge: For our character AI system, generate two candidate NPC responses and evaluate them using the current persona, retrieved character/world knowledge, dialogue history, relationship state, and scene context. Instead of applying the same fixed checklist to every turn, first select a small set of context-relevant principles—such as persona consistency, lore grounding, emotional continuity, or conversational naturalness—and then make a pairwise preference judgment between the candidates. These preferences could later be used for preference-based optimization or as feedback for iterative prompt/model improvement.


## Paper 2 — LongMemEval: Benchmarking Chat Assistants on Long-Term Interactive Memory

### 1. Full Citation & Link

Wu, D., Wang, H., Yu, W., Zhang, Y., Chang, K.-W., & Yu, D. (2025). *LongMemEval: Benchmarking chat assistants on long-term interactive memory*. International Conference on Learning Representations (ICLR 2025). https://arxiv.org/abs/2410.10813

**Official ICLR page:** https://proceedings.iclr.cc/paper_files/paper/2025/hash/d813d324dbf0598bbdc9c8e79740ed01-Abstract-Conference.html

**Code:** https://github.com/xiaowu0162/LongMemEval

---

### 2. Structured Summary (4–6 sentences)

LongMemEval investigates whether LLM-based conversational systems can reliably remember and use information across long-term, multi-session interactions rather than only within a short recent context. The authors construct a benchmark of 500 carefully curated questions that evaluates five core memory abilities: information extraction, multi-session reasoning, temporal reasoning, knowledge updates, and abstention when the required information is unavailable. Their experiments show that commercial chat assistants and long-context LLMs experience roughly a 30% accuracy drop when they must recover information from sustained conversation histories, demonstrating that simply increasing the context window does not guarantee reliable long-term memory. The paper then decomposes a memory system into indexing, retrieval, and reading stages and studies design choices such as session-level decomposition, fact-augmented retrieval keys, and time-aware query expansion. These memory optimizations substantially improve retrieval and downstream question answering, suggesting that reliable conversational memory requires explicit memory architecture rather than simply placing the entire dialogue history into the model context. Overall, the paper provides both an evaluation framework and practical design guidance for building more reliable persistent conversational systems.

### 3. Three Key Insights

1. **A large context window is not the same as reliable memory.** Even when models technically have enough context capacity to contain a long conversation, they can still fail to identify and correctly use information from earlier interactions. This is especially relevant to long-running character conversations because storing every previous message in the prompt does not guarantee that the character will actually remember the right event at the right time.

2. **Long-term memory is not a single ability.** LongMemEval separates memory into information extraction, multi-session reasoning, temporal reasoning, knowledge updates, and abstention. This is useful for our project because a character can succeed at simple recall while still failing more complex consistency requirements—for example, remembering an old fact but failing to recognize that it was later updated.

3. **Memory architecture matters at multiple stages.** The paper shows that performance depends not only on the underlying language model but also on how memories are indexed, retrieved, and presented to the model. Techniques such as session decomposition, fact-augmented keys, and time-aware query expansion improve retrieval effectiveness, suggesting that memory should be treated as an explicit system component rather than as additional prompt text.

### 4. Two Limitations or Risks

1. **LongMemEval evaluates conversational memory rather than full character consistency.** Its tasks focus primarily on whether an assistant can retrieve and reason over previously established information. A believable fictional character additionally needs to preserve personality, speaking style, relationships, motivations, knowledge boundaries, and context-dependent behavior. Therefore, strong LongMemEval performance would not necessarily mean that a character remains believable across a long role-playing interaction.

2. **The benchmark reduces memory behavior to question-answer correctness.** This makes evaluation controlled and reproducible, but real character conversations are more open-ended. A character might retrieve the correct memory yet express it in a way that violates its personality or current emotional state. Conversely, it may intentionally avoid stating a remembered fact because doing so is more appropriate for the narrative situation. Our project therefore needs to evaluate memory together with persona and contextual appropriateness rather than using retrieval accuracy alone.

### 5. One Concrete Inspiration

**Character Memory Stress Test** — Adapt LongMemEval's five memory abilities into controlled role-playing scenarios for our Character Consistency Workbench.

For example:

* **Information Extraction:** Can the character remember a fact the player told it many turns ago?
* **Multi-Session Reasoning:** Can it combine information learned during different interactions?
* **Temporal Reasoning:** Can it distinguish what happened before versus after a particular story event?
* **Knowledge Update:** If a relationship, location, or world fact changes, does the character use the newest valid information instead of an outdated memory?
* **Abstention / Knowledge Boundary:** Can the character avoid claiming to remember or know something that was never established?

The same scenario could then be run using **baseline prompting**, **prompting + long-term memory**, and the **full integrated system**. This would let us measure not only whether memory improves recall, but whether better retrieval actually improves overall character consistency without introducing inappropriate knowledge or behavior.
