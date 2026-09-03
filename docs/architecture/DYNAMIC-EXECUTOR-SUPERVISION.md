# Dynamic Executor Supervision

Status: MVP architecture contract
Issue: #351

## Purpose

metaO is the authoritative project supervisor. It owns project decomposition, the work graph, scheduling, executor selection, supervision, replanning, acceptance, and completion. Executors such as Jules, Codex, Gemini, or any future provider-neutral runtime are replaceable workers. No executor owns the project plan or may certify its own work as accepted.

This contract is manufacturer-, country-, and business-model-neutral. Candidate executors are evaluated by observable capability, availability, cost, trust, policy, and evidence rather than provider identity or nationality.

## Engineering basis

The design follows established control-plane and reliability patterns:

- filter feasible execution targets by constraints and available capacity before ranking/binding (scheduler design);
- classify retryable overload/rate conditions separately from persistent quota, credit, authorization, and capability failures;
- use bounded retries with exponential backoff and jitter rather than retry storms;
- preserve task state outside the executor so work can be reassigned after failure or exhaustion;
- evaluate third-party software/services as supply-chain dependencies before giving them repository, credentials, code, artifacts, or sensitive data;
- fail closed when trust, capability, quota semantics, or execution state cannot be established sufficiently for the requested operation.

Normative/engineering references include NIST SP 800-161 Rev.1 C-SCRM, NIST SSDF 1.1, Kubernetes Scheduling Framework, Google SRE guidance on overload/cascading failures, and AWS Builders Library guidance on retries/backoff/jitter.

## Authority invariants

1. Tasks belong to metaO, never to executors.
2. Only metaO mutates the authoritative work graph.
3. Executors may report discoveries, failures, dependencies, estimates, and evidence; those reports are inputs, not authority.
4. Executor completion never implies task or project acceptance.
5. Quota exhaustion or provider unavailability does not fail a task while a policy-compliant compatible executor exists.
6. Provider-specific quota/rate semantics remain behind provider adapters.
7. Unknown executor/runtime states fail closed.
8. Dynamic discovery never implies automatic enrollment, credential disclosure, repository access, or data disclosure.
9. Paid fallback requires explicit budget/policy authority.
10. Executor transfer requires a reproducible checkpoint bound to repository state, task contract, attempt history, and evidence.
11. A resumed executor must verify the repository/workspace state before continuing.
12. Project continuity must not depend on a single executor or a compile-time executor catalog.
13. Trust qualification is provider-neutral: the same evidence requirements apply regardless of vendor or country of origin.

## Control planes

### Project plane

Owned by metaO. Maintains objective, requirements, constraints, milestones, work graph, dependencies, priorities, completion criteria, and project state.

### Execution-capacity plane

Maintains two registries:

- `DiscoveredExecutorRegistry`: untrusted/unqualified candidates and their provenance.
- `QualifiedExecutorRegistry`: candidates that passed the required trust, capability, policy, and operational qualification.

### Scheduling plane

For each READY task:

1. derive hard execution requirements;
2. retrieve qualified candidates;
3. remove candidates that fail capability, policy, trust, deadline, concurrency, or availability gates;
4. normalize provider-specific capacity information;
5. rank eligible candidates using project policy;
6. bind one executor for the current attempt;
7. keep task authority in metaO.

### Supervision plane

Uses event-driven updates when available and bounded reconciliation polling as a recovery mechanism. It observes at least:

- executor/session state;
- local workspace state;
- local Git branch/HEAD/diff/worktree state;
- remote Git branch/PR/check state;
- acceptance/test evidence;
- quota, rate, account, budget, and provider-health signals.

Polling intervals are configuration values to be established by tests and operational measurement, not architectural constants. The MVP must support active-execution reconciliation in the 1-5 minute range and permit shorter intervals when provider cost/rate limits and observed overhead make them safe.

## Normalized executor capacity model

Provider adapters map native signals to the following minimum states:

- `AVAILABLE`
- `CONCURRENCY_EXHAUSTED`
- `TEMPORARILY_RATE_LIMITED`
- `TEMPORARILY_QUOTA_EXHAUSTED`
- `WINDOW_QUOTA_EXHAUSTED`
- `CREDIT_EXHAUSTED`
- `SPEND_LIMIT_EXHAUSTED`
- `AUTH_FAILURE`
- `ACCOUNT_DISABLED`
- `PROVIDER_UNAVAILABLE`
- `CAPABILITY_MISMATCH`
- `POLICY_INELIGIBLE`
- `TRUST_UNQUALIFIED`
- `UNKNOWN`

A capacity observation records provenance, observation time, confidence, whether the condition is recoverable, and a recovery time/window when supported by evidence.

A raw HTTP status such as 429 is never sufficient by itself to decide retry versus failover. The provider adapter must classify the semantic condition using documented protocol fields, provider responses, observed telemetry, or configured policy.

## Retry, recovery, and failover

