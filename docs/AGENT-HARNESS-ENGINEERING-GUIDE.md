# Agent and Harness Engineering Guide

Status: NORMATIVE_FOR_AGENT_AND_HARNESS_AUTHORING
Applies to: repository `oigorbrito/metaO`
Issue: #655

## 1. Purpose

This guide defines how metaO authors and evolves repository-level agent instructions, coding-agent harness guidance, and related operational Markdown.

It exists to improve agent effectiveness without creating a second source of architectural, governance, verification, benchmark, or Acceptance authority.

The governing separation is:

```text
AGENT_INSTRUCTIONS -> execution guidance and routing
CANONICAL_DOCS      -> project authority and durable contracts
EMPIRICAL_PROTOCOL  -> claim/evidence discipline
BENCHMARKS          -> selection/design evidence
TESTS               -> repository-specific executed evidence
ACCEPTANCE          -> final metaO authority
```

These implications are forbidden:

```text
MORE_INSTRUCTIONS == BETTER_AGENT
TASK_SUCCESS == INSTRUCTION_COMPLIANCE
PAPER_RESULT == METAO_RESULT
BENCHMARK_WIN == METAO_ACCEPTED
HARNESS_SCORE == HARD_GATE_OVERRIDE
```

## 2. Evidence basis and claim boundary

This guide is informed by external empirical work on long-context use, agentic instruction following, repository exploration, and harness optimization.

Relevant findings include:

- long contexts can exhibit position-sensitive retrieval degradation, so critical rules should not depend on being rediscovered inside large undifferentiated documents;
- agentic instruction following degrades as instructions become long and structurally complex, especially for tool and conditional constraints;
- task completion and scaffold/instruction compliance are distinct evaluation dimensions;
- repository exploration/localization quality is a measurable precursor to downstream repair quality;
- well-grounded domain guidance can improve efficiency, while poorly aligned guidance can anchor an agent toward the wrong repair;
- harness behavior is an empirical optimization target: changing retrieval, context construction, memory, stopping, tools, or control flow can materially change performance even with a fixed base model.

External results are methodological evidence only. They do not constitute executed metaO evidence and do not change project hard gates, frozen contracts, or Acceptance semantics.

## 3. Documentation architecture

Use progressive disclosure.

### Tier 0 — `AGENTS.md`

`AGENTS.md` is the short repository entrypoint for agents.

It SHOULD contain only:

- non-negotiable execution rules that must be seen early;
- pointers to canonical authority;
- issue/branch/PR workflow constraints that affect the current action;
- explicit activation conditions for exceptional procedures;
- high-value fail-closed distinctions.

It SHOULD NOT contain:

- full architecture explanations;
- copied requirement catalogs;
- duplicated benchmark methodology;
- long historical context;
- implementation-specific facts already owned by canonical docs;
- large checklists that are only conditionally applicable.

Target behavior: an agent can read `AGENTS.md`, know where authority lives, and load deeper context only when the task requires it.

### Tier 1 — canonical project documents

Current project truth remains owned by the documents listed in `docs/DOCUMENT-AUTHORITY-MAP.md`.

Agent guidance MUST reference those documents instead of restating their full content.

When two documents disagree, the authority map and the more specific canonical contract govern; `AGENTS.md` does not override them.

### Tier 2 — task/domain guides

Task-specific operating guides MAY explain how to perform a bounded class of work, for example:

- release operations;
- benchmark ingestion;
- GitHub workflow;
- runtime certification;
- documentation reconciliation;
- harness experimentation.

These guides MUST name their authority boundary and MUST NOT silently redefine project-wide semantics.

### Tier 3 — historical/reference evidence

Historical roadmaps, old evaluations, donor notes, and closed work-unit documents are evidence/reference material.

They MUST NOT be treated as current authority merely because they are detailed.

## 4. Anti-redundancy rules

For every durable rule, prefer one authoritative statement plus references.

### 4.1 Single-owner rule

