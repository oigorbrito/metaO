# MetaO Test Evidence — 2026-10-01

This document records the local/operator validation runs performed after the `v0.2.0-rc.1` release qualification.

## Release qualification

| Test | Result | Evidence |
|---|---|---|
| Local release gate | **PASS 21/21** | `gate-20260930-161814.json` |
| Independent release-evidence validation | **VALID_PASS** | `gate-20260930-161814.json` |
| Exact qualified HEAD | **PASS** | `23fc5c659ae5f0606e9e6774108c44636e29b0ac` |
| RC tag | **PASS** | `v0.2.0-rc.1` |

The release evidence is bound to the exact executable commit above.

## Direct runtime checks

### GPT-6 Luna
- metaO → GPT-6 Luna smoke: **PASS**
- Direct GPT-6 Luna probe: **PASS**
- Codex CLI authentication: **PASS**
- Codex CLI version exercised: `0.154.0`
- Repository mutation in the read-only supervision benchmark: **NONE_READ_ONLY**

### Codex project supervision
- Model discovery selected `gpt-6-astra` for the compatibility probe.
- Real Codex provider turns: **2**
- Work units: `analyze`, `synthesize`
- Project verdict: **PROJECT_ACCEPTED**
- Benchmark exit: **0**
- Cross-provider handoff: **NOT_PROVEN**
- Provider failover: **NOT_TESTED**
- Real multi-provider: **NOT_TESTED**

The earlier `gpt-6-luna` ChatGPT-account incompatibility was resolved by explicit model discovery/selection rather than being interpreted as a provider failure.

## B2 — MetaO workspace-write benchmark

Final adjudication:
- **BENCHMARK_V2_ADJUDICATION = PASS**
- **METAO_CODEX_WORKSPACE_WRITE_BENCHMARK = PASS**
- Negative control: **PASS**
- metaO Codex execution: **PASS**
- Independent tests: **PASS**
- Diff check: **PASS**
- Baseline restored: **PASS**

The first hash check reported `FILE_HASH_RESTORED = FAIL`, but the preserved evidence was subsequently adjudicated and the benchmark was accepted. The disposable worktree was kept for inspection.

## B3 — executor comparison / supervision

### Codex
- Bare: **5/5**
- metaO-supervised: **5/5**
- Success rate: **100% / 100%**
- Median tokens: **35,312 / 35,492**
- Median latency: **13.949s / 12.009s**
- Median token overhead: **0.51%**
- Median latency overhead: **-13.91%**
- **B3_CODEX = PASS**
- Evidence: `benchmark-evidence/b3-codex-20261001-095327/b3-codex-summary.json`

### Antigravity
- Bare: **5/5**
- metaO-supervised: **5/5**
- Success rate: **100% / 100%**
- Median tokens: **33,256 / 49,842**
- Median latency: **22.014s / 22.227s**
- Median token overhead: **49.87%**
- Median latency overhead: **0.97%**
- **B3_ANTIGRAVITY = PASS**
- Evidence: `benchmark-evidence/b3-antigravity-20261001-100053/b3-antigravity-summary.json`

The initial bare runs were blocked by headless command permission. After the local permission configuration was corrected, the reruns completed with no permission denial.

## B4 — cost proxy

### Codex
- Bare: **5/5**
- metaO-supervised: **5/5**
- Median tokens: **35,312 / 35,492**
- Median token overhead: **0.51%**
- Median latency overhead: **-13.91%**

The mixed executor harness initially returned a failing overall status because the run did not complete, but the Codex measurements themselves completed successfully.

### Antigravity
- Bare: **5/5**
- metaO-supervised: **5/5**
- Median tokens: **34,070 / 40,149**
- Median token overhead: **17.84%**
- Median latency: **22.280s / 21.888s**
- Median latency overhead: **-1.76%**
- **B4_ANTIGRAVITY = PASS**
- Evidence: `benchmark-evidence/b4-cost-20261001-101435/b4-antigravity-adjudication.json`

### Gemini
- Gemini CLI availability: **PASS**
- Direct probe: **BLOCKED/FAILED**
- Observed service response: **HTTP 503 UNAVAILABLE** / high demand
- A separate earlier probe also encountered **HTTP 429**
- B4 Gemini benchmark: **not completed**

Therefore there is **no Gemini cost comparison claim** in this evidence set.

## Current pull-request validation

The following GitHub workflow results are additional regression evidence for the current open PR heads. They do **not** replace the exact-head local release qualification above.

| PR | Head | Validation | Result |
|---|---|---|---|
| #733 | `eacf01614787bf9dceb08b71ca7176802d18a837` | CI #1544 | **PASS** |
| #734 | `61f341521868002726896ab789a099b0e64a741c` | CI #1545 | **PASS** |
| #736 | `9b766912b17c78885812803a60f91be6c7a1905a` | CI #1543 | **PASS** |