Retryable transient conditions use bounded exponential backoff with jitter. Retry budgets prevent amplification and cascading failure.

When an executor cannot continue, metaO evaluates:

- estimated recovery time;
- task deadline/priority;
- checkpoint transfer cost;
- compatible free/included/paid alternatives;
- expected quality/reliability;
- policy and budget constraints.

The outcome may be `RETRY_SAME_EXECUTOR`, `PARK_UNTIL_RECOVERY`, `FAILOVER`, `SPLIT_OR_REPLAN_TASK`, or `BLOCK`.

Circuit-breaker state prevents repeatedly assigning work to an unhealthy executor. Recovery probes must be bounded; a recovered provider must not receive an uncontrolled burst of queued work.

## Checkpoint and handoff

Agent handoff is not chat handoff. The portable handoff is:

- authoritative task contract;
- project/work-graph references;
- base commit and current HEAD;
- branch/worktree identity;
- accepted/rejected diffs and commits;
- completed and remaining acceptance criteria;
- test/build evidence;
- discovered blockers/dependencies;
- attempt history and failure classification;
- policy constraints and allowed data/repository scope.

The receiving executor verifies repository state before modification. If the state cannot be reproduced, metaO blocks or repairs the workspace before execution resumes.

## Dynamic executor discovery

A market/discovery sub-agent may search official provider documentation, APIs, release notes, public repositories, registries, marketplaces, and other configured sources for new execution capacity or changed terms.

Discovery output is evidence only. Each candidate record includes:

- provider/runtime identity;
- source URLs/provenance;
- observed capabilities;
- authentication/integration mechanism;
- price/business model;
- concurrency/quota/rate semantics;
- data handling/repository-access implications when knowable;
- terms/operational constraints;
- observation/freshness timestamps;
- confidence and unresolved claims.

The scout cannot self-authorize a candidate.

## Qualification and trust gate

Before a candidate may receive code, credentials, repository access, artifacts, prompts containing confidential information, or production access, metaO performs a policy-driven supply-chain/trust assessment.

Minimum outcomes:

- `QUALIFIED`
- `QUALIFIED_RESTRICTED` (e.g. public repo only, no secrets, sandbox only)
- `UNQUALIFIED`
- `BLOCKED`

Unknown or unverifiable claims reduce permissions; they never increase them. Provider nationality is not a trust decision input by itself. Evidence about ownership, service terms, authentication, data use/retention, security controls, incident history, integration boundaries, and observed behavior may be relevant when available.

For an untrusted but potentially useful executor, a qualification sandbox may use synthetic/non-sensitive repositories and canary tasks to measure behavior without exposing protected project data.

## Scheduling objective

The scheduler uses hard gates first and multi-objective ranking second. Ranking may consider:

- capability fit;
- current availability and recovery estimate;
- historical success/reliability;
- context/checkpoint continuity;
- expected quality;
- latency/deadline utility;
- monetary cost and retry cost;
- trust/permission level;
- verification/handoff overhead.

Project policy controls weights and constraints. `free` is a cost attribute, not an unconditional priority: a repeatedly failing free executor may have higher expected project cost than a reliable paid executor.

## MVP acceptance tests

The first executable slice must include deterministic/adversarial tests for at least:

1. registered executor succeeds and remains selected;
2. transient rate limit uses bounded backoff+jitter and does not create a retry storm;
3. quota exhaustion with known recovery time parks or fails over according to policy;
4. quota exhaustion with a compatible free alternative transfers the task;
5. paid fallback is rejected without budget authority;
6. paid fallback is allowed within explicit budget and policy;
7. provider outage opens the circuit and removes the executor from candidate scheduling;
8. recovered provider is probed before normal scheduling resumes;
9. checkpoint handoff preserves task/repository/evidence identity across two different executor adapters;
10. receiving executor detects mismatched HEAD/worktree and fails closed;
11. discovered but unqualified executor cannot receive repository credentials/data;
12. qualification sandbox can promote only after required evidence is present;
13. country/vendor identity alone neither approves nor rejects an executor;
14. unknown quota/runtime state fails closed rather than fabricating a reset time;
15. executor reports a new dependency, but only metaO mutates the work graph;
16. executor reports COMPLETED while independent acceptance fails: task remains unaccepted;
17. local/Git/remote disagreement is detected and reconciled or blocked before promotion;
18. no available executor causes PROJECT/TASK BLOCKED with evidence, not false completion.

## MVP implementation boundary

The smallest production-oriented slice should introduce provider-neutral domain types and decision logic before adding provider-specific Jules/Codex/Gemini adapters:

- executor identity/capability profile;
- capacity observation and failure classification;
- discovered versus qualified registry records;
- project execution policy and budget authority;
- candidate hard-filter and deterministic ranking interface;
- checkpoint/attempt transfer contract;
- supervision/reconciliation decision states;
- deterministic tests covering the acceptance matrix above.

Provider adapters then normalize Jules/Codex/Gemini/native signals into these contracts without changing the governance kernel.