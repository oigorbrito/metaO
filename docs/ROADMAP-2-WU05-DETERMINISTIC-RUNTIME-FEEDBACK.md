# Roadmap 2 WU05 — Deterministic Runtime Feedback V1

## Objective

Close the loop between already-audited mission attempts and the deterministic
cost/quality router without introducing learned routing, hidden model state, or
runtime-specific logic.

Roadmap 1 already records per-attempt:

- orchestrator id;
- execution status;
- independent acceptance decision;
- start/end timestamps;
- failure class;
- cost.

Block H already provides `HistoricalScore.update(...)`, a deterministic EMA.
WU05 connects those two existing pieces.

## Observation semantics

Each executed attempt becomes one immutable observation:

```text
outcome = 1.0 when independent acceptance == ACCEPT, otherwise 0.0
quality = same binary independently accepted signal in v1
latency_ms = max(0, ended_at - started_at) * 1000
cost = attempt.cost
```

The observation id is stable per mission/execution:

```text
<mission_id>:<execution_id>
```

Recording is idempotent. Re-recording identical evidence is a no-op; reusing an
observation id with different data fails closed.

## Persistence

Implementations:

- `InMemoryRuntimeFeedbackStore`
- `SQLiteRuntimeFeedbackStore`

SQLite stores append-only observations and recomputes `HistoricalScore` in
stable `(observed_at_epoch, observation_id)` order. No opaque serialized model
state is stored.

## Routing overlay

`HistoricalFeedbackCatalog` wraps the already-governed catalog.

Cold start:

```text
no feedback samples -> manifest routing metrics remain authoritative
```

After observations exist, only the signals already consumed by the deterministic
router are replaced by the historical EMA:

- success_rate <- outcome_ema
- quality <- quality_ema
- latency_ms <- latency_ema_ms
- cost <- cost_ema

The overlay does **not** change:

- live health;
- quarantine disposition;
- capabilities;
- trust profile;
- configured reliability.

Therefore perfect historical feedback cannot override `QUARANTINED` or
`UNHEALTHY`.

## Operator behavior

`RuntimeCatalogOperator` records feedback after the underlying `MissionOperator`
has durably committed the mission outcome. Feedback is advisory, never final
authority.

If feedback storage is temporarily unavailable:

```text
committed mission outcome remains authoritative
feedback error is retained on the operator instance
next routing decision uses the last durable history
```

A feedback outage cannot transform ACCEPT into failure or bypass independent
acceptance.

## CLI / database behavior

The generic runtime factory accepts `METAO_RUNTIME_FEEDBACK_DB` as an explicit
override. When it is absent, the operational runtime-control database is reused.
The installed WU04 entrypoint already maps the mission `--db` to that operational
DB, so normal invocations automatically share feedback:

```text
metao --db .metao/metao.db run mission-1.json --factory metao.runtime_factory:create_operator
metao --db .metao/metao.db run mission-2.json --factory metao.runtime_factory:create_operator
```

No additional service or database is required.

## Required evidence

1. in-memory observations are idempotent and conflicts fail closed;
2. EMA values match the pre-existing deterministic `HistoricalScore` semantics;
3. SQLite feedback survives restart without duplicate samples;
4. cold start preserves manifest routing metrics;
5. a failed preferred runtime plus accepted fallback changes the next selection deterministically;
6. the changed selection survives operator/process restart;
7. quarantine remains authoritative over perfect feedback;
8. feedback persistence failure cannot invalidate a committed mission;
9. separate installed CLI invocations reuse the same SQLite feedback history;
10. feedback modules remain SDK-neutral and add no ML routing dependency;
11. full historical suite remains green;
12. real LangGraph/CrewAI and Block O regressions remain green.

## Non-goals

WU05 does not add:

- learned routing;
- reinforcement learning;
- embeddings for runtime selection;
- model training;
- external telemetry SaaS;
- automatic quarantine thresholds;
- production SLO claims.

## Gate

```text
DETERMINISTIC_RUNTIME_FEEDBACK = PASS
FEEDBACK_DURABLE = YES
FEEDBACK_IDEMPOTENT = YES
NEXT_MISSION_USES_HISTORY = YES
QUARANTINE_OVERRIDES_HISTORY = YES
ACCEPTANCE_AUTHORITY_UNCHANGED = YES
LEARNED_ROUTING = NO
SDK_NEUTRAL = YES
FULL_REGRESSION = GREEN
```
