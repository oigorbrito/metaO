# metaO Closure Plan

Status: NORMATIVE_FOR_PROJECT
Baseline version: V1
Applies to: repository `tihotm/metaO`
Last reconciled commit: `19152a5451a55bdf354b14d4ac88f08f0c335187`

This is the master closure plan for the post-MVP baseline. It replaces issue-by-issue ping-pong as the primary planning view.

## Block A - Documentation and requirements baseline

- OBJECTIVE: establish canonical authority, baseline, and traceability documents.
- ISSUES: #274, #245, #227, #70.
- PRS: existing doc/reconciliation PRs only where still relevant.
- DEPENDENCIES: current repo truth and issue reconciliation.
- ENTRY_CRITERIA: baseline and authority docs created.
- IMPLEMENTATION_WORK: create canonical docs, classify history, link baseline.
- TESTS: link checks, markdown sanity.
- EVIDENCE: updated docs and exact commit binding.
- EXIT_CRITERIA: one authoritative baseline view exists.
- WHAT_CAN_RUN_IN_PARALLEL: history classification and traceability drafting.
- WHAT_MUST_REMAIN_OPEN: external CI blocker.
- EXTERNAL_BLOCKERS: hosted GitHub Actions, unavailable external evidence files.

## Block B - Collective Rust integration and wiring

- OBJECTIVE: keep the Rust-native product direction coherent while preserving current repository reality.
- ISSUES: #228, #271, #90, #91.
- PRS: canonical integration and parity PRs.
- DEPENDENCIES: architecture baseline and acceptance contract.
- ENTRY_CRITERIA: Core and acceptance boundaries are frozen.
- IMPLEMENTATION_WORK: preserve adapter neutrality, wiring boundaries, and acceptance semantics.
- TESTS: unit, regression, integration, release gate.
- EVIDENCE: exact-head tests and release evidence.
- EXIT_CRITERIA: Core remains stable across wiring changes.
- WHAT_CAN_RUN_IN_PARALLEL: documentation and verification work.
- WHAT_MUST_REMAIN_OPEN: gaps that still need dedicated runtime or hostile evidence.
- EXTERNAL_BLOCKERS: provider/runtime availability.

## Block C - Project Discovery composition

- OBJECTIVE: resolve Project Discovery foundations and completion semantics.
- ISSUES: #171, #172, #173, #174, #175, #176, #177.
- PRS: discovery and completion flow PRs.
- DEPENDENCIES: architecture baseline, governance, and budget rules.
- ENTRY_CRITERIA: discovery scope is distinct from closure scope.
- IMPLEMENTATION_WORK: project contract, state machine, completion gate.
- TESTS: focused and integration tests for discovery flow.
- EVIDENCE: end-to-end project discovery behavior.
- EXIT_CRITERIA: discovery flow is operationally understood and wired.
- WHAT_CAN_RUN_IN_PARALLEL: docs baseline and capability mapping.
- WHAT_MUST_REMAIN_OPEN: future product expansion beyond discovery.
- EXTERNAL_BLOCKERS: none beyond current repo truth.

## Block D - Core control-plane integration

- OBJECTIVE: keep selection, policy, budget, runtime control, and evidence cohesive.
- ISSUES: #140, #142, #158, #160, #166.
- PRS: control-plane wiring and policy PRs.
- DEPENDENCIES: Project Discovery and architecture baseline.
- ENTRY_CRITERIA: governance vocabulary and runtime admission surfaces are stable.
- IMPLEMENTATION_WORK: budget enforcement, runtime health, admission, evidence flow.
- TESTS: block G/H/J style unit and integration coverage.
- EVIDENCE: repository truth and release evidence.
- EXIT_CRITERIA: control-plane path is coherent.
- WHAT_CAN_RUN_IN_PARALLEL: runtime diversity work.
- WHAT_MUST_REMAIN_OPEN: anything requiring external systems.
- EXTERNAL_BLOCKERS: hosted CI, external runtime availability.

## Block E - Two-runtime architecture proof

