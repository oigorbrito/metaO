# Post-MVP Maturity Test Plan V1

Status: canonical execution plan for issue #357.

This plan governs promotion from provider-neutral contracts and local deterministic evidence to operational claims. It does not itself promote any capability. A capability may be claimed only at the highest evidence level actually executed for that capability.

## Evidence levels

- L0 — design/specification only.
- L1 — deterministic unit/contract tests.
- L2 — composed local integration using real project code and deterministic local doubles/fixtures.
- L3 — fault-injection / multiprocess / restart / fencing evidence.
- L4 — real runtime or real external protocol boundary without paid/provider-success semantics.
- L5 — real provider-backed success/failure execution with authorized credentials and cost boundary.
- L6 — hosted/remote operational execution, including remote Git/CI/reconciliation where applicable.
- L7 — measured operational/SLO evidence with causal attribution.

No L5+ claim may be inferred from L1-L4 evidence. `NOT_TESTED` is not `PASS`.

## Current evidence baseline

| Block | Current state | Highest executed evidence | Canonical owner | Remaining boundary |
| --- | --- | --- | --- | --- |
| Dynamic executor supervision kernel | Partial | deterministic/local composed | #351 | real provider/runtime reconciliation and project-level E2E |
| Executor market scout / qualification | Local slice resolved | L1 | #354 | live discovery and credentialed/provider-backed qualification |
| Engineering knowledge authority | Public API qualified | L1 + full Rust workspace regression | #355 | live refresh pipeline / authorized source update operations |
| Two real orchestrator runtimes | Proven | L4 | #448 | provider-backed model success was intentionally excluded |
| Real-runtime adapter wave | Partial | L4 | #359 | provider-backed success and real cross-provider handoff/failover |
| Project-level supervision | Partial | L2/L3 local composed | #360 | real providers, remote Git, hosted CI, complete operational E2E |
| Multiprocess fencing | Proven local | L3 | #449 / #168 matrix | hosted/operational evidence if stronger claim required |
| Durable external-effect dedup | Proven local | L3 | #449 / #168 matrix | real product-effect boundary for L7 product-effect claims |
| WorkGraph authority | Resolved fixture | L1/L2 | #362 | production scheduler/durability not implied |
| Workload identity | Partial | L1 | #159 | real SPIFFE/SPIRE attestation |
| Credential lease lifecycle | Partial | L1 | #165 | real broker issue/renew/revoke lifecycle |
| Hosted GitHub Actions | Blocked external | infrastructure only | #71 | account/runner allocation must permit steps to execute |

## Dependency-driven execution sequence

### M1 — Consolidate local authority and supervision evidence

**End-state:** every locally implemented authority boundary is consumed through canonical public APIs and participates in composed project-level tests without private-path bypasses.

**Why:** local integration must be internally coherent before adding provider credentials or hosted infrastructure.

**Engineering basis:** fail-closed authority separation, exact contract binding, independent acceptance, deterministic reproduction.

**Required evidence:** L1-L3 depending on subsystem.

**Executable in:** ChatGPT/GitHub plus authorized local executor for Rust/Python qualification.

**Exact gates:** focused lint/tests for each touched component; related composed test; full locked Rust workspace or full Python unit suite; exact HEAD; clean worktree.

**Exit criteria:** no identified local-only gap remains in #351/#354/#355/#360 that can be closed without crossing a real-provider/remote-infrastructure boundary.

**Current status:** substantially complete. #354 and #355 are resolved. #360 now has a local composed precursor but remains open for the real operational slice.

### M2 — Real provider-backed adapter success

**End-state:** at least two adapters execute successful provider-backed work with valid authorized credentials, while preserving canonical failure normalization, cancellation/intervention and evidence capture.

**Why:** credential-free live-auth and real-binary smoke tests prove protocol boundaries but not successful provider work.

**Engineering basis:** same adapter contract must normalize auth, quota/rate, success, failure and unknown states without provider-specific authority leakage.

**Required evidence:** L5.

**Dependencies:** #359; explicit authorization for valid provider credentials and spending/cost boundaries.

**Executable in:** authorized local/external executor with provider credentials. Not safely completable from GitHub mutation alone.

**Exact tests:** one provider-backed success per selected provider; canonical failure mapping; cancellation/intervention; evidence capture; unknown failure fail-closed.

**Exit criteria:** two or more real providers produce comparable successful execution facts through production adapters.

**Blocked/external:** valid credentials, provider availability, explicit cost authorization.

### M3 — Real cross-provider handoff and failover

**End-state:** work starts on one real provider/runtime, a forced quota/outage/capacity condition is observed, state is checkpointed, a second provider resumes the bounded work, and stale/late owner actions cannot corrupt the accepted result.

**Why:** multi-provider support is not proven until ownership transfer works under failure.

**Engineering basis:** fencing, checkpoint durability, failure causality, retry eligibility, idempotent external effects, exact project/spec binding.

**Required evidence:** L5, with L3 controls reused as invariants.

**Dependencies:** M2, #351, #359, #360.

**Executable in:** authorized local/external executor with two provider boundaries.

**Exact tests:** forced quota/outage; checkpoint; provider handoff; stale-owner rejection; no duplicate external effect; independent acceptance after recovery.

**Exit criteria:** real cross-provider failover PASS with complete lineage.

### M4 — Remote Git and hosted CI reconciliation

