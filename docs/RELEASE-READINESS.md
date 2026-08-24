# metaO Release Readiness

Status: ROADMAP 6 FUNCTIONAL ASSEMBLY COMPLETE — EXECUTION AND MERGE GATES PENDING.

This file deliberately separates four things:

1. evidence already executed on merged `main`;
2. capability assembled in the canonical Roadmap 2-5 integration candidate;
3. Roadmap 6 third-runtime work stacked on top of that candidate;
4. production claims that have not been proven.

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

These historical PASS results do **not** automatically validate later unmerged Roadmap 2 WU05 / Roadmap 3-6 changes.

## Canonical pre-Roadmap-6 integration candidate

PR #56 / branch `roadmap6/integration-candidate-v1` is the single integration surface for the cumulative Roadmap 2-5 work.

It contains:

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

Policy, budget, approval, independent acceptance, quarantine, failover, replanning, observability and audit remain metaO control-plane authorities. Runtime SDKs remain confined to adapters/plugins.

## Roadmap 6 third-runtime stack

Roadmap 6 is stacked on top of PR #56 and remains draft/unmerged.

### WU03 — third runtime evaluation

PR #57 selected:

`OpenAI Agents SDK 0.21.1`

Selection was based on current upstream evidence and prioritized:

- architectural diversity;
- a thin adapter;
- deterministic provider-free testing;
- zero Core changes;
- upstream maintenance;
- low operational cost.

### WU04 — OpenAI Agents adapter

PR #58 prepares:

- `src/metao/adapters/openai_agents.py`;
- SDK-neutral duck typing via `run_sync` and `final_output`;
- deterministic evidence normalization;
- SDK-free adapter unit tests;
- real SDK sandbox using first-party `agents.testing.ScriptedModel`;
- the existing framework-neutral Runtime Conformance Harness unchanged.

Architecture status:

```text
CORE_CHANGED = NO
ORCHESTRATOR_CONTRACT_CHANGED = NO
SDK_IMPORT_IN_CORE = NO
```

### WU05 — three-runtime regression

PR #59 prepares one declarative real-runtime regression with exact pins:

```text
OpenAI Agents 0.21.1
CrewAI 1.15.16
LangGraph 1.2.11
```

Prepared scenarios include:

- active certification of all three runtimes;
- exact PASS reuse inside TTL;
- freshness-triggered recertification;
- selective certificate revocation;
- deterministic three-runtime selection;
- heterogeneous failover;
- quarantine overriding routing score;
- preservation of latest-certification-verdict authority.

Direct WU04 -> WU05 comparison shows only integration test, workflow and documentation changes; no production source file changed in WU05.

### WU06 — closeout/readiness

PR #60 records Roadmap 6 as functionally assembled but not executed or merge-ready.

## Execution gate

No post-baseline candidate is merge-eligible until executable output confirms the required gates.

Required order:

1. execute PR #56 canonical integration candidate;
2. fix any concrete regression on PR #56 without weakening Core boundaries;
3. execute WU04 real OpenAI Agents conformance;
4. execute WU05 three-runtime regression;
5. run the full unit suite;
6. run real LangGraph/CrewAI/OpenAI Agents sandboxes;
7. run Block O O1-O5;
8. verify installed CLI compatibility;
9. verify SDK-neutral Core/control-plane boundary;
10. merge only dependency-ordered green work or a single later canonical consolidation candidate.

## Current execution blocker

GitHub-hosted Actions is currently failing before the first job step materializes.

Observed across Roadmap 6 and the canonical PR #56:

```text
job conclusion = failure
steps = [] / null
job logs = BlobNotFound
```

A controlled rerun of the PR #56 canonical integration job on 2026-08-24 produced the same result:

```text
workflow run = 32731724864
run_attempt = 2
job = canonical-integration
job_id = 97451005960
steps = null
logs = BlobNotFound
```

Therefore no checkout, dependency installation or test command executed. This is classified as an external execution blocker, not a functional PASS or FAIL result for metaO code.

## Current evidence status

```text
LAST_MERGED_EXECUTED_FULL_SUITE = 171/171 PASS
CANONICAL_CANDIDATE_IMPLEMENTATION = ASSEMBLED
ROADMAP_6_FUNCTIONAL_ASSEMBLY = COMPLETE
THIRD_RUNTIME_SELECTED = OpenAI Agents SDK 0.21.1
THREE_RUNTIME_REGRESSION = PREPARED
CANONICAL_CANDIDATE_TEST_PASS = NOT CLAIMED
ROADMAP_6_TEST_PASS = NOT CLAIMED
REMOTE_EXECUTION = BLOCKED_EXTERNAL
MERGE_GATE = PENDING
PRODUCTION_CLAIM = NO
```

## Not claimed

The repository does not currently claim:

- production deployment readiness or SLO compliance;
- external paid model/provider production execution;
- executable proof of the OpenAI Agents integration;
- executable proof of three-runtime selection/failover/lifecycle behavior;
- Kubernetes/cloud/distributed-database readiness;
- a configured Sigstore/Cosign production identity backend;
- hostile-network cryptographic authenticity without such a provider;
- learned routing, reinforcement learning or automatic training;
- scale/load characteristics not separately measured;
- security certification or penetration-test completion.

## Next architectural gate

The third-runtime design gate is now complete at the implementation level. The next legitimate gate is **execution evidence**, not a fourth framework or broader infrastructure expansion.

Until executable infrastructure is available:

- continue only work that preserves the frozen architecture and has an explicit documented objective;
- do not merge PR #56 or Roadmap 6 stacked PRs;
- do not convert pre-step Action failures into functional FAIL claims;
- do not declare PASS without real test output;
- do not add a fourth runtime merely to continue feature count.
