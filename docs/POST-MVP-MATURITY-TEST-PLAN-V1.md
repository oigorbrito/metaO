# POST-MVP MATURITY TEST PLAN V1

Status: execution plan draft
Parent: #357
Related: #351 #353 #354 #355 #358 #359 #360

## 1. Purpose

Move metaO from provider-neutral contracts to operationally evidenced supervision of real projects and replaceable external executors. The target is not "many adapters"; it is proof that metaO owns decomposition, scheduling, supervision, failover, engineering judgment, acceptance and project completion while executors remain bounded workers.

This plan preserves the canonical evidence ladder from `POST-MVP-OPERATIONAL-BASELINE-V1.md`: L0 concept, L1 specified, L2 implemented, L3 wired, L4 focused tested, L5 regression tested, L6 integration tested, L7 operational evidence. No higher claim may be inferred from a lower level.

## 2. Engineering rationale

The plan is anchored in established engineering patterns rather than provider-specific opinion:

- scheduler feasibility filtering before scoring/ranking;
- capacity-aware scheduling and delayed requeue when capacity returns;
- bounded retries with exponential backoff and jitter;
- checkpoint/recovery with task state external to executors;
- independent acceptance authority;
- supply-chain/trust qualification before third-party software/services receive sensitive assets;
- secure SDLC verification and validation;
- continuous monitoring of deployed AI/runtime behavior because pre-deployment evaluation alone is insufficient;
- quality goals and acceptance criteria treated as measurable product characteristics.

Key references: Kubernetes Scheduling Framework; Google SRE overload/capacity guidance; AWS Builders Library retries/backoff/jitter; NIST SP 800-161 Rev.1; NIST SP 800-218 SSDF; NIST AI RMF/TEVV resources; ISO/IEC 25010:2023.

## 3. Execution rule

Every block must answer five questions before promotion:

1. What property are we trying to establish?
2. Why is that property necessary for metaO's product thesis?
3. What evidence would falsify the claim?
4. What test level is sufficient for this block?
5. What exact evidence binds the result to the candidate commit/configuration/runtime?

## 4. Work split

### Chat / GitHub-capable work

The chat can perform: current documentation research; issue/roadmap maintenance; contract and deterministic code review; GitHub branch/PR changes; static consistency checks; review of CI results/logs; creation of fixtures/test matrices; comparison of documented provider semantics; audit of authority/provenance boundaries.

### Executor/local/authorized-environment work

An executor or local environment is required for: `cargo fmt`, `clippy`, and full Cargo execution when hosted CI is blocked; authenticated calls to real Jules/Codex/Gemini/DeepSeek/etc.; provider quota/rate experiments; local workspace/process observation; fault injection involving processes/network/filesystem; real Git worktree/remote reconciliation; secret-bearing integrations; multi-hour operational trials.

The chat must not claim L4-L7 evidence for tests that were only written or reasoned about.

## 5. Ordered test/maturity blocks

### B0 — Qualify current dynamic supervision + knowledge kernel

Concept/end state: establish that #353/#355 compile, lint and pass their deterministic acceptance matrix at the exact PR head.

Why it matters: all later provider adapters depend on the provider-neutral semantics. A broken kernel would multiply defects across every executor integration.

Why viable: the code is already implemented and deterministic tests exist; the remaining uncertainty is executable qualification.

Estimated engineering effort: 1-3 h if local Rust environment is healthy; 3-6 h if build/wiring defects surface.

Owner: executor/local environment for execution; chat for triage, patch review and GitHub updates.

Required evidence:
- `cargo fmt --check`
- `cargo clippy --workspace --all-targets --all-features -- -D warnings`
- `cargo test --workspace --all-targets --all-features`
- focused executor-capacity and engineering-knowledge tests
- exact commit SHA and command output

Exit: L5 for the deterministic kernel, no false PASS from hosted pre-step failures.

### B1 — Property/adversarial expansion of the kernel

Concept/end state: prove invariants over ranges/combinations rather than only examples.

Why: schedulers and failover logic fail at edge combinations: zero budget, unknown recovery, equal scores, inconsistent checkpoints, stale evidence, conflicting source strengths.

Why viable: pure provider-neutral functions are suitable for proptest/table-driven testing.

Estimated effort: 3-6 h.

Owner: chat can design/review tests; executor runs them.

Required cases:
- arbitrary candidate ordering does not change deterministic winner except documented tie-break;
- unqualified candidate is never selected regardless of score/cost;
- paid executor never crosses hard budget authority;
- unknown capacity/recovery never fabricates reset time;
- HEAD mismatch always blocks handoff;
- stale material knowledge never becomes authoritative without refresh;
- hard policy conflict is not overridden by repeated confirmation.

Exit: L5 with property/adversarial evidence.

