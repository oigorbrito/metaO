# OMA + OMA7 Donor Composition for metaO

Status: PROPOSED canonical addendum under Issue #151
Audit date: 2026-08-26

This document records the maximum relevant reuse of OMA and OMA7 in metaO while preserving the frozen meta-orchestrator boundary: metaO governs whole orchestrators and mission outcomes; it does not absorb coding-agent or framework-specific topology into Core.

## 1. Frozen audit pins

```text
OMA  = tihotm/oma@ca43381dc8bce4041da4fc09efbe939642729939
OMA7 = tihotm/oma-experiment@a92e0dbb31652ccaf7f3d8168f47df92af72bc7f
```

Every implementation Work Unit MUST re-pin the exact donor paths and tests actually consumed.

## 2. Donor roles

```text
OMA  = trust / authority / acceptance / terminal-closure donor
OMA7 = execution-identity / supervision / accounting / preflight / experiment-harness donor
```

Neither donor becomes:

- the metaO foundation;
- a mandatory orchestrator runtime;
- a replacement for Conductor;
- a whole-package Core dependency.

## 3. Cross-donor division of responsibility

```text
OMA
  -> authoritative trust and terminal acceptance invariants

SMAG
  -> governance, risk, execution-budget, failure causality,
     deterministic reporting and engineering harness

OMA7
  -> execution/materialization identity, supervision state,
     accounting, runtime admission/preflight and invariant registry
```

The goal is composition by strongest proven capability, not duplication by donor.

## 4. OMA — maximum relevant reuse

OMA is already substantially mapped into Roadmap 8. Primary reuse targets are:

| Capability | Decision | metaO boundary |
|---|---|---|
| executor DONE != accepted | ADAPT | terminal acceptance |
| composed fail-closed validation | ADAPT | acceptance pipeline |
| authoritative subject state / TOCTOU | ADAPT | terminal freshness |
| capability/authority registry | ADAPT | authority source of truth |
| delegation subset rules | ADAPT | approval/authority |
| immutable policy roots/bundles | ADAPT | policy evidence |
| provenance binding | ADAPT | EvidenceEnvelope / trust |
| obligation binding | ADAPT | acceptance obligations |
| deterministic aggregation | ADAPT | evidence aggregation |
| durable retry/cost history | ADAPT | A11 RetryHistoryPort |
| omitted-history attack closure | TEST-DONOR | adversarial retry tests |
| validation closure/root | ADAPT | terminal proof |
| authoritative terminal re-read | ADAPT | same-terminal-boundary source of truth |
| CAS / competing writer semantics | TEST-DONOR | durable terminal concurrency |
| trust-artifact negative tests | TEST-DONOR | hostile authenticity boundary |
| local-root != cryptographic authenticity | ADOPT semantic rule | security/trust |

### 4.1 Existing Roadmap 8 destinations

Do not create duplicate OMA authorities. Current destinations include:

- #94 — A02 independent verifier fit;
- #96 — A05/A07/A09 authoritative terminal sources;
- #98 — A11 authoritative retry history;
- #100 — A16/A19 terminal proof + adversarial closure;
- #113 — A08/A04/A06 approval authority + hostile provenance;
- #119 — A08 approver authority/freshness primitives.

### 4.2 OMA invariants to preserve

```text
CALLER_CONTEXT != FINAL_SOURCE_OF_TRUTH
CALLER_RETRY_HISTORY != FACTUAL_HISTORY_AUTHORITY
KNOWN_ROOT_STRING != CRYPTOGRAPHIC_AUTHENTICITY
LOCAL_HASH_ROOT != HOSTILE_IDENTITY_PROOF
EXECUTOR_DONE != METAO_ACCEPTED
```

### 4.3 OMA items that must not be copied wholesale

- SQLite implementation as a second durability foundation;
- Python-specific Core types;
- custom cryptography;
- caller-authored identity/authority strings as trust proof;
- OMA's internal storage layout where existing metaO ports/stores can carry the same invariant.

## 5. OMA7 — identity model

OMA7 separates:

```text
SubjectIdentity
MaterializationIdentity
ExecutionContextIdentity
VerificationContextIdentity
ScopePolicyIdentity
ProvenanceAnchorIdentity
MissionIdentity
```

High-value invariant:

```text
logical subject
!= materialized runtime instance
!= execution context
!= verification context
!= scope policy
!= provenance anchor
```

Evidence applicable to one identity combination must not silently authorize a materially different combination.

### 5.1 Required fit decisions

Tracked by #152.

