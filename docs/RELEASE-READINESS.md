# metaO Release Readiness

Status: CANONICAL INTEGRATION CANDIDATE — EXECUTION AND MERGE GATES PENDING.

This file deliberately separates three things:

1. evidence already executed on merged `main`;
2. capability implemented in the canonical Roadmap 2-5 candidate;
3. production claims that have not been proven.

## Merged and executed baseline

Merged baseline before the current stacked candidate:

`628b73409aa596bdcea7cf39136f455a0c220b05`

Evidence already executed on that merged line includes:

- full unit regression: `171/171 PASS`;
- real LangGraph 1.2.11 sandbox execution;
- real CrewAI 1.15.16 sandbox execution using a deterministic local BaseLLM;
- Block O O1-O5 regression;
- two-runtime selection/failover/governance behavior;
- declarative runtime catalog;
- durable runtime quarantine;
- runtime control CLI;
- framework-neutral `OrchestratorContract` and independent acceptance boundary.

These historical PASS results do **not** automatically validate later unmerged
Roadmap 2 WU05 / Roadmap 3-5 changes.

## Canonical candidate capability

`roadmap6/integration-candidate-v1` is intended to be the single integration
surface for all post-baseline work.

It contains the cumulative functional implementation for:

### Deterministic runtime feedback

- immutable/idempotent runtime observations;
- SQLite feedback persistence;
- deterministic EMA aggregation using existing `HistoricalScore`;
- feedback overlay that changes routing metrics only;
- quarantine/live health remain authoritative;
- no learned routing.

### Runtime conformance and admission

- SDK-neutral active conformance harness;
- execution-id/orchestrator-id/evidence binding checks;
- fail-closed runtime admission before registry/catalog mutation;
- rollback on catalog registration failure.

### Durable certification

- immutable PASS/FAIL conformance certificates;
- SQLite certification ledger;
- certified declarative onboarding;
- exact persisted PASS reuse;
- real LangGraph/CrewAI certification scenarios prepared.

### Certificate lifecycle

- optional certificate freshness windows;
- append-only timestamped recertification generations;
- in-place SQLite migration for legacy certificates;
- immutable certificate revocation;
- operator CLI for certificate history/revocation;
- latest exact certification generation is authoritative;
- no fallback to an older PASS behind a newer FAIL, revoked PASS or stale verdict.

### Preserved metaO authority

None of the above changes the central rule:

`ORCHESTRATOR_DONE != METAO_ACCEPTED`

Policy, budget, approval, independent acceptance, quarantine, failover, replanning,
observability and audit remain metaO control-plane authorities. Runtime SDKs remain
confined to adapters/plugins.

## Reconciled stacked history

The candidate inherits the linear Roadmap 3-5 stack and reconciles the two
parallel Roadmap 2 branches without overwriting evolved production code.

From PR #38 it restores the previously missing:

- focused deterministic-feedback test suite;
- WU05 documentation;
- WU05 workflow.

The three feedback production modules already present in the later stack were
confirmed as exact reused blobs. `runtime_factory.py` intentionally remains the
newer cumulative implementation.

From PR #39 it restores the Roadmap 2 closeout history. This file supersedes the
old #39 release-readiness wording because the integration candidate now includes
Roadmaps 3-5.

## Candidate execution gate

The candidate is **not merge-eligible** until executable output confirms:

1. full unit suite;
2. Roadmap 2 WU05 deterministic-feedback suite;
3. Roadmap 3 conformance/admission/certification regressions;
4. Roadmap 4 certified onboarding/reuse regressions;
5. Roadmap 5 freshness/revocation/lifecycle/latest-verdict regressions;
6. real LangGraph 1.2.11 runtime regression;
7. real CrewAI 1.15.16 runtime regression;
8. real certified lifecycle regressions;
9. Block O O1-O5;
10. installed CLI smoke/compatibility;
11. SDK-neutral Core/control-plane boundary.

A consolidated workflow exists to execute these gates when hosted runner
allocation is available again.

## Current evidence status

The GitHub-hosted runner problem affecting the post-WU04 work occurs before the
first job step. The operator explicitly chose to continue implementation rather
than treat that external allocation issue as a development blocker.

Therefore:

```text
LAST_MERGED_EXECUTED_FULL_SUITE = 171/171 PASS
CANONICAL_CANDIDATE_IMPLEMENTATION = ASSEMBLED
CANONICAL_CANDIDATE_TEST_PASS = NOT CLAIMED
CANONICAL_CANDIDATE_REMOTE_EXECUTION = PENDING
CANONICAL_CANDIDATE_MERGE_GATE = PENDING
```

## Not claimed

The repository does not currently claim:

- production deployment readiness or SLO compliance;
- external paid model/provider production execution;
- Kubernetes/cloud/distributed-database readiness;
- a configured Sigstore/Cosign production identity backend;
- hostile-network cryptographic authenticity without such a provider;
- learned routing, reinforcement learning or automatic training;
- scale/load characteristics not separately measured;
- security certification or penetration-test completion;
- a third orchestrator framework integration.

## Next architectural gate

A third runtime should be evaluated only against this canonical integration
candidate, not against one of the intermediate stacked PR heads. Selection of a
third runtime must use current upstream documentation/code/tests and should not be
made solely from historical familiarity.
