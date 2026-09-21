# Canonical Donor Evaluation Matrix

Status: canonical research output for #178  
Date: 2026-08-28  
Product code change: **NO**

## Purpose

This document consolidates the evidence-driven donor evaluations performed under #178 and its child issues. It records what may be reused, what must remain reference-only, and where executable metaO proof is still required.

The matrix is a research and design input. It does **not** authorize a donor to become a second metaO Core, policy authority, durable workflow authority, evidence authority, or acceptance authority.

## Methodological scope

The research process used by this matrix must remain narrower than the architecture decisions it informs.

The matrix may define how evidence is collected, preserved, compared, reproduced and reported. It must not present project-specific architecture preferences, weights or authority boundaries as universal scientific rules.

Methodological guidance is limited to established empirical-software-engineering practices: explicit research questions, transparent case/candidate selection, traceable data sources, fixed or recorded study procedures, sufficient context for independent assessment, reporting of negative and contradictory evidence, explicit limitations, and preservation of the evidence chain required to reproduce or independently replicate material claims.

A methodological rule may be added to this document only when it improves one or more of:

- traceability from claim to observed evidence;
- reproducibility of an execution or measurement;
- comparability between candidates;
- transparency of uncertainty, limitations or deviations;
- resistance to selective reporting or post-hoc criterion changes.

Methodological additions must not silently change an already frozen product criterion or architecture gate.

## Evidence rules

```text
DONOR_POPULAR != DONOR_FIT
DOCUMENTED != CODE_CONFIRMED
CODE_CONFIRMED != TEST_CONFIRMED
TEST_CONFIRMED != EXECUTED
EXECUTED != MEASURED
PAPER_RESULT != METAO_RESULT
BENCHMARK_PASS != METAO_ACCEPTED
ABSENCE_OF_EVIDENCE != EVIDENCE_OF_ABSENCE
FAILED_REPRODUCTION != DONOR_INVALID_WITHOUT_CAUSAL_DIAGNOSIS
```

Promoted donor semantics must be translated into deterministic tests owned by an existing metaO implementation issue before product adoption.

## Empirical evidence contract

Any donor claim used to justify `ADAPT`, `TEST_DONOR`, promotion, rejection on technical grounds, or a comparative superiority statement must record enough information for an independent engineer to reconstruct how the claim was obtained.

For each material claim, preserve where applicable:

1. **research question or decision claim** — the exact proposition being evaluated;
2. **subject identity** — repository, artifact, paper or standard and immutable commit/tag/version/DOI when available;
3. **selection rationale** — why the donor was included and what comparison scope it represents;
4. **unit of analysis** — file, function, subsystem, scenario, benchmark, runtime, protocol or complete donor;
5. **evidence source** — exact code path, test, command, run, artifact, issue or publication;
6. **environment** — relevant OS/runtime/toolchain/dependency versions for executed evidence;
7. **procedure** — commands, fixture, inputs, configuration and ordering needed to repeat the observation;
8. **observed result** — raw result or immutable pointer to it, including failures and unexpected outcomes;
9. **interpretation** — the bounded claim supported by that observation;
10. **limitations and threats** — known reasons the result may not generalize or may not be comparable;
11. **deviations** — any departure from the planned or previously frozen procedure;
12. **provenance** — link from the matrix claim back to the evidence and from the evidence forward to the resulting disposition.

A claim that cannot satisfy the applicable parts of this contract remains `DOCUMENTED`, `UNKNOWN`, `NOT_PROVEN`, `BLOCKED`, or another explicitly weaker state. Missing reproducibility metadata must not be silently inferred.

## Reproducibility and replication vocabulary

Use the following project vocabulary consistently:

- **repeatable** — the same team can repeat the procedure using the recorded setup and obtain a materially equivalent result;
- **reproduced** — an independent execution using the recorded artifacts/procedure obtains a materially equivalent result;
- **replicated** — an independently constructed evaluation of the same claim, potentially with a different implementation or setup, reaches a materially consistent conclusion;
- **not reproduced** — the attempt did not obtain a materially equivalent result; this is an observation requiring diagnosis, not automatic proof that the original claim or donor is invalid;
- **not reproducible from available artifacts** — the evidence package is insufficient to perform the attempt.

These labels describe evidence status, not architecture quality.

## Comparability rules

Comparative statements such as "lower cost", "more reliable", "better isolation", "fewer tokens", "faster", or "smaller trusted surface" require comparable observations.

A comparable measurement must keep constant, or explicitly account for, material factors such as:

- task/scenario and expected outcome;
- metaO contract and acceptance criteria;
- workload size and input context;
- model/provider configuration when LLM behavior is involved;
- runtime/toolchain versions;
- retry policy, timeout and concurrency;
- measurement boundary and units;
- warm/cold start state when relevant;
- number of observations or repetitions when variability exists.

When material factors differ, report the result as a case-specific observation rather than a candidate ranking unless a justified normalization method is documented.

Single-run measurements may be retained as exploratory evidence but must not be represented as stable performance/cost estimates when the measured phenomenon is variable.

If repeated measurements are used, preserve all valid observations or the declared exclusion rule. Do not keep only the best run.

## Anti-bias and anti-selective-reporting rules

The following are prohibited for decision-bearing donor evaluation:

```text
CHANGE_CRITERION_AFTER_RESULT_WITHOUT_RECORD = NO
RERUN_UNTIL_PASS_AND_REPORT_ONLY_PASS = NO
DROP_NEGATIVE_RESULT_WITHOUT_DECLARED_REASON = NO
SUBSTITUTE_README_CLAIM_FOR_EXECUTED_EVIDENCE = NO
SUBSTITUTE_STAR_COUNT_FOR_ENGINEERING_EVIDENCE = NO
GENERALIZE_ONE_FIXTURE_TO_ALL_WORKLOADS = NO
INFER_CAUSALITY_FROM_UNCONTROLLED_ASSOCIATION = NO
```

If a criterion, fixture or interpretation changes after results are observed, retain the original result and record the change, reason and effect on prior conclusions.

## Frozen metaO authority boundaries

```text
ORCHESTRATOR_DONE != METAO_ACCEPTED
RUNTIME_SELF_REPORT != GOVERNANCE_AUTHORITY
IDENTITY_FACT != AUTHORIZATION_DECISION
GATEWAY_VERDICT != METAO_ACCEPTED
TELEMETRY != DECISION_AUTHORITY
RUNTIME_SDK_TYPE != CORE_TYPE
FRAMEWORK_CONTROL_HOOK != ORCHESTRATOR_CONTRACT
```

The central architecture test remains:

> Can a complete orchestrator/runtime be replaced by a materially different one without changing metaO Core contracts, policy/budget semantics, evidence schema, or independent acceptance?

## Canonical matrix

