# Roadmap 7 WU01 — Failure-Aware Replan Authority

Date: 2026-08-24

## Status

```text
WU01_IMPLEMENTATION = PREPARED
WU01_EXECUTION = PENDING
WU01_PASS = NOT CLAIMED
```

## Problem

metaO already had framework-neutral replan primitives in `src/metao/replan.py`:

- `FailureClass`;
- `ControlAction`;
- `evaluate()`;
- `ReplanLimit`;
- alternate-runtime reselection helpers.

However the real `execute_mission()` loop did not use `evaluate()` to decide whether a failed attempt should replan, halt or escalate. Any non-accepted result effectively advanced to another runtime until `max_attempts` was exhausted.

That left an authority gap between the documented replan policy and the actual mission loop.

## Objective

Integrate deterministic failure-aware replan authority into the real control-plane loop without changing `OrchestratorContract` and without delegating policy/budget authority to runtime SDK error strings.

## Authority boundary

The runtime owns only execution.

Runtime/adaptor free-form error text is advisory and may classify only operational recovery signals:

```text
TRANSIENT
TIMEOUT
RUNTIME
```

A runtime cannot manufacture these metaO authorities by returning matching words:

```text
POLICY
BUDGET
ACCEPTANCE
```

MetaO policy and budget hard gates continue to be evaluated before runtime execution by control-plane-owned state.

`ExecutionStatus.CANCELLED` is authoritative execution state and maps to `FailureClass.CANCELLED`.

## Implemented behavior

`execute_mission()` now asks `replan.evaluate()` after every non-accepted runtime attempt.

### REPLAN

Recoverable failures re-enter selection with the already-attempted runtime excluded.

The mission history records:

```text
... -> RUNNING -> REPLANNING -> SELECTING -> ...
```

### HALT

Hard stop decisions terminate immediately instead of attempting another runtime.

Current concrete runtime-level halt case:

```text
ExecutionStatus.CANCELLED -> FailureClass.CANCELLED -> HALT
```

### ESCALATE

When the exact replan attempt budget is exhausted, the mission stops with:

```text
replan_limit_reached
```

WU01 preserves the current terminal mission semantics. Durable human escalation is intentionally not added in this work unit.

## Security / authority hardening

Before WU01, `_failure_class_for_execution()` trusted any recognized text classification, including strings such as:

```text
policy denied
budget exhausted
```

That would be unsafe once `replan.evaluate()` became authoritative because a runtime SDK could influence metaO hard-gate behavior through free-form error text.

WU01 therefore treats runtime text classification as advisory and accepts only runtime recovery classes. Policy/budget/acceptance authority remains metaO-owned.

## Test scenarios prepared

`tests/unit/test_roadmap_7_work_unit_01.py` covers:

1. timeout on preferred runtime -> deterministic failover -> fallback accepted;
2. runtime error text containing `policy denied` cannot seize policy authority and is demoted to `RUNTIME`;
3. spontaneous `ExecutionStatus.CANCELLED` halts without failover;
4. exact `max_attempts` produces `replan_limit_reached` and does not execute a third runtime;
5. metaO policy deny blocks before any runtime execution.

Full unit regression is also part of the workflow gate.

## Architecture constraints

```text
ORCHESTRATOR_CONTRACT_CHANGED = NO
FRAMEWORK_SDK_ADDED_TO_CORE = NO
LEARNED_ROUTING_ADDED = NO
POLICY_AUTHORITY_DELEGATED_TO_RUNTIME = NO
BUDGET_AUTHORITY_DELEGATED_TO_RUNTIME = NO
```

This work changes control-plane composition because replan authority is a metaO responsibility, not a framework accommodation.

## Execution blocker

GitHub-hosted Actions remains externally blocked before the first job step. The latest controlled rerun of PR #56 also produced `steps = null` and `BlobNotFound` logs.

Therefore WU01 is prepared but not declared PASS.

## Planned Roadmap 7 sequence

WU01 establishes the missing authority boundary first.

Candidate follow-up work, only after focused review of this boundary:

1. WU02 — explicit replan decision/audit projection;
2. WU03 — durable escalation semantics if escalation requires human intervention;
3. WU04 — heterogeneous three-runtime recovery regression;
4. WU05 — closeout/readiness.

The sequence may be reduced if later work is redundant with existing mission state/audit structures.
