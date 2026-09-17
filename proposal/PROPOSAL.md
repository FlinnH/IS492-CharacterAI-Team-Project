# Project Proposal

## 1. Problem Significance

LLM-based characters often appear convincing in short interactions but become less coherent as conversations grow. They may contradict their backstory, forget prior interactions, drift toward generic assistant behavior, change speaking style, or reveal knowledge the character should not possess. For creators—game writers, interactive-fiction authors, educators, and developers—these failures are hard to diagnose, because a character is experienced as one entity even though its behavior depends on several underlying mechanisms.

This problem requires an AI-native approach because the desired interaction is open-ended rather than scripted. A conventional dialogue tree can guarantee consistency but cannot respond naturally to arbitrary player input. Generative models provide that flexibility, yet generation introduces instability across persona, memory, knowledge, and context.

---

## 2. Prior Work & Gaps

Prior research addresses parts of this problem independently. Li et al. (2024) show that models exhibit measurable persona drift across multi-turn conversations, with adherence to the original system instruction weakening as dialogue continues. Their split-softmax intervention improves stability, but it requires inference-level model access and does not address memory, relationships, or knowledge boundaries. Du et al. (2026) show that stronger role-play can emerge from structured character reasoning and a context-dependent reward model, yet benchmark gains do not solve persistent memory, retrieval, or debugging in deployed applications.

