# Architecture Survival L2 Contract Matrix V1

> Salvaged from historical PR #361 onto current `main` under #651. Historical observations remain provenance only; new PASS/FAIL claims require fresh execution on the salvage head.

Status: FROZEN CONTRACT / SOURCE-MAPPED / EXECUTION PENDING

## Purpose

L2 compares implementation strategies against the same deterministic control-plane semantics. A donor does not receive credit for a capability outside its intended layer. For example, a durable runtime is not penalized for lacking Project Plane authority; it is tested only after being composed with a Project Plane candidate.

No strategy may claim L2 PASS until an adapter executes these fixtures and produces a machine-readable receipt.

## Contract cases

| ID | Fixture | Required outcome | Hard-gate meaning |
|---|---|---|---|
| L2-A01 | executor reports DONE without independent acceptance evidence | REJECT / NOT ACCEPTED | executor completion is not acceptance |
| L2-A02 | executor proposes authoritative WorkGraph mutation | proposal only; no authority transfer | Project Plane remains sovereign |
| L2-A03 | evidence is bound to state A; repository moves to state B | evidence becomes inapplicable | stale evidence cannot authorize |
| L2-A04 | provider/capacity/evidence state is malformed or unknown | BLOCK / fail closed | unknown cannot become success |
| L2-A05 | paid fallback lacks explicit authority/budget | REJECT dispatch | cost authority remains outside executor |
| L2-A06 | invalid graph contains cycle/orphan/duplicate | NO DISPATCH | invalid decomposition cannot execute |
| L2-A07 | all tasks report complete while a mandatory obligation is unproven | PROJECT NOT DONE | project completion is independent |

## Current source mapping

The following statuses are not L2 execution results.

- SUPPORTED: exact source inspection found a mechanism materially aligned with the fixture.
- PARTIAL: mechanism exists but the exact metaO contract boundary has not been demonstrated.
- N/A: outside the component's responsibility.
- UNKNOWN: inspection has not established the claim.

| Candidate / mechanism | A01 | A02 | A03 | A04 | A05 | A06 | A07 |
|---|---|---|---|---|---|---|---|
| metaO current contracts | SUPPORTED | PARTIAL | SUPPORTED | SUPPORTED | SUPPORTED | PARTIAL | SUPPORTED |
| Vigla project supervisor | SUPPORTED | PARTIAL | PARTIAL | SUPPORTED | UNKNOWN | SUPPORTED | PARTIAL |
| Pactrail transaction/evidence kernel | PARTIAL | N/A | SUPPORTED | SUPPORTED | N/A | N/A | N/A |
| Duroxide durability runtime | N/A | N/A | PARTIAL | PARTIAL | N/A | N/A | N/A |
| Durare durability runtime | N/A | N/A | PARTIAL | PARTIAL | N/A | N/A | N/A |
| ACP Rust SDK transport | N/A | N/A | N/A | PARTIAL | N/A | N/A | N/A |

## metaO source evidence

Current metaO already contains directly relevant contract mechanisms:

- `ExecutionObservedUsage` rejects `SelfReported` and `Unknown` evidence bases.
- `evaluate_pre_runtime_gate` blocks denied policy, stop risk, and insufficient budget.
- `ProjectCompletionGate` requires independently accepted or verified evidence bound to the exact project contract and rejects unresolved obligations.
- `evaluate_effect_retry` treats ambiguous external effects as blocked or requiring policy/human intervention unless idempotency enforcement is independently evidenced.

These are contract-level source findings. L2 execution still requires fixture invocation.

## Adapter requirement

Every surviving strategy must expose the same minimal adapter result:

```text
fixture_id
strategy_id
result = PASS | REJECT | BLOCK | NOT_DONE | UNSUPPORTED
authority_owner
evidence_binding
reason_code
exact_source_sha
adapter_sha
```

An adapter must not translate an `UNSUPPORTED` fixture into PASS.

## Composition rule

L2 scores are computed for strategies, not repositories:

```text
strategy =
    Project Plane
  + executor boundary
  + durability mechanism
  + evidence/acceptance mechanism
```

Examples to test later:

1. metaO current + ACP + Pactrail evidence semantics + Durare
2. metaO current + ACP + Pactrail evidence semantics + Duroxide
3. Vigla supervision + metaO sovereign Project Plane + ACP + Durare
4. Vigla supervision + metaO sovereign Project Plane + ACP + Duroxide

No fork or migration decision is authorized before at least one complete strategy executes all seven fixtures.

## Execution order

1. Execute L2 against current metaO contracts first.
2. Build the thinnest adapter necessary for each external mechanism.
3. Mark unsupported boundaries explicitly.
4. Execute all seven fixtures deterministically.
5. Only then advance surviving strategies to L3 crash/restart tests.
