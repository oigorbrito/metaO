# Post-MVP Convergence Wave 1

Status: EXECUTION_CANDIDATE_NOT_YET_QUALIFIED
Base: `main` at `b57017c8bd98f6a3c8ce2331fd2a9e8cfa0da437`
Branch: `post-mvp/convergence-wave1-v1`

## Purpose

Converge two useful but diverged post-MVP implementation lines onto the current main lineage without replaying stale history or treating old branch ancestry as authority.

Sources:

- PR #364 / `feat/github-governed-adapter`: governed GitHub repository adapter and deterministic unit coverage.
- PR #352 / `post-v0.1/dynamic-executor-supervision-v1`: provider-neutral executor capacity/failover kernel and engineering knowledge authority kernel with focused tests.

## Convergence rule

`TRANSPLANT_CURRENT_SEMANTICS != CHERRY_PICK_STALE_HISTORY`

Only files or semantics still compatible with the current canonical baseline are copied. The old #352 `[lib] path = "src/root.rs"` change is intentionally NOT transplanted because current main already owns a canonical `src/lib.rs`. The existing main `Cargo.toml` is also preserved because it already contains the required serde/serde_json/proptest dependencies.

## Converged GitHub slice

- `src/metao/github_adapter.py`
- `tests/unit/test_github_adapter.py`
- `tests/unit/test_github_adapter_v2.py`

Properties represented:

- deterministic reads do not require mutation authority;
- issue/branch/file/PR/review/merge mutations require exact operation-scoped authorization;
- workflow run and workflow job reads are explicit GitHub Actions primitives;
- merge binds expected head SHA;
- normalized evidence excludes credentials.

## Converged dynamic supervision slice

- `experiments/rust-chassis-a/metao-contracts/src/executor_capacity.rs`
- `experiments/rust-chassis-a/metao-contracts/tests/executor_capacity_tests.rs`

Properties represented:

- explicit rate-limit/quota/concurrency/credit/spend/provider/auth/account/capability/unknown states;
- `Continue`, evidenced retry, park-until, failover and block decisions;
- hard eligibility before ranking;
- free-before-paid behavior with explicit paid budget authority;
- deterministic reliability/cost/tie-break ranking;
- short evidenced free recovery may be preferred over paid fallback;
- verified checkpoint rejects Git HEAD mismatch;
- executor completion never implies metaO acceptance.

## Converged engineering-knowledge slice

- `experiments/rust-chassis-a/metao-contracts/src/engineering_knowledge.rs`
- `experiments/rust-chassis-a/metao-contracts/tests/engineering_knowledge_tests.rs`

Properties represented:

- authorized source and freshness checks;
- stronger empirical evidence can conflict with weaker project documentation;
- hard safety/policy conflict remains non-overridable;
- non-hard deviation requires risk-derived explicit confirmation;
- stale material evidence requires refresh;
- vendor/country identity has no independent engineering-authority weight.

## Deliberately not yet promoted

- old #352 `src/root.rs` and Cargo `[lib]` override;
- old #364 dedicated hosted workflow, because hosted Actions remains externally blocked and no new workflow is required to execute the local qualification gate;
- architectural/product PASS claims from either old PR;
- raw local evidence from issue #367 until independently promoted.

## Required local qualification (B0)

Run on the exact convergence branch HEAD and retain raw outputs:

```text
python -m unittest tests.unit.test_github_adapter tests.unit.test_github_adapter_v2 -v
cargo fmt --all --check --manifest-path experiments/rust-chassis-a/Cargo.toml
cargo clippy --manifest-path experiments/rust-chassis-a/Cargo.toml --workspace --all-targets --all-features -- -D warnings
cargo test --manifest-path experiments/rust-chassis-a/Cargo.toml -p metao-contracts --test executor_capacity_tests --test engineering_knowledge_tests
cargo test --manifest-path experiments/rust-chassis-a/Cargo.toml --workspace --all-targets --all-features
```

The root `experiments/rust-chassis-a/Cargo.toml` is a virtual workspace manifest. The earlier `cargo fmt --check --manifest-path ...` form could fail with `Failed to find targets` because no root package is selected. `--all` is therefore part of the reproducible formatting gate and selects all workspace packages without weakening the scope.

## Remaining wiring before product promotion

The two new Rust modules are intentionally testable through `#[path]` before touching the current large `metao-contracts/src/lib.rs`. After B0 passes, add exactly:

```rust
pub mod engineering_knowledge;
pub mod executor_capacity;
```

to the canonical module declarations in `src/lib.rs`, rerun focused tests and full workspace regression, then evaluate integration into the public product path.

## Evidence state

```text
GITHUB_ADAPTER_CODE_CONVERGED = YES
DYNAMIC_SUPERVISION_CODE_CONVERGED = YES
ENGINEERING_KNOWLEDGE_CODE_CONVERGED = YES
STALE_HISTORY_REPLAYED = NO
CURRENT_CARGO_ROOT_REPLACED = NO
FOCUSED_TESTS_ON_CONVERGENCE_HEAD = NOT_TESTED
FULL_REGRESSION_ON_CONVERGENCE_HEAD = NOT_TESTED
RUST_MODULES_PUBLICLY_WIRED = NO
REAL_PROVIDER_FAILOVER = NOT_TESTED
PRODUCT_PROMOTION = NOT_AUTHORIZED
```