| Family | Donor / source | Evaluated pin / artifact | Final disposition | Reusable value | Canonical metaO owner / boundary |
|---|---|---|---|---|---|
| Discovery | `github/spec-kit` | `5aa8bea7823dcd056f111f847bf2d576bad3f0a5` | **ADAPT — PRIMARY** | explicit underspecification, do-not-guess, clarification/readiness, WHAT/WHY vs HOW, converge against spec | #170–#177; metaO retains `ProjectContract` and `SPEC_READY` authority |
| Discovery | `Fission-AI/OpenSpec` | `a0ddb60d040c61f4907436a9d91310934b1dda63` | **ADAPT — SECONDARY** | explore-before-commit, proposal/spec/design/tasks separation, change/archive evolution | #170–#177; not hard readiness authority |
| Discovery | `bmad-code-org/BMAD-METHOD` | `cf0d98f03042c9640c3facd15efd93d8c8ce66c6` | **REFERENCE / SELECTIVE ADAPT** | right-size process, parent-intent traceability, replan from evidence | #170–#177; no BMAD workflow/backlog authority |
| Clarification benchmark | `fangz-cs/ClarifyCodeBench` | `5e2d5b5ce6259daa034cebb69f65e5e4c6dec3e9` | **TEST_DONOR** | 419 human-annotated underspecified tasks, key-question concepts, taxonomy | #180 / #170–#177; benchmark judge is not a hard gate |
| Clarification benchmark | SWE-RPG / arXiv:2608.09072 | paper available; advertised `Xin-Zhou-smu/SWE-RPG-Bench` repository observed public but empty (`size=0`) | **REFERENCE_FROM_PAPER / BLOCKED_EXTERNAL_ARTIFACT** | repository-level clarification/planning research hypothesis | #180 remains owner of reproducibility caveat; no code pin invented |
| Requirements standard | ISO/IEC/IEEE 29148:2018 | published standard reference | **REFERENCE_ONLY** | clarity, completeness, verifiability semantics where relevant | #170–#177; draft future editions are not published authority |
| Governance | `microsoft/agent-governance-toolkit` | `46463ef8689433817fcc0c582a7881f515d4df15` | **ADAPT / TEST_DONOR** | deterministic policy mediation, framework boundary, identity/trust, SRE/conformance | existing governance/security owners; never second Core/acceptance authority |
| Governance | `aws-samples/sample-agentic-governance-platform` | `665bd07af4615e550d7980154ad34c811aff81ff` | **REFERENCE_ONLY** | enterprise registry/access/policy/observability/cost architecture | vendor-coupled AWS + Entra implementation; no Core dependency |
| Governance | `ryanwi/agent-control-plane` | `99da3934faa2aa7be09df72134cc5e8023e8704f` | **ADAPT / TEST_DONOR** | policy, approvals, budgets, kill-switch, preconditions, append-only events/replay/recovery | #140/#141/#168 and Rust parity owners; no duplicate authority |
| Durability | `humanlayer/agentcontrolplane` | `eaa2a7ed1d9cb4e13dc53defaf420e36f481dcad` | **REFERENCE_ONLY** | long-lived asynchronous agent/task durability concepts | Kubernetes/Agent/Task topology must not enter generic Core |
| Engineering evidence | `trietphan/agent-control-center-core` | `f9305056f90c61ac53ecc74a1b31af19809971fe` | **ADAPT / TEST_DONOR — ENGINEERING ONLY** | OOP adapter conformance, isolated Git worktree, independent verifier, artifact hashes, review CAS | #144/WUS; Git/worktree assumptions stay domain-specific |
| Governance hub | `glemmestad/frontkeep` | `db3f5392eab968865b4e64b05424913cb27acf78` | **REFERENCE / SEMANTIC_DONOR** | Rust hub, project gate, Cedar policy, budgets, credential minting, audit | #140/#149 as reference; not workflow or acceptance authority |
| Enforcement | `agentcontrol/agent-control` | `7cb21af33e46ae5122288acc92d8ce5b3f7159e7` | **DEFER / TEST_DONOR** | evaluator/control runtime incl. budget evaluator | overlaps AGT/#162/#168; no proven unique product gap |
| Software factory | `racecraft-lab/Paddock` | `c767bbbb9483ddc56ca8fccd3fefee35194c87ea` | **REFERENCE_ONLY** | hardened software-factory intake/evidence patterns | engineering-specific; not generic Core |
| Gateway/deployment | `agentsystems/agent-control-plane` | `f09a940d4185a44dfab7df77796641268c592e18` | **REFERENCE_ONLY** | gateway, container discovery, append-only audit | deployment reference; auth surface not stronger canonical security donor |
| Multi-runtime | `Jovancoding/Network-AI` | `39fb0cbf559998a78b454009668409b8edd41ceb` | **REFERENCE / TEST_DONOR** | broad cross-framework adapter coverage and adapter harness ideas | #145/#222 Phase 3; cross-framework support alone does not prove whole-orchestrator replacement |
| Multi-runtime | Microsoft generic framework adapter | AGT pin `46463ef8689433817fcc0c582a7881f515d4df15` | **ADAPT / TEST_DONOR** | generic wrapper/intervention boundary | #145/#222 Phase 3; cannot set acceptance |
| Governance benchmark | `agentic-control-plane/agentgovbench` | `e0ce93ae175376d7847c69a64d0c36bdfa6ca717` | **TEST_DONOR** | 48 deterministic scenarios across identity, policy, provenance, scope, rate limits, audit, fail-mode, isolation | #145/#168; does not replace restart/failover/chaos/causal gates |
| Adversarial | `ethz-spylab/agentdojo` | `089ed468cf3ed0322acc66b0211f26d9d90dbf60` | **TEST_DONOR** | realistic tool-use + indirect prompt-injection fixtures | #162/#168 |
| Adversarial | `x89zhang/AgentDyn` | `a4eb0787c4701a1fed7420b9cdd070559ca7f0b8` | **TEST_DONOR** | dynamic/open-ended injection trajectories; separate utility/security outcomes | #162/#168 |
| Red-team orchestration | `microsoft/PyRIT` | `97620079a7fe44245a3a1fad6faf130a8f854d6d` | **REFERENCE / TEST TOOLING** | attack/converter orchestration | #162/#168; never canonical scorer or policy authority |
| Budget protocol | `runcycles/cycles-protocol` | `9899d0474ecb50247e3fa46d23a7f1b825048122` | **ADAPT / TEST_DONOR** | concurrency-safe reserve/commit/release, idempotent settlement, recovery conformance | #140/#168/#222 parity where applicable |
| Delegated authority | `xmuruaga/bounded-agents` / APC | `d31a1ea115a3e97ab972ac8d03f23ef36cf9b653` | **STRONG SEMANTIC / TEST_DONOR** | monotonic delegation attenuation and composition-aware authorization | #149/#159/#168 depending layer; model output cannot widen authority |
| Identity/delegation | `sunilp/aip` | `0ad099d354561b750517827b519f34eac98af98b` | **ADAPT / TEST_DONOR** | invocation-bound delegation/provenance; concrete negative vectors for signed-but-unauthorized requests | #159/#165/#168; identity/token fact != policy acceptance |
| Enforcement gateway | `preloop/preloop` | `95d387a6752bffd6656e43763f176aad5fcffd9b` | **REFERENCE / ADAPT BELOW CORE** | policy/approval/gateway/runtime-plugin enforcement | #145/#149/#168; no Core or acceptance authority |
| Transport gateway | `agentgateway/agentgateway` | `5fb188b669df04ded08ee4e8cbb6b2bf9d2f5c20` | **REFERENCE_ONLY** | MCP/A2A/LLM connectivity, JWT/policy/routing/failover/observability | transport/enforcement infrastructure only |
| A2A governance fixture | `ygmrs/a2a-governance-gateway` | `c02fa389e19b5b73fba2832ee7e79a5d90efdf06` | **TEST_DONOR / REFERENCE_ONLY** | compact identity/capability/budget/HITL/audit fixture | #145/#162/#168; demo stores are not production authority |
| Control boundary | `responsibleai/agent-hooks` | `0821ebbae252c45cd225304a464d1130963b82a8` | **STRONG ADAPT / TEST_DONOR** | framework-neutral lifecycle interception contract + multi-language conformance vectors | #145/#168; hook verdict != orchestrator contract/acceptance |
| Control boundary | `edictum-ai/edictum` | `8ef51664fc8dbc136044771ee2c9ec67ca4ba04e` | **ADAPT / TEST_DONOR** | fail-closed tool/workflow gates, principal/evidence fixtures, unknown-side-effect retry discipline | #141/#158/#162/#168; no evidence/acceptance authority |

