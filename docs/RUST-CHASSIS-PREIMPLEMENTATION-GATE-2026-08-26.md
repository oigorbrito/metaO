# Rust chassis pre-implementation gate — 2026-08-26

Parent research: #178  
Chassis owner: #189  
Rust bake-off: #190  
Final qualification gate: #195

## Purpose

Do not expand or migrate the metaO Core until the chassis decision is supported by reproducible evidence.

This gate separates:

```text
RUST_LANGUAGE_EVIDENCE != CARGO_WORKSPACE_SUPPORT
CARGO_WORKSPACE_SUPPORT != METAO_ARCHITECTURE_PROOF
OMICRON_TEST_EXISTS != METAO_TEST_PASSED
UPSTREAM_PASS != METAO_ACCEPTANCE
```

## Candidate set

```text
P = current Python metaO baseline
A = explicit Rust Cargo workspace + mature crates + Omicron/kube-rs patterns
B = Nidus-based Rust modular host
```

Pavex and Loco remain secondary/reference candidates unless L0/L1 evidence shows a plausible kernel/control-plane advantage.

## Issue graph

- #191 — qualify Rust/Cargo/Omicron evidence.
- #192 — freeze current Python golden contracts and expected outcomes.
- #193 — isolated Rust explicit-workspace spike.
- #194 — isolated Nidus comparison spike.
- #195 — final pre-implementation chassis qualification gate.
- #196 — extract Omicron simulation/E2E/live/compatibility test patterns.
- #197 — execute qualification levels L0–L5 with PASS/PARTIAL/FAIL/BLOCKED/NOT_PROVEN states.
- #198 — final ADR; only artifact allowed to unlock migration/Core expansion.
- #199 — fixed hard-gate/weighted scorecard defined before candidate execution.

## Qualification levels

### L0 — documentation and contract inspection

Exact pins, primary documentation, stated guarantees/limitations, licensing and release status.

### L1 — code and test-path inspection

Exact implementation/test paths, CI/build/security checks, architecture-boundary evidence.

### L2 — isolated executable fixtures

Reproducible Python baseline plus Rust candidate minimal slices. Kernel tests must not require network/database.

### L3 — architecture/conformance battery

C1–C12 chassis tests, golden fixtures, hard-DENY/evidence/acceptance invariants, property tests and failure containment.

### L4 — multi-runtime integration

At least two materially different runtimes/adapters without Core contract changes.

### L5 — adversarial and operational

Restart/resume, stale or revoked state, concurrent budgets, out-of-order evidence, malicious runtime reports, measured dependency/build/unsafe/test cost.

## Hard architecture gates

A candidate is not eligible for migration if any non-negotiable gate fails:

1. Core purity / no runtime-framework SDK leakage.
2. Whole-orchestrator replacement without Core/policy/evidence/acceptance changes.
3. `SUCCEEDED != ACCEPTED`.
4. Hard DENY precedence cannot be overridden.
5. Evidence binding required before acceptance.
6. Runtime self-report cannot mint governance authority.
7. Failure containment: panic/error/timeout cannot become acceptance.
8. No duplicate durable or acceptance authority.
9. Contract/version conflicts fail deterministically.
10. Golden semantic equivalence for frozen requirements.

C1–C12 from #189/#195 remain mandatory in addition to the hard-gate list above.

## Fixed scorecard before L2

Weights are defined in #199 and may change only before L2 candidate execution, with rationale recorded.

```text
Correctness / invariants          25
Architecture isolation           20
Robustness / failure behavior     15
Testability / verification        15
Dependency / trusted surface      10
Maintainability / ergonomics       7
Maturity / ecosystem risk          5
Build/runtime engineering cost     3
TOTAL                            100
```

Evidence confidence is graded independently:

```text
0 NOT_PROVEN
1 DOCUMENTED
2 CODE_CONFIRMED
3 TEST_CONFIRMED upstream
4 EXECUTED in metaO fixture
5 MEASURED in comparable metaO fixture
```

## Initial evidence recorded

### metaO Python baseline

Pinned `main`:

```text
b69a4e502b07ddfa1f5e05399710e335d5edfbc0
```

The latest observed CI run for this exact commit concluded `failure`. The job response exposes no execution steps, so the cause is currently `NOT_PROVEN`; the baseline must not be treated as green from historical memory. #192/#197 own resolution.

### Omicron architecture/test precedent

Pinned Omicron:

```text
c64cb205000bbc9460de84cbd4c8d85f946b8f08
```

L1 evidence confirms dedicated packages:

```text
end-to-end-tests/
live-tests/
```

`end-to-end-tests/README.adoc` documents Buildomat package/deploy execution and local `cargo nextest run -p end-to-end-tests`.

`live-tests/README.adoc` documents tests operating against an already-deployed real Oxide system, and explicitly distinguishes:

```text
normal tests -> real control-plane components with simulated sled agents/localhost networking
E2E tests    -> more realistic environment
live tests   -> deployed real-system behavior
```

This is strong production/integration evidence for Omicron as a test-architecture donor. It is not evidence that metaO already passes equivalent tests.

## Migration decision rules

```text
NO_CANDIDATE_WINS_ON_STARS = TRUE
NO_CANDIDATE_WINS_ON_LANGUAGE_PREFERENCE = TRUE
NO_CANDIDATE_WINS_ON_README = TRUE

RUST_MIGRATION_REQUIRES = all hard gates PASS + material long-term advantage
NIDUS_ADOPTION_REQUIRES = same conformance as explicit workspace + material productivity/modularity gain + acceptable maturity risk
```

Final allowed outcomes:

```text
KEEP_PYTHON
MIGRATE_TO_RUST_EXPLICIT_WORKSPACE
MIGRATE_TO_RUST_NIDUS_HOST
DEFER_DECISION_AND_CLOSE_EVIDENCE_GAPS
```

## Stop rule

```text
PRE_IMPLEMENTATION_CHASSIS_GATE = OPEN
PRODUCT_CORE_EXPANSION = BLOCKED_BY_DECISION_GATE
MIGRATION_AUTHORIZED = NO
```

The gate is closed only by the final evidence-backed ADR in #198 after #195/#197 complete.