### B2 — Circuit breaker, retry budget and recovery admission

Concept/end state: prevent retry storms and repeated assignment to unhealthy executors.

Why: Google SRE and AWS reliability guidance show retries can amplify overload and produce cascading failure; jitter/backoff and bounded retries are standard mitigations.

Why viable: deterministic virtual-time tests can establish state transitions before real-provider trials.

Estimated effort: 4-8 h.

Owner: executor implementation/tests; chat specification/review.

Tests:
- CLOSED -> OPEN after configured factual failure threshold;
- OPEN rejects new scheduling;
- HALF_OPEN admits bounded probes only;
- successful probes restore eligibility;
- failed probes reopen circuit;
- retry budget exhaustion causes failover/park rather than infinite retry;
- jitter distribution is bounded and avoids identical retry timestamps in a simulated cohort.

Exit: L5 deterministic; later B7 calibrates thresholds empirically.

### B3 — Durable checkpoint + local/Git/remote reconciliation

Concept/end state: make executor replacement reproducible from repository/evidence state rather than chat history.

Why: cross-agent continuity is impossible to guarantee if authoritative state remains inside one provider session.

Why viable: metaO already has execution/evidence/recovery primitives and repository-convergence fixtures.

Estimated effort: 6-12 h.

Owner: executor/local environment.

Tests:
- checkpoint binds task id, base, branch, HEAD, attempt and evidence;
- receiving executor refuses divergent HEAD;
- local clean / remote divergent is detected;
- local dirty/untracked state is represented and blocks unsafe transfer;
- accepted commit can be resumed by a second adapter without original chat/session context;
- crash between commit and ledger update is reconciled deterministically;
- duplicate dispatch is fenced/idempotent.

Exit: L6 in local multiprocess/integration harness.

### B4 — Provider adapter contract and first real adapter: Jules

Concept/end state: one real external coding agent is supervised through provider-neutral contracts.

Why: Jules exposes sessions/activities/plan approval and therefore exercises dispatch, observe, intervention and evidence without giving acceptance authority to the executor.

Why viable: official API exists; metaO already has runtime adapter/admission/certification patterns.

Estimated effort: 6-12 h implementation + 2-4 h real smoke/negative tests.

Owner: executor for authenticated implementation/runtime tests; chat for current API verification and review.

Tests:
- source/repo authorization;
- session creation;
- require plan approval where supported;
- execution blocked before metaO approval;
- activity/status normalization;
- provider auth failure;
- quota/rate signal normalization;
- unknown provider state fails closed;
- `COMPLETED` remains non-authoritative until metaO acceptance;
- artifact/PR binds to task/session/repository evidence.

Exit: L7 `REAL_RUNTIME` for bounded Jules slice.

### B5 — Adapter diversity wave

Concept/end state: prove that core behavior survives provider replacement.

Initial adapters: Codex/OpenAI, Gemini/Antigravity-supported surfaces, DeepSeek and other user-authorized executors/sub-agents where an automatable integration boundary exists.

Why: metaO's frozen invariant requires replacing an orchestrator/executor without changing Core.

Why viable: the provider-neutral kernel and first adapter establish the normalization seam.

Estimated effort: 4-10 h per adapter depending on API/CLI quality; 2-4 h qualification test per adapter.

Owner: executor/local + authorized credentials; chat researches official docs and compares semantics.

Minimum adapter acceptance:
- capabilities discovery/config;
- dispatch/observe;
- quota/rate/account classification when observable;
- artifact/evidence collection;
- auth failure;
- execution failure;
- unknown state fail closed;
- cancellation/intervention where provider supports it;
- one real-runtime smoke.

Exit: at least three materially different real execution surfaces at L6/L7 before broad claims of provider neutrality.

### B6 — Cross-provider failover experiment

Concept/end state: start a task on executor A, force a capacity/provider failure, continue on B and independently accept the result.

Why: this is the core continuity property behind quota-aware supervision.

Why viable: B3 supplies checkpointing; B4/B5 supply real adapters.

Estimated effort: 6-10 h for first controlled experiment; 2-4 h per additional provider pair.

Owner: executor/local authorized environment.

Fault matrix:
- quota exhausted;
- transient rate limit;
- provider unavailable;
- auth revoked;
- process/session terminated;
- incompatible capability discovered mid-task.

Metrics:
- failover detection latency;
- handoff time;
- duplicate work;
- lost/invalid commits;
- acceptance failure rate;
- total task time;
- incremental monetary cost.

Exit: L7 `REAL_RUNTIME + FAULT_INJECTION` for at least one A->B path.

### B7 — Empirical calibration (#358)

Concept/end state: select defaults from measurements, not intuition.

Why: 1/3/5-minute polling, retry thresholds, wait-for-free and ranking weights are policy values, not universal truths.

