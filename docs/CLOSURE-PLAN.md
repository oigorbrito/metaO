# metaO Closure Plan

Status: NORMATIVE_FOR_PROJECT
Baseline version: V1
Applies to: repository `oigorbrito/metaO`
Qualified executable commit: `974bb9389ea34e409d8d9cff50b47f427f7877e2`
Date reconciled: 2026-09-09

A later documentation-only merge may advance repository `HEAD` without changing the executable evidence binding above. Any later product-code, packaging, executable-test, or workflow change requires requalification before inheriting these PASS claims.

This is the master closure plan for the post-MVP baseline. It replaces issue-by-issue ping-pong as the primary planning view.

## Current closure fact: canonical operator initialization and onboarding

The canonical Python operator initialization/onboarding requirement is resolved on the exact integrated executable state above.

```text
REPOSITORY = oigorbrito/metaO
BRANCH = main
QUALIFIED_EXECUTABLE_COMMIT = 974bb9389ea34e409d8d9cff50b47f427f7877e2
PYTHON = 3.12.10
CLEAN_CLONE = YES
ISOLATED_VENV = YES
INSTALLED_CLI = YES
UNIT_REGRESSION = current full suite PASS
README_QUICKSTART_E2E = PASS
NEGATIVE_BOOTSTRAP_E2E = PASS
CANONICAL_INITIALIZATION_E2E = PASS
FIRST_MISSION = ACCEPTED
CROSS_PROCESS_INSPECT = PASS
FINAL_WORKTREE = CLEAN
INITIALIZATION_RESOLVED = YES
HOSTED_CI = BLOCKED_EXTERNAL_PRE_STEP (#71)
```

The canonical initialization E2E traversed installed CLI -> doctor -> canonical factory loading -> declarative runtime catalog -> real LangGraph runtime -> required certification -> admission -> mission execution -> `ACCEPTED` -> separate-process inspect with persisted execution/evidence/proof observable.

The README clean-room E2E proves the committed documented onboarding path without hidden `my_app` modules, external credentials, or an uncommitted runtime catalog. The installed-console negative-bootstrap E2E proves the covered first-run failures occur before partial mission persistence.

This closes the initialization/onboarding obligation only. It does not imply final project closure, hosted-CI PASS, or real external-provider success. Issue #71 remains the independent hosted-runner blocker.

## Block A - Documentation and requirements baseline

- OBJECTIVE: establish canonical authority, baseline, and traceability documents.
- ISSUES: #274, #245, #227, #70, #434, #440.
- PRS: existing doc/reconciliation PRs only where still relevant.
- DEPENDENCIES: current repo truth and issue reconciliation.
- ENTRY_CRITERIA: baseline and authority docs created.
- IMPLEMENTATION_WORK: create canonical docs, classify history, link baseline.
- TESTS: link checks, markdown sanity, factual reconciliation against exact source state.
- EVIDENCE: updated docs and exact executable-commit binding.
- EXIT_CRITERIA: one authoritative baseline view exists and current operational claims bind to executable evidence.
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

- OBJECTIVE: align issues, PRs, labels, branches, and docs with current truth.
- ISSUES: #70, #71, #73, #74, #274, #434, #440.
- PRS: current docs/convergence PRs.
- DEPENDENCIES: baseline, authority map, and current issue state.
- ENTRY_CRITERIA: canonical docs exist.
- IMPLEMENTATION_WORK: reconcile tracker state and superseded docs; remove absorbed/transient branch refs when branch-deletion authority is available.
- TESTS: doc link validation and issue-state review.
- EVIDENCE: documented reconciliation.
- EXIT_CRITERIA: one current status view; stale branch refs are either removed or explicitly classified as hygiene-only residue.
- WHAT_CAN_RUN_IN_PARALLEL: closure-plan drafting and capability mapping.
- WHAT_MUST_REMAIN_OPEN: mass issue closure without evidence.
- EXTERNAL_BLOCKERS: remote branch deletion requires a Git client because the connected repository API does not expose delete-ref.

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

