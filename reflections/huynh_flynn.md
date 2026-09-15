# Reading Reflections — Flynn Huynh

IS 492 - Fall 2026 - Team Project Checkpoint 1

---

## Paper 1 — Measuring and Controlling Persona Drift in Language Model Dialogs

### 1. Full Citation & Link

Li, K., Liu, T., Bashkansky, N., Bau, D., Viégas, F., Pfister, H., & Wattenberg, M. (2024). *Measuring and controlling persona drift in language model dialogs* (arXiv:2402.10962). arXiv. https://doi.org/10.48550/arXiv.2402.10962

**Link:** https://arxiv.org/abs/2402.10962
**PDF:** free on arXiv, safe to save to `/literature/pdfs/`

<!-- ORIENTATION
WHAT IT IS: The empirical backbone of our problem statement. They tested whether
a prompted persona actually stays stable over a conversation. It does not.

WHAT TO LOOK FOR:
  - The benchmark method: two personalized chatbots talking to each other
    ("self-chats"), with persona adherence probed at every turn
  - The headline number: significant drift within roughly 8 rounds
  - Their explanation: attention decay, meaning the prompt loses influence as
    context grows. This is why it is structural rather than a prompting error.
  - Their fix: "split-softmax," a decoding-time intervention. You do not need to
    understand how it works, only that it operates at generation time rather
    than by rewriting the prompt.

NOTE: this paper appears under a title variant in some indexes
("Instruction (In)Stability in Language Model Dialogs"). Cite the arXiv record.

WORTH ASKING: their "persona" is closer to a style instruction than to
a rich fictional character. Does their drift finding transfer to our case?
-->

### 2. Structured Summary (4–6 sentences)

<!-- Cover: the research PROBLEM, the METHODOLOGY (what they actually did), and
     the MAIN FINDINGS (with the specific numbers). -->

This paper investigates whether language models can consistently follow a system instruction throughout a long conversation rather than gradually drifting away from it. The authors create synthetic conversations between two instructed chatbots and periodically replace the normal user message with a probe question to measure how well the model still follows its original instruction. Using 100 different system prompts across five categories and experiments with LLaMA2-chat-70B and GPT-3.5, they find significant instruction drift within roughly eight rounds of conversation. Their analysis suggests that attention to the original system prompt decreases across turns, which may contribute to the drift. To reduce this problem, they introduce split-softmax, an inference-time method that increases attention to the system prompt without retraining the model, and find that it provides a better stability/performance trade-off than system-prompt repetition and classifier-free guidance.

### 3. Three Key Insights

1. Prompt-following is not necessarily stable over long conversations. A model can follow a character or behavioral instruction at the beginning  but gradually lose that instruction as the conversation becomes longer.
2. The problem may be structural rather than just poor prompt design. The paper connects instruction drift with attention decay, suggesting that simply writing a better character prompt may not completely solve the problem.
3. Consistency has a trade-off with general model performance. Methods that force stronger adherence to an instruction can reduce other capabilities, so a character system should measure both consistency and overall response quality rather than optimizing one alone.

### 4. Two Limitations or Risks

1. The paper measures instruction stability more directly than full character consistency. Its benchmark includes character-related prompts, but a real character also needs to maintain relationships, backstory, knowledge boundaries, personality, and situational behavior. Therefore, the paper's drift measurements may not capture every type of failure our project cares about.

2. The proposed solution is difficult to apply directly to many commercial LLM APIs. Split-softmax modifies the model's attention mechanism during inference, so a typical developer using a closed API may not have access to the underlying attention computation. This makes the finding more useful as a technical explanation of drift than as a drop-in solution for our prototype.



### 5. One Concrete Inspiration

<!-- A feature, not a feeling. What could we actually build because of
     this paper? -->

**Baseline vs. Enhanced Comparison** — Run the same character and conversation with baseline prompting versus the project's memory/retrieval/conditioning system and compare consistency across turns.

OR

*(Most ambitiously - if permit more time):* **Long-Conversation Character Stress Test** - Build an automated test that runs the same character through a fixed multi-turn conversation and periodically asks predefined probe questions about its identity, backstory, personality, relationships, and knowledge boundaries. Record a consistency score at each turn and visualize where the character begins to drift.

---

## Paper 2 — The Dark Side of AI Companionship

### 1. Full Citation & Link