Why viable: B4-B6 create a repeatable workload and observable providers.

Estimated effort: 8-16 h of engineering/operator time plus automated experiment runtime.

Owner: executor/local trial; chat analyzes results and updates policy/docs.

Candidate supervision fallback intervals: 30s, 60s, 180s, 300s where provider limits permit. Prefer event-driven observations when available.

Measure:
- detection latency;
- monitoring API/quota cost;
- MTTR;
- duplicate dispatch/work;
- provider throttling caused by supervision;
- completion time;
- paid fallback cost;
- false-positive failovers.

Exit: evidence-backed defaults plus configurable override; no claim that one cadence is globally optimal.

### B8 — Engineering Knowledge Authority operationalization

Concept/end state: metaO's technical recommendations are bound to authorized, fresh sources and empirical evidence, with explicit conflict/override semantics.

Why: project docs, junior user instructions or an LLM's unsupported assertion must not automatically become engineering authority.

Why viable: #355 provides initial domain rules; source refresh can be built incrementally.

Estimated effort: 8-16 h for registry/persistence/refresh decision engine; 4-8 h for initial source adapters and fixtures.

Owner: chat can research and seed official-source contracts; executor implements persistence/scheduler/source ingestion.

Tests:
- unauthorized source cannot update authoritative knowledge;
- stale source produces REQUIRE_REFRESH for material decision;
- newer source does not win merely by date if evidentiary authority is weaker;
- empirical reproduced evidence can conflict with project documentation and must be surfaced;
- conflicting authoritative sources produce explicit unresolved conflict, not fabricated certainty;
- non-hard user deviation preserves adverse evidence and waiver provenance;
- hard safety/policy constraint remains blocked;
- country/vendor identity has no independent authority weight;
- manual vs automatic refresh policy is auditable.

Exit: L6 with deterministic source fixtures; L7 only after live refresh observation.

### B9 — Executor Market Scout + supply-chain qualification (#354)

Concept/end state: discover new capacity without equating internet discovery with trust or authorization.

Why: project continuity should not require a compile-time provider catalog, while third-party services create supply-chain/data-exposure risks.

Why viable: NIST C-SCRM provides a risk-management basis; metaO already has runtime certification/security concepts.

Estimated effort: 10-20 h for scout/registry/qualification pipeline; additional provider qualification time varies.

Owner: executor implementation; chat performs source research and qualification criteria review.

Tests:
- discovery writes only to untrusted/discovered registry;
- scout cannot authorize spending/credentials;
- source provenance/freshness/confidence mandatory;
- unknown candidate gets synthetic/canary repo only;
- data-handling claim absent -> restricted/no sensitive access;
- failed canary -> UNQUALIFIED/BLOCKED;
- qualification certificate expires/revokes;
- vendor/country alone never approves/rejects;
- explicit user/provider policy can constrain allowed regions for legal/data-governance reasons, with the policy—not nationality prejudice—as authority.

Exit: L6 synthetic qualification; L7 after at least one newly discovered candidate is safely qualified in a non-sensitive trial.

### B10 — Project decomposition/work graph authority

Concept/end state: given a project objective once, metaO creates and owns the authoritative work graph; executors may report discoveries but cannot mutate it directly.

Why: without this, metaO is only a router and the project manager remains the executor/human.

Why viable: ProjectContract, clarification, discovery coordinator and project-completion contracts already exist in the Rust chassis.

Estimated effort: 12-24 h depending on planner implementation maturity.

Owner: executor implementation; chat designs acceptance fixtures/reviews.

Tests:
- vague objective becomes traceable requirements + work units;
- each work unit traces to a requirement/acceptance criterion;
- executor discovery becomes a proposed dependency/event only;
- only metaO commits work-graph mutation;
- cycles/invalid dependencies fail closed;
- replan preserves history/provenance;
- user-fixed requirements remain fixed unless explicit governed revision;
- metaO recommendation remains distinct from user requirement.

Exit: L6 deterministic/integration work-graph path.

### B11 — Whole-project autonomous supervision E2E (#360)

Concept/end state: prove the product thesis on a bounded but complete project.

Suggested specimen: small API/service with authentication, persistence, tests, containerization and CI; acceptance must be machine-verifiable.

Why: individual runtime tests do not prove meta-orchestration.

Why viable: B0-B10 establish the necessary pieces independently before composition.

Estimated effort: 8-16 h engineering setup plus 4-12 h experiment/operator runtime depending on provider latency and project size.

Owner: executor/local environment, supervised/reviewed through chat/GitHub.

Required observations:
- user supplies project objective once;
- no manual task decomposition;
- metaO creates >1 work unit;
- >1 executor is used;
- at least one capacity/outage fault is injected;
- metaO checkpoints and transfers task;
- at least one failed work result is detected;
- metaO creates corrective/replanned work;
- executor completion alone never accepts;
- final independent acceptance passes or project ends evidence-backed BLOCKED;
- traceability requirement -> work unit -> commit/artifact -> test/evidence -> verdict.