Each identity must be classified as one of:

```text
ADAPT_TO_CORE
ADAPT_TO_ADAPTER_OR_CERTIFICATION
REFERENCE_ONLY
PLUGIN_ONLY
REJECT
```

OMA7's current coding-specific execution fields (Codex binary, model, reasoning level, Docker image, dataset/harness fields) MUST NOT become universal metaO Core requirements.

## 6. OMA7 — supervisor/control record

Relevant donor concepts:

- `SupervisorState`;
- `FailureClassification`;
- `EscalationReason`;
- `RetryBudget`;
- `BudgetState`;
- `ControlPolicyIdentity`;
- `AttemptIdentity` and parent/superseded lineage;
- stale-writer/CAS protection for durable control records.

Composition:

```text
#140 Risk + ExecutionBudget
  <- OMA7 budget/accounting invariants

#141 failure/retry/recovery/failover
  <- OMA7 supervisor states, failure classes, attempt lineage, CAS

A11 authoritative retry history
  <- OMA remains history authority

Conductor
  <- remains durable execution mechanism
```

No second retry engine or durable control-record store is authorized merely to reuse OMA7 semantics.

## 7. OMA7 — accounting

OMA7 distinguishes factual events for:

```text
EXECUTION
VERIFICATION
HUMAN_APPROVAL
HUMAN_ESCALATION
HUMAN_OVERRIDE
HUMAN_INTERVENTION
```

Reuse targets:

- monotonic append-only event indexing;
- execution vs verification cost distinction;
- human intervention as first-class factual provenance;
- evidence references from accounting entries;
- deterministic ledger head and event count;
- stale-write rejection;
- idempotent duplicate handling;
- fail-closed malformed/schema-mismatched reads.

Tracked by #153.

Target composition:

```text
Mission accounting
├── Execution accounting / ExecutionBudget   -> #140
├── Verification accounting / A18            -> Roadmap 8
└── Human intervention provenance             -> Evidence/EventLedger
```

Do not create a mandatory OMA7 filesystem ledger. Existing metaO durable stores remain preferred.

## 8. OMA7 — evidence ledger and post-execution facts

Reuse targets:

- append-only evidence event indexing;
- evidence deduplication/idempotency;
- strict schema/version validation;
- evidence identity binding;
- binding cost-ledger head/count into evidence;
- human-intervention summary binding;
- post-execution records as factual append-only events.

Composition rule:

```text
metaO EvidenceEnvelope/EventLedger = canonical authority
OMA7 ledger code                  = donor semantics/tests
```

A post-execution record must never rewrite the original execution outcome or terminal acceptance history.

## 9. OMA7 — runtime admission / host capability / preflight

Tracked by #154 and used as a secondary donor in #145/#149.

Reuse targets:

- explicit `SUPPORTED` / `BLOCKED` capability state;
- structured blockers;
- explicit capability-source resolution rather than assuming PATH discovery proves readiness;
- immutable runtime/config pins;
- execution-context identity derived from pins;
- dry-run plan before dispatch;
- execution-plan identity;
- production preflight;
- execution-context mismatch -> BLOCK;
- readiness checks that do not consume attempts or budget;
- sandbox facts for mount/workdir/network/ephemeral-home where applicable.

Generic boundary:

```text
Runtime/Adapter facts
-> Runtime Admission / Certification
-> Policy / Risk
-> dispatch only if requirements satisfied
```

A runtime's self-declared capability is evidence to verify, never final certification authority.

## 10. OMA7 — engineering/scientific harness

Tracked by #155 and composed into #143.

Adopt/reference:

```text
DOCUMENTED
CODE_CONFIRMED
TEST_CONFIRMED
EXECUTED
MEASURED
```

These levels MUST NOT be conflated.

Additional reuse targets:

- canonical 1:1 invariant registry;
- per-invariant CODE_STATUS / TEST_STATUS / EXECUTION_STATUS;
- factual CURRENT-STATE discipline;
- baseline HEAD;
- excluded scope;
- promoted claims and open claims;
- real-execution counters remain zero until execution exists;
- release readiness derived from facts;
- no measured product-advantage claim without causal evidence;
- engineering order `ADOPT > COMPOSE > ADAPT > BUILD`.

### 10.1 Document-drift regression donor

At audit pin `a92e0db...`, OMA7's `docs/CURRENT-STATE.md` still contains an older recorded `HEAD = 8c870ca`.

Use this as a real regression case for metaO document-drift detection:

