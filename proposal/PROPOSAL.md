# Project Proposal

## 1. Problem Significance

LLM-based characters often appear convincing in short interactions but become less coherent as conversations grow. They may contradict their backstory, forget prior interactions, drift toward generic assistant behavior, change speaking style, or reveal knowledge the character should not possess. For character creators—including game writers, interactive-fiction authors, educators, and developers—these failures are difficult to diagnose because a character is experienced as one coherent entity even though its behavior depends on multiple underlying mechanisms.

This problem requires an AI-native approach because the desired interaction is open-ended rather than scripted. A conventional dialogue tree can guarantee consistency but cannot respond naturally to arbitrary player input. Generative models provide that flexibility, yet generation introduces instability across persona, memory, knowledge, and context. The core challenge is therefore not simply writing a better system prompt, but building a character system that can preserve identity while adapting naturally to changing conversations and situations.

---

## 2. Prior Work & Gaps

Prior research addresses several parts of this problem independently. Li et al. (2024) demonstrate that language models exhibit measurable instruction and persona drift across multi-turn conversations, with adherence to the original system instruction weakening as dialogue continues. Their split-softmax intervention improves stability, but it requires inference-level model access and does not address richer character properties such as memory, relationships, or knowledge boundaries.

Du et al. (2026) show that stronger role-playing can emerge from structured character reasoning and preference-based optimization. Their HER framework separates system-level planning from first-person role reasoning and uses a context-dependent reward model to evaluate character responses. However, benchmark improvements do not directly solve persistent memory, retrieval, or long-term debugging in deployed applications.

The human consequences also extend beyond immersion. Maples et al. (2024) show that users can perceive AI companions as meaningful sources of social support, while Zhang et al. (2025) identify relational harms such as algorithmic compliance, misinformation, and inappropriate reinforcement.

The remaining gap is integration. Memory, retrieval, persona conditioning, contextual reasoning, and alignment are typically studied separately. Their interactions may create new failures: retrieved information may conflict with persona, stronger persona conditioning may reduce situational appropriateness, and remembered information may exceed a character's intended knowledge boundary.

---

## 3. Proposed Technical Approach

The project will build a **creator-facing Character Consistency Workbench** with two connected components: a **Character Runtime** and an **Evaluation & Debugging Layer**.

The Character Runtime begins with a structured **Character Specification** containing backstory, personality, relationships, dialogue style, behavioral constraints, and knowledge boundaries. For each user turn, a **Memory Module** retrieves relevant information from previous interactions, while a **Character RAG Module** retrieves character- and world-specific knowledge. A **Context Builder** combines these results with current scene information, conversation history, and relationship state. A **Persona and Style Conditioner** then transforms this combined context into the final generation prompt.

The resulting response is passed to the Evaluation & Debugging Layer, which checks for persona drift, memory inconsistency, factual contradiction, inappropriate knowledge, style drift, and situational mismatch. Inspired by HER, a later-stage **Context-Adaptive Judge** can evaluate candidate responses using principles selected for the specific interaction—for example persona consistency, lore grounding, emotional continuity, or conversational naturalness—rather than applying one universal score.

Creators can run a fixed long-form or adversarial scenario under multiple configurations, such as baseline prompting, prompting plus memory, prompting plus retrieval, and the full integrated pipeline. This makes the system useful not only for generating characters but for identifying which components actually improve or damage long-term character coherence.

---

## 4. Checkpoint 2 Validation Plan

Checkpoint 2 will validate the core prompting and context-construction logic before building the full runtime. The same structured character specification and scripted test conversations will be evaluated using **ChatGPT, Claude, and Gemini**. Tests will include normal dialogue, long-context conversations, adversarial persona challenges, knowledge-boundary questions, and situations requiring changes in emotional or conversational behavior. Each tool will receive equivalent prompt chains, and outputs will be compared for persona consistency, memory use, factual grounding, style stability, and situational appropriateness. Failure cases will inform the final architecture and prompt design for the MVP.

---

## 5. Risk Analysis & Mitigation

| Risk                                                                                               | Category                | Mitigation                                                                                                                                     |
| -------------------------------------------------------------------------------------------------- | ----------------------- | ---------------------------------------------------------------------------------------------------------------------------------------------- |
| Stored conversation history may contain sensitive user information.                                | Privacy / data security | Minimize retained data, separate character memory from unnecessary personal information, and allow stored memories to be inspected or deleted. |
| A character may reproduce stereotypes, abusive language, or harmful relational behavior.           | Bias / toxicity         | Add safety constraints independent of persona and explicitly test adversarial and algorithmic-compliance scenarios.                            |
| Strong role-play instructions may encourage the model to follow unsafe user requests in character. | Safety                  | Maintain non-negotiable safety rules outside the editable character specification and include safety stress tests.                             |
| The model may invent memories, lore, relationships, or facts.                                      | Hallucination           | Ground factual claims in retrieved character/world data, track provenance, and flag unsupported responses during evaluation.                   |

---

## References

Du, C., Wang, X., Chen, A., Li, W., Xu, R., Liu, J., Huang, Z., Tian, R., Sun, Z., Li, Y., Feng, L., Ding, D., Zhao, P., & Xiao, Y. (2026). HER: Human-like reasoning and reinforcement learning for LLM role-playing. In M. Liakata, V. P. Moreira, J. Zhang, & D. Jurgens (Eds.), *Findings of the Association for Computational Linguistics: ACL 2026* (pp. 25725–25762). Association for Computational Linguistics. https://doi.org/10.18653/v1/2026.findings-acl.1283

Li, K., Liu, T., Bashkansky, N., Bau, D., Viégas, F., Pfister, H., & Wattenberg, M. (2024). *Measuring and controlling persona drift in language model dialogs*. arXiv. https://doi.org/10.48550/arXiv.2402.10962

Maples, B., Cerit, M., Vishwanath, A., & Pea, R. (2024). Loneliness and suicide mitigation for students using GPT3-enabled chatbots. *npj Mental Health Research, 3*(1), 4. https://doi.org/10.1038/s44184-023-00047-6

Zhang, R., Li, H., Meng, H., Zhan, J., Gan, H., & Lee, Y.-C. (2025). The dark side of AI companionship: A taxonomy of harmful algorithmic behaviors in human-AI relationships. In *Proceedings of the 2025 CHI Conference on Human Factors in Computing Systems* (Article 13, pp. 1–17). Association for Computing Machinery. https://doi.org/10.1145/3706598.3713429
