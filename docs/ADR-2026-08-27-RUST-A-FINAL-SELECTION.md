# ADR — Final chassis selection: Rust A

Date: 2026-08-27
Status: Accepted for implementation planning
Repository: `tihotm/metaO`

## Decision

Select **Rust A (explicit Cargo workspace)** as the target chassis for metaO.

This supersedes the operational HOLD recorded after the earlier provisional Rust selection. The historical ADRs and benchmark records remain valid evidence and must not be rewritten in place.

## Current product state

- Current implemented product chassis: Python.
- Python remains the executable semantic oracle during migration.
- Rust A is the selected target chassis.
- C# C remains a technically viable alternative, but is not selected.
- Big-bang rewrite remains forbidden.

## Evidence basis

The selection is based on the frozen #199 framework plus the subsequent owner-reviewed tie-break evidence.

### Comparable runtime evidence

Semantic equivalence: PASS.

| Metric | Rust A | C# C | Result |
|---|---:|---:|---|
| Median wall-clock | 39.0405 ms | 323.8627 ms | Rust ~8.3x lower |
| Median CPU | 15.625 ms | 250 ms | Rust 16x lower |
| Median peak working set | 3,305,472 B | 29,908,992 B | Rust ~9x lower |
| Audited artifact size | 4,048,719 B | 374,260 B | C# ~10.8x smaller |

The previous Rust artifact value of 374,260 B is invalid and must not be reused.

### Controlled maintainability evidence

Across the three previously frozen maintenance tasks, Rust required fewer objective changed LOC in all three tasks. Those static change-size measurements are retained as comparable evidence. Compile/test cycle timing from that earlier experiment must not be treated as perfectly apples-to-apples because the Rust and C# test scopes were not identical.

### Fault-injection evidence

Only the fault classes actually implemented in the comparable harness may be treated as proven.

For both Rust A and C# C:

- exception/panic: 250/250 expected failures contained; 0 escaped; 0 true invariant violations; 250/250 post-fault recovery successes;
- stale/mis-bound evidence: 250/250 rejected; 0 true invariant violations; 250/250 post-fault recovery successes;
- hard-gate failures observed: 0.

Not proven as comparable final evidence:

- timeout/hang: `NOT_PROVEN_AS_REAL_HANG`;
- malformed/incompatible protocol: `NOT_IMPLEMENTED_IN_HARNESS`.

These gaps become pre-migration verification work, not hidden PASS results.

### Mutation evidence

Rust A:

- generated: 26
- viable: 23
- killed: 19
- survived: 4
- mutation score: 82.6086956522%

Four surviving mutations remain in `evaluate_acceptance` and must be resolved by focused tests or classified with proof as equivalent before migration proceeds beyond the initial gate.

C# C mutation testing is `NOT_COMPARABLE_TOOLING` in the recorded environment. The last Stryker attempt reached the mutation harness but failed during package restore due NuGet/network/security-package credentials. C# receives no penalty or synthetic score for this missing measurement.

## Decision rationale

Rust A is selected because the new comparable runtime evidence shows a material operational advantage while both candidates preserve the tested semantic invariants. Rust also retained the stronger controlled change-size signal from the earlier maintenance tasks. C# retains a clear advantage in audited artifact size, but that single advantage does not outweigh the observed CPU, memory, wall-clock, and maintenance evidence for this control-plane kernel.

The selection is not based on language prestige, personal preference, or test-win counting.

## Mandatory implementation constraints

1. Python remains the executable oracle until semantic parity is demonstrated.
2. No big-bang rewrite.
3. Migration is incremental, capability-by-capability.
4. No runtime/orchestrator SDK type may leak into Core.
5. `ORCHESTRATOR_DONE != METAO_ACCEPTED` remains mandatory.
6. Hard DENY, budget, authority/provenance, evidence binding, and contract/version conflict remain fail-closed.
7. Any BLOCKED / UNKNOWN / NOT_PROVEN state must remain explicit.
8. Existing #199 weights and historical benchmark evidence are immutable.

## Pre-migration Gate 0

Before product migration advances beyond setup/parity scaffolding:

- resolve or prove equivalent the 4 surviving Rust acceptance mutants;
- implement a real timeout/hang fault injection path;
- implement malformed/incompatible protocol fault injection;
- verify 0 hard-gate violations in those new tests;
- reconcile the qualified Python oracle changes onto the current integration path without weakening existing semantics.

## Operational state

`LANGUAGE_SELECTION = RUST_A`

`PYTHON_ROLE = EXECUTABLE_ORACLE_DURING_MIGRATION`

`MIGRATION_MODE = INCREMENTAL`

`BIG_BANG_REWRITE = FORBIDDEN`

`PRODUCT_MIGRATION = AUTHORIZED_ONLY_THROUGH_GATED_PLAN`