## 2026-09-21 agent-system donor program

This section records the current research set for a lean supervisor/executor system and the controlled-fork/partial-migration strategy defined by `ADR-2026-09-21-CONTROLLED-FORK-PARTIAL-DONOR-MIGRATION.md`.

### Research question

```text
RQ:
Which externally evaluated project should provide the selected chassis,
and which narrower mechanisms from the remaining projects should be
transplanted, rejected, retained as alternatives, or used only as gates,
such that complexity and cost are minimized without losing the intended
objective or required quality?
```

This section is **not** a final winner table. The projects below were evaluated by different upstream studies on different workloads, models, costs, and measurement boundaries. Their reported numbers are therefore evidence about the capability tested by each upstream study, not a valid universal ranking across projects.

The canonical interpretation rule is:

```text
UPSTREAM_BENCHMARK_RESULT
-> EVIDENCE_FOR_THE_MEASURED_MECHANISM
!= BEST_CHASSIS_PROVEN
!= METAO_LOCAL_GAIN_PROVEN
!= PROMOTION_AUTHORIZED
```

### Current candidate and donor map

| Project / repository | Evaluated research pin | Upstream evidence observed at pin | Candidate role | Current empirical disposition | Explicit limit |
|---|---|---|---|---|---|
| **Harbor** — `harbor-framework/harbor` | `71c77fdd119df12eb6ab56e5bc0f29bf62fad338` | Upstream documents a benchmark/environment framework, Docker/cloud execution, third-party benchmark adapters, verifier/telemetry infrastructure, and published parity-oriented adapter evaluations. | **CHASSIS_CANDIDATE / EXECUTION-EVALUATION DONOR** | `TRANSPLANT_CANDIDATE` for execution/evaluation infrastructure; final chassis remains unselected | Adapter/runtime parity supports neutrality of evaluated conversions; it does **not** prove Harbor is the best supervisor, decomposer, or universal chassis. |
| **BenchFlow** — `benchflow-ai/benchflow` | `6b99a10e99a366633b93411249bb71f4c178d804` | Upstream exposes a universal environment/task framework, hardened scoring contract, benchmark adoption with parity verification, multi-agent/multi-round patterns, and explicit task/evidence semantics. | **CHASSIS_CANDIDATE / EVIDENCE-SEMANTICS DONOR** | `TRANSPLANT_CANDIDATE` for provenance, fail-closed semantics, task/oracle/verifier boundaries and conversion-loss reporting | Representation/parity evidence does **not** prove lower execution cost or superior supervision; do not import a second runtime merely to obtain evidence semantics. |
| **AOrchestra** — `FoundationAgents/AOrchestra` | `14a1a2051d6b03c479b706f8f555a60b8419e3b5` | Upstream reports evaluation across GAIA, SWE-bench and Terminal-Bench and a **16.28% relative improvement** over the strongest reported baseline with Gemini-3-Flash. The system decomposes goals and synthesizes subagents from instruction/context/tools/model. | **SUPERVISOR / DECOMPOSITION / ROUTING DONOR** | `TRANSPLANT_CANDIDATE` | Reported multi-benchmark gain supports the orchestration mechanism under those conditions; it does **not** prove AOrchestra is the best general chassis or that its complete runtime should be retained. |
| **OneDayAgent** — `zjunlp/OneDayAgent` | `f29f6d496437c9ea7b8b5e8fe232d186b868b9f5` | Upstream reports evaluation on AgentIF-OneDay (104 tasks, multiple model backends) with overall score **0.821**, using task decomposition, execution memory, global verification and repair. | **LONG-HORIZON COMPOSITION / VERIFY / REPAIR DONOR** | `TRANSPLANT_CANDIDATE`; decomposition competes with other decomposers | Strong evidence for the combined long-horizon harness does **not** establish transfer to SWE/Harbor workloads; decomposition is potentially redundant with AOrchestra and must be compared rather than accumulated. |
| **FoldAgent / Context-Folding** — `sunnweiwei/FoldAgent` | `58a2d6964ecebe99940529eace50a0558901b8a5` | Upstream implementation exposes context folding, branch-style subtask execution and SWE-bench Verified evaluation support, with a training stack for FoldGRPO/PPO. | **CONTEXT-ISOLATION / BRANCH-FOLD DONOR** | `TRANSPLANT_CANDIDATE` for the minimal branch/fold primitive; training stack remains `DIVERGENT_ALTERNATIVE` until needed | The minimal context mechanism and the RL training stack are separate adoption decisions. Do **not** import the training subsystem merely because the folding primitive is useful. |
| **AgentFlow** — `lupantech/AgentFlow` | `b94006436b8712ab8682846fb0d886a5f174f2d4` | Upstream reports a Planner/Executor/Verifier/Generator architecture with Flow-GRPO and gains across 10 benchmarks: **+14.9% search, +14.0% agentic, +14.5% math, +4.1% science** for the reported 7B setup. | **TRAINABLE-PLANNER / VERIFY / GENERATE ALTERNATIVE** | `DIVERGENT_ALTERNATIVE` initially; planner training remains future candidate | Planner, verifier and generator overlap with AOrchestra/OneDayAgent roles. Do not keep duplicate permanent mechanisms without an ablation showing distinct value. |
| **TeamBench** — `ybkim95/TeamBench` | `d185aef1916fd86a9ba554d581fd256319a973af` | Upstream publishes **931 evaluation instances, 19 categories, 5 ablation conditions and a 27-configuration cross-provider grid** with Planner/Executor/Verifier separation. | **COORDINATION BENCHMARK / GATE** | `BENCHMARK_OR_GATE_ONLY` | Its main value is measuring whether coordination helps and at what cost. It is not evidence that its runtime should become product architecture. |
| **mini-SWE-agent** — `swe-agent/mini-swe-agent` | `04d809ceab9df28f9adaed044884180159172930` | Upstream describes an agent class of roughly **100 Python lines** and reports **>74% SWE-bench Verified** performance. | **MINIMAL EXECUTOR / COMPLEXITY BASELINE** | `DOMAIN_SPECIFIC_PLUGIN` plus mandatory baseline candidate for SWE experiments | High SWE-bench performance supports a minimal executor in that domain; it does **not** imply that all tasks should use mini-SWE or that supervisor overhead is justified. |
| **SWE-ReX** — `SWE-agent/SWE-ReX` | `5c995c365dfb1fd5bc56fda688be5d8538f9931f` | Upstream demonstrates the same agent API across local/remote/Docker/cloud execution and shows SWE-agent running **30 SWE-bench instances in parallel**; documentation targets massively parallel execution. | **MINIMAL RUNTIME / SANDBOX DONOR** | `TRANSPLANT_CANDIDATE` only if the selected chassis lacks an equivalent runtime boundary | ReX solves runtime execution, not benchmark semantics, evidence authority, decomposition or acceptance. Do not create a second runtime if the selected chassis already satisfies the requirement. |
| **Agentless** — `OpenAutoCoder/Agentless` | `5ce5888b9f149beaace393957a55ea8ee46c9f71` | Upstream reports **82/300 = 27.3% SWE-bench Lite at US$0.34/issue** for the original configuration and later reports 40.7% Lite / 50.8% Verified with Claude 3.5 Sonnet. The pipeline narrows repository context before repair and reranking. | **SWE HIERARCHICAL-LOCALIZATION DONOR** | `DOMAIN_SPECIFIC_PLUGIN` | The value is bounded to SWE-style localization/repair. Do not make repository localization a universal supervisor primitive. Later reported results must retain their changed model/configuration context. |
| **MASAI** — `masai-dev-agent/masai` | `21b60fb15a7743d1e39f55f6ae66f87b3175308b` | Upstream reports **28.33% SWE-bench Lite** on 300 issues from 11 Python repositories at **< US$2/issue average**, using modular specialist subagents. | **SWE SPECIALIST-DECOMPOSITION REFERENCE/DONOR** | `DIVERGENT_ALTERNATIVE` or `REDUNDANT_WITH_SELECTED_MECHANISM` after generic decomposition is selected | Specialist decomposition overlaps with AOrchestra/OneDayAgent decomposition. Preserve as a competing treatment or bounded SWE strategy, not a second universal decomposition authority. |

