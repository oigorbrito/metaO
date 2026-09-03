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
| Governance | `ryanwi/agent-control-plane` | `99da3934faa2aa7be9c5e8023e8704f` | **ADAPT / TEST_DONOR** | policy, approvals, budgets, kill-switch, preconditions, append-only events/replay/recovery | #140/#141/#168 and Rust parity owners; no duplicate authority |
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
