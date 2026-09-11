# Retry pressure and anti-flap donor fit

Related: #464, PR #465, parent #160, scientific matrix #168 T6.

This note classifies external donor semantics only. It does not grant dispatch, retry, failover, Acceptance, or provider-SDK authority.

## Authority boundary

MetaO keeps the following separation:

- factual runtime health: runtime-health projection;
- ordinary selection: Strategy;
- retry/recovery/failover causality: canonical authority tracked under #141;
- policy/risk/budget denial: canonical constraints tracked under #140.

Runtime health may gate eligibility but must not become a second retry/failover dispatcher.

## Donor reviewed

Envoy outlier detection and retry policy semantics were reviewed as reference behavior.

Relevant donor concepts:

- consecutive-failure thresholds before ejection;
- temporary ejection with a base duration;
- repeated ejection increasing exclusion duration up to a configured maximum;
- maximum percentage of hosts ejected;
- success/health-check based return to service;
- retry attempt limits and exponential retry backoff.

## Fit classification

| Donor semantic | Classification | MetaO treatment in #465/#464 |
| --- | --- | --- |
| Consecutive failure threshold | ADAPTED | Already represented by deterministic factual health thresholds; framework-neutral and not HTTP-specific. |
| Failure-percentage threshold | ADAPTED | Already represented by factual failure-ratio health projection. |
| Retry attempt bound | FIT | Canonical retry causality already owns `current_attempt` / `max_attempts`; #465 preserves this authority. |
| Retry pressure bound | ADAPTED | Health projection exposes retry pressure; #465 makes excessive pressure ineligible for ordinary retry without dispatching a retry. |
| Temporary ejection/cooldown timer | REFERENCE_ONLY | Not copied in #465. Adding wall-clock cooldown would introduce new durable temporal authority that is not presently justified independently of #141/#462. |
| Repeated-ejection duration multiplier | REFERENCE_ONLY | Useful anti-flap reference, but requires durable ejection history and clock semantics; deferred until a concrete executable failure demonstrates need. |
| Maximum ejection percentage | REFERENCE_ONLY | Envoy-specific cluster-availability tradeoff. MetaO selection/reselection is mission/runtime authority, not an Envoy upstream cluster; no direct copy. |
| Active-health-check unejection | REJECTED_AS_AUTHORITY | A successful probe must not erase factual runtime history or directly mint ordinary HEALTHY eligibility. Controlled recovery remains explicit. |
| Exponential retry backoff | REFERENCE_ONLY | Timing/backoff policy belongs with canonical retry execution authority, not runtime-health projection. |

## Resulting invariants for the current slice

1. ordinary retry is bounded first by canonical causal/attempt/policy/risk/budget authority;
2. excessive factual retry pressure blocks ordinary retry;
3. `UNHEALTHY` and `QUARANTINED` are not ordinary retry targets;
4. `RECOVERING` remains outside ordinary retry and requires separate controlled-recovery authority;
5. `UNKNOWN` cannot be used as a fresh healthy retry target;
6. health eligibility does not dispatch retry or failover;
7. a single probe/success cannot clear authoritative failure history by donor imitation.

## Cooldown/restart decision

No new wall-clock cooldown state is added in PR #465.

Reason: the current branch can enforce bounded retry pressure and anti-flap eligibility using already-owned factual state and canonical attempt limits. A durable cooldown clock would add new authoritative state, persistence, restart, and time-source semantics. That should be implemented only if exact-head executable qualification or a deterministic failing sequence shows that existing `QUARANTINED` / `RECOVERING` hysteresis is insufficient.

Therefore for this slice:

```text
TEMPORAL_COOLDOWN = REFERENCE_ONLY
NEW_DURABLE_TIMER_AUTHORITY = NO
RETRY_BACKOFF_EXECUTION_AUTHORITY = NO
```

## Qualification boundary

This donor classification is design evidence only. It is not executable qualification. PR #465 remains non-merge-ready until its exact head passes the documented local Rust gate with a clean worktree.
