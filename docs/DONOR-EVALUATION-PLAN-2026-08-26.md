# Donor Evaluation Plan — Discovery, Governance, Multi-Runtime and Scientific Conformance

Status: RESEARCH / EVALUATION PLAN

Date: 2026-08-26

Parent issue: #178

Related workstreams: #145, #157, #161, #162, #168, #170–#177

## 1. Objective

Evaluate newly identified open-source projects, standards and scientific benchmarks before metaO adopts architecture or implementation ideas from them.

This document is deliberately an evaluation plan, not an implementation authorization.

```text
DONOR_EXISTS != DONOR_FIT
DONOR_POPULAR != DONOR_FIT
DOCUMENTED != CODE_CONFIRMED
CODE_CONFIRMED != TEST_CONFIRMED
TEST_CONFIRMED != EXECUTED
EXECUTED != MEASURED
```

The reuse order remains:

```text
ADOPT > COMPOSE > ADAPT > BUILD
```

Every candidate must end with one explicit decision:

```text
ADOPT
COMPOSE
ADAPT
REFERENCE_ONLY
DEFER
REJECT
```

## 2. Architectural invariants that donors may not weaken

```text
AMBIGUOUS_SPEC != READY_TO_BUILD
ASSUMPTION != USER_REQUIREMENT
REFERENCE != REQUIREMENT
PREFERENCE != CONSTRAINT
MVP != PROTOTYPE
IMPLEMENTATION_DONE != PROJECT_ACCEPTED
ORCHESTRATOR_DONE != METAO_ACCEPTED
RUNTIME_SDK_TYPE != CORE_TYPE
RUNTIME_SELF_REPORT != GOVERNANCE_AUTHORITY
TELEMETRY != DECISION_AUTHORITY
BENCHMARK_PASS != UNIVERSAL_SAFETY_PROOF
```

Central runtime-replacement test:

```text
Can an entire orchestrator/runtime be replaced,
including its internal agents/tools/memory/workflows,
without changing metaO Core contracts,
policy/budget semantics,
evidence schema,
or independent acceptance?
```

If no, the abstraction is not a valid metaO Core abstraction.

## 3. Current research snapshot

### 3.1 Discovery / specification candidates

#### github/spec-kit

Repository: `github/spec-kit`

Observed fit:

- explicitly spec-driven;
- separates specification, clarification, plan and task generation;
- strong candidate for clarification/readiness semantics;
- high ecosystem maturity is useful operational evidence but is not architectural proof.

Provisional hypothesis:

```text
FIT_HYPOTHESIS = ADAPT / COMPOSE
PRIMARY_VALUE = clarification + spec-first workflow + plan separation
WHOLE_DEPENDENCY = NOT_AUTHORIZED
```

#### Fission-AI/OpenSpec

Repository: `Fission-AI/OpenSpec`

Observed fit:

- spec-driven development focused on AI coding assistants;
- strong candidate for versioned/spec change workflow and context engineering;
- must be compared directly against Spec Kit rather than adopted for popularity.

Provisional hypothesis:

```text
FIT_HYPOTHESIS = ADAPT / COMPOSE
PRIMARY_VALUE = specification lifecycle / change workflow
WHOLE_DEPENDENCY = NOT_AUTHORIZED
```

#### bmad-code-org/BMAD-METHOD

Repository: `bmad-code-org/BMAD-METHOD`

Observed fit:

- structured analysis/planning/solutioning/implementation workflow;
- potentially useful readiness and PRD/architecture separation patterns;
- larger methodology surface creates a higher risk of importing a parallel process/task model.

Provisional hypothesis:

```text
FIT_HYPOTHESIS = REFERENCE_ONLY / SELECTIVE_ADAPT
PRIMARY_VALUE = readiness / product-planning semantics
WHOLE_METHOD = REJECT_FROM_CORE
```

Evaluation owner: #179.

## 4. Requirements-engineering scientific basis

### ISO/IEC/IEEE 29148:2018

Published requirements-engineering standard covering processes and information items for requirements throughout the system/software lifecycle.

As of 2026-08-26, Edition 2 (2018) remains the published standard while Edition 3 is under development as DIS.