### Evidence grade for this research sweep

The entries above currently have the following local evidence ceiling unless a stronger metaO record is added:

```text
EXACT_UPSTREAM_PIN = RECORDED
UPSTREAM_README_OR_PUBLISHED_RESULT = OBSERVED
LOCAL_METAO_EXECUTION = NOT_YET_ESTABLISHED_BY_THIS_SECTION
LOCAL_COMPARABLE_TRANSPLANT_RESULT = NOT_YET_ESTABLISHED
FINAL_CHASSIS_WINNER = NOT_SELECTED_BY_THIS SECTION
```

Therefore, upstream quantitative results may be used to:

- justify inclusion in the research set;
- avoid re-proving already documented upstream facts unnecessarily;
- design local hypotheses and ablations;
- prioritize which mechanisms are worth transplanting.

They must not be used to:

- declare a final chassis winner across incomparable studies;
- claim local token/cost savings without a comparable local boundary;
- claim that a transplanted mechanism preserves its upstream gain;
- authorize product migration;
- promote a mechanism into the permanent core without the applicable local gate.

### Distinct capability map and redundancy boundaries

The target system seeks **distinct capabilities**, not every implementation.

| Capability family | Primary candidates | Redundancy/divergence rule |
|---|---|---|
| execution/evaluation chassis | Harbor, BenchFlow, SWE-ReX (runtime-only) | Select one primary execution ownership boundary. ReX may be below the chassis only if it does not create a second competing runtime authority. |
| evidence/provenance/parity semantics | BenchFlow, Harbor | Prefer one canonical evidence representation. Adapter parity and evidence provenance are complementary only when their authorities remain explicit. |
| generic decomposition/routing | AOrchestra, OneDayAgent, AgentFlow, MASAI | Treat as competing treatments. Do not permanently combine multiple decomposers without an `A`, `B`, `A+B` ablation showing incremental benefit. |
| context isolation/reduction | FoldAgent, OneDayAgent, Agentless (SWE-specific), AOrchestra context selection | Distinguish generic folding, execution memory, and domain-specific localization. Combine only if each removes a different measured bottleneck. |
| composition / synthesis | OneDayAgent, AgentFlow Generator, AOrchestra orchestration loop | Select the smallest mechanism that preserves required output quality. |
| independent verification / repair | OneDayAgent, AgentFlow Verifier, Harbor verifier | Verification authority must remain independent from executor self-report; repair must not silently convert failure into PASS. |
| SWE localization | Agentless, MASAI specialist roles | Keep outside universal core unless non-SWE evidence demonstrates broader applicability. |
| minimal executor baseline | mini-SWE-agent | Baseline/control, not universal winner. More complex executors must justify added cost/complexity. |
| coordination necessity gate | TeamBench and comparable ablation harnesses | Evaluation-only by default. Its purpose is to determine **when not to supervise/decompose** as much as when to do so. |
| learned planner optimization | AgentFlow Flow-GRPO, FoldAgent training stack | High-cost optional optimization. Admit only after a simpler non-trained strategy is shown to be the bottleneck. |

