# metaO Composition Map

Status: FROZEN for Block C (2026-08-23)

This document defines exactly what metaO may reuse, adapt, extract, reference, or build from approved donors. It is intentionally short at the decision level: implementation details may evolve, but donor responsibility boundaries may not drift silently.

## 1. Global implementation rule

For every capability:

```text
1. SEARCH COMPOSITION MAP
2. FIND APPROVED DONOR
3. COPY / ADOPT maximum viable proven unit
4. PRESERVE donor tests when applicable
5. ADAPT only at metaO boundaries
6. BUILD only missing metaO-specific logic
7. MEASURE reuse/adaptation/new LOC
8. PROVE through real path
```

Priority:

```text
ADOPT > ADAPT > BUILD
```

`BUILD` requires a written reason showing why no approved donor can satisfy the capability.

## 2. Evidence levels

```text
L0 DECLARED
L1 IMPLEMENTED
L2 UNIT_PROVEN
L3 INTEGRATION_PROVEN
L4 E2E_PROVEN
L5 INDEPENDENTLY_EXECUTED
```

`MOCK_ONLY` is an additional label and never substitutes for L3/L4/L5.

A critical feature counts as proven only when implementation exists, a test traverses the real path, and that test would fail if the implementation were removed.

## 3. Donor pinning policy

Pins below record the audit/composition reference used to freeze Block C. Before code is copied/adapted, implementation work MUST record the exact donor repository, donor commit and donor path actually consumed.

| Donor | Block-C reference pin | Pin rule |
|---|---|---|
| `tihotm/oma` | `ca43381dc8bce4041da4fc09efbe939642729939` | use exact consumed paths; never import OMA wholesale |
| `conductor-oss/conductor` | `b54f0d4ee546c1053367e1c14405c5396c17bfb1` | candidate pin only; final foundation pin is set after Block D L5 fit test |
| `UKGovernmentBEIS/inspect_ai` | `ebf4815ee260afcc8c34ad9d66e6f8d98a89e905` | extract only scoring/approval/limit/accounting units actually needed |
| `in-toto/in-toto` | `a8ce9ee2125ae5a4b041a4e37cc1cf10eed0da6b` | reference/adapt verification and provenance semantics; do not adopt as foundation |
| `sigstore/cosign` | `58aae9e112fa1de80594eed34667e920ac4d4a3b` | standard crypto/attestation implementation candidate for hostile boundary |
| `open-policy-agent/opa` | `551581feeceafa3129be543f0394fcf43beafde7` | optional policy decision-log reference/adaptation; not mandatory runtime dependency |

Other previously audited donors (OpenLinker, AgentField, Network-AI, ORCH, RouteLLM/RouterBench, CADTopo, Temporal, Dapr, MAS-Orchestra) MUST be pinned to exact commits/paths at the first implementation work unit that consumes them. Block C freezes their roles below, not unmeasured source pins.

### SMAG composition addendum

The bounded SMAG audit is recorded in [`SMAG-DONOR-COMPOSITION.md`](SMAG-DONOR-COMPOSITION.md) at `tihotm/smag@548a2ce85acb2aeb0e2d64a0fd03cfd839763ad8`.

The addendum is a governance, evidence, execution-control and engineering-harness donor map. It does not authorize SMAG as a metaO foundation, orchestrator, Core dependency, durable-workflow authority or acceptance authority. Every implementation work unit must still re-pin the exact donor commit, paths and tests it consumes.

## 4. Foundation / durable execution

### SOURCE
`conductor-oss/conductor`

### WHAT
- durable workflow/task execution;
- retries/timeouts;
- pause/resume/wait;
- worker boundary;
- external worker pattern;
- framework bridge mechanism;
- A2A patterns where useful;
- durable HUMAN task/approval wait.

### HOW
Run Conductor as an external durable execution foundation behind a thin metaO port/adapter. Prefer adoption of its real runtime behavior over rewriting equivalent workflow infrastructure.

### WHERE
`metaO DurableExecutionPort` / foundation adapter layer.