PR #733 is now restricted to `server.ts`, `src/App.tsx`, `src/components/EventLedgerView.tsx`, and `src/components/StatsBar.tsx`. PR #734 is restricted to `server.ts`, `src/lib/cliSafety.ts`, and `tests/securityHeaders.test.ts`. Unrelated README reversions and agent-journal files were removed before the current CI runs above.

PR #735 itself previously passed CI #1542 before the README discoverability link was added. Its final workflow result belongs in the PR conversation rather than being recursively written into this dated evidence file.

## Additional MetaO test families already evidenced in the repository

The B2/B3/B4 benchmarks above are not the whole MetaO validation surface. The repository's capability and closure documentation records additional executable test families. These are listed here so they are not confused with the executor benchmarks above; they were **not rerun as part of the B2/B3/B4 benchmark sessions**.

### Operator initialization and negative bootstrap

The operational baseline records the clean-room qualification as:
- current full suite: **PASS**
- README quickstart E2E: **PASS**
- installed-console negative-bootstrap E2E: **PASS**
- canonical initialization E2E: **PASS**
- first mission: **ACCEPTED**
- cross-process inspect: **PASS**

The negative-bootstrap integration covers invalid first-run cases and verifies failure without partial mission persistence. The relevant integration test is `tests/integration/test_operator_bootstrap_negative_e2e.py`.

### Rust closure / fault-injection evidence

The recorded local closure evidence includes these executable families:

| Test family | Recorded result / level | Scope boundary |
|---|---|---|
| Durable external-effect dedup + restart | **PASS**, L4 restart / real local external service | Local real process + local real external service; not a generalized hosted provider claim |
| Multiprocess fencing | **PASS**, L4 multiprocess restart | Single-host local authority store; not distributed/hosted HA proof |
| Composed system closure | Executable closure evidence recorded | Composes governance, runtime-health degradation, lost-ACK recovery, fencing, dedup, stage evidence, retry causality and independent acceptance |
| Acceptance budget regression | Executed in release mode | Contract/boundary regression evidence |
| Scientific fault/evidence matrix | Executable evidence matrix | Explicitly separates covered gates from blocked external/toolchain cases |
| Discovery persistence | Executable tests | Reopen/resume, missing state, corrupt payload fail-closed, contract binding mismatch and unresolved-decision persistence |

The repository records the concrete commands for the Rust closure families, including `cargo test -p metao-testkit --test composed_system_closure_tests`, `cargo test -p metao-testkit --test scientific_fault_evidence_tests`, `cargo test -p metao-contracts --test acceptance_budget_tests --release`, and the dedicated multiprocess/external-effect tests.

### Runtime and adversarial boundaries

The capability matrix also records executable coverage for:
- governance budget/approval;
- runtime certification and revocation;
- hostile trust / adversarial acceptance boundaries;
- Rust Project Discovery composition;
- Rust governed execution composition;
- Rust two-runtime conformance.

These should remain evidence-level claims, not be collapsed into the B3/B4 executor success rates.

### Explicitly unclosed / not equivalent to a PASS

The repository also identifies boundaries that remain incomplete or environment-dependent:
- formal TLA+ model execution is **specified but not executed locally** where `tlc`/Java is unavailable;
- a real credential-broker lifecycle is **specified/contracted**, with no real broker configured locally;
- real provider execution for the Rust two-runtime conformance slice is unavailable locally;
- broader hosted/distributed HA and generalized external-provider coverage remain outside the local proof boundary.

These limitations are intentionally retained rather than converted into benchmark PASS claims.

### Documentation consistency note

The capability matrix contains a historical `QUALIFIED_EXECUTABLE_COMMIT` binding that differs from the exact executable commit used by the v0.2.0-rc.1 release evidence documented above. This PR does **not** silently rewrite that historical binding. The release claim remains explicitly bound to `23fc5c659ae5f0606e9e6774108c44636e29b0ac`; reconciling the separate capability-matrix metadata should be treated as a distinct documentation task.

## What these tests establish

These tests establish exercised behavior for the exact local environment and benchmark runs above, including release-gate closure, independent evidence validation, real Codex-backed project supervision, workspace-write supervision and restoration, repeated bare-vs-metaO executor measurements, Antigravity supervision, cost/latency proxy measurements for Codex and Antigravity, and fail-closed behavior in the exercised paths.

They do **not** establish production SLO compliance, security certification, generalized multi-provider failover, generalized Gemini availability, broad provider reliability, production-scale economics, or superiority over simpler governance architectures.

Token counts in B3/B4 are **cost proxies**, not monetary cost. Actual monetary comparison requires the applicable provider pricing and billing context for the exact models/accounts used.