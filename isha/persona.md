# Literature Review: User Personas and Harmful Compliance in AI Agents

## 1. Research Question

**How do user personas and personal context influence an AI agent's willingness to comply with harmful requests?**

The goal of this literature review is to determine whether this question has already been studied, identify gaps in existing work, and assess whether Pilot A offers a sufficiently novel research direction.

We are particularly interested in the relationship between user identity, background, perceived stakes, and harmful behavior in LLM agents.

## 2. Related Work

| Paper | What It Found | What It Doesn't Cover / Potential Gap | Similarity (1–5) |
|---|---|---|---:|
| [Who's Asking? User Personas and the Mechanics of Refusal in Large Language Models (NeurIPS 2024)](https://proceedings.neurips.cc/paper_files/paper/2024/hash/e40d5118ee8f837729fa877add71c38f-Abstract-Conference.html) | Studies how user personas affect refusal behavior on harmful queries and investigates mechanisms behind persona-dependent responses. | Focuses on persona prompting and refusal behavior rather than multi-step tool execution by agents. | 5/5 |
| [Differential Harm Propensity in Personalized LLM Agents: The Curious Case of Mental Health Disclosure (Yildirim, 2026)](https://arxiv.org/abs/2603.16734) | Examines whether user biography and mental-health disclosure affect harmful and benign task completion in agentic settings. Personalization can increase refusals, but effects are not consistently robust. | Directly overlaps with personalization and harmful agent behavior. A new study must isolate a different factor or test a meaningfully different setting. | 5/5 |
| [When Personalization Legitimizes Risks: Uncovering Safety Vulnerabilities in Personalized Dialogue Agents (ACL 2026)](https://aclanthology.org/2026.acl-long.1260/) | Studies how personalized memories and persona-grounded harmful requests affect safety. Reports that personalization can make harmful requests appear more legitimate. | Closely overlaps with persona-conditioned harmful compliance. The distinction would need to come from the specific variables, tasks, or agent setting studied. | 5/5 |
| [PENGUIN / Personalized Safety](https://arxiv.org/abs/2505.18882) | Investigates personalization and user-specific context in safety-sensitive scenarios. | Potentially relevant to user attributes and context-sensitive safety, but its exact overlap with harmful multi-step tool use needs further verification. | 4/5 |
| [PropensityBench: Evaluating Latent Safety Risks in Large Language Models via an Agentic Approach](https://arxiv.org/abs/2511.20703) | Evaluates whether agents choose risky tools under different operational pressures and dangerous capability settings. | Focuses primarily on risky tool-use propensity rather than isolating user persona as the independent variable. | 2/5 |
| [AgentHarm (ICLR 2025)](https://proceedings.iclr.cc/paper_files/paper/2025/hash/c493d23af93118975cdbc32cbe7323f5-Abstract-Conference.html) | Provides a benchmark for evaluating harmful multi-step agent tasks, including tool use and robustness to jailbreaks. | Provides an evaluation framework rather than primarily studying how user personas change harmful compliance. | 3/5 |

## 3. Preliminary Findings

The literature suggests that the broad question of whether user personas or personal context influence harmful compliance has already received substantial attention.

Three especially relevant directions have been studied:

1. **Persona-conditioned refusal:** User personas can influence whether a model refuses or complies with harmful requests.
2. **Personalization in agentic tasks:** User biographies, mental-health disclosures, and personal memories can change harmful and benign task completion.
3. **Risky tool use:** Benchmarks such as PropensityBench and AgentHarm provide ways to evaluate harmful actions and tool-use decisions in agentic settings.

Consequently, a study that simply assigns different personas to an LLM and measures harmful compliance would likely overlap with existing work.

The more promising opportunity is to identify a specific experimental variable or setting that prior work has not adequately isolated.

## 4. Candidate Research Gaps

These are hypotheses to investigate, not yet verified gaps.

### A. Separating User Persona from Perceived Stakes

Does an agent respond differently to a harmful request because of the user's identity or background, versus because of the urgency, justification, or consequences described in the request?

A controlled experiment could vary persona and perceived stakes independently while keeping the underlying task constant.

### B. Persona Effects on Multi-Step Tool Execution

Do persona-dependent behavior changes observed in dialogue models transfer to agents that can execute tools and perform multi-step actions?

This could distinguish verbal compliance from actual tool-use behavior, provided existing agentic personalization studies do not already cover the proposed conditions.

### C. Persona Effects Across Benign and Harmful Tasks

Does a persona that improves helpfulness on benign tasks also increase compliance with harmful requests, or does the effect depend on task risk?

This direction would require a carefully defined hypothesis because prior work already evaluates both harmful and benign tasks.

### D. Robustness Across Models and Persona Types

Are persona effects consistent across different LLMs, persona categories, and task types, or are the observed effects model-specific?

A cross-model study could be useful if it tests a meaningful generalization question that existing work leaves unresolved.

## 5. Preliminary Research-Gap Assessment

**Status: Partially explored; substantial overlap with existing work.**

The broad persona-and-harmful-compliance question is not new. Existing work studies persona-dependent refusals, personalized safety, personal memories, and harmful agent behavior.

A viable project should therefore:

- Identify the closest prior experiments and compare their exact independent variables, benchmarks, and evaluation metrics.
- Choose a narrower research question that is not already answered by those experiments.
- Use AgentHarm or another suitable benchmark only if it supports the chosen hypothesis.
- Distinguish actual harmful tool execution from a model merely stating that it would comply.
- Evaluate both harmful and benign tasks to identify potential safety–helpfulness trade-offs.

No definitive novelty claim should be made until the full experimental setups and limitations of the closest papers have been examined.

## 7. Working Conclusion

Prior work already establishes that personas and personal context can influence LLM safety behavior. The strongest next step is not to test persona effects in general, but to identify a specific, controlled question that existing studies have not adequately addressed.

The final research question should be selected only after the closest papers' methods, limitations, and evaluation settings have been compared directly.

---

*Note: This is a preliminary literature review. Paper summaries, publication details, and similarity judgments should be checked against the full papers before being used to support a formal novelty claim.*