Initialization, README onboarding, the README evidence gate, the covered negative-bootstrap paths, and the numeric hard-gate audit are no longer Block L blockers for the qualified Python operator path. Remaining Block L decisions must be based on the other readiness criteria and explicitly separated external blockers.

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

## Operational/onboarding closure matrix

Bound to `974bb9389ea34e409d8d9cff50b47f427f7877e2`:

```text
CLEAN_CLONE_INSTALL = PASS
CLI_HELP = PASS
README_QUICKSTART = PASS
DOCTOR = PASS
RUNTIME_BOOTSTRAP = PASS
CERTIFICATION = PASS
FIRST_MISSION = ACCEPTED
CROSS_PROCESS_INSPECT = PASS
NEGATIVE_BOOTSTRAP_CASES = PASS
PARTIAL_STATE_CREATED_ON_COVERED_FAILURES = NO
UNIT_REGRESSION = current full suite PASS
WORKTREE_HYGIENE = PASS
HOSTED_CI = BLOCKED_EXTERNAL (#71)
```

This matrix closes the first-use/operator-operability slice. The independent numeric hard-gate audit and README evidence gate are also resolved on the qualified integrated main. It does not close real external-provider qualification, credential-broker lifecycle, formal-model execution, or final project readiness.

## Final-Closure Wave Delta

Status: LOCAL_IMPLEMENTATION_RECONCILIATION

Historical integrated `main` recorded by the earlier wave: `5348605cbcfb3bc02f3076fe1723447feff3ecdd`.

Historical initialization-only reconciled `main`: `9dbdf542eaad59e5cc80b8a1a845bf527a36893c`.

Current qualified executable `main` for the operational/onboarding slice: `974bb9389ea34e409d8d9cff50b47f427f7877e2`.

Historical closure branch: `post-mvp/final-local-closure-v2`.

New executable closure evidence from that historical wave:

- `metao-testkit/tests/composed_system_closure_tests.rs` composes policy/risk/budget admission, runtime-health degradation, durable lost-ACK external effect recovery, multiprocess fencing, stale-owner rejection, execution-stage evidence, usage preservation, retry causality, machine-readable gate evidence, and independent acceptance for the recorded lineage.
- `metao-testkit/tests/scientific_fault_evidence_tests.rs` records an executable fault/evidence matrix for the currently covered closure gates and explicitly separates blocked external/toolchain cases.
- `metao-contracts/tests/acceptance_budget_tests.rs` was executed in release mode for the recorded boundary regressions.
- `metao-contracts/src/discovery_persistence.rs` provides the #176 product persistence boundary and filesystem implementation for durable Discovery save/reopen/resume.
- `metao-contracts/tests/discovery_persistence_tests.rs` covers reopen, deterministic resume, explicit missing state, corrupt payload fail-closed, contract binding mismatch and unresolved-decision persistence.

Current additional executable evidence:

- canonical Python operator initialization executed and passed on integrated `main@974bb9389ea34e409d8d9cff50b47f427f7877e2` in a clean clone/isolated venv;
- the same guarded qualification sequence executed the current full unit suite successfully;
- README clean-room quickstart executed successfully from an installed CLI and committed examples, reaching mission `ACCEPTED` and cross-process inspection without hidden application modules or credentials;
- installed-console negative bootstrap E2E executed successfully for not-configured, invalid DB path, missing mission, invalid JSON, and missing runtime catalog cases, preserving no partial mission DB for the covered failures;
- the initialization E2E reached a certified/admitted real LangGraph runtime, mission `ACCEPTED`, and cross-process persisted inspection;
- final clean-room worktree status was clean.

Remaining non-local closure items include:

- real external provider runtime execution is not proven by the initialization/README E2Es;
- real credential broker issue/renew/revoke lifecycle is not configured locally;
- bounded formal model execution remains separate from implementation proof;
- hosted GitHub Actions remains governed by issue #71 until a hosted run reaches configured repository steps;
- SWE-RPG executable publication/pinning remains external under issue #180 where still applicable;
- numeric hard-gate audit #420-#429 was converged by #443 and qualified successfully on integrated main;
- stale remote branches are repository hygiene and should be deleted once branch-delete access is available.