### MODE
`ADOPT` + thin `ADAPT` boundary.

### DO_NOT_TAKE
- global metaO policy authority;
- final acceptance authority;
- metaO strategy/scoring;
- assumption that Conductor server is the global security boundary;
- Conductor-specific SDK types in metaO Core.

### CURRENT_EVIDENCE_LEVEL
`PRIMARY FOUNDATION CANDIDATE`; audit evidence up to code/integration/E2E, but `NOT_YET_L5_BY_METAO`.

### FIT_TEST_REQUIRED
YES — Block D foundation fit test. If FAIL, evaluate Dapr then Temporal according to the existing foundation audit.

---

## 5. Runtime/event invariants

### SOURCE
OpenLinker

### WHAT
- lease;
- fencing;
- stale-worker rejection;
- event idempotency;
- concurrency controls;
- replay test patterns.

### HOW
Extract the smallest proven invariant units/patterns and adapt them to metaO runtime/durable-execution identities.

### WHERE
runtime/durable boundary and recovery tests.

### MODE
`EXTRACT / ADAPT`.

### DO_NOT_TAKE
OpenLinker as the full foundation or its unrelated domain architecture.

### CURRENT_EVIDENCE_LEVEL
strong real PostgreSQL/concurrency evidence from prior audit.

### FIT_TEST_REQUIRED
YES when first integrated.

---

## 6. Lifecycle / recovery

### SOURCE
AgentField

### WHAT
- health/presence;
- restart/replay invariants;
- preserve successful progress;
- operational lifecycle/recovery tests.

### HOW
Adapt lifecycle invariants to orchestrator-level health and durable mission recovery.

### WHERE
orchestrator lifecycle/recovery layer.

### MODE
`ADAPT`.

### DO_NOT_TAKE
agent-specific topology as metaO Core semantics.

### CURRENT_EVIDENCE_LEVEL
real control-plane/functional evidence from prior audit.

### FIT_TEST_REQUIRED
YES when first integrated.

---

## 7. Strategy state scaffolding

### SOURCE
Network-AI

### WHAT
- `SystemSnapshot`-style state snapshot;
- pool/status structures;
- budget/state structures;
- strategy lifecycle scaffolding;
- capability/adapter concepts where framework-neutral.

### HOW
Translate data structures into orchestrator-level state. Preserve structure, not agent-level semantics.

### WHERE
metaO strategy state.

### MODE
`ADAPT`.

### DO_NOT_TAKE
- `StrategyAgent` as metaO Core;
- agent-level topology semantics;
- framework integrations proven only through fake `.invoke()`, `.run()` or `.kickoff()` paths.

### CURRENT_EVIDENCE_LEVEL
real strategy code; external framework integration evidence includes `MOCK_ONLY` paths.

### FIT_TEST_REQUIRED
YES for any copied code.

---

## 8. Historical scoring

### SOURCE
ORCH

### WHAT
EMA/historical scoring using outcome, quality/accuracy, latency and cost signals.

### HOW
Extract the scoring algorithm and map signals to orchestrator history.

### WHERE
DeterministicScorer.

### MODE
`EXTRACT / ADAPT`.

### DO_NOT_TAKE
routing topology unrelated to orchestrator-level selection.

### CURRENT_EVIDENCE_LEVEL
published algorithm/benchmark evidence from prior audit.

### FIT_TEST_REQUIRED
YES — reproduce baseline and deterministic behavior locally.

---

## 9. Cost-quality routing methodology

### SOURCE
RouteLLM / RouterBench

### WHAT
- cost-quality tradeoff methodology;
- benchmark methodology;
- simple baseline comparisons.

### HOW
Use as methodology and algorithm reference; start with simple deterministic routing rather than complex learned routing.

### WHERE
strategy benchmark and scorer evaluation.

### MODE
`REFERENCE / ADAPT`.

### DO_NOT_TAKE
model-router assumptions as direct orchestrator semantics without fit evidence.

### CURRENT_EVIDENCE_LEVEL
published benchmark evidence.

### FIT_TEST_REQUIRED
YES for metaO-specific benchmark.