Zhang, R., Li, H., Meng, H., Zhan, J., Gan, H., & Lee, Y.-C. (2025). The dark side of AI companionship: A taxonomy of harmful algorithmic behaviors in human-AI relationships. In *Proceedings of the 2025 CHI Conference on Human Factors in Computing Systems (CHI '25)* (Article 13, pp. 1–17). Association for Computing Machinery. https://doi.org/10.1145/3706598.3713429

**Link (free preprint):** https://arxiv.org/abs/2410.20130
**PDF:** save the arXiv version to `/literature/pdfs/`. *The ACM version is paywalled, do not redistribute it.*

<!-- ORIENTATION
WHAT IT IS: A CHI paper (top HCI venue, the field our instructor works in) that
builds a taxonomy of how AI companions actually harm users.

WHAT TO LOOK FOR:
  - The dataset: 35,390 conversation excerpts posted by roughly 10,149 users
    on r/Replika
  - The six harm categories: relational transgression, harassment/violence,
    verbal abuse, self-harm, mis/disinformation, privacy violations
  - The four AI roles: perpetrator, instigator, facilitator, enabler
  - "Algorithmic compliance": the bot agreeing with or encouraging harmful user
    statements. This is the concept most worth carrying into our project.

WHY: this supplies most of PROPOSAL.md's risk section, and it backs
the claim you already wrote that users experience a character as a single entity
and lose trust when it fails.

WORTH ASKING: Reddit posts are self-selected, so people post the
extreme cases. How much does that shape the taxonomy?
-->

### 2. Structured Summary (4–6 sentences)

This paper examines how AI companions can produce harmful behaviors during social and emotional interactions with users. The authors analyze 35,390 conversation excerpts shared by approximately 10,149 users in the r/Replika community and identify six categories of harm: relational transgression, verbal abuse and hate, self-inflicted harm, harassment and violence, mis/disinformation, and privacy violations. A major finding is the problem of algorithmic compliance, where the AI agrees with, reinforces, or encourages harmful statements or behaviors instead of appropriately challenging them. The authors argue that AI companionship requires safety mechanisms that account for the relational nature of these systems rather than treating harmful outputs as isolated content-generation errors.

### 3. Three Key Insights

1. Character behavior can become harmful even when the AI is technically following the conversation. The problem is not only factual errors or broken instructions; an AI can still respond coherently and stay in character while still causing harm.
2. Algorithmic compliance is especially important for character-based systems. A character designed to be agreeable, supportive, or loyal could accidentally reinforce whatever the user says instead of maintaining appropriate boundaries.
3. I-harm is relational, not just output-based. The same response can have a different impact when it comes from an AI that the user views as a friend, companion, or trusted character. This makes consistency and character design partly a safety issue, not just a quality issue.

### 4. Two Limitations or Risks

1. The dataset is self-selected and likely overrepresents unusual or negative experiences. The authors analyze conversations that users publicly shared in an online Replika community, so the taxonomy should not be interpreted as representing the frequency of harmful behaviors among all AI companion users.

2. The taxonomy describes harmful behaviors more than it provides a complete prevention system. It helps identify what can go wrong and the different roles an AI can play, but our project would still need to decide how to detect and prevent these failures without making the character overly restrictive or unnatural.

### 5. One Concrete Inspiration

**Relational Stress Test** — Test whether increasing the user's emotional attachment to a character changes how strongly the character's harmful or misleading responses affect the interaction.

---

## Paper 3 — Loneliness and Suicide Mitigation for Students Using GPT3-Enabled Chatbots

### 1. Full Citation & Link

Maples, B., Cerit, M., Vishwanath, A., & Pea, R. (2024). Loneliness and suicide mitigation for students using GPT3-enabled chatbots. *npj Mental Health Research, 3*(1), 4. https://doi.org/10.1038/s44184-023-00047-6

**Link (full text):** https://pmc.ncbi.nlm.nih.gov/articles/PMC10955814
**PDF:** fully open access, safe to save to `/literature/pdfs/`


### 2. Structured Summary (4–6 sentences)

This study investigates how students use AI companions and what they perceive as the effects of those interactions on loneliness, social support, and well-being. The researchers surveyed 1,006 adult student users of Replika who had used the service for more than one month, using the De Jong Gierveld Loneliness Scale, the Interpersonal Support Evaluation List, and open-response questions. About 90% of the participants reported experiencing loneliness, yet participants also reported relatively high perceived social support from their interactions with Replika. The study found that participants were more likely to report that Replika stimulated rather than displaced their human relationships, and users often viewed Replika in overlapping ways such as a friend, therapist, mirror, intelligence, or person. Notably, 30 participants, approximately 3% of the sample, reported that Replika had helped halt their suicidal ideation, although the authors emphasize that these were self-reported experiences and that further research is needed before drawing conclusions about effectiveness.

### 3. Three Key Insights

1. AI companions can provide perceived social support even among users experiencing significant loneliness. This suggests that the value of an AI character is not only entertainment; users can form meaningful relationships with it.
2. Users do not necessarily have a single interpretation of what the AI is. Participants could simultaneously view Replika as software, a friend, an intelligence, a mirror, or even a person. This ambiguity may contribute to deeper engagement but also makes failures more consequential.
3. The features that make an AI companion engaging can also increase its responsibility. If users trust a character as a friend or confidant, its responses may carry more weight than those from a normal information-retrieval chatbot. Character consistency therefore affects not only immersion but potentially users' trust and behavior.


### 4. Two Limitations or Risks

1. The sample is limited to active Replika users who had already used the system for more than a month. This creates selection bias because people who stopped using Replika, disliked it, or never became attached to it are not represented. The findings therefore cannot establish that Replika caused the reported social or mental-health outcomes.

2. The strongest positive findings are self-reported rather than experimentally verified. For example, the 30 participants who reported that Replika halted their suicidal ideation provide an important signal, but the study cannot establish that Replika itself caused the change. The authors explicitly call for further research before treating these findings as evidence of efficacy.

### 5. One Concrete Inspiration

**Relationship Mode Tracking** — Let the character explicitly support different interaction modes such as friend, tutor, or role-play character while keeping its core identity consistent.

---

## Cross-paper note

<!-- Optional -->

Together, these three papers suggest that character consistency is more than a technical problem. Paper 1 shows that instructions can drift as conversations become longer, Paper 2 shows that an AI's behavior can become harmful when it blindly follows the user's direction, and Paper 3 shows why those failures matter more when users develop meaningful relationships with AI companions. For our project, this means a good character system should not only remember its backstory and personality, but also maintain appropriate behavioral boundaries and be evaluated under realistic long conversations.