Exit: L7 `REAL_RUNTIME + REAL_EXTERNAL_SYSTEM + FAULT_INJECTION` for the bounded project slice.

### B12 — Security/hostile and operational fault closure

Concept/end state: prove metaO remains safe under hostile/exceptional boundaries, not just happy-path AI failures.

Why: operational maturity requires filesystem, process, network, credential, Git and resource-failure behavior; secure development frameworks require verification beyond functionality.

Estimated effort: 12-24 h initial matrix; larger exhaustive campaigns are separate.

Owner: executor/local sandbox.

Fault families:
- filesystem permissions/path traversal/symlinks;
- Git divergence/conflicts/force-updated remote;
- expired/revoked credentials;
- malformed provider payloads;
- process timeout/crash;
- network partitions/timeouts;
- evidence truncation/corruption;
- resource exhaustion;
- concurrent duplicate supervisors;
- hostile executor attempts to expand scope or access unauthorized files.

Exit: L6/L7 fault/adversarial evidence for closure-target boundaries.

### B13 — Release/convergence gate

Concept/end state: bind all claims to the exact candidate and make documentation/status truthful.

Estimated effort: 3-6 h after other blocks are green.

Owner: chat + executor.

Required:
- capability map updated by evidence level;
- traceability updated;
- exact SHA local release gate;
- no unresolved product-critical blocker mislabeled as external;
- hosted CI separately classified if still blocked;
- branch/main/PR convergence checked;
- post-MVP baseline revised only after actual evidence exists.

Exit: candidate eligible for post-MVP maturity baseline promotion.

## 6. Recommended critical path

B0 -> B1 -> B2/B3 -> B4 -> B5 -> B6 -> B7

In parallel after B0: B8.

After B8 base exists: B9.

B10 can proceed in parallel with B4-B9 provided it does not alter the provider-neutral capacity contracts without impact analysis.

Composition: B11 only after B3+B4 and at least one second real executor from B5. B12 must run before final maturity promotion. B13 is last.

## 7. Estimated total engineering effort

These are planning ranges, not delivery promises. Assuming the existing repository primitives are reusable and provider credentials/environments are available:

- Kernel qualification/adversarial closure (B0-B3): ~14-29 h
- Real adapters + failover + calibration (B4-B7): ~26-52 h plus provider experiment runtime
- Knowledge authority + market scout (B8-B9): ~22-44 h
- Project authority + whole-project E2E (B10-B11): ~24-52 h
- Hostile/fault/release closure (B12-B13): ~15-30 h

Total engineering/operator effort order of magnitude: ~101-207 h. This is deliberately a range because real-provider integration quality and fault findings dominate uncertainty. It should be reduced by reusing already-proven metaO runtime/certification/recovery infrastructure rather than rebuilding it.

## 8. Test pyramid for this roadmap

For every new capability, prefer the cheapest test capable of falsifying the claim:

1. Static/type/validation tests.
2. Deterministic unit/table tests.
3. Property/adversarial tests.
4. Integration with fake provider and virtual time.
5. Multiprocess/local Git tests.
6. Real provider smoke/negative tests.
7. Cross-provider fault-injection experiment.
8. Whole-project operational trial.

Do not jump directly to expensive agent runs for logic that can be falsified deterministically.

## 9. Metrics to retain across experiments

- task success/acceptance rate;
- executor self-reported success vs independent acceptance discrepancy;
- failure detection latency;
- MTTR;
- failover frequency;
- handoff failure/duplicate-work rate;
- quota/rate-limit incidence;
- retries per task;
- monitoring overhead;
- monetary cost per accepted work unit/project;
- elapsed time per accepted work unit/project;
- stale/insufficient-knowledge decision rate;
- number of user overrides and resulting acceptance defect rate;
- security/qualification rejection rate.

## 10. Stop/rollback rules

Stop promotion and return to the failing block if:

- evidence cannot be bound to exact code/config/runtime identity;
- unknown state is silently coerced to success/availability;
- executor completion bypasses independent acceptance;
- paid capacity is used without explicit authority;
- unqualified candidate receives protected data;
- checkpoint cannot reproduce repository state;
- retry behavior creates amplification/retry storm;
- project work graph can be mutated directly by an executor;
- stale/unauthorized knowledge becomes authoritative for a material decision.

## 11. Immediate next action

Execute B0 on current PR #352 head. Do not start broad provider integration until the provider-neutral kernel and engineering-knowledge contracts have real green execution evidence. In parallel, prepare B1/B2 tests so they can run in the same local/executor qualification wave and minimize ping-pong.