---

## 10. Replan/evaluate/escalate

### SOURCE
CADTopo

### WHAT
- evaluate;
- halt;
- replan;
- escalate patterns.

### HOW
Adapt algorithmic control flow to mission-level independent acceptance and orchestrator reselection.

### WHERE
replan/failover layer.

### MODE
`ALGORITHM DONOR / ADAPT`.

### DO_NOT_TAKE
domain-specific topology assumptions.

### CURRENT_EVIDENCE_LEVEL
algorithm/reference evidence from prior audit.

### FIT_TEST_REQUIRED
YES.

---

## 11. Future learned routing

### SOURCE
MAS-Orchestra

### WHAT
learned routing / reinforcement learning / adaptive topology concepts.

### MODE
`FUTURE REFERENCE ONLY`.

### WHERE
post-V1 research only.

### DO_NOT_TAKE
anything into V1 implementation.

### FIT_TEST_REQUIRED
not in V1.

---

## 12. Reliability/security references

### SOURCE
Temporal

### WHAT
Workflow/Activity separation, replay determinism, recovery/versioning invariants.

### MODE
`REFERENCE` unless Conductor fails Block D and Temporal becomes fallback candidate.

### DO_NOT_TAKE
Temporal-specific coupling into metaO Core.

### SOURCE
Dapr

### WHAT
identity, security, ACL, resiliency and operational-test scenarios.

### MODE
`REFERENCE` unless Conductor fails Block D and Dapr becomes fallback candidate.

### DO_NOT_TAKE
Dapr as mandatory infrastructure without the foundation fallback decision.

---

# Acceptance / Evidence / Trust Composition

## 13. A01 — executor DONE != accepted

SOURCE: `tihotm/oma`

WHAT: false-DONE prevention; separation between execution result and acceptance.

HOW: adapt OMA acceptance/terminal semantics into framework-neutral metaO acceptance authority.

WHERE: Acceptance layer.

MODE: `ADAPT / EXTRACT`.

DO_NOT_TAKE: Python-specific Core coupling or OMA as the durable foundation.

CURRENT_EVIDENCE_LEVEL: implementation + direct/integrated tests; prior CI evidence.

FIT_TEST_REQUIRED: YES in metaO terminal acceptance path.

## 14. A02 — independent verifier

SOURCE: OMA + Inspect AI + in-toto.

WHAT: independent verification boundary, scorer/verifier structure, authorized provenance/verification semantics.

HOW: orchestrator produces evidence; verifier is selected/authorized independently; verifier result is normalized into EvidenceEnvelope.

WHERE: VerifierPort / acceptance verification.

MODE: `ADAPT`.

DO_NOT_TAKE: evaluator framework as final authority.

CURRENT_EVIDENCE_LEVEL: donors identified; metaO composition not implemented.

FIT_TEST_REQUIRED: YES.

## 15. A03 — evidence binding

SOURCE: OMA.

WHAT: subject, subject-state, verification-context, policy-bundle and obligation binding.

HOW: extract semantics and tests; map to EvidenceEnvelope.

WHERE: acceptance hard gates.

MODE: `EXTRACT / ADAPT`.

DO_NOT_TAKE: untyped caller strings as final trust source where an authoritative registry exists.

CURRENT_EVIDENCE_LEVEL: implemented/tested in OMA.

FIT_TEST_REQUIRED: YES.

## 16. A04 — stale evidence

SOURCE: OMA trust/snapshot; Sigstore reference for hostile/distributed freshness/authenticity.

WHAT: epoch/state freshness, expiration, authoritative snapshot comparison.

MODE: `ADAPT`; `ADOPT/REFERENCE` standard attestation when hostile boundary requires it.

WHERE: acceptance hard gates.

DO_NOT_TAKE: hand-rolled cryptography.

CURRENT_EVIDENCE_LEVEL: local boundary strongly implemented in OMA; hostile boundary requires standard crypto.

FIT_TEST_REQUIRED: YES.

## 17. A05 — mutated state

