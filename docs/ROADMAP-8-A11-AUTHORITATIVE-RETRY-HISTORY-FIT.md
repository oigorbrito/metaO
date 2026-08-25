# Roadmap 8 — A11 Authoritative Retry History Donor Fit

Status: DONOR DECISION COMPLETE / PRODUCT IMPLEMENTATION DEFERRED.

Issue: #98

## Objective

Freeze the smallest evidence-based design needed to satisfy A11: retries, recovery and their costs must come from authoritative durable history at terminalization. A caller must not be able to omit older attempts, reset counters after restart, or replace an over-budget history with a shorter tuple.

## Current metaO surface

Current `main` already has useful operational durability:

```text
MissionState.attempts
MissionOutcome.attempted_orchestrators
MissionRunContext
MissionStorePort
InMemoryMissionStore
SQLiteMissionStore
```

`SQLiteMissionStore` persists the whole current mission snapshot and `replace()` writes a newer record revision.

That is appropriate for current mission state. It is not, by itself, an append-only historical authority: a replacement snapshot is structurally capable of presenting a shorter attempt list unless another boundary prevents it.

Therefore:

```text
MISSION_SNAPSHOT_EXISTS != AUTHORITATIVE_RETRY_HISTORY
```

## Frozen donor

```text
repo   = tihotm/oma
commit = ca43381dc8bce4041da4fc09efbe939642729939
paths  = src/oma/retry.py
         src/oma/retry_ledger.py
         tests/test_retry.py
         tests/test_retry_ledger.py
         tests/test_retry_ledger_audit.py
```

No donor code is copied in this audit.

## Retry-domain invariants from OMA

`retry.py` defines one causal retry domain. The important transferable invariants are:

- exact retry-domain identity;
- exact subject binding;
- exact lineage binding;
- exact retry-policy binding;
- unique event ids;
- contiguous event sequence;
- attempt numbering cannot reset or skip causally required history;
- retry/recovery reasons are policy constrained;
- cumulative cost is computed over the complete domain;
- process/run changes do not create a new budget domain;
- recovery refers to prior factual attempts rather than inventing history.

The metaO adaptation should bind the domain to mission/subject/lineage and retain framework-neutral orchestrator/execution identities.

## Append-only ledger semantics from OMA

`retry_ledger.py` is explicitly a factual history store, not an authorization service.

Its purpose is to preserve the complete causal history so final validation cannot be reopened by omitting historical retry or cost events.

Key behavior:

```text
initialize valid domain once
append exact next sequence only
duplicate event id -> conflict, no rewrite
binding mismatch -> block, no persistence
policy digest mismatch -> domain is not authoritative for that policy
over-limit factual event -> persisted, result BLOCKED
reopen SQLite -> complete history remains
```

The important distinction is the over-limit event: the fact that an attempt happened is never deleted merely because it violated a budget. That event must remain visible to later terminalization.

## Donor adversarial evidence

At the frozen pin, `tests/test_retry_ledger_audit.py` proves three especially relevant cases:

1. complete over-limit retry history blocks terminalization;
2. presenting only an earlier prefix does **not** reopen acceptance because the authoritative ledger wins;
3. the terminal pipeline replaces the caller-presented retry tuple with the authoritative stored history.

This directly matches the A11 threat model.

## Composition decision

Do not overload `MissionStorePort` with two conflicting meanings.

```text
MissionStorePort
  role = current operational mission snapshot/state

RetryHistoryPort
  role = append-only factual retry/attempt/cost authority
```

The two ports MAY share the same physical SQLite database. Logical separation is the key requirement; a second database service is not required.

This is not duplicate history if the authoritative attempt/retry event is recorded once and the mission snapshot only carries a current-state projection for operator ergonomics.

Decision:

```text
OMA retry-domain semantics = ADAPT
OMA SQLite append-only ledger semantics = ADAPT
whole OMA dependency = NO
new infrastructure service = NO
minimum metaO BUILD = framework-neutral RetryHistoryPort and records
```

## Proposed minimum metaO contract

Design target only:

```text
RetryDomainBinding
  retry_domain_id
  mission_id
  subject_id
  lineage_id
  retry_policy_id
  policy_digest

RetryHistoryEvent
  event_id
  sequence
  kind                 # INITIAL / RETRY / RECOVERY / terminal factual kinds as needed
  attempt_number
  run_id
  orchestrator_id
  execution_id
  subject_id
  lineage_id
  retry_policy_id
  reason
  execution_cost

RetryHistoryResult
  decision             # WRITTEN / BLOCKED / CONFLICT / BLOCK
  reasons

RetryHistoryPort
  initialize(binding, initial_event) -> RetryHistoryResult
  append(binding, event) -> RetryHistoryResult
  get(binding) -> tuple[RetryHistoryEvent, ...] | None
```

Names may change during implementation; invariants may not.

## Terminal authority rule

