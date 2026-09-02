# Architecture Survival Results V1

Status: IN PROGRESS / NON-AUTHORITATIVE

This file records evidence observed during the first architecture-survival qualification wave. It deliberately separates independent reproduction from upstream project CI.

## Evidence classes

- `INDEPENDENT_REPRODUCED`: commands executed by the metaO harness at an exact donor SHA with retained logs/receipt.
- `UPSTREAM_CI_GREEN`: donor-owned GitHub Actions completed successfully at the exact audited SHA. Useful evidence, but not independent reproduction.
- `SOURCE_INSPECTED`: conclusion derived from exact source/code inspection.
- `RUNNER_INFRA_BLOCKED`: the metaO harness never reached step execution. This is neither donor PASS nor donor FAIL.

## metaO harness status

Repository: `tihotm/metaO`
PR: `#361`
Harness branch: `experiments/architecture-survival-v1`
Current audited harness head: `83d70f55f5659656e3c995824a21e3f056169392`

The current observed workflow runs are:

- CI run `33578577609` -> `failure`
- Architecture Survival V1 run `33578577623` -> `failure`

The Architecture Survival run contained all six expected jobs:

- `metao-current-baseline`
- `donor-vigla`
- `donor-duroxide`
- `donor-pactrail`
- `donor-durare`
- `donor-acp-rust-sdk`

Each job completed with `failure`, but GitHub reported an empty `steps` array and no assigned runner identity. No qualification artifact was produced. The ordinary metaO CI job on the same commit also failed with zero reported steps.

Because both the metaO baseline and every donor matrix job failed before checkout/setup, the independent wave is classified `RUNNER_INFRA_BLOCKED`. No implementation received an empirical PASS or FAIL from these runs.

This is a harness-environment finding, not a donor-code finding.

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

Exact-head CI run `30330302253` completed successfully.

The exact-head qualification evidence is useful for build/test discipline, but it does not prove metaO fitness.

A separate published post-upgrade real-issue benchmark at this audited line reported a functional effectiveness risk that must remain visible in scoring: Pactrail's containment and trace integrity mechanisms remained intact while its frozen regression campaign did not demonstrate strong issue-solving success. This does not invalidate its transaction/evidence mechanisms; it limits any claim that Pactrail should automatically become the project-level executor.

### Vigla

Exact-head CI run `30273215212` completed successfully.

Source inspection additionally found:

- worker progress is self-reported/advisory and not treated as arbiter evidence;
- audit executes tests/lint against the worktree rather than merely recording the worker's claim;
- infrastructure errors propagate rather than manufacturing a pass;
- decomposition is validated as a DAG before dispatch;
- arbiter decisions are separate from worker completion.

This remains the strongest observed project-level supervision alignment among external candidates, but its supervisor/decomposition authority still needs the common metaO L2 authority test.

### Duroxide

Exact-head upstream CI is green. Source inspection found SQLite provider support plus provider-test/test-hooks/replay-oriented features. It remains a durability component candidate, not a project-authority implementation. The critical unresolved question is duplicate-effect behavior in the crash window around effect completion and checkpoint persistence.

### Durare

Exact-head upstream CI is green. Source inspection found SQLite/Postgres backends, failpoints and transaction semantics designed for re-runnable bodies and serialization/deadlock restart. It remains in direct comparison with Duroxide. The decisive test is the common metaO crash/restart/idempotency harness, not feature count.

### ACP Rust SDK

Current audited HEAD is `c63610fc38a642f7a73ba2719f403f17d771c345`. Source inspection confirms the Rust SDK exposes Client/Agent/Proxy/Conductor-oriented protocol layers and supporting crates. ACP is evaluated as an executor transport boundary, not as a project-control-plane replacement.

## L0 provisional scoring direction

These are directional findings only. They are deliberately not final 0-100 scores because independent L1 and common L2/L3 tests have not executed yet.

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

The L2 contract is now frozen in `docs/ARCHITECTURE-SURVIVAL-L2-CONTRACT-V1.md`.

Execution order:

1. Execute L2 against current metaO contracts first.
2. Build the thinnest adapter necessary for each external mechanism.
3. Mark unsupported boundaries explicitly.
4. Execute all seven fixtures deterministically.
5. Run Duroxide vs Durare vs minimal SQLite baseline under identical crash/restart/effect-dedup tests.
6. Run ACP against at least three real executor families without granting ACP any Project Plane authority.
7. Build the first lifecycle cost ledger: added/deleted LOC, dependencies, build/test duration, runtime footprint, migration complexity and expected maintenance surface.

No migration/fork decision is authorized from this file alone.