A normative rule SHOULD have one canonical owner document.

Other documents should use a short pointer such as:

```text
Authority: docs/ACCEPTANCE-CONTRACT.md
```

rather than copying the rule set.

### 4.2 No synchronized-copy requirement

Do not create documentation structures that require the same rule to be manually kept in sync across `AGENTS.md`, README, workflow docs, architecture docs, and runbooks.

If a change would require editing several copies of identical normative text, first consider replacing those copies with references.

### 4.3 Preserve local context

Small restatements are acceptable when they are required to make a local procedure safe, but they must be:

- short;
- semantically identical to the owner rule;
- clearly subordinate to the owner document.

### 4.4 Historical immutability

Do not rewrite historical evidence to match current architecture. Add supersession notices or current pointers instead.

## 5. Instruction design rules

### 5.1 Put critical constraints early

Rules that can cause unsafe mutation, invalid evidence, unauthorized merge, or false Acceptance claims belong near the top-level agent entrypoint.

Do not rely on an agent finding a critical constraint deep inside a large historical document.

### 5.2 Prefer explicit condition/action rules

Use verifiable forms:

```text
IF <condition>
THEN <required action>
DO NOT <forbidden action>
```

Prefer observable constraints over vague prose such as "be careful", "use best practices", or "ensure quality".

### 5.3 Separate invariant from rationale

State the rule first, then point to rationale/evidence.

Example:

```text
Rule: benchmark evidence may influence executor/harness selection only after eligibility hard gates.
Rationale: see benchmark-selection architecture and empirical protocol.
```

### 5.4 Minimize conflicting instruction sources

Before adding a rule, search for existing guidance that already covers the behavior.

If a new instruction conflicts with a benchmark scaffold, runtime contract, test protocol, or canonical project rule, resolve the conflict explicitly. Do not depend on the model to infer precedence.

### 5.5 Make activation conditions explicit

Conditional procedures such as closure checklists, destructive cleanup, releases, external-provider execution, or broad audits must state when they activate.

Mere file presence is not authorization.

### 5.6 Prefer retrieval over bulk injection

When agent/runtime capabilities permit it, retrieve relevant canonical sections for the current task instead of injecting the full documentation corpus into every interaction.

The harness SHOULD optimize for relevant context coverage per token, not maximum context volume.

## 6. Harness engineering scope

A harness includes the code and configuration around a model that changes what the model can observe or do, including:

- system/developer instructions;
- repository instruction files;
- context retrieval and ranking;
- memory/state;
- tool exposure and tool contracts;
- subagent or delegation policy;
- stopping/continuation criteria;
- verification hooks;
- retry/control flow;
- trace capture.

Changing any of these may change behavior even if the base model is unchanged.

Therefore, material harness changes are engineering changes and require evaluation proportional to their expected effect.

## 7. Evaluation protocol for agent/harness changes

A material instruction or harness change MUST state a falsifiable hypothesis.

Preferred form:

```text
HYPOTHESIS:
Changing <harness component> will improve <metric/behavior>
on <task set>
without regressing <protected constraints>.
```

### 7.1 Minimum evaluation tuple

Record, where applicable:

```text
HARNESS_ID:
HARNESS_VERSION_OR_COMMIT:
MODEL_ID:
MODEL_VERSION:
PROVIDER:
TASK_SET:
TASK_SET_VERSION:
BASELINE:
CANDIDATE:
REPETITIONS:
SEED_OR_STOCHASTICITY_CONTROL:
METRICS:
HARD_CONSTRAINT_CHECKS:
RAW_ARTIFACTS:
RESULT:
LIMITATIONS:
```

This is compatible with the repository's canonical empirical protocol and existing `BenchmarkEvidence` identity fields.

### 7.2 Evaluate both task success and compliance

A harness change can improve task success while increasing rule violations.

At minimum, distinguish:

- task outcome / solution quality;
- instruction/scaffold compliance;
- tool-policy compliance;
- evidence/Acceptance integrity;
- cost/tokens/latency when decision-relevant;
- repository exploration/context efficiency when retrieval behavior changed.

### 7.3 Use representative task sets

Do not optimize only against one convenient example and generalize broadly.

Task sets should cover the failure modes the harness claims to improve. When a change targets repository navigation, include localization/exploration-sensitive tasks. When it targets long instructions, include multi-constraint tasks.

### 7.4 Protect against overfitting

Separate, when practical:

- development/search tasks used to tune the harness;
- selection/validation tasks used to choose a candidate;
- held-out tasks used to estimate generalization.

If a task set was used to select the candidate, label it as selection data rather than untouched final evidence.

### 7.5 Stochastic evaluation

For model-mediated behavior with meaningful variance:

- use multiple repetitions when practical;
- preserve per-run results;
- report aggregation and dispersion;
- avoid "rerun until PASS";
- bind results to exact model/provider/harness/task identity.

A single run may be useful diagnostic evidence but should not be generalized into a stable performance claim without justification.

### 7.6 Negative evidence is retained

Regressions, failed hypotheses, blocked runs, and contradictory results are part of the evidence record.

Do not discard them merely because a later candidate performs better.

## 8. Benchmark use inside metaO

Benchmark evidence is selection/design evidence.

It may support:

- choosing among otherwise eligible executors;
- choosing between harness candidates;
- identifying capability gaps;
- prioritizing experiments;
- estimating cost/latency/quality tradeoffs.

It may not:

- bypass capability eligibility;
- bypass health/capacity/quarantine/certification;
- bypass policy/budget/approval;
- mint trust/provenance;
- mint final Acceptance.

Canonical ordering remains:

```text
Mission
  -> capability eligibility
  -> health / capacity / quarantine / certification
  -> SelectionPolicy
  -> benchmark/evidence-informed selection
  -> Executor
  -> Verification
  -> Acceptance
```

## 9. Documentation change checklist

Before merging an agent/harness documentation change:

- identify the owner document for every new normative rule;
- remove avoidable duplicated normative text;
- confirm `AGENTS.md` remains an entrypoint rather than a knowledge dump;
- verify links/pointers to canonical authority;
- state whether product/runtime semantics changed;
- state whether executable evidence is required;
- if empirical claims are added, bind them to source or executed evidence;
- ensure benchmark claims do not exceed the studied task/model/harness context;
- preserve `BENCHMARK_EVIDENCE != METAO_ACCEPTANCE`.

## 10. References

Methodological references:

1. Lee, Y. et al. (2026), *Meta-Harness: End-to-End Optimization of Model Harnesses*, arXiv:2603.28052.
   https://arxiv.org/abs/2603.28052
2. Qi, Y. et al. (2025), *AGENTIF: Benchmarking Instruction Following of Large Language Models in Agentic Scenarios*, arXiv:2505.16944.
   https://arxiv.org/abs/2505.16944
3. Ding, D. et al. (2026), *OctoBench: Benchmarking Scaffold-Aware Instruction Following in Repository-Grounded Agentic Coding*, arXiv:2601.10343.
   https://arxiv.org/abs/2601.10343
4. Zhang, S. et al. (2026), *SWE-Explore: Benchmarking How Coding Agents Explore Repositories*, arXiv:2606.07297.
   https://arxiv.org/abs/2606.07297
5. Xu, Z. et al. (2026), *SWE-bench Science: Can Coding Agents Resolve Engineering Tasks in Science?*, arXiv:2608.19799.
   https://arxiv.org/abs/2608.19799
6. Liu, N. F. et al. (2023), *Lost in the Middle: How Language Models Use Long Contexts*, arXiv:2307.03172.
   https://arxiv.org/abs/2307.03172

Repository empirical claims remain governed by `docs/EMPIRICAL-EVIDENCE-AND-REPRODUCIBILITY.md`.