- OBJECTIVE: prove the same Core path can accept materially different runtimes.
- ISSUES: #163, #206, #204.
- PRS: adapter and runtime proof PRs.
- DEPENDENCIES: adapter-neutral contract.
- ENTRY_CRITERIA: at least two distinct runtimes are wired.
- IMPLEMENTATION_WORK: adapter fit, runtime normalization, compare behavior.
- TESTS: regression and integration runtime tests.
- EVIDENCE: runtime-specific slices with shared Core boundary.
- EXIT_CRITERIA: runtime replaceability is evidenced.
- WHAT_CAN_RUN_IN_PARALLEL: discovery and governance docs.
- WHAT_MUST_REMAIN_OPEN: real external provider claims not yet evidenced.
- EXTERNAL_BLOCKERS: provider/account policy.

## Block F - Durable execution, restart, failover, fencing

- OBJECTIVE: preserve progress across failure while rejecting stale ownership.
- ISSUES: #141, #160, #164.
- PRS: runtime invariants and recovery PRs.
- DEPENDENCIES: durable state and runtime control.
- ENTRY_CRITERIA: replay and recovery primitives exist.
- IMPLEMENTATION_WORK: leasing, stale-worker rejection, recovery snapshotting.
- TESTS: runtime invariant and failover tests.
- EVIDENCE: durable restart and failover behavior.
- EXIT_CRITERIA: stale ownership is rejected and progress is preserved.
- WHAT_CAN_RUN_IN_PARALLEL: security boundary work.
- WHAT_MUST_REMAIN_OPEN: distributed multi-host recovery.
- EXTERNAL_BLOCKERS: none required for local evidence.

## Block G - Security, workload identity, credential lifecycle

- OBJECTIVE: keep trust, provenance, and authority fail-closed.
- ISSUES: #159, #165, #167.
- PRS: security boundary PRs.
- DEPENDENCIES: acceptance and runtime control.
- ENTRY_CRITERIA: authority and provenance primitives exist.
- IMPLEMENTATION_WORK: credential lifecycle, trust binding, hostile provenance handling.
- TESTS: hostile trust tests and security invariants.
- EVIDENCE: explicit rejection of unauthorized or stale authority.
- EXIT_CRITERIA: authority cannot be caller-invented.
- WHAT_CAN_RUN_IN_PARALLEL: runtime diversity and fault model work.
- WHAT_MUST_REMAIN_OPEN: full hostile external-system attestation.
- EXTERNAL_BLOCKERS: external trust roots.

## Block H - Operational fault model and adversarial/system tests

- OBJECTIVE: cover failure classes end-to-end.
- ISSUES: #92, #206, #254.
- PRS: fault-model and adversarial coverage PRs.
- DEPENDENCIES: all lower-level control and acceptance paths.
- ENTRY_CRITERIA: failure taxonomy exists.
- IMPLEMENTATION_WORK: fault injection, adversarial state, terminal proof closure.
- TESTS: adversarial, replay, invalid-state, and release-path tests.
- EVIDENCE: explicit failure-class coverage.
- EXIT_CRITERIA: known failure classes are represented in executable evidence.
- WHAT_CAN_RUN_IN_PARALLEL: documentation baseline finalization.
- WHAT_MUST_REMAIN_OPEN: any unmodeled external failure class.
- EXTERNAL_BLOCKERS: if a required external system is unavailable.

## Block I - Independent acceptance and evidence closure

- OBJECTIVE: keep acceptance separate from execution and make evidence replayable.
- ISSUES: #228, #271, #73, #69.
- PRS: acceptance validator / proof PRs.
- DEPENDENCIES: architecture baseline and evidence schema.
- ENTRY_CRITERIA: acceptance contract is frozen.
- IMPLEMENTATION_WORK: independent acceptance, replay, exact JSON validation.
- TESTS: acceptance and validator unit tests.
- EVIDENCE: exact evidence file validation and replay proof.
- EXIT_CRITERIA: acceptance authority is deterministic and auditable.
- WHAT_CAN_RUN_IN_PARALLEL: release documentation work.
- WHAT_MUST_REMAIN_OPEN: exact historical evidence file if missing.
- EXTERNAL_BLOCKERS: file availability, hosted CI.

## Block J - Quality-model evaluation

