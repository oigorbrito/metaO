# metaO Verification and Validation

Status: NORMATIVE_FOR_PROJECT
Baseline version: V1
Applies to: repository `tihotm/metaO`
Last reconciled commit: `5348605cbcfb3bc02f3076fe1723447feff3ecdd`

## Verification ladder

1. static/doc review
2. focused unit tests
3. regression/unit suite
4. integration tests
5. real runtime evidence
6. operational evidence

## What each layer proves

- static/doc review proves intent and structure only;
- focused tests prove one narrow behavior;
- regression tests prove that a set of known behaviors still hold;
- integration tests prove module boundaries work together;
- real runtime evidence proves the runtime path, not just a mocked shape;
- operational evidence proves the current release path or blocker state.

## Current executable evidence sources

- unit tests in `tests/unit/`
- integration tests in `tests/integration/`
- golden fixtures in `tests/golden/`
- local release gate in `scripts/run-local-release-gate.ps1`
- release evidence validator in `scripts/validate_release_evidence.py`

## Validation principles

- `IMPLEMENTED != EXECUTED`
- `EXECUTED != ACCEPTED`
- `UNIT_PASS != SYSTEM_PASS`
- `SIMULATED != REAL`
- `DOCUMENTED != IMPLEMENTED`

## Current release-path interpretation

The repository has a validated local release path on the historical canonical candidate documented in the release-readiness artifacts. Hosted CI is separately blocked and must not be conflated with product correctness.

## Post-PR-343 final-closure delta

PR #343 was merged into `main` at `19152a5451a55bdf354b14d4ac88f08f0c335187`. The Rust chassis is now the primary current-head evidence path for the post-MVP operationalization wave.

Additional evidence added on branch `post-mvp/final-closure-v1`:

- `cargo test -p metao-testkit --test composed_system_closure_tests`
- `cargo test -p metao-testkit --test scientific_fault_evidence_tests`
- `cargo test -p metao-contracts --test acceptance_budget_tests --release`
- `cargo clippy --workspace --all-targets -- -D warnings`

Additional current-main evidence after PRs #347, #348 and #349:

- `cargo test -p metao-contracts --test discovery_persistence_tests`
- `cargo test -p metao-contracts --test discovery_coordinator_tests`
- `cargo test -p metao-contracts --test control_plane_stateful_property_tests`
- `cargo test -p metao-testkit --test composed_system_closure_tests`

The current local closure branch adds a product `DiscoveryStateStore` boundary and a filesystem-backed implementation. This upgrades #176 from test-only durable serialization evidence to a framework-neutral product persistence/resume path while preserving the claim boundary that this is not a mandated production database.

Current claim boundaries:

- the composed system proof uses simulated runtimes, real local OS processes, a real local external-effect service, durable file-backed state, multiprocess fencing, and fault injection;
- it does not claim real external orchestrator/provider execution;
- AcceptanceBudget debug/release parity is supported only for the executed `acceptance_budget_tests` target;
- Python runtime tests requiring `agents` or `crewai` did not execute in this environment because those dependencies are unavailable;
- the formal model is present, but TLC/java execution is blocked by missing local tooling.

## Remote reconciliation snapshot

Date: `2026-08-31`

The remote repository remains reachable through Git transport even though the `gh` GraphQL path returned `401` in this environment.

Evidence collected from `origin`:

- current `origin/main` for this reconciliation is `5348605cbcfb3bc02f3076fe1723447feff3ecdd`;
- PR head refs were fetched directly with `git ls-remote` / `git fetch` for the relevant closure families;
- PRs #347, #348 and #349 are ancestors of current `origin/main`;
- older PR-head comparisons remain historical and must not override current ancestry checks;
- protected evidence refs remain preserved for `#200`, `#201`, `#202`, and `#217`;
- `#217` still carries the `PRODUCT_MIGRATION = NOT_AUTHORIZED` disposition.

Current reconciliation boundary:

- remote refs can be inspected and preserved with Git transport;
- API-driven PR/issue closure was not executed in this environment because the GitHub API path remained unavailable here;
- no PR was auto-closed on ancestry alone.

## PR ref classification snapshot

Date: `2026-08-31`

The following relevant PR heads were fetched from `origin` and compared against `origin/main` with `git diff origin/main...refs/tmp/pr<N>`. Each one has a non-empty diff against current `origin/main`, so none can be treated as absorbed solely by local ancestry checks:

| PR | DIFF FILES | CURRENT CLASSIFICATION |
|---|---:|---|
| #291 | 4 | STILL_HAS_UNIQUE_CODE |
| #294 | 2 | STILL_HAS_UNIQUE_CODE |
| #297 | 2 | STILL_HAS_UNIQUE_CODE |
| #299 | 4 | STILL_HAS_UNIQUE_CODE |
| #305 | 3 | STILL_HAS_UNIQUE_CODE |
| #307 | 3 | STILL_HAS_UNIQUE_CODE |
| #311 | 4 | STILL_HAS_UNIQUE_CODE |
| #312 | 3 | STILL_HAS_UNIQUE_CODE |
| #313 | 3 | STILL_HAS_UNIQUE_CODE |
| #317 | 3 | STILL_HAS_UNIQUE_CODE |
| #318 | 3 | STILL_HAS_UNIQUE_CODE |
| #319 | 3 | STILL_HAS_UNIQUE_CODE |
| #322 | 3 | STILL_HAS_UNIQUE_CODE |
| #324 | 2 | STILL_HAS_UNIQUE_CODE |
| #326 | 2 | STILL_HAS_UNIQUE_CODE |
| #328 | 2 | STILL_HAS_UNIQUE_CODE |
| #339 | 3 | STILL_HAS_UNIQUE_CODE |
| #341 | 1 | STILL_HAS_UNIQUE_CODE |
| #200 | preserved evidence ref | PROTECTED_EVIDENCE |
| #201 | preserved evidence ref | PROTECTED_EVIDENCE |
| #202 | preserved evidence ref | PROTECTED_EVIDENCE |
| #217 | preserved evidence ref | PROTECTED_EVIDENCE / PRODUCT_MIGRATION_NOT_AUTHORIZED |

## Evidence to keep exact

- branch
- commit / SHA
- worktree cleanliness
- test command
- gate result
- evidence artifact path
- blocker classification

## Closure gates

- focused tests must exist for the capability before the capability can be claimed implemented;
- regression tests must exist before claiming stable behavior across the release path;
- integration tests must exist before claiming composed boundaries;
- real-runtime evidence must exist before claiming runtime truth;
- operational evidence must exist before claiming current operational readiness.