SOURCE: OMA authoritative subject-state CAS/TOCTOU patterns.

WHAT: authoritative state re-read and terminal freshness protection.

HOW: preserve same-terminal-boundary source-of-truth semantics even if the storage implementation differs under metaO foundation.

WHERE: terminal acceptance boundary.

MODE: `ADAPT`.

DO_NOT_TAKE: caller-authored current state as final authority.

CURRENT_EVIDENCE_LEVEL: integrated/durable OMA evidence.

FIT_TEST_REQUIRED: YES.

## 18. A06 — provenance

SOURCE: OMA primary; in-toto and Sigstore supplementary.

WHAT: provenance DAG/root, verifier trust, evidence digest binding; signed attestation semantics when needed.

WHERE: EvidenceEnvelope and provenance gate.

MODE: `ADAPT / REFERENCE / ADOPT standard crypto`.

DO_NOT_TAKE: unrelated supply-chain framework as foundation.

CURRENT_EVIDENCE_LEVEL: OMA local provenance implemented/tested.

FIT_TEST_REQUIRED: YES.

## 19. A07 — authority

SOURCE: OMA authority/capability registry.

WHAT: authoritative capability source, delegation subset, no caller-fabricated root authority.

HOW: adapt registry/authority invariants to metaO governance store. For hostile/distributed root identity, use standard identity/attestation technology.

WHERE: global authority gate.

MODE: `ADAPT`.

DO_NOT_TAKE: caller issuer strings as authenticity proof; custom cryptography.

CURRENT_EVIDENCE_LEVEL: OMA local durable boundary implemented and adversarially tested.

FIT_TEST_REQUIRED: YES.

## 20. A08 — approval

SOURCE: Conductor durable HUMAN task; Inspect AI approval as secondary pattern.

WHAT: durable wait, approve/reject, resume and approver interaction pattern.

HOW: use foundation human-task mechanism as transport/state; metaO policy/authority still decides when approval is required and whether the approval is valid.

WHERE: approval/escalation adapter.

MODE: `ADOPT` foundation mechanism + `ADAPT` metaO evidence binding.

DO_NOT_TAKE: Conductor as final policy/acceptance authority.

CURRENT_EVIDENCE_LEVEL: donor capability identified; metaO L5 depends on Block D.

FIT_TEST_REQUIRED: YES after foundation confirmation.

## 21. A09 — policy evidence

SOURCE: OMA policy bundle/root; optional OPA decision-log patterns.

WHAT: policy identity/root binding and auditable decision evidence.

HOW: use OMA-style immutable policy binding; optionally adapt OPA decision logs if a policy engine is adopted later.

WHERE: policy gate and audit trail.

MODE: `ADAPT / OPTIONAL REFERENCE`.

DO_NOT_TAKE: mandatory OPA runtime dependency without later fit justification.

CURRENT_EVIDENCE_LEVEL: OMA policy binding implemented/tested.

FIT_TEST_REQUIRED: YES.

## 22. A10 — partial acceptance

SOURCE: OMA.

WHAT: `NOT_DONE` semantics and exact required-evidence/obligation denominator.

MODE: `EXTRACT / ADAPT`.

WHERE: acceptance decision model.

DO_NOT_TAKE: missing evidence as success.

CURRENT_EVIDENCE_LEVEL: implemented/tested.

FIT_TEST_REQUIRED: YES.

## 23. A11 — retry preservation

SOURCE: OMA durable SQLite retry ledger; AgentField recovery invariants supplementary.

WHAT: append-only retry/cost history, omitted-history attack prevention, lineage binding, preserve valid progress.

HOW: preserve source-of-truth semantics; storage may be adapted to the chosen durable foundation.

WHERE: retry/recovery gate.

MODE: `ADAPT`.

DO_NOT_TAKE: caller-supplied retry tuple as terminal authority.

CURRENT_EVIDENCE_LEVEL: OMA durable attack found/fixed; whole-suite evidence recorded.

FIT_TEST_REQUIRED: YES with real foundation/runtime path.

## 24. A12 — cross-orchestrator evidence