```text
RECORDED_HEAD != REPOSITORY_FACT
-> drift warning/failure
-> never silently promote CURRENT-STATE as factual
```

## 11. OMA7 — engineering workload only

The following remain behind #144 specialized engineering-workload plugin:

- SWE-bench adapters and benchmark semantics;
- Git-backed coding workspace/materialization details;
- Codex CLI/auth handling;
- Docker lifecycle;
- coding workspace path/scope policies;
- filesystem traversal/symlink/write probes.

They may be highly reusable for coding missions without becoming generic Core concepts.

## 12. Cross-donor composition matrix

| metaO capability | Primary donor | Secondary donor(s) | Destination |
|---|---|---|---|
| terminal acceptance | OMA | Inspect AI / in-toto | Roadmap 8 |
| authority/freshness | OMA | standards providers | #96/#113/#119 |
| retry factual history | OMA | OMA7/SMAG semantics | #98/#141 |
| Risk Governance | SMAG | OMA7 failure/control taxonomy | #140 |
| ExecutionBudget | SMAG | OMA7 accounting/budget state | #140 |
| failure causality | SMAG | OMA7 supervisor/lineage | #141 |
| execution-stage evidence | SMAG | OMA7 ledger semantics / OMA closure | #142 |
| engineering harness | SMAG | OMA7 invariant/scientific harness | #143/#155 |
| engineering workload plugin | WUS/SMAG | OMA7/OpenHands/Codex/Cline | #144 |
| runtime conformance | runtime donors | OMA7 preflight/host facts | #145/#154 |
| security/isolation | SMAG | OMA7 preflight | #149 |
| execution/verification identity | OMA7 | OMA trust binding | #152 |
| accounting/evidence ledger semantics | OMA7 | OMA/SMAG | #153 |

## 13. Core exclusions

Do not take into generic metaO Core:

- coding-agent topology;
- Codex-specific fields;
- SWE-bench semantics as universal acceptance;
- Docker implementation details;
- Git/worktree assumptions for non-engineering workloads;
- OMA SQLite as a second foundation;
- OMA7 filesystem ledgers as mandatory production stores;
- framework/provider SDK types;
- runtime self-reports as authority;
- caller-authored capability/provenance claims as final truth;
- custom cryptography.

## 14. Work Units

Master tracking:

- #151 — OMA + OMA7 donor delta audit.

Unique OMA7 delta:

- #152 — canonical execution/materialization/verification identity model;
- #153 — accounting and evidence ledger composition;
- #154 — runtime admission, host capability and sandbox preflight;
- #155 — invariant registry, evidence levels and release-readiness harness.

Existing Work Units updated to consume OMA7 as a secondary donor:

- #140 — Risk + ExecutionBudget;
- #141 — failure causality/recovery/retry/failover;
- #142 — execution-stage evidence/reporting;
- #143 — engineering harness;
- #144 — engineering-workload plugin;
- #145 — runtime conformance;
- #149 — security/isolation.

SMAG master coordination: #138.

## 15. Recommended order

```text
Roadmap 8 OMA-derived trust/acceptance work continues by existing dependencies

#152 identity fit
-> #153 accounting/evidence fit
-> #154 runtime admission/preflight fit
-> #155 harness fit

In parallel, existing #140/#141/#142/#143/#149 may consume OMA7
secondary-donor tests/semantics when their ordered implementation reaches those slices.

#144/#145 expand only when fit/conformance justifies them.
```

## 16. Evidence policy

```text
DONOR_EXISTS != FIT_PROVEN
DOCUMENTED != IMPLEMENTED
TEST_CONFIRMED != EXECUTED
EXECUTED != ACCEPTED
LOCAL_HASH != CRYPTOGRAPHIC_AUTHENTICITY
RUNTIME_READY != RUNTIME_EXECUTED
POST_EXECUTION_RECORD != RETROACTIVE_SUCCESS
```

For every actual reuse Work Unit, record:

- donor repo;
- exact commit;
- exact path(s);
- reused/adapted test(s);
- decision mode;
- boundary/authority owner;
- reused/adapted/new LOC when practical;
- executable evidence level.

## 17. Architecture invariant

The final architecture remains:

```text
Mission
-> Strategy / Selection
-> Policy / Budget / Risk
-> OrchestratorContract
-> Runtime Admission / Adapter
-> real orchestrator
-> Evidence
-> Independent Acceptance
-> Accept / Replan / Failover / Block
```

OMA, SMAG and OMA7 strengthen this pipeline. None of them changes the strategic unit from whole orchestrator/workload to internal agent topology.
