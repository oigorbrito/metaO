# metaO Verification and Validation

Status: NORMATIVE_FOR_PROJECT
Baseline version: V1
Applies to: repository `tihotm/metaO`
Last reconciled commit: `ffc1aae`

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