- OBJECTIVE: map quality goals to executable evidence.
- ISSUES: #140, #164, #165, #167, #204.
- PRS: quality and evidence mapping docs.
- DEPENDENCIES: capability map and verification baseline.
- ENTRY_CRITERIA: measurable evidence exists for key slices.
- IMPLEMENTATION_WORK: define quality gates and missing-evidence boundaries.
- TESTS: any repository-specific doc checks.
- EVIDENCE: quality model and gap map.
- EXIT_CRITERIA: quality claims are evidence-backed.
- WHAT_CAN_RUN_IN_PARALLEL: traceability and historical classification.
- WHAT_MUST_REMAIN_OPEN: unmeasured production claims.
- EXTERNAL_BLOCKERS: none required.

## Block K - Repository / GitHub convergence

- OBJECTIVE: align issues, PRs, labels, and docs with current truth.
- ISSUES: #70, #71, #73, #74, #274.
- PRS: current docs/convergence PRs.
- DEPENDENCIES: baseline, authority map, and current issue state.
- ENTRY_CRITERIA: canonical docs exist.
- IMPLEMENTATION_WORK: reconcile tracker state and superseded docs.
- TESTS: doc link validation and issue-state review.
- EVIDENCE: documented reconciliation.
- EXIT_CRITERIA: one current status view.
- WHAT_CAN_RUN_IN_PARALLEL: closure-plan drafting and capability mapping.
- WHAT_MUST_REMAIN_OPEN: mass issue closure without evidence.
- EXTERNAL_BLOCKERS: remote GitHub access when needed.

## Block L - Operational release / readiness assessment

- OBJECTIVE: distinguish post-MVP readiness from final closure.
- ISSUES: release-readiness, #69, #71, #73.
- PRS: release evidence validator and readiness docs.
- DEPENDENCIES: operational evidence and exact-head validation.
- ENTRY_CRITERIA: canonical baseline and current evidence matrix exist.
- IMPLEMENTATION_WORK: readiness gate, blocker register, exact-head release evidence.
- TESTS: local gate, validator, current-head checks.
- EVIDENCE: exact current-head release evidence and blocker separation.
- EXIT_CRITERIA: `POST_MVP_OPERATIONAL_READY` is either satisfied or blocked with reasons.
- WHAT_CAN_RUN_IN_PARALLEL: final closure audit.
- WHAT_MUST_REMAIN_OPEN: external blockers.
- EXTERNAL_BLOCKERS: hosted CI, unavailable evidence files.

## Block M - Final closure audit

- OBJECTIVE: determine what remains for project closure after operational readiness.
- ISSUES: parent closure issue set.
- PRS: closure reconciliation PRs.
- DEPENDENCIES: all prior blocks.
- ENTRY_CRITERIA: readiness state is stable.
- IMPLEMENTATION_WORK: closure domains, remaining work, and final evidence review.
- TESTS: closure audit review.
- EVIDENCE: final closure model and exact current status.
- EXIT_CRITERIA: no unresolved structural contradictions remain.
- WHAT_CAN_RUN_IN_PARALLEL: none essential.
- WHAT_MUST_REMAIN_OPEN: anything still externally blocked or not executed.
- EXTERNAL_BLOCKERS: external systems and pending evidence.

## Final-Closure Wave Delta

Status: ACTIVE_RECONCILIATION

Current integrated `main`: `19152a5451a55bdf354b14d4ac88f08f0c335187`.

Current closure branch: `post-mvp/final-closure-v1`.

New executable closure evidence:

- `metao-testkit/tests/composed_system_closure_tests.rs` composes policy/risk/budget admission, runtime-health degradation, durable lost-ACK external effect recovery, multiprocess fencing, stale-owner rejection, execution-stage evidence, usage preservation, retry causality, machine-readable gate evidence, and independent acceptance for the current lineage.
- `metao-testkit/tests/scientific_fault_evidence_tests.rs` records an executable fault/evidence matrix for the currently covered closure gates and explicitly separates blocked external/toolchain cases.
- `metao-contracts/tests/acceptance_budget_tests.rs` has been executed in release mode for the current boundary regressions.

Remaining non-local closure items:

- real external provider runtime execution is not proven by the Rust closure branch;
- real credential broker issue/renew/revoke lifecycle is not configured locally;
- Python historical runtime tests requiring `agents` and `crewai` dependencies did not execute in this environment;
- bounded formal model execution is blocked because TLC/java are unavailable;
- hosted GitHub Actions remains governed by issue #71 until a hosted run reaches configured repository steps;
- SWE-RPG executable publication/pinning remains external under issue #180.