### Engineering limits for the final project

The final project must obey the following limits regardless of which donor wins a local comparison:

```text
ONE_PRIMARY_CHASSIS = YES
ONE_CANONICAL_ACCEPTANCE_AUTHORITY = YES
ONE_CANONICAL_EVIDENCE_AUTHORITY = YES
SECOND_DURABLE_WORKFLOW_ENGINE_BY_ACCIDENT = NO
SECOND_RUNTIME_AUTHORITY_BY_ACCIDENT = NO
EXECUTOR_SELF_PROMOTION = NO
SUPERVISOR_SELF_ACCEPTANCE = NO
UPSTREAM_RESULT_AS_LOCAL_PASS = NO
DOMAIN_PLUGIN_AS_UNIVERSAL_CORE = NO
DUPLICATE_MECHANISM_WITHOUT_ABLATION = NO
CORE_PROMOTION_WITHOUT_REMOVAL_PATH = NO
```

Additional empirical limits:

1. **Objective preservation:** a reduction in cost, tokens, LOC or runtime is not an improvement if the declared objective or acceptance quality falls outside the predeclared bound.
2. **Quality preservation:** simpler is preferred only when quality is equivalent within the declared tolerance or when the trade-off rule explicitly accepts the loss.
3. **Scope preservation:** a SWE-bench result supports SWE-bench-like claims, not a general-agent claim.
4. **Configuration preservation:** model/provider changes must be recorded; a later stronger model result is not directly attributable to architecture.
5. **Attribution:** when two mechanisms are introduced together, the combined result cannot establish which mechanism caused the change without an appropriate ablation.
6. **Removability:** donor mechanisms should enter behind interfaces that permit baseline-vs-treatment comparison and rollback.
7. **Fail-closed evidence:** missing or incompatible evidence remains `UNKNOWN`, `NOT_TESTED`, or `BLOCKED`; it must not become PASS through inference.
8. **Complexity budget:** dependencies, changed core LOC, new interfaces, trusted surface and operational overhead are first-class costs alongside token/USD/runtime cost.
9. **No sunk-cost promotion:** implementation effort already spent is not evidence that the mechanism should remain.
10. **Selection over accumulation:** when two mechanisms satisfy the same role, the default experiment is comparison, not permanent coexistence.

