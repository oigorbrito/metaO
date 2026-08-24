# metaO Release Readiness

Status: ROADMAP 2 FUNCTIONAL SCOPE CLOSED; WU05 INTEGRATION PENDING.

This file deliberately separates repository evidence from production claims and from work that is implemented but not yet merged.

## Implemented and repository-proven on the merged line

- framework-neutral `OrchestratorContract` and replaceable Core;
- Conductor durable-execution adapter boundary;
- runtime lease/fencing/idempotency/replay/recovery invariants;
- deterministic strategy state, historical scoring and cost-quality routing;
- mission-level replan/failover controls;
- independent final acceptance with binding, freshness, provenance, authority and policy hard gates;
- global policy, acceptance budgets and human-approval evidence contracts;
- real LangGraph and CrewAI SDK execution through thin adapter/plugin boundaries with common acceptance-evidence normalization;
- declarative runtime catalog with trusted local plugin factories;
- durable runtime quarantine with live-health precedence and SQLite persistence;
- installed CLI runtime controls for list/quarantine/restore/history;
- local/hostile trust profiles, freshness/replay guards and a standards-crypto provider port;
- public operator facade: `run`, `status`, `inspect`, `cancel`, `resume`.

Roadmap 2 merged baseline after WU04: `628b73409aa596bdcea7cf39136f455a0c220b05`.

Last merged full repository regression: 171/171 PASS.

## Real-runtime evidence

Repository tests have executed real LangGraph 1.2.11 and CrewAI 1.15.16 SDK/runtime paths in deterministic/local sandbox scenarios, including runtime swap and Block O regressions.

This proves the adapter/runtime integration boundary against those SDKs. It does **not** prove production behavior against external paid model providers or hosted services.

## WU05 integration state

Roadmap 2 WU05 — Deterministic Runtime Feedback V1 is implemented in PR #38 but is not part of the merged baseline yet.

Its scope adds durable, idempotent attempt observations and deterministic EMA feedback into runtime selection while preserving independent acceptance, quarantine precedence and SDK-neutral Core boundaries. It explicitly does not introduce learned routing.

Current GitHub-hosted Actions attempts for that PR fail before the first job step is allocated. Because no checkout/install/test step executes, those runs are not functional test PASS or FAIL evidence. WU05 remains unmerged until executable CI evidence is available.

## Independently executed foundation evidence

Block D independently executed Conductor 3.32.0 with workflow/worker behavior, retry, timeout, pause/resume and recovery after restart. This evidence establishes the selected durable foundation fit; it does not make every later feature L5 automatically.

## Not claimed by repository evidence

- production deployment readiness or SLO compliance;
- external paid model/provider production execution for LangGraph or CrewAI;
- a configured Sigstore/Cosign identity/attestation backend;
- hostile-network cryptographic authenticity without that external provider;
- Kubernetes/cloud/distributed-database readiness;
- learned routing, reinforcement learning or automatic model training;
- scale/load characteristics not separately measured;
- security certification or penetration-test completion.

## Release gate

The merged implementation gate is green only when:

1. all repository unit/architecture tests for the candidate commit pass;
2. all critical modules import;
3. at least two orchestrator runtimes share the neutral contract and evidence-normalization boundary;
4. no framework-specific SDK leaks into metaO Core;
5. cryptographic verification remains delegated through `CryptoProviderPort` rather than implemented ad hoc;
6. operator entrypoints and Quickstart are present.

Production release requires separate deployment, real-provider, load, security and operational acceptance appropriate to the target environment.

Roadmap 3 work may proceed independently of the current hosted-runner allocation issue; this does not authorize merging unverified candidate changes into `main`.