Three further studies show that integration itself is the hard part. Yang et al. (2025) find that a structured character specification is the most valuable component of a role-playing pipeline: removing their pre-defined aspects framework caused the largest drop in their ablation. Wang et al. (2024) show that components can work against each other—retrieval-augmented role customization scored *below* using no retrieval at all when the character source was noisy, because retrieved fragments distract the model. Tu et al. (2024) show that character knowledge must be measured as three separate properties (whether the character says anything substantive, whether it is accurate, and whether it stays inside the character's knowledge boundary), and report that automatic judges agree with human raters least on knowledge accuracy.

The human stakes are documented too: Maples et al. (2024) find users perceive AI companions as real sources of social support, while Zhang et al. (2025) identify relational harms such as algorithmic compliance.

This is not a legacy problem. Laban et al. (2026) analyze over 200,000 simulated conversations and report an average 39% drop from single-turn to multi-turn settings, decomposing it into a small loss of aptitude and a large rise in *unreliability*; Jia et al. (2026) find frontier models degrade sharply after roughly five and twelve turns. Larger context windows have not made identity stable, and because the failure is unreliability rather than capability, it has to be measured. The remaining gap is integration: these components are studied separately, so their interactions—retrieved facts overriding persona, conditioning reducing situational fit, memory crossing a knowledge boundary—remain largely untested.

---

## 3. Proposed Technical Approach

The project will build a **creator-facing Character Consistency Workbench** with two connected components: a **Character Runtime** and an **Evaluation & Debugging Layer**.

The Character Runtime begins with a structured **Character Specification** containing backstory, personality, relationships, dialogue style, behavioral constraints, and knowledge boundaries. At each turn, a **Memory Module** retrieves relevant prior interactions and a **Character RAG Module** retrieves character- and world-specific knowledge. A **Context Builder** combines these with the current scene, conversation history, and relationship state, and a **Persona and Style Conditioner** turns the result into the final generation prompt.

The resulting response is passed to the Evaluation & Debugging Layer, which checks for persona drift, memory inconsistency, factual contradiction, inappropriate knowledge, style drift, and situational mismatch. Inspired by HER, a later-stage **Context-Adaptive Judge** can evaluate candidate responses using principles selected for the specific interaction—for example persona consistency, lore grounding, emotional continuity, or conversational naturalness—rather than applying one universal score.

Creators can run the same long-form or adversarial scenario under several configurations—baseline prompting, prompting plus memory, prompting plus retrieval, and the full pipeline—so the tool not only generates characters but shows which components actually improve or damage long-term coherence.

---

## 4. Checkpoint 2 Validation Plan

Checkpoint 2 will validate the prompting and context-construction logic before the runtime is built. The same character specification and scripted conversations will be run on **ChatGPT, Claude, and Gemini** with equivalent prompt chains, covering normal dialogue, long conversations, adversarial persona challenges, knowledge-boundary questions, and situations requiring a change in emotional behavior. Outputs will be compared for persona consistency, memory use, factual grounding, style stability, and situational fit. Following Laban et al. (2026), each scenario will be run more than once, since unreliability persists even at low temperature, and probes will be placed mid-conversation rather than only at the start.

---

## 5. Risk Analysis & Mitigation

| Risk | Category | Mitigation |
| --- | --- | --- |
| Stored conversation history may contain sensitive user information. | Privacy / data security | Minimize retained data, keep character memory separate from unnecessary personal detail, and let stored memories be inspected or deleted. |
| A character may reproduce stereotypes, abuse, or harmful relational behavior. | Bias / toxicity | Keep safety constraints independent of persona; test adversarial and algorithmic-compliance scenarios. |
| Role-play instructions may push the model to follow unsafe user requests in character. | Safety | Keep non-negotiable safety rules outside the editable specification; include safety stress tests. |
| The model may invent memories, lore, or facts, and our own detector may mislabel them. | Hallucination | Ground claims in retrieved character and world data, track provenance, and hand-label a sample of turns to check the detector against human judgment before reporting scores (Tu et al., 2024). |

---

## References

Du, C., Wang, X., Chen, A., Li, W., Xu, R., Liu, J., Huang, Z., Tian, R., Sun, Z., Li, Y., Feng, L., Ding, D., Zhao, P., & Xiao, Y. (2026). HER: Human-like reasoning and reinforcement learning for LLM role-playing. In *Findings of the Association for Computational Linguistics: ACL 2026* (pp. 25725–25762). Association for Computational Linguistics. https://doi.org/10.18653/v1/2026.findings-acl.1283

Jia, Q., Shen, Y., Song, X., Zhang, K., Wang, S., Pei, D., Zhu, X., & Zhai, G. (2026). One battle after another: Probing LLMs' limits on multi-turn instruction following with a benchmark evolving framework. In *Proceedings of the 64th Annual Meeting of the Association for Computational Linguistics (Volume 1: Long Papers)* (pp. 9574–9590). Association for Computational Linguistics. https://doi.org/10.18653/v1/2026.acl-long.433

Laban, P., Hayashi, H., Zhou, Y., & Neville, J. (2026). LLMs get lost in multi-turn conversation. In *Proceedings of the International Conference on Learning Representations (ICLR 2026)*. https://arxiv.org/abs/2505.06120

Li, K., Liu, T., Bashkansky, N., Bau, D., Viégas, F., Pfister, H., & Wattenberg, M. (2024). *Measuring and controlling persona drift in language model dialogs*. arXiv. https://doi.org/10.48550/arXiv.2402.10962

Maples, B., Cerit, M., Vishwanath, A., & Pea, R. (2024). Loneliness and suicide mitigation for students using GPT3-enabled chatbots. *npj Mental Health Research, 3*(1), 4. https://doi.org/10.1038/s44184-023-00047-6

Tu, Q., Fan, S., Tian, Z., Shen, T., Shang, S., Gao, X., & Yan, R. (2024). CharacterEval: A Chinese benchmark for role-playing conversational agent evaluation. In *Proceedings of the 62nd Annual Meeting of the Association for Computational Linguistics (Volume 1: Long Papers)* (pp. 11836–11850). Association for Computational Linguistics. https://doi.org/10.18653/v1/2024.acl-long.638

Wang, Z. M., Peng, Z., Que, H., Liu, J., Zhou, W., Wu, Y., Guo, H., Gan, R., Ni, Z., Yang, J., Zhang, M., Zhang, Z., Ouyang, W., Xu, K., Huang, S. W., Fu, J., & Peng, J. (2024). RoleLLM: Benchmarking, eliciting, and enhancing role-playing abilities of large language models. In *Findings of the Association for Computational Linguistics: ACL 2024* (pp. 14743–14777). Association for Computational Linguistics. https://doi.org/10.18653/v1/2024.findings-acl.878

Yang, B., Liu, D., Xiao, C., Zhao, K., Tang, C., Li, C., Yuan, L., Yang, G., & Lin, C. (2025). Crafting customisable characters with LLMs: A persona-driven role-playing agent framework. In *Findings of the Association for Computational Linguistics: EMNLP 2025* (pp. 20216–20240). Association for Computational Linguistics. https://aclanthology.org/2025.findings-emnlp.1100

Zhang, R., Li, H., Meng, H., Zhan, J., Gan, H., & Lee, Y.-C. (2025). The dark side of AI companionship: A taxonomy of harmful algorithmic behaviors in human-AI relationships. In *Proceedings of the 2025 CHI Conference on Human Factors in Computing Systems* (Article 13, pp. 1–17). Association for Computing Machinery. https://doi.org/10.1145/3706598.3713429