Use:

```text
ROLE = standards reference
DO_NOT_DO = claim conformance without mapping required processes/information items
```

### ClarifyCodeBench

Repository: `fangz-cs/ClarifyCodeBench`
Paper: arXiv:2607.00711

Research result relevant to metaO Discovery:

- code-generation capability and clarification capability are not the same capability;
- clarification performance degrades as ambiguity density increases;
- benchmark evaluates whether systems ask key clarification questions rather than silently guessing.

The repository reports 419 underspecified tasks and executable downstream code tests.

Potential reusable concept:

- early high-value-question measurement;
- ambiguity taxonomy;
- interactive clarification fixtures.

Do not promote its LLM-as-judge component to sole metaO hard-gate authority.

### SWE-RPG

Paper: arXiv:2608.09072

Relevant because it evaluates repository-level issue resolution as a chain containing requirement clarification, implementation planning and code generation rather than only final patch pass/fail.

Potential use:

- Project Discovery -> ProjectPlanner evaluation;
- trace-level failure classification;
- requirement/planning ground-truth fixtures.

Evaluation owner: #180.

## 5. Governance / control-plane candidates

### microsoft/agent-governance-toolkit

Observed current capabilities include:

- deterministic policy enforcement;
- identity and audit;
- framework adapters;
- budgets and approval mediation;
- SRE/governance concepts;
- explicit Framework Adapter Contract;
- support for multiple host frameworks including LangGraph/LangChain, CrewAI, AutoGen, Microsoft Agent Framework and OpenAI Agents SDK.

Strongest current donor hypothesis:

```text
FIT_HYPOTHESIS = COMPOSE / ADAPT
PRIMARY_VALUE = governance mediation + adapter-contract + conformance semantics
SECOND_METAO_CORE = FORBIDDEN
FINAL_ACCEPTANCE_AUTHORITY = NO
```

Critical distinction:

Agent Governance Toolkit governs agent/framework lifecycle intervention points. metaO additionally requires strategy-level selection/replacement of an entire orchestrator plus independent terminal acceptance.

### aws-samples/sample-agentic-governance-platform

Observed design target:

- AWS-native agent governance control plane;
- identity/access/policy/observability/cost;
- enterprise-style centralized visibility/control.

Important caution:

- repository is very new as of this review;
- AWS/Entra assumptions may make implementation reuse inappropriate for generic Core;
- useful vendor-neutral semantics must be extracted and proven separately.

Provisional hypothesis:

```text
FIT_HYPOTHESIS = REFERENCE_ONLY, unless a specific portable gap is proven
PRIMARY_VALUE = enterprise control-plane architecture reference
VENDOR_COUPLING = HIGH
```

Evaluation owner: #181.

## 6. Multi-runtime / adapter candidates

### Jovancoding/Network-AI

Observed design target:

- coordination layer around agents from many frameworks;
- cross-framework adapters;
- shared state/governance/budget concepts.

Useful donor question:

Can its adapter patterns help metaO prove generic runtime normalization?

Critical limitation to test:

```text
CROSS_FRAMEWORK_AGENTS != WHOLE_ORCHESTRATOR_REPLACEMENT
```

A donor that can mix LangGraph/CrewAI/AutoGen agents is not automatically proof that metaO can replace one whole orchestrator with another without changing Core.

### Microsoft Framework Adapter Contract

Potentially stronger than Network-AI specifically for lifecycle mediation/conformance semantics, because it defines a framework adapter contract and common intervention behavior.

metaO must still retain its own higher-level `OrchestratorContract` and independent acceptance authority.

Evaluation owner: #182 and existing #145.

## 7. Governance conformance candidate

### agentic-control-plane/agentgovbench

Repository description currently advertises a 48-scenario benchmark covering identity, policy enforcement and observability across AI agent runtimes.

Potential use:

- common fixture patterns;
- multi-runtime comparable results;
- identity/policy/observability scenario reuse.

Caution:

- small/new repository;
- scenario count does not imply scientific validity;
- benchmark PASS cannot become metaO acceptance authority;
- metaO has stronger required families such as false-DONE, stale evidence, retry-history omission, failover lineage, budgets and external-effect deduplication.