### Required next evidence before final selection

The next decision-bearing study must produce a common local boundary for the top chassis candidates and the first transplant candidates. At minimum record:

```text
EXACT_PIN
BASELINE_COMMAND
TASK_CORPUS
MODEL_PROVIDER_VERSION
RUNTIME
ACCEPTANCE_VERIFIER
SUCCESS_RATE
INPUT_TOKENS
CACHED_INPUT_TOKENS
OUTPUT_TOKENS
USD_COST
WALL_TIME
RETRIES
NEW_DEPENDENCIES
NEW_CORE_LOC
CHANGED_CORE_LOC
INTERFACES_CHANGED
FAILURE_CLASSIFICATION
RAW_ARTIFACT_POINTERS
```

The study should not repeat upstream experiments merely to reproduce marketing numbers. It should test only the unresolved transfer question: whether the selected chassis can absorb the candidate mechanism with acceptable complexity and preserve or improve the intended objective and quality.


## Claim-to-evidence record template

New or materially revised donor conclusions should use the following record, either inline, in the owning issue, or in a linked immutable artifact:

```text
CLAIM_ID:
RESEARCH_QUESTION:
DONOR:
PIN_OR_VERSION:
UNIT_OF_ANALYSIS:
SELECTION_RATIONALE:
EVIDENCE_GRADE:
CODE_OR_DOC_POINTERS:
EXECUTION_COMMANDS:
FIXTURE_OR_INPUT:
ENVIRONMENT:
RAW_ARTIFACT_POINTERS:
OBSERVED_RESULT:
INTERPRETATION:
LIMITATIONS:
DEVIATIONS:
REPRODUCIBILITY_STATUS:
METAO_OWNER:
DISPOSITION_IMPACT:
```

Fields that do not apply may be marked `N/A` with a short reason. They must not be fabricated merely to complete the template.

## Promotion threshold

A donor may be promoted from reference-only evidence into a product-affecting adaptation only when:

- the relevant claim is bound to an immutable source/version where such a pin exists;
- code-dependent claims have been inspected in code rather than inferred from prose;
- behavior-dependent claims have executable evidence or an explicit reason why execution is impossible;
- the metaO-owned fixture expresses the required semantic behavior independently of donor marketing terminology;
- observed failures and contradictory evidence are retained;
- the result states its limitations and does not generalize beyond the tested scope;
- a canonical metaO owner exists for the promoted behavior;
- promotion does not create a second architecture authority prohibited elsewhere in this document.