SOURCE: metaO-specific contract + donor evidence structures above.

WHAT: normalize LangGraph/CrewAI/OpenAI Agents/other results into one EvidenceEnvelope.

HOW: thin adapters map orchestrator output to the frozen Acceptance Contract; no framework SDK types cross into Core.

WHERE: OrchestratorAdapter -> EvidenceEnvelope.

MODE: `BUILD MINIMUM METAO-SPECIFIC NORMALIZATION` using donor structures/invariants.

DO_NOT_TAKE: framework-specific result models as Core contracts.

CURRENT_EVIDENCE_LEVEL: CONTRACT_FROZEN; implementation proof deferred to multi-orchestrator block.

FIT_TEST_REQUIRED: YES with at least two real orchestrators.

## 25. A13 — conflicting evidence

SOURCE: OMA aggregation/exact evidence-set semantics.

WHAT: duplicate/unexpected/conflicting evidence handling and deterministic aggregation root.

MODE: `EXTRACT / ADAPT`.

WHERE: evidence aggregation gate.

DO_NOT_TAKE: best-of-N cherry-picking unless explicitly authorized by aggregation policy.

CURRENT_EVIDENCE_LEVEL: implemented/tested in OMA.

FIT_TEST_REQUIRED: YES.

## 26. A14 — confidence

SOURCE: Inspect AI scorer/evaluator patterns; optional DeepEval/Promptfoo only if later fit audit is needed.

WHAT: score/reason/confidence structures and evaluator separation.

HOW: adapt scoring output into EvidenceEnvelope after all hard gates; confidence only controls additional verification/escalation.

WHERE: verifier/scoring layer.

MODE: `EXTRACT / ADAPT`.

DO_NOT_TAKE: confidence as authorization or hard-gate bypass.

CURRENT_EVIDENCE_LEVEL: donor identified; not implemented in OMA/metaO.

FIT_TEST_REQUIRED: YES.

## 27. A15 — human escalation

SOURCE: Conductor durable HUMAN task + Inspect AI approval/escalation patterns.

WHAT: durable wait/resume plus human decision UX/semantics.

HOW: foundation owns waiting; metaO owns trigger, authority, evidence binding and final decision.

WHERE: escalation layer.

MODE: `ADOPT / ADAPT`.

DO_NOT_TAKE: in-memory-only callback as sole approval state.

CURRENT_EVIDENCE_LEVEL: donor identified; depends on foundation L5.

FIT_TEST_REQUIRED: YES.

## 28. A16 — auditability

SOURCE: OMA validation closure/evidence roots; optional Sigstore/Rekor/in-toto/OPA audit patterns where threat model justifies them.

WHAT: deterministic validation closure, durable proof roots and decision reasoning.

HOW: preserve enough durable information to reconstruct every final decision.

WHERE: audit trail/terminal record.

MODE: `ADAPT`; optional `ADOPT` of standard transparency/attestation components.

DO_NOT_TAKE: claims of cryptographic non-repudiation without actual standard signatures/transparency proof.

CURRENT_EVIDENCE_LEVEL: strong local OMA evidence.

FIT_TEST_REQUIRED: YES.

## 29. A17 — deterministic acceptance

SOURCE: OMA validation graph/closure semantics.

WHAT: deterministic final decision over fixed evidence/policy/state.

MODE: `EXTRACT / ADAPT`.

WHERE: final acceptance evaluator.

DO_NOT_TAKE: probabilistic model output directly as final authority.

CURRENT_EVIDENCE_LEVEL: implemented/tested in OMA.

FIT_TEST_REQUIRED: YES, repeated-run determinism test.

## 30. A18 — acceptance cost

SOURCE: Inspect AI limit/usage/accounting patterns.

WHAT: monetary, token, wall-clock and attempt limits for verification itself.

HOW: adapt usage counters/limit patterns into metaO `AcceptanceBudget` bound to mission/execution and policy.

WHERE: acceptance budget hard gate.

MODE: `EXTRACT / ADAPT`.

DO_NOT_TAKE: Inspect AI task runtime as metaO foundation.