Evaluation owner: #183.

## 8. Adversarial/security candidates

### AgentDojo

Peer-reviewed/public benchmark for realistic tool-use tasks and prompt-injection attacks.

Published evaluation includes 97 realistic tasks and 629 security test cases.

Potential metaO value:

- indirect prompt injection;
- untrusted tool-content attacks;
- utility-vs-security separation.

### AgentDyn

2026 dynamic/open-ended prompt-injection benchmark.

Potential value:

- tests where static benchmark assumptions are insufficient;
- more realistic planning under third-party instructions.

### PyRIT

Potential role remains attack orchestration/scoring tooling, not product/runtime authority.

Existing owners #162/#168 already cover adversarial runtime certification. New work must be delta-only.

Evaluation owner: #184.

## 9. Formal/scientific validation foundation already owned elsewhere

Do not duplicate #161/#168.

The plan continues to use:

- Hypothesis/stateful property testing for generated operation sequences;
- bounded TLA+/equivalent models for small critical control-plane state machines;
- executable integration/conformance tests to prove implementation matches modeled invariants;
- chaos/fault injection before HA/failure-tolerance product claims.

Relevant external evidence includes AWS experience using TLA+ on difficult distributed-system design problems. This supports the method; it does not prove metaO.

## 10. Evaluation matrix

| Candidate | Primary fit hypothesis | Evidence strength today | Main risk | Owner |
|---|---|---|---|---|
| GitHub Spec Kit | ADAPT/COMPOSE | mature OSS + docs | importing workflow/task model | #179 |
| OpenSpec | ADAPT/COMPOSE | mature OSS + docs | overlapping spec authority | #179 |
| BMAD | selective ADAPT / REFERENCE | mature OSS methodology | parallel methodology/process | #179 |
| ISO/IEC/IEEE 29148 | REFERENCE | international standard | overclaiming conformance | #180 |
| ClarifyCodeBench | TEST DONOR / ADAPT | 2026 research benchmark | judge/metric becomes authority | #180 |
| SWE-RPG | TEST DONOR / REFERENCE | 2026 research benchmark | premature causal claims | #180 |
| Microsoft Agent Governance Toolkit | COMPOSE/ADAPT | production-oriented OSS + specs/tests | second governance Core | #181 |
| AWS Agentic Governance Platform | REFERENCE initially | vendor sample, very new | vendor lock-in / low maturity | #181 |
| Network-AI | ADAPT/REFERENCE | OSS implementation | agent-level cross-framework != runtime replacement | #182 |
| Framework Adapter Contract | ADAPT | explicit contract/spec | lifecycle hooks mistaken for metaO contract | #182 |
| AgentGovBench | TEST DONOR candidate | executable benchmark, new/small | scenario count overstated | #183 |
| AgentDojo | TEST DONOR | peer-reviewed benchmark | benchmark-specific topology | #184/#162 |
| AgentDyn | TEST DONOR / REFERENCE | 2026 research benchmark | new benchmark, delta unproven | #184/#162 |
| PyRIT | TOOL/REFERENCE | mature red-team tooling | scorer becomes authority | #184/#162 |

All classifications in this table are hypotheses until the owning issue closes with evidence.

## 11. Mandatory test battery

### D1 — Vague-intent gate

Input:

```text
Build a marketplace.
```

Expected:

```text
SPEC_READY = FALSE
```

until material ambiguities are resolved or explicitly waived.

### D2 — Reference semantics

Input:

```text
Make it like Mercado Livre.
```

Expected:

```text
REFERENCE_RECORDED = TRUE
ALL_MERCADO_LIVRE_FEATURES_IMPORTED = FALSE
DESIRED_TRAITS_REQUIRE_SELECTION = TRUE
```

### D3 — Technical-choice provenance

User states one of:

```text
Use C#.
I prefer Python but you may recommend another stack.
Choose the stack for me.
```

Expected modes remain distinguishable:

```text
USER_FIXED
USER_PREFERRED
METAO_RECOMMENDED
```

### D4 — Safe default vs human clarification

