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
