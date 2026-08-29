# Phase 8 runtime retirement gate

Status: executed locally on the Phase 8 runtime-qualification branch.

This gate exists to decide whether the Rust runtime is qualified for operational promotion while the Python oracle remains available as historical reference and test oracle.

Frozen corpus:

- `tests/golden/phase6_shadow_v1.json`
- `tests/phase6_shadow_oracle.py`
- `experiments/rust-chassis-a/metao-testkit/tests/phase6_shadow.rs`

Corpus shape:

- total cases: 44
- comparable cases: 38
- runtime cases: 6
- runtime comparison kind: `NOT_COMPARABLE`

Gate definition:

1. The frozen shadow corpus must replay deterministically for the comparable cases.
2. Runtime qualification must traverse the real Rust path:
   - registry
   - adapter boundary
   - out-of-process execution
   - timeout / crash containment
   - restart / recovery
   - failover
   - evidence capture
   - canonical acceptance
3. Cutover state must promote `runtime` to `RUST_ACTIVE`.
4. Rollback must restore `runtime` to `PYTHON` and be idempotent.
5. Python remains available as oracle/reference; runtime retirement only removes product dependence, not historical evidence.

Executable checks used by this gate:

- `python -m unittest tests.unit.test_phase8_runtime_qualification tests.unit.test_phase7_gated_cutover tests.unit.test_phase6_differential_shadow_mode -v`
- `cargo test -p metao-wire --test restart_recovery`
- `cargo test -p metao-testkit --test phase6_shadow`

Observed gate result on this branch:

- runtime qualification: PASS
- sustained comparable replay: PASS
- rollback: PASS
- Python oracle/reference retained: YES

