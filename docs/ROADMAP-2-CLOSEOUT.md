# Roadmap 2 Closeout

Status: FUNCTIONAL SCOPE CLOSED; WU05 INTEGRATION PENDING.

This document closes the Roadmap 2 feature scope without overstating repository integration evidence.

## Completed and merged

- WU01 — Second Real Runtime Sandbox V1: real LangGraph and CrewAI SDK execution with framework-specific code confined to adapters/plugins.
- WU02 — Declarative Runtime Catalog V1: trusted local plugin factories plus framework-neutral routing metadata.
- WU03 — Durable Runtime Quarantine V1: revisioned runtime controls with SQLite persistence and quarantine precedence over routing.
- WU04 — Runtime Control CLI V1: runtime list/quarantine/restore/history through the installed `metao` entrypoint.

Merged Roadmap 2 baseline after WU04: `628b73409aa596bdcea7cf39136f455a0c220b05`.

Last merged full repository regression: 171/171 PASS.

Real-runtime evidence on the merged line: LangGraph 1.2.11 + CrewAI 1.15.16 PASS, including Block O sandbox regressions.

## WU05 — implemented, not yet merged

WU05 — Deterministic Runtime Feedback V1 is implemented in PR #38 / branch `roadmap2/wu05-deterministic-runtime-feedback-v1`.

Implemented scope:

- immutable per-attempt runtime observations;
- idempotent in-memory and SQLite feedback stores;
- deterministic EMA aggregation through the pre-existing `HistoricalScore` primitive;
- routing overlay that replaces only deterministic score inputs after evidence exists;
- durable history across process restart;
- quarantine/live-health precedence preserved;
- advisory fail-open feedback persistence after mission outcome commit;
- no learned routing, RL, embeddings, training, sklearn or torch dependency.

The PR remains open because GitHub-hosted Actions jobs are currently failing before the first job step is allocated. Those runs provide no executable test evidence and are not counted as functional PASS or FAIL.

## Architecture frozen by Roadmap 2

```text
Mission
  -> Strategy / Selection
  -> Policy / Budget
  -> OrchestratorContract
  -> Runtime Adapter / Plugin
  -> Whole Orchestrator Runtime
  -> Evidence
  -> Independent Acceptance
  -> Accept / Replan / Failover / Block
```

The strategic unit remains a whole orchestrator/runtime. Runtime-internal agents, tools, memory and workflow topology are outside Core authority.

Central invariant:

```text
ORCHESTRATOR_DONE != METAO_ACCEPTED
```

Framework SDK imports remain outside Core/control-plane modules.

## Repository-proven vs not claimed

Repository-proven:

- two real orchestrator SDK integrations (LangGraph and CrewAI) under deterministic/local sandbox execution;
- runtime selection, failover, policy, budget, approval, cancellation and independent acceptance;
- declarative runtime catalog;
- durable runtime quarantine and operational CLI controls;
- unified mission/attempt observability on the merged line.

Not claimed:

- external paid model/provider production execution;
- production deployment SLOs;
- Kubernetes/cloud/distributed-database readiness;
- learned or adaptive ML routing;
- automatic runtime quarantine thresholds;
- large-scale load/latency benchmarks;
- security certification or penetration-test completion.

## Closeout decision

Roadmap 2 feature expansion is frozen. New functional work should move to Roadmap 3 rather than growing WU05 or reopening earlier WUs.

Integration bookkeeping remains:

1. merge WU05 only after executable CI evidence is available;
2. update this closeout status from `WU05 INTEGRATION PENDING` to final GREEN after that merge;
3. do not block Roadmap 3 design/implementation on hosted-runner availability.

## Scope guard for Roadmap 3

Continue to prefer `ADOPT > ADAPT > BUILD` and do not introduce Kubernetes, cloud orchestration, distributed databases, microservices, learned routing, sophisticated UI or large benchmark infrastructure without a concrete requirement and evidence-backed decision.