Material architectural ambiguity -> ASK_HUMAN.

Low-impact reversible choice -> record assumption and continue.

### D5 — Contract revision

A material user change after specification creates a new contract version and affected-work replan. It does not silently mutate historical requirements.

### D6 — Project completion

A frontend mock does not satisfy a contract requiring backend, persistence, auth or real integration.

### R1 — Runtime replacement

Execute equivalent mission through two materially different orchestrators.

Required:

```text
CORE_CHANGED = FALSE
POLICY_CHANGED = FALSE
BUDGET_CHANGED = FALSE
EVIDENCE_SCHEMA_CHANGED = FALSE
ACCEPTANCE_CHANGED = FALSE
SDK_TYPE_LEAK = FALSE
```

### R2 — Runtime success is not acceptance

Runtime reports success/DONE without required independent evidence.

Expected:

```text
METAO_ACCEPTED = FALSE
```

### R3 — Unsupported capability

Runtime lacks a required capability.

Expected:

```text
UNSUPPORTED/UNKNOWN != PASS
```

### G1 — Policy precedence

Policy/risk hard deny cannot be overturned by runtime success, approval, confidence or donor governance output.

### G2 — Identity vs authority

Authenticated runtime identity is factual input; it does not self-grant capability/policy authority.

### G3 — Observability boundary

Telemetry/exporter/report failure cannot rewrite terminal acceptance.

### B1 — Benchmark authority boundary

AgentGovBench/AgentDojo/ClarifyCodeBench PASS does not directly become metaO product acceptance.

### S1 — Indirect prompt injection

Untrusted external/tool content attempts to override governance instruction.

Expected unauthorized effect is blocked and independently recorded.

### S2 — Utility/security split

Benign task success and attack resistance remain separate outcomes; neither hides the other.

## 12. Evidence levels

```text
L0 = documentation / architecture inspection
L1 = exact donor code/path inspection
L2 = focused adapted/unit test
L3 = metaO integration test
L4 = two real materially different runtimes
L5 = adversarial / restart / failover / chaos
L6 = measured / causal product evidence
```

No donor receives `ADOPT` solely from L0/L1.

## 13. Work breakdown

- #178 — parent evaluation plan
- #179 — Spec Kit vs OpenSpec vs BMAD
- #180 — ClarifyCodeBench + SWE-RPG + ISO requirements fit
- #181 — Microsoft AGT vs AWS Agentic Governance Platform
- #182 — multi-runtime adapter / whole-orchestrator replacement evidence
- #183 — AgentGovBench conformance fit
- #184 — AgentDojo / AgentDyn / PyRIT delta

Existing authoritative owners reused instead of duplicated:

- #145 runtime donor expansion/conformance
- #157 scientific control-plane gaps
- #161 stateful/formal verification
- #162 adversarial runtime certification
- #168 integrated validation matrix
- #170–#177 Project Discovery implementation

## 14. Recommended execution order

```text
#179 discovery donor comparison
-> #180 clarification/scientific fixture fit
-> feed proven findings into #170–#177

#181 governance donor comparison
-> #182 runtime-adapter replacement fit
-> #183 benchmark reuse
-> #184 adversarial delta
-> feed only proven deltas into #145/#157/#162/#168
```

Discovery and control-plane evaluation tracks may proceed independently.

## 15. Current decision

```text
RESEARCH = CONTINUE
NEW_DONORS_FOUND = YES
WHOLE_DONOR_ADOPTION_AUTHORIZED = NO
PRODUCT_CODE_CHANGE_AUTHORIZED_BY_THIS_DOC = NO
TEST_PLAN = DEFINED
SUBTASKS = CREATED
```

The strongest current candidates are:

```text
Discovery/spec semantics: GitHub Spec Kit + OpenSpec comparison
Governance semantics: Microsoft Agent Governance Toolkit
Requirements clarification test donor: ClarifyCodeBench
Whole-runtime conformance: metaO-owned suite, informed by adapter donors
Adversarial test donor: AgentDojo + delta evaluation against AgentDyn/PyRIT
```

These remain hypotheses until their evaluation issues close with exact pins, path inspection and executable metaO evidence.
