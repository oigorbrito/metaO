# ADR — Select explicit Rust workspace as the metaO chassis

Date: 2026-08-27
Status: ACCEPTED
Supersedes: `docs/ADR-2026-08-27-CHASSIS-DECISION.md` decision state `DEFER_DECISION_AND_CLOSE_EVIDENCE_GAPS`
Evidence authority: #199, #215, #216, #218

## Decision

```text
SELECTED_CHASSIS = A / explicit Rust Cargo workspace
PRODUCT_MIGRATION = AUTHORIZED_STAGED_ONLY
BIG_BANG_REWRITE = FORBIDDEN
#199_SCORECARD = FROZEN
ARCHITECTURE_PIPELINE = FROZEN
```

The metaO long-term chassis is candidate A: the explicit Rust Cargo workspace qualified under the frozen #199 scorecard.

This decision does not authorize an in-place rewrite or immediate removal of the Python implementation. Python remains the executable oracle during staged migration until each migrated semantic slice reaches parity and acceptance gates.

## Frozen architecture that remains unchanged

```text
Mission
  -> Strategy / Selection
  -> Policy / Budget
  -> OrchestratorContract
  -> Runtime Adapter
  -> Orchestrator real
  -> Evidence
  -> Independent Acceptance
  -> Accept / Replan / Failover / Block
```

The central architectural test remains:

> Can an entire orchestrator, including its agents, tools, memory and workflows, be replaced without changing metaO Core?

The following invariants remain non-negotiable:

- `ORCHESTRATOR_DONE != METAO_ACCEPTED`;
- runtime self-report cannot mint governance or acceptance authority;
- runtime/orchestrator SDK-specific types must not enter Core/kernel;
- hard deny, budget, authority, provenance and evidence gates are non-compensable;
- no second durable workflow engine or second acceptance authority;
- contract/version conflicts fail deterministically;
- blocked, unknown or not-proven evidence cannot silently become PASS.

## Evidence trail

### Semantic qualification

All principal candidates reached executable semantic qualification without a currently recorded H1-H10 hard-gate failure at their qualification heads.

Candidate A executed:

```text
fmt = PASS
clippy -D warnings = PASS
qualification = 10/10 PASS
out_of_process = 5/5 PASS
fuzz harness cargo check = PASS
HEAD = ce6d2790ac5a5118f144a16788bfc68045602ce9
```

Candidate C executed:

```text
restore/build -warnaserror = PASS
direct semantic harness = 79/79 PASS
L5 = 10/10 PASS
HEAD = ef641e94b1ad1cfb137d69a7a8c0648804f58033
```

Python P was repaired and re-executed for the carried L5 budget defects, preserving the golden baseline. Rust B/Nidus was also qualified but did not prove a material advantage over A and carried a larger framework/dependency surface.

### Frozen scorecard before final tie-break

After closure of the major semantic evidence gaps, #215 produced:

```text
P = 86.6
A = 94.0
B = 82.0
C = 93.4
A - C = 0.6
```

Because the top-two delta was below 5 points, the frozen #199 sensitivity rule required additional comparable evidence rather than an immediate selection.

### Same-machine A-vs-C tie-break

The #216 protocol was defined before observing the final measurements.

Five-sample build medians and footprint:

```text
A / Rust
clean build median = 11,430 ms
incremental build median = 132 ms
artifact footprint = 135,032,927 bytes
workspace dependency unique lines = 25
kernel dependency unique lines = 2

C / C#
clean build median = 3,889 ms
incremental build median = 2,087 ms
artifact footprint = 1,982,106 bytes
PackageReference count = 0
ProjectReference count = 14
```

The original C# probe result `PackageReference=7` was rejected as an instrumentation defect. The corrected XPath-based inventory reports zero explicit PackageReferences.

The build/runtime-cost evidence is mixed: C is materially better on clean-build time and measured build-artifact footprint, while A is materially better on incremental-build time. Therefore neither receives an artificial winner-takes-all score for this dimension.

### Predeclared maintainability proxy

Three bounded tasks were implemented independently on disposable branches for A and C and all focused executions passed.

| Task | A / Rust | C / C# |
|---|---|---|
| identity primitive + validation + round-trip | 2 files, 30 LOC, 2,545 ms | 2 files, 50 LOC, 6,947 ms |
| rejection reason propagated + focused test | 4 files, 37 LOC, 1,381 ms | 3 files, 48 LOC, 4,715 ms |
| fake adapter replacement | 1 file, 57 LOC, 1,512 ms | 1 file, 65 LOC, 4,388 ms |

Aggregate observations:

```text
A changed LOC total = 124
C changed LOC total = 163
A compile+test cycle total = 5,438 ms
C compile+test cycle total = 16,050 ms
A lower changed LOC = 3/3 tasks
A faster measured compile+test cycle = 3/3 tasks
```

For the adapter-replacement task, both candidates kept kernel and public contract untouched. This confirms the intended whole-orchestrator replacement boundary in the bounded maintenance proxy.

## Final frozen-scorecard recomputation

Only dimensions with materially new evidence were adjusted; weights and hard gates were not changed.

- Maintainability / ergonomics: A `4 -> 5`; C remains `4`.
- Dependency / trusted surface: A and C remain `5`; C dependency count is corrected to zero explicit PackageReferences.
- Build/runtime engineering cost: A remains `4`; C `3 -> 4`, reflecting mixed measured evidence rather than subjective preference.
- Maturity/ecosystem risk remains equal and below evidence grade 4; no popularity, stars or language familiarity are used.

Final weighted totals:

```text
A = 95.4
C = 94.0
RAW_DELTA = 1.4
```

Because the delta remains below 5, the mandatory sensitivity rule was applied again. Removing all dimensions still below evidence grade 4 preserves the same winner:

```text
SENSITIVITY_WINNER = A
WINNER_STABLE_AFTER_LOW_GRADE_REMOVAL = YES
```

This satisfies the predeclared #216 acceptance rule: a candidate may advance when it either obtains a >=5-point lead or remains the winner after removal of grade<4 dimensions.

## Consequences

### Selected

Candidate A — explicit Rust Cargo workspace.

### Qualified runner-up

Candidate C — explicit C#/.NET modular chassis. Its strong clean-build and footprint results remain valid evidence, but they do not overturn the stable sensitivity result.

### Not selected

Candidate B — Rust/Nidus host. Viable, but no material advantage over A was proven and it adds framework/dependency surface.

### Incumbent migration oracle

Candidate P — Python. It remains the executable semantic oracle during migration and must not be deleted merely because A is selected.

## Migration policy

Migration must be staged by semantic slice.

For every slice:

1. pin the Python behavior and exact fixture set;
2. implement the equivalent Rust slice behind the existing contract boundary;
3. replay the frozen golden fixtures and focused negative/adversarial tests;
4. verify no runtime SDK types leak into Core/kernel;
5. verify independent acceptance authority remains separate from runtime success;
6. verify budget, evidence, provenance, authority and contract-version gates fail closed;
7. preserve rollback to the Python slice until Rust evidence reaches the required grade;
8. only then supersede/remove the Python slice.

A failed or blocked migration slice does not invalidate the chassis selection. It is recorded as FAIL/BLOCKED and independent slices may continue.

## Final classification

```text
ADR_STATUS = ACCEPTED
SELECTED_CHASSIS = RUST_A_EXPLICIT_WORKSPACE
DECISION_CONFIDENCE = STABLE_UNDER_FROZEN_SENSITIVITY_RULE
PRODUCT_MIGRATION = AUTHORIZED_STAGED_ONLY
PYTHON_ORACLE = PRESERVE_DURING_MIGRATION
BIG_BANG_REWRITE = FORBIDDEN
```