**End-state:** metaO supervises local Git, remote Git and CI state as distinct facts, reconciles divergence, and does not treat a push/PR/CI request as equivalent to observed completion.

**Why:** project supervision requires authoritative external observations, not caller declarations.

**Engineering basis:** exact SHA/tree binding, remote observation, CI result provenance, last-known-good semantics.

**Required evidence:** L6.

**Dependencies:** #363 GitHub adapter boundary, #360, hosted runner availability (#71 for GitHub-hosted Actions if that substrate is used).

**Executable in:** connected GitHub plus an environment where CI jobs actually start.

**Exact tests:** create/update branch on disposable repo; observe remote SHA; dispatch CI; confirm steps actually execute; introduce divergence/failure; reconcile; accept only exact verified tree.

**Exit criteria:** remote Git + CI state appears in project traceability and independently influences acceptance.

**Blocked/external:** #71 remains an infrastructure/account/runner-allocation blocker for hosted Actions until steps execute.

### M5 — Engineering knowledge refresh operations

**End-state:** authorized technical sources are refreshed on an auditable cadence; stale evidence requires refresh; stronger/current evidence can challenge project documentation; user override preserves adverse evidence and cannot override hard policy/safety constraints.

**Why:** #355 proves the decision contract, not the live refresh pipeline.

**Engineering basis:** provenance, freshness, confidence, source authorization and conflict resolution.

**Required evidence:** L2 for deterministic refresh orchestration; L4/L5 where real external source retrieval is claimed.

**Dependencies:** #355.

**Executable in:** local deterministic source fixture first; real source retrieval later with user-authorized network sources.

**Exact tests:** stale source -> REQUIRE_REFRESH; update cadence recorded; changed authoritative source alters decision; failed refresh does not silently preserve a stronger claim; override history remains auditable.

**Exit criteria:** refresh/reconciliation path is executable rather than only modeled.

### M6 — Identity and credential lifecycle

**End-state:** externally attested workload identity gates real credential issue/renew/revoke; failover cannot reuse expired/revoked leases; unknown revocation state fails closed.

**Why:** local contracts cannot substitute for real attestation/broker behavior.

**Engineering basis:** identity provenance, least privilege, short-lived leases, revocation, no secret material in canonical facts.

**Required evidence:** L5/L6 depending on substrate.

**Dependencies:** #159, #165, provider/runtime integration.

**Executable in:** environment with authorized SPIFFE/SPIRE or equivalent attestation and a real credential broker.

**Exact tests:** attestation success/failure; issue; renew; revoke; failover reuse rejection; stale identity; broker outage; unknown revocation fail-closed.

**Exit criteria:** one complete real lifecycle PASS with secret material excluded from evidence records.

### M7 — Scientific composed validation and chaos

**End-state:** the scientific matrix in #168 contains reproducible composed evidence for restart, failover, stale owner, duplicate-effect pressure and real orchestrator/provider boundaries, with simulation vs real marked machine-readably.

**Why:** HA/resilience claims require injected faults and observed recovery, not happy-path integration.

**Engineering basis:** causal fault injection, fencing, durable effects, exact evidence basis.

**Required evidence:** L3-L6 depending on claim.

**Dependencies:** M2-M6 as applicable.

**Executable in:** local multiprocess harness for L3; authorized real environments for L5-L6.

**Exact tests:** restart at controlled cut points; late owner; lost acknowledgement; duplicate effect; transient vs terminal failure; provider outage; remote reconciliation.

**Exit criteria:** #168 acceptance matrix is satisfied at each claimed level without promoting simulated evidence as real.

### M8 — Operational SLO and final post-MVP closure

**End-state:** operational trials produce measured availability/recovery/cost/latency evidence and project acceptance remains independently verifiable under realistic load and faults.

**Why:** production maturity is an observed property over time, not a one-shot E2E.

**Engineering basis:** SLOs, causal telemetry, evidence retention, incident/recovery traceability.

**Required evidence:** L7.

**Dependencies:** M2-M7.

**Executable in:** authorized operational environment.

**Exact tests/measurements:** success rate, recovery time, duplicate-effect rate, failover success, cost variance, evidence completeness, acceptance false-positive/false-negative investigation.

**Exit criteria:** published measured thresholds are met over a defined trial window and every product-level claim maps to L7 evidence where required.

## Stop criteria

Stop promotion and leave the owning issue open when any of the following applies:

1. the next proof requires credentials, spending, hosted infrastructure or external administrative action that is not explicitly authorized;
2. a hosted job fails before configured steps execute;
3. the executed gate is lower than the claim being proposed;
4. evidence is caller-declared where independent observation is required;
5. exact commit/tree/spec binding cannot be established;
6. an unresolved hard policy/safety constraint exists;
7. simulated/deterministic evidence is the only evidence available for a real-provider or operational claim.

## Canonical ownership

- #357 owns this maturity plan.
- #356 is duplicate and must remain closed as duplicate.
- #360 owns project-level operational E2E and remains open until real provider/remote Git/CI requirements are satisfied.
- #359 owns provider-backed adapter success and real cross-provider handoff.
- #159 and #165 own real identity and credential lifecycle boundaries.
- #168 owns the scientific validation matrix.
- #71 owns the hosted-runner infrastructure blocker.

This document is a planning/evidence artifact. It does not convert any `PARTIAL`, `BLOCKED`, `NOT_TESTED` or local-only result into a stronger product claim.