CURRENT_EVIDENCE_LEVEL: donor capability exists; metaO acceptance-budget composition not implemented.

FIT_TEST_REQUIRED: YES.

## 31. A19 — adversarial executor

SOURCE: OMA adversarial audit/regression patterns; standard attestation donors for hostile boundary.

WHAT: false-DONE, stale/substituted evidence, fabricated authority, retry omission, replay/duplicate and provenance attacks.

HOW: port adversarial test patterns and ensure every attack traverses the real metaO acceptance path.

WHERE: acceptance/security test suite.

MODE: `ADAPT`.

DO_NOT_TAKE: mock-only proof for hostile boundary claims.

CURRENT_EVIDENCE_LEVEL: strong OMA local supported-boundary evidence.

FIT_TEST_REQUIRED: YES.

## 32. A20 — final acceptance authority

SOURCE: OMA invariant + metaO-specific architecture.

WHAT: only metaO can issue final accepted state.

HOW: compose OMA acceptance invariants behind a framework-neutral metaO terminal authority; orchestrators only return execution results/evidence.

WHERE: metaO Core AcceptanceAuthority.

MODE: `ADAPT` + minimal `BUILD` of metaO-specific orchestration boundary.

DO_NOT_TAKE: orchestrator/framework `SUCCESS` as final acceptance.

CURRENT_EVIDENCE_LEVEL: CONTRACT_FROZEN; implementation proof later.

FIT_TEST_REQUIRED: YES.

---

# 33. Explicit metaO-specific BUILD items

The following BUILD items are approved because they are the abstraction that distinguishes metaO from its donors. They MUST still reuse donor data structures, algorithms and tests where applicable.

1. framework-neutral `OrchestratorContract` boundary;
2. framework-neutral `EvidenceEnvelope` normalization;
3. composition that makes metaO the final acceptance authority across orchestrators;
4. orchestrator-level eligibility/scoring composition where no single donor already provides the whole meta-strategy.

`BUILD_ITEMS_WITHOUT_DONOR = NONE` in the sense of greenfield capability invention: every approved BUILD item has donor invariants/structures/algorithms to reuse, but the cross-donor metaO boundary itself is necessarily project-specific.

## 34. Prohibited composition

The following are forbidden without a new architecture decision:

```text
metaO Core imports LangGraph/CrewAI/OpenAI Agents SDKs
Conductor owns global metaO policy
Conductor owns final acceptance
score/confidence bypasses hard gates
caller state/history/authority is terminal source of truth when an authoritative source exists
Network-AI mock-only framework tests are treated as real integration
custom cryptographic signature scheme is written inside metaO
MAS-Orchestra learned routing enters V1
whole donor repositories are copied when only small invariant units are needed
```

## 35. Implementation measurement contract

For every consumed donor unit, implementation work MUST record:

```text
DONOR_REPO
DONOR_COMMIT
DONOR_PATH

REUSED_LOC
ADAPTED_LOC
NEW_METAO_LOC

DONOR_TESTS_REUSED
DONOR_TESTS_EXECUTED
METAO_TESTS_NEW

DEPENDENCIES_ADDED
ADAPTER_LOC

INTEGRATION_TIME
FAILED_FIT_TESTS

IMPLEMENTATION_LEVEL
MOCK_ONLY

FINAL_DECISION
```

No reuse percentage may be published before these measurements exist.

## 36. Freeze gate

Block C is considered structurally complete only when:

```text
ACCEPTANCE_CONTRACT = FROZEN
COMPOSITION_MAP = FROZEN
A01_A20_MAPPED = YES
UNRESOLVED_ARCHITECTURAL_GAPS = 0
ORCHESTRATOR_SPECIFIC_SDK_IN_CORE_PLAN = NO
HAND_ROLLED_CRYPTO_PLANNED = NO
```

Next block after this freeze:

```text
D — CONDUCTOR FOUNDATION FIT TEST L5
```

Conductor remains `PRIMARY FOUNDATION CANDIDATE` until that L5 test passes in the metaO environment.