```text
CALLER_OR_MISSION_SNAPSHOT_HISTORY = CANDIDATE / PROJECTION
RETRY_HISTORY_PORT = FACTUAL SOURCE OF TRUTH
```

Before a retry-sensitive final decision, metaO must load the complete authoritative domain and evaluate policy/cost/lineage over it.

A caller cannot authorize a shorter history by providing fewer attempts.

## Required safety behavior

```text
unknown/uninitialized domain               -> BLOCK
policy/domain/subject/lineage mismatch      -> BLOCK
sequence gap or reset                       -> BLOCK
duplicate event id                          -> CONFLICT/BLOCK
negative or malformed cost                  -> BLOCK
restart / new run id                        -> history preserved
attempt limit exceeded                      -> factual event remains + terminal block
cost limit exceeded                         -> factual event remains + terminal block
caller omits prior events                   -> stored history wins
mission snapshot has shorter projection     -> stored history wins
```

The ledger does not issue `METAO_ACCEPTED`. It is a factual authority consumed by retry/recovery and final acceptance gates.

## Relationship to current replanning

Current Roadmaps 2–7 already provide bounded replan/failover and durable mission attempt records. A11 is not a replacement for that logic.

Future composition should be:

```text
attempt starts/finishes
-> append factual event once
-> current MissionStore projection may update
-> replan logic reads policy + authoritative history
-> terminal acceptance re-reads authoritative history
```

Do not maintain a second independent attempt counter that can drift from the ledger. Attempt number and cumulative execution cost should derive from, or be checked against, authoritative history.

## Relationship to A18 AcceptanceBudget

A11 and A18 govern different dimensions that meet at terminalization:

```text
A11 = execution/retry/recovery factual history and execution cost
A18 = verification/acceptance money, tokens, wall-clock and verifier attempts
```

Future implementation must name these resource classes explicitly so the same cost is not charged twice and neither budget can be reset through another subsystem.

## Required future adversarial tests

Product implementation must prove through the real metaO path:

1. two failed attempts then a third over limit remain three factual events;
2. restarting process/operator does not reset attempt or cost totals;
3. presenting only attempt 1 when authoritative history has attempts 1–3 still blocks;
4. MissionStore snapshot truncated to fewer attempts cannot override RetryHistoryPort;
5. duplicate event id cannot rewrite an old event;
6. sequence 1 -> 3 without 2 is rejected;
7. same domain id with changed lineage/subject/policy is rejected;
8. same policy id with changed policy content/digest cannot read the old authoritative domain;
9. an over-limit attempt is recorded even though the decision blocks;
10. repeated terminal evaluation over unchanged authoritative history is deterministic;
11. framework SDK types never enter retry-history contracts;
12. factual ledger result never becomes final acceptance authority.

Primitive-only ledger tests are not enough for a future `FINAL_PATH_PROVEN` classification; omitted-history attacks must traverse terminal acceptance.

## Implementation order

This audit is independent and complete. Product code remains deferred by the Roadmap 8 sequence in #92.

```text
#90 / PR #91 canonical EvidenceEnvelope -> executable-green
A18 ordered functional slice
A02 verifier slice
A05/A07/A09 authoritative terminal sources
A11 authoritative retry history integrated with terminal/adversarial closure
```

The exact later WU grouping may combine A11 with the final adversarial closure if that produces a smaller coherent terminal-path change. It must not be stacked blindly on an unexecuted WU01 branch.

## Measurement

```text
DONOR_REPO = tihotm/oma
DONOR_COMMIT = ca43381dc8bce4041da4fc09efbe939642729939
DONOR_PATHS = retry.py, retry_ledger.py, retry tests
DONOR_CODE_COPIED = 0 LOC
DEPENDENCIES_ADDED = 0
METAO_PRODUCT_CODE_CHANGED = NO
NEW_EXTERNAL_SERVICE = NO
FIT_DECISION = COMPLETE
```

## Non-goals

```text
NO second workflow engine
NO replacement of MissionStore
NO duplicated independent retry counters
NO caller-authored terminal history
NO framework SDK coupling
NO fourth orchestrator
NO learned routing
```

## Acceptance criteria result

```text
EXACT_DONOR_PIN_PATHS = RECORDED
OMITTED_HISTORY_ATTACK = DOCUMENTED
SNAPSHOT_VS_LEDGER_RESPONSIBILITY = FROZEN
MINIMUM_RETRY_HISTORY_PORT = DOCUMENTED
APPEND_ONLY_FACTUAL_NOT_FINAL_AUTHORITY = EXPLICIT
RESTART_AND_CUMULATIVE_COST_NON_RESET = EXPLICIT
DUPLICATE_STORAGE_SERVICE = NOT_REQUIRED
PRODUCT_CODE_CHANGE = NO
IMPLEMENTATION = DEFERRED_TO_ORDERED_ROADMAP8_WU
```
