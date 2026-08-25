# Roadmap 7 WU02 — Durable Replan Escalation

Date: 2026-08-24

## Status

```text
WU02_IMPLEMENTATION = PREPARED
WU02_EXECUTION = PENDING
WU02_PASS = NOT CLAIMED
```

## Problem

Roadmap 7 WU01 made `replan.evaluate()` authoritative in the real mission loop, including `ControlAction.ESCALATE` when the automatic attempt limit is exhausted.

The product-facing durable operator still had no safe continuation semantics for that escalation:

- the exhausted mission became terminal;
- the existing approval/resume path only supported approval **before** any runtime attempt;
- `resume()` explicitly rejected a waiting mission containing prior attempts;
- restarting the whole mission after approval would retry runtimes that already failed and would discard the bounded replan meaning.

## Decision

A replan-limit escalation may become `WAITING_APPROVAL` only when a currently routable, capability-compatible runtime remains that has not already been attempted.

Human approval authorizes exactly **one additional runtime attempt**.

It does not:

- reset the mission;
- retry an already-attempted runtime;
- create a new automatic failover loop;
- bypass live health or quarantine;
- bypass policy/acceptance binding;
- change `OrchestratorContract`.

## Flow

```text
automatic attempt 1
-> recoverable failure
-> REPLAN
-> automatic attempt 2
-> replan limit reached
-> unattempted runtime exists
-> WAITING_APPROVAL
-> durable ApprovalRequest
-> human approve
-> fresh routing snapshot
-> exactly one unattempted runtime attempt
-> ACCEPT or terminal failure/block
```

If no unattempted routable runtime exists at escalation time, metaO does not create a pointless human approval request; the original terminal replan-limit outcome remains authoritative.

## Implementation

### MissionOperator projection

`MissionOperator.run()` recognizes an outcome with:

- existing runtime attempts;
- `replan_limit_reached`;
- at least one fresh routable unattempted candidate.

It projects that terminal automatic outcome into:

```text
MissionStatus.WAITING_APPROVAL
AcceptanceDecision.REQUIRE_HUMAN
```

The durable approval request reason is:

```text
replan_limit_reached
```

Pre-runtime policy approval remains unchanged.

### Resume semantics

Approved replan escalation uses `execute_mission_once()` rather than restarting `execute_mission()`.

The continuation:

- refreshes catalog health/quarantine at resume time;
- excludes `attempted_orchestrators` from the entire prior lineage;
- preserves the current consumed budget snapshot;
- continues attempt numbering (`1, 2, 3`, not `1, 2, 1`);
- uses a unique continued execution id derived from the original prefix;
- appends the new attempt and history to the durable mission record;
- preserves the bound approval record through SQLite restart.

A failed approved extra attempt is terminal and records:

```text
approved_escalation_attempt_exhausted
```

WU02 intentionally does not implement repeated approval generations. That would require an explicit multi-approval history model rather than silently overwriting the existing durable approval record.

## Safety properties

```text
FAILED_RUNTIME_RETRY_AFTER_ESCALATION = FORBIDDEN
APPROVAL_EXTRA_ATTEMPTS = 1
LIVE_HEALTH_RECHECK = YES
QUARANTINE_RECHECK = YES
PRIOR_ATTEMPTS_PRESERVED = YES
PRIOR_BUDGET_SNAPSHOT_PRESERVED = YES
ORCHESTRATOR_CONTRACT_CHANGED = NO
SDK_IN_CORE = NO
```

## Tests prepared

`tests/unit/test_roadmap_7_work_unit_02.py` covers:

1. two automatic failures + third candidate -> durable `WAITING_APPROVAL`;
2. approval -> exactly third runtime executes -> lineage `1,2,3` -> ACCEPT;
3. denial -> BLOCK without executing the remaining runtime;
4. remaining runtime becomes unhealthy before resume -> BLOCK, no retry of old runtimes;
5. all runtimes already exhausted -> no pointless approval request;
6. SQLite restart between escalation, approval and resume preserves lineage and approval binding;
7. existing pre-runtime approval path remains unchanged.

The workflow also runs:

- Roadmap 7 WU01 focused regression;
- existing Roadmap 1 approval/resume regression;
- full unit suite;
- SDK-neutral source boundary check.

## Execution blocker

The WU01 workflow itself reproduced the repository-wide GitHub-hosted Actions blocker: it completed in failure within seconds before executable evidence was available. No WU01 or WU02 PASS is inferred.

## Scope deliberately not added

- repeated escalation/approval generations;
- arbitrary human-selected runtime override;
- retrying already-failed runtimes;
- dynamic increase of budget limits;
- learned recovery policy;
- distributed approval service;
- framework-specific recovery hooks.
