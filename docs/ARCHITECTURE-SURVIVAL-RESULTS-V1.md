# Architecture Survival Results V1

Status: IN PROGRESS / NON-AUTHORITATIVE

This file records evidence observed during the first architecture-survival qualification wave. It deliberately separates independent reproduction from upstream project CI.

## Evidence classes

- `INDEPENDENT_REPRODUCED`: commands executed by the metaO harness at an exact donor SHA with retained logs/receipt.
- `UPSTREAM_CI_GREEN`: donor-owned GitHub Actions completed successfully at the exact audited SHA. Useful evidence, but not independent reproduction.
- `SOURCE_INSPECTED`: conclusion derived from exact source/code inspection.
- `RUNNER_INFRA_BLOCKED`: the metaO harness never reached step execution. This is neither donor PASS nor donor FAIL.

## metaO harness run

Repository: `tihotm/metaO`
PR: `#361`
Harness branch: `experiments/architecture-survival-v1`
Harness head when first run was created: `d3a8ef100628bb2f92172c0aaa2b539226b81859`
Workflow run: `33578262151`

Two attempts were observed. On the second attempt all six jobs completed with `failure` and zero reported workflow steps:

- `metao-current-baseline`
- `donor-vigla`
- `donor-duroxide`
- `donor-pactrail`
- `donor-durare`
- `donor-acp-rust-sdk`

No job log blob or qualification artifact was produced. Because even the local metaO baseline failed before checkout/setup, the wave is classified `RUNNER_INFRA_BLOCKED`; no implementation received an empirical PASS/FAIL from this run.

## Exact audited heads and upstream CI

| Candidate | Exact audited HEAD | Upstream CI at exact HEAD | Current evidence class |
|---|---|---|---|
| Pactrail | `582a22db473b455f7f5bdc185bf430639b88a49f` | CI run `30330302253` = success | `UPSTREAM_CI_GREEN` + `SOURCE_INSPECTED` |
| Vigla | `bbd19ae2d5a77401502756c550b5dcd4ae59bbc9` | CI run `30273215212` = success | `UPSTREAM_CI_GREEN` + `SOURCE_INSPECTED` |
| Duroxide | `8ecb61debc771480bfccd0d93f272a5679f1f840` | CI run `33404693680` = success | `UPSTREAM_CI_GREEN` + `SOURCE_INSPECTED` |
| Durare | `1eea2ce3c2e849c70cef81cd048c8ed7d1267d9f` | CI run `31920657197` = success | `UPSTREAM_CI_GREEN` + `SOURCE_INSPECTED` |
| ACP Rust SDK | `c63610fc38a642f7a73ba2719f403f17d771c345` | security and other workflows present at exact HEAD; upstream success observed | `UPSTREAM_CI_GREEN` + `SOURCE_INSPECTED` |
| metaO current | `2710a2580f6510c479e19c24b6dd4ee491bcdbc9` base of PR #361 | independent run blocked before steps | existing project evidence only; new wave `RUNNER_INFRA_BLOCKED` |

## Upstream CI detail that materially affects scoring

### Pactrail

Exact-head CI shows successful jobs including:

- `cargo fmt --all -- --check`;
- `cargo clippy --workspace --all-targets --all-features --locked -- -D warnings`;
- `cargo test --workspace --all-features --locked`;
- permission/storage failure recovery matrix;
- hostile-repository OCI containment checks;
- dependency-policy checks;
- release build.

However, Pactrail's own latest published post-upgrade real-issue benchmark at this HEAD reports a functional failure that must be counted rather than hidden: on the frozen regression campaign Pactrail passed `0/6` while OpenCode passed `2/6`; its source isolation and trace integrity remained intact in all six Pactrail runs. This is evidence of strong containment/evidence mechanics but a material execution-policy effectiveness risk. It is not a reason to discard its transaction/evidence mechanisms.

### Vigla

Exact-head CI run `30273215212` includes a successful Rust job with format, check, clippy, release clippy, tests, optional embedding tests, generated binding verification, license verification, recovery-receipt reproduction, and audit. Separate supply-chain, browser E2E and frontend jobs also completed successfully.

Source inspection additionally found:

- worker progress is self-reported/advisory and not treated as arbiter evidence;
- audit executes tests/lint against the worktree rather than merely recording the worker's claim;
- infrastructure errors propagate rather than manufacturing a pass;
- decomposition is validated as a DAG before dispatch;
- arbiter decisions are separate from worker completion.

This is currently the strongest observed project-level supervision alignment among external candidates, but its supervisor/decomposition authority still needs a common metaO authority test.

### Duroxide

Exact-head upstream CI is green. Source inspection found SQLite provider support plus provider-test/test-hooks/replay-oriented features. It remains a durability component candidate, not a project-authority implementation. The critical unresolved question is duplicate-effect behavior in the crash window around effect completion and checkpoint persistence.

### Durare

Exact-head upstream CI is green. Source inspection found SQLite/Postgres backends, failpoints and transaction semantics designed for re-runnable bodies and serialization/deadlock restart. It remains in direct comparison with Duroxide. The decisive test is the common metaO crash/restart/idempotency harness, not feature count.

### ACP Rust SDK

Current main HEAD is `c63610fc38a642f7a73ba2719f403f17d771c345`. Upstream workflows at that exact SHA include successful security automation. Source inspection confirms the Rust SDK exposes Client/Agent/Proxy/Conductor-oriented protocol layers and supporting crates. ACP is evaluated as an executor transport boundary, not as a project-control-plane replacement.

## L0 provisional scoring direction

These are directional scores only. They are deliberately not final 0-100 scores because independent L1 and common L2/L3 tests have not executed yet.

| Candidate/mechanism | Authority fit | Evidence integrity | Durability | Operational fit | Current direction |
|---|---|---|---|---|---|
| metaO current core | strongest by contract | strong existing contracts | incomplete operational proof | relatively small | baseline to beat |
| Vigla | strong, one authority mismatch to test | strong independent audit design | meaningful recovery mechanisms | medium/high surface | leading external project-level candidate |
| Pactrail | not a full Project Plane | very strong | strong transaction/checkpoint primitives | medium surface | leading evidence/transaction donor; execution-policy risk |
| Duroxide | N/A as Project Plane | neutral/component | very strong candidate | small embedded runtime | durability finalist |
| Durare | N/A as Project Plane | neutral/component | very strong candidate | small/medium embedded runtime | durability finalist |
| ACP Rust SDK | N/A as Project Plane | neutral transport | session/protocol only | strong simplification potential | executor-boundary favorite |

## Hard-gate findings already established by source inspection

- Roder is not a direct authority-compatible base: its task ledger and verification review are model-visible tools; the model can replace ledger state and submit its own verification metadata. Keep provider/extension/eval mechanisms only.
- Forge is not a direct authority-compatible base without rewiring: inspected `MultiAgentOrchestrator` transitions a task to `Done` when its agent `EventLoop` succeeds; its verification loop exists separately and a legacy path does not govern that completion transition.
- ccswarm is not a current whole-control-plane replacement: its inspected event model still lacked heartbeat/checkpoint/cancellation/timeout/reconciliation semantics needed by metaO.

These findings eliminate unnecessary whole-project fork experiments while preserving mechanism-level donor value.

## Next executable gates

Once any independent runner is available, execute in this order:

1. Reproduce exact-head native qualification for all five external sources and metaO baseline.
2. Freeze common deterministic L2 contract fixtures for authority/evidence semantics.
3. Implement one minimal adapter per surviving strategy to those fixtures.
4. Run Duroxide vs Durare vs minimal SQLite baseline under identical crash/restart/effect-dedup tests.
5. Run ACP against at least three real executor families without granting ACP any Project Plane authority.
6. Build the first lifecycle cost ledger: added/deleted LOC, dependencies, build/test duration, runtime footprint, migration complexity and expected maintenance surface.

No migration/fork decision is authorized from this file alone.