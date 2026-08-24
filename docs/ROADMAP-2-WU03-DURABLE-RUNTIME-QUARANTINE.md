# Roadmap 2 WU03 — Durable Runtime Quarantine V1

## Objective

Give the metaO control plane an explicit, durable and auditable way to remove a
runtime from selection without deleting the adapter, changing its score, or
pretending that its live health changed.

The strategy layer already treats `OrchestratorStatus.QUARANTINED` as
ineligible. WU03 supplies the missing operator-control state that can project a
runtime into that status.

## Semantics

```text
live runtime health
        +
operator runtime control
        ↓
GovernedOrchestratorCatalog
        ↓
HEALTHY / DEGRADED / UNHEALTHY / QUARANTINED
        ↓
existing deterministic router
```

Rules:

1. `QUARANTINED` overrides live health and makes the runtime ineligible.
2. `ACTIVE` means only that the manual block is removed; it never forces a
   runtime healthy.
3. Quarantine does not mutate quality, cost, reliability, capabilities or the
   runtime descriptor.
4. Restore is explicit and revisioned.
5. Quarantine/restore history is append-only and records actor, reason and time.
6. If every matching runtime is quarantined, the mission fails closed with no
   runtime execution.

## Persistence

Implementations:

- `InMemoryRuntimeControlStore`
- `SQLiteRuntimeControlStore`

Each transition creates a monotonically increasing revision per runtime.
SQLite persistence survives process restart and can be shared across CLI
invocations/processes.

## Declarative runtime factory integration

The WU02 factory accepts an optional `RuntimeControlStorePort`.

For the default CLI-compatible factory, set:

```text
METAO_RUNTIME_CATALOG=/path/to/runtimes.json
METAO_RUNTIME_CONTROL_DB=/path/to/metao-runtime-control.db
```

The same runtime manifest is then routed through `GovernedOrchestratorCatalog`.
No orchestrator SDK type enters the control modules.

## Required evidence

1. in-memory control records preserve immutable revision history;
2. SQLite quarantine survives restart;
3. SQLite restore survives restart and preserves prior quarantine evidence;
4. quarantined preferred runtime is never selected or executed;
5. all eligible runtimes quarantined fails closed;
6. explicit restore re-enables a healthy preferred runtime without score change;
7. ACTIVE never overrides an UNHEALTHY live runtime;
8. quarantine overrides HEALTHY until restore;
9. malformed audit records fail closed;
10. runtime-control modules remain SDK-neutral.

## Gate

```text
DURABLE_RUNTIME_QUARANTINE = PASS
QUARANTINE_SURVIVES_RESTART = YES
QUARANTINED_RUNTIME_EXECUTED = NO
RESTORE_PRESERVES_LIVE_HEALTH = YES
CONTROL_HISTORY_APPEND_ONLY = YES
SDK_NEUTRAL = YES
FULL_REGRESSION = GREEN
```
