# Architecture Survival Lifecycle Cost Ledger V1

> Salvaged from historical PR #361 onto current `main` under #651. Historical observations remain provenance only; new PASS/FAIL claims require fresh execution on the salvage head.

Status: INITIAL BASELINE / MEASUREMENT FIELDS FROZEN

## Rule

Cost is not "hours to first demo".

The comparison uses lifecycle cost-benefit:

- implementation and adaptation;
- validation burden;
- operational burden;
- dependency and upgrade burden;
- future extension cost;
- failure/recovery cost;
- migration reversibility;
- licensing and ecosystem constraints.

Quality hard-gate failures cannot be offset by lower cost.

## Strategies under comparison

### S0 — Current metaO, selective donors

Project Plane: current metaO
Executor boundary: ACP candidate
Evidence/apply: current metaO, with Pactrail mechanisms evaluated selectively
Audit/arbiter: current metaO, with Vigla patterns evaluated selectively
Durability: Duroxide vs Durare vs minimal SQLite baseline

### S1 — Pactrail-centered composition

Project Plane: metaO contract layer
Execution/evidence/apply kernel: Pactrail candidate
Executor boundary: ACP candidate
Durability: native Pactrail semantics plus common durability comparison

### S2 — Vigla-centered composition

Project Plane authority: metaO contract layer
Mission supervision/audit: Vigla candidate
Executor boundary: ACP candidate
Evidence binding: current metaO plus Pactrail mechanisms if selected
Durability: Duroxide vs Durare

### S3 — New minimal composition

Only if S0-S2 show excessive adaptation cost.

Project Plane: extracted metaO contracts
Executor boundary: ACP
Durability: winning L3 backend
Evidence/apply: extracted or ported Pactrail semantics
Audit: extracted Vigla semantics

## Measurement fields

| Metric | Unit | S0 | S1 | S2 | S3 |
|---|---|---:|---:|---:|---:|
| New production LOC | measured | TBD | TBD | TBD | TBD |
| Deleted/replaced LOC | measured | TBD | TBD | TBD | TBD |
| New direct dependencies | count | TBD | TBD | TBD | TBD |
| New runtime services | count | TBD | TBD | TBD | TBD |
| Build duration | seconds | TBD | TBD | TBD | TBD |
| Test duration | seconds | TBD | TBD | TBD | TBD |
| Startup latency | ms | TBD | TBD | TBD | TBD |
| Idle memory | MB | TBD | TBD | TBD | TBD |
| Provider addition delta | LOC + tests | TBD | TBD | TBD | TBD |
| Adapter addition delta | LOC + tests | TBD | TBD | TBD | TBD |
| L2 hard-gate pass rate | 0/7 | TBD | TBD | TBD | TBD |
| L3 fault pass rate | passed/total | TBD | TBD | TBD | TBD |
| External infrastructure required | list | TBD | TBD | TBD | TBD |
| Upgrade coupling | low/medium/high | TBD | TBD | TBD | TBD |
| Reversibility | low/medium/high | TBD | TBD | TBD | TBD |

## Cost scoring

No synthetic score is assigned until measured values exist.

After L2/L3:

Lifecycle cost is evaluated as:

```text
TCO =
  adaptation
+ validation
+ operations
+ maintenance
+ upgrade coupling
+ dependency risk
+ recovery cost
- reusable verified capability
```

The subtraction is conceptual only: a donor reduces cost only when its capability survives common tests.

## Current qualitative baseline

| Mechanism | Reuse promise | Current evidence | Cost risk |
|---|---|---|---|
| ACP Rust SDK | high | source + upstream CI | protocol adaptation and executor availability |
| Pactrail evidence/apply | high | source + upstream CI | integration with sovereign Project Plane |
| Vigla audit/arbiter | high | source + upstream CI | authority/decomposition rewiring |
| Duroxide | high for durability | source + upstream CI | semantic mismatch in exact-once/effect boundary |
| Durare | high for durability | source + upstream CI | backend/runtime coupling and transaction model |
| Current metaO contracts | already owned | existing repository evidence | operational gaps still under test |

## Decision thresholds

A strategy may be recommended only when:

1. all applicable L2 hard gates pass;
2. L3 failure behavior is at least as safe as the current baseline;
3. no critical donor claim remains only README-level;
4. the added dependency/maintenance burden is justified by measured verified capability;
5. rollback to the current metaO contract layer remains feasible until a release baseline is frozen.

## Current decision

OPEN.

The first measured values begin after an executable runner is available for independent reproduction and after minimal L2 adapters exist.