`REFERENCE_ONLY` may require less evidence because it does not authorize product behavior. A weakly evidenced donor may therefore remain useful as a source of hypotheses without being promoted.

## Promoted deltas already owned by metaO

No new product implementation issue is required from this research sweep. Valid deltas map to existing owners:

```text
DISCOVERY / MATERIAL AMBIGUITY             -> #170-#177
BUDGET ATOMICITY / IDEMPOTENT SETTLEMENT   -> #140 / #168 / #222 parity
FAILURE / RETRY / RECOVERY LINEAGE         -> #141 / #168
DELEGATION ATTENUATION / COMPOSITION        -> #149 / #159 / #168
WORKLOAD IDENTITY / TEMPORAL AUTHORITY      -> #159 / #165 / #168
WHOLE-ORCHESTRATOR REPLACEMENT              -> #145 / #222 Phase 3
ADVERSARIAL RUNTIME CERTIFICATION           -> #162 / #168
EXTERNAL-EFFECT IDEMPOTENCY                 -> #158 / #168
ENGINEERING-WORKLOAD CONTAINMENT            -> #144 / WUS
```

## Required negative vectors carried forward

The research produced concrete regression requirements rather than product authority:

1. a valid signature/identity with invalid scope, expiry, depth or budget must still DENY;
2. a child delegation can never widen parent scope/budget/time authority;
3. individually allowed actions may still be forbidden when their session composition violates policy;
4. a model text refusal cannot rescue a forbidden tool/action attempt;
5. adapter/internal exceptions must not blindly retry an unknown non-idempotent effect;
6. replayed history cannot rewrite an already-bound terminal outcome;
7. gateway, benchmark, telemetry and runtime PASS/DONE signals cannot issue `METAO_ACCEPTED`;
8. runtime/framework SDK objects stop at the adapter boundary;
9. changing orchestrator must leave Mission/Policy/Budget/Evidence/Acceptance contracts unchanged.

## Open research caveat

Issue #180 remains open only for a reproducibility limitation:

```text
SWE_RPG_PAPER = AVAILABLE
SWE_RPG_ADVERTISED_REPOSITORY = PUBLIC_BUT_EMPTY_AT_INSPECTION
REPRODUCIBLE_CODE_PIN = NOT_AVAILABLE
CLASSIFICATION = BLOCKED_EXTERNAL_ARTIFACT
PRODUCT_WIP_BLOCKED = NO
```

Do not convert this absence into a fabricated code pin or a product failure. ClarifyCodeBench and deterministic metaO assertions remain sufficient to continue Project Discovery design/testing independently.

## Research limitations

This matrix is a bounded engineering study, not a universal ranking of agent frameworks, languages, runtimes or governance systems.

Its conclusions are conditional on:

- the metaO requirements and authority boundaries under evaluation;
- the exact donor pins/artifacts inspected;
- the fixtures and workloads actually executed;
- the environments and configurations recorded for those executions;
- the evidence available at the time of evaluation.

A later donor version, different workload, different operational environment or different research question may produce a different result. Such a result should trigger a new or amended evidence record rather than retroactively rewriting the original observation.

## Methodological references

This matrix's empirical/reproducibility rules are informed by established software-engineering research guidance, including:

- Runeson, P.; Höst, M. *Guidelines for conducting and reporting case study research in software engineering*. Empirical Software Engineering 14, 131–164 (2009). DOI: `10.1007/s10664-008-9102-8`.
- ACM SIGSOFT. *Empirical Standards for Software Engineering Research* — method-specific standards and checklists for conducting and reporting empirical software-engineering research.

These references govern research conduct/reporting principles only. They do not define metaO product requirements, architecture boundaries, donor dispositions or score weights.

## Final authority result

```text
SECOND_METAO_CORE = NO
SECOND_POLICY_AUTHORITY = NO
SECOND_DURABLE_WORKFLOW_AUTHORITY = NO
SECOND_EVIDENCE_AUTHORITY = NO
SECOND_ACCEPTANCE_AUTHORITY = NO
WHOLE_DONOR_PRODUCT_DEPENDENCY = NO
NEW_UNMAPPED_PRODUCT_OBLIGATION = 0
PRODUCT_CODE_CHANGE = NO
```

Implementation remains authorized only through the canonical Rust migration and existing issue owners.
