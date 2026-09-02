# Architecture Survival V1

Status: EXPERIMENTAL / NON-AUTHORITATIVE UNTIL REPRODUCED

## Purpose

Compare implementation strategies for metaO by lifecycle cost-benefit, not by repository preservation or rewrite preference.

The comparison unit is a strategy composed from a base plus reusable donor mechanisms. A strategy may preserve the current metaO repository, fork another project, compose libraries, port selected mechanisms, or rebuild a smaller kernel.

## Non-negotiable invariants

1. Executor completion never implies task acceptance.
2. Only metaO authority may authoritatively mutate the Project/WorkGraph plane.
3. Acceptance evidence must bind to the exact execution identity/state it proves.
4. Unknown capacity/runtime/evidence state fails closed.
5. Paid fallback requires explicit authority and budget.
6. Executor transfer requires a reproducible checkpoint bound to verified repository state.
7. Project completion requires independent project-level acceptance.

## Engineering basis

The experiment is designed around:

- reproducible executable evidence rather than self-reported claims;
- exceptional-condition and fail-closed testing;
- exact source/build/run provenance;
- product-quality evaluation across reliability, maintainability, security, performance efficiency, compatibility and related quality characteristics;
- cheapest test capable of falsifying a claim before expensive real-provider testing.

## Scoring model

Hard gates are evaluated before weighted scoring. A hard-gate failure prevents recommendation for production authority regardless of convenience or speed.

Weighted score (100 points):

- Correctness and authority integrity: 20
- Recovery and durability semantics: 15
- Evidence/provenance integrity: 15
- Security and fail-closed behavior: 10
- Maintainability/modularity: 10
- Interoperability/provider neutrality: 8
- Operational simplicity: 7
- Performance efficiency: 5
- Testability/fault-injection quality: 5
- Supply-chain/license/maturity: 5

Lifecycle cost is tracked separately rather than subtracted from quality:

- migration/adaptation effort;
- new LOC and deleted LOC;
- dependency count and infrastructure footprint;
- build/test duration;
- runtime memory/startup where measured;
- provider-addition effort;
- expected maintenance surface;
- upgrade/compatibility burden;
- licensing and external-service burden.

A strategy wins only when its quality clears all hard gates and its lifecycle cost-benefit is better than the alternatives.

## Test pyramid

### L0 — Static/source inspection

- license and provenance;
- dependency surface;
- authority boundaries;
- task/completion semantics;
- verifier independence;
- persistence implementation;
- panic/unwrap/error policy;
- presence of real fault hooks and tests.

### L1 — Native repository qualification

For exact donor HEAD:

- format gate;
- clippy/lint gate where supported;
- native test suite or the closest isolated core suite;
- machine-readable receipt with donor HEAD and CI run identity.

Passing L1 proves only that the donor's own selected gates passed at that exact HEAD. It does not prove metaO fitness.

### L2 — Common deterministic contract tests

All implementation strategies must face the same tests:

1. executor reports DONE without acceptance evidence -> reject;
2. executor proposes/attempts WorkGraph mutation -> no authority transfer;
3. evidence generated for state A and repository moves to state B -> evidence inapplicable;
4. malformed/unknown provider state -> block/fail closed;
5. paid fallback without authority -> reject;
6. invalid DAG (cycle/orphan/duplicate) -> no dispatch;
7. all tasks complete but a mandatory requirement remains unsatisfied -> project incomplete.

### L3 — Fault and durability tests

1. process crash after durable step A and before step B;
2. restart in a fresh process;
3. duplicate-effect window around checkpoint persistence;
4. database/storage interruption;
5. filesystem permission denial;
6. Git HEAD/base drift;
7. truncated/corrupt checkpoint;
8. timeout/cancellation during external effect;
9. provider temporarily rate-limited;
10. provider quota exhausted with evidenced recovery;
11. current executor disappears and compatible executor resumes;
12. handoff checkpoint HEAD mismatch -> reject.

### L4 — Real runtime/provider tests

Only after L0-L3 pass:

- at least three executor/provider families where practical;
- real session start/status/cancel/resume;
- quota/rate-limit observations where observable;
- cross-executor failover;
- real worktree execution and independent acceptance.

### L5 — Whole-project trial

The same bounded project specification is supplied to each surviving strategy. Measure decomposition, dispatch, supervision, recovery, failover, independent acceptance, final project verdict, elapsed time, provider cost and evidence completeness.

## Initial donor qualification matrix

The first CI matrix qualifies these implementation sources at exact observed HEADs:

- AKMessi/pactrail
- Kilbex/Vigla
- microsoft/duroxide
- SamuelXing/durare
- agentclientprotocol/rust-sdk
- current metaO Rust chassis baseline

Other donors remain eligible for mechanism-specific tests after their capability enters a surviving strategy.

## Stop rules

Immediately classify a strategy as not production-authoritative if any tested path allows:

- executor self-report to become acceptance;
- executor-owned authoritative WorkGraph mutation;
- stale or mismatched evidence to authorize integration;
- unknown state to become success;
- unauthorized paid dispatch;
- unreproducible handoff to resume;
- retry amplification or uncontrolled duplicate side effects;
- infrastructure failure to manufacture a passing result.

## Evidence policy

Every empirical claim must include at minimum:

- exact source repository and commit SHA;
- exact test command;
- runner/platform identity;
- result and exit status;
- logs/artifacts where available;
- explicit claim scope and limitations.

No README claim, release note, green badge, simulated test, or prior SHA is sufficient evidence for a stronger claim without reproduction.