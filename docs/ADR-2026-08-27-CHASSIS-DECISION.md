# ADR — metaO chassis decision — 2026-08-27

Status: ACCEPTED

Decision owner: #198  
Decision gate: #195  
Execution consolidation: #197  
Frozen scorecard: #199

## Decision

```text
DEFER_DECISION_AND_CLOSE_EVIDENCE_GAPS
PRODUCT_MIGRATION = NOT_AUTHORIZED
#199_SCORECARD = FROZEN
```

This is a completed architecture decision, not an undecided placeholder. The evidence available on 2026-08-27 is sufficient to decide that no product migration is justified yet, while preserving the qualified candidates for later reconsideration after the recorded evidence gaps close.

## Context

The metaO chassis bake-off compared four candidates under the scorecard frozen in #199:

```text
P = current Python baseline
A = explicit Rust Cargo workspace
B = Nidus-based Rust modular host
C = explicit C#/.NET modular control-plane chassis
```

Candidate C was admitted later by #207 without changing hard gates, weights, evidence grades, or adding language/framework preference.

The architectural invariant remains:

> An entire orchestrator, including its agents, tools, memory and workflows, must be replaceable without changing metaO Core.

Additional non-compensable rules include:

- `ORCHESTRATOR_DONE != METAO_ACCEPTED`;
- runtime self-report cannot mint governance/acceptance authority;
- hard DENY/budget/authority/provenance/evidence gates are non-compensable;
- no runtime/framework SDK types in Core contracts;
- no second durable workflow engine or second acceptance authority.

## Evidence state by candidate

### P — Python baseline

Evidence anchors: #192 / PR #201.

- canonical frozen golden baseline exists and is reproducible;
- four explicit golden semantic cases are recorded;
- Python remains the historical product baseline;
- executed L5 defects remain recorded for shared-budget oversubscription and settlement-retry idempotency.

Classification:

```text
P = PARTIAL
SEMANTIC_BASELINE = EXECUTED
L5 = FAIL/PARTIAL on recorded budget/idempotency cases
```

Python therefore cannot be treated as an all-green reference merely because it is the incumbent chassis.

### A — explicit Rust workspace

Evidence anchors: #193 / PR #200.

Recorded current spike evidence includes:

- kernel has zero direct external crates and only the internal contracts dependency;
- identity-boundary defect was repaired structurally with private inner fields and validating constructors;
- `cargo fmt --all --check = PASS`;
- measured workspace snapshot: 7 crate definitions, 9 Rust source files, 782 Rust LOC, 13 unique workspace cargo-tree lines, 2 kernel tree lines, no owned executable `unsafe` observed;
- `cargo clippy` and `cargo test`, including the focused identity gate, remain blocked on the recorded Windows host because `link.exe` is unavailable;
- Miri/fuzz execution is not proven on that host.

Classification:

```text
A = PARTIAL / BLOCKED_TOOLCHAIN
IDENTITY_REPAIR = CODE_CONFIRMED
EXECUTED_CONFORMANCE = NOT_PROVEN
```

The toolchain blocker is not a semantic Rust failure, but it prevents promoting the relevant hard gates to executed PASS.

### B — Nidus Rust host

Evidence anchors: #194 / PR #202.

Recorded current spike evidence includes:

- metaO kernel remains free of Nidus/Axum/Tower/Tokio types;
- Nidus is isolated to the host layer;
- upstream Nidus module-graph and lifecycle/rollback capabilities have test-confirmed evidence;
- identity-boundary repair is code-confirmed;
- measured workspace snapshot: 8 crate definitions, 10 Rust source files, 761 Rust LOC, 28 unique workspace cargo-tree lines, 2 kernel tree lines, no owned executable `unsafe` observed;
- B carries a materially larger host dependency/trusted surface than A;
- a material productivity/maintainability advantage over A is not yet measured/proven;
- metaO `cargo clippy`/`cargo test` remain blocked by the same missing `link.exe` toolchain condition.

Classification:

```text
B = PARTIAL / BLOCKED_TOOLCHAIN
NIDUS_HOST_CAPABILITIES = CODE/UPSTREAM_TEST_SUPPORTED
MATERIAL_ADVANTAGE_OVER_A = NOT_PROVEN
EXECUTED_CONFORMANCE = NOT_PROVEN
```

### C — explicit C#/.NET chassis

Evidence anchors: #207 / PR #208.

Current head executed locally on .NET 10:

```text
dotnet restore MetaO.ChassisC.sln = PASS
dotnet build MetaO.ChassisC.sln --no-restore -warnaserror = PASS
DIRECT_COUNT = 79
DIRECT_FAILURES = 0
```

All ten added L5 operational/adversarial cases executed PASS:

```text
RESTART_CHECKPOINT_ROUNDTRIP=PASS
RESTART_RESUME=PASS
RESUME_REVALIDATES_POLICY=PASS
RESUME_REVALIDATES_STATE=PASS
RESUME_REVALIDATES_GOVERNANCE=PASS
REVOKED_RUNTIME_NOT_SELECTED=PASS
REVOCATION_OVERRIDES_HEALTH=PASS
HEALTHY_NOT_EQUAL_AUTHORIZED=PASS
REVOKED_SUCCESS_NOT_ACCEPTED=PASS
RESUME_REVOKED_RUNTIME=PASS
```

Combined qualification:

```text
C_L0 = PASS
C_L1 = PASS
C_L2 = PASS
C_L3 = PASS
C_L4 = PASS
C_L5 = PASS
```

The C# spike therefore clears its current qualification battery. Standard VSTest parity remains a separate tooling-path concern and is not substituted for the executed direct semantic harness.

## Why C is not selected for migration now

Candidate C is currently the strongest fully executed challenger, but the frozen decision rules do not allow a candidate to win merely because competitors are blocked by an external toolchain condition.

Selecting C now would require treating A/B `BLOCKED_TOOLCHAIN` as an implicit loss or assuming that C's current executed advantage is a material long-term product advantage. Neither inference is supported by the evidence.

The scorecard also requires a material long-term migration advantage over keeping Python, not merely a green experimental harness. The current evidence proves C# feasibility and conformance; it does not yet prove that the total migration cost/risk is justified relative to fixing the incumbent baseline or completing the Rust comparison.

Therefore:

```text
C_PASS != C_MIGRATION_AUTHORIZED
```

## Why Python is not selected as a final KEEP decision now

The incumbent Python baseline has real executed L5 defects. Choosing `KEEP_PYTHON` as a final foundation decision before those defects are reconciled against the challenger evidence would overstate the incumbent's current correctness position.

The correct action is to keep Python as the product baseline while migration remains unauthorized, not to claim the bake-off has proved Python superior.

## Why A/B are not rejected

The recorded Rust blocker is an unavailable MSVC linker/toolchain on the execution host:

```text
error: linker 'link.exe' not found
```

That is `BLOCKED_TOOLCHAIN`, not a semantic FAIL. The repaired identity boundary is code-confirmed but lacks executable confirmation on a functioning Rust build host.

B additionally has an unresolved burden of proof: its larger host dependency surface must demonstrate a material advantage over A.

## Scorecard disposition

No numeric score is manufactured for evidence that is not comparable or executable. In particular:

- BLOCKED is not converted to PASS or FAIL;
- code-confirmed repairs are not promoted to executed evidence;
- unlike build/runtime metrics are not treated as directly equivalent;
- language familiarity, stars, README claims, framework feature count and user preference contribute zero decision authority.

The frozen #199 weights and hard gates remain unchanged.

## Migration cost and rollback posture

No product migration is authorized by this ADR. Therefore no destructive migration or rollback operation is initiated.

The current product baseline remains Python while the chassis experiments stay isolated. This preserves the lowest-risk rollback posture: no production foundation has moved.

If a future ADR selects a new chassis, it must include a staged migration plan preserving the current orchestrator contract, golden semantics, independent acceptance authority and a reversible boundary between product code and the selected host/runtime implementation.

## Follow-up work authorized

Only evidence-gap closure and decision-quality work are authorized by this ADR:

1. Execute A and B on a Rust host with a functioning linker/toolchain, including focused hard-gate tests, `cargo clippy`, and `cargo test`.
2. Preserve Miri/fuzz as attempted/recorded evidence according to availability; do not convert unavailable tools to semantic failure.
3. Resolve or explicitly supersede the Python L5 shared-budget oversubscription and settlement-retry idempotency defects.
4. Compare engineering/migration cost only after the same semantic slice has executable evidence across viable candidates.
5. Re-open the chassis selection only when new evidence can materially distinguish `KEEP_PYTHON`, `MIGRATE_TO_RUST_EXPLICIT_WORKSPACE`, `MIGRATE_TO_RUST_NIDUS_HOST`, or `MIGRATE_TO_CSHARP_EXPLICIT_DOTNET`.

## Consequences

Positive:

- candidate C is fully qualified without forcing premature migration;
- Rust blockers remain honestly classified as infrastructure/toolchain blockers;
- Python defects remain visible rather than normalized away;
- no scorecard criterion was changed after observing results;
- product implementation can continue only within the existing authorization boundaries, not as a chassis migration.

Negative:

- chassis selection remains unresolved by design;
- additional Rust execution and Python defect closure are required before a migration/keep decision can be made with comparable evidence;
- the repository retains experimental PRs #200, #202 and #208 until the next evidence-backed selection/reconciliation step.

## Final classification

```text
ADR_STATUS = ACCEPTED
FINAL_CLASSIFICATION = DEFER_DECISION_AND_CLOSE_EVIDENCE_GAPS
PRODUCT_MIGRATION = NOT_AUTHORIZED
#199_SCORECARD = FROZEN
```
