# metaO Release Readiness

Status: IMPLEMENTATION GATE — candidate for the next integration/release phase.

This file deliberately separates repository evidence from production claims.

## Implemented and repository-proven

- framework-neutral `OrchestratorContract` and replaceable Core;
- Conductor durable-execution adapter boundary;
- runtime lease/fencing/idempotency/replay/recovery invariants;
- deterministic strategy state, historical scoring and cost-quality routing;
- mission-level replan/failover controls;
- independent final acceptance with binding, freshness, provenance, authority and policy hard gates;
- global policy, acceptance budgets and human-approval evidence contracts;
- thin LangGraph (`invoke`) and CrewAI (`kickoff`) adapter boundaries with common acceptance-evidence normalization;
- local/hostile trust profiles, freshness/replay guards and a standards-crypto provider port;
- public operator facade: `run`, `status`, `inspect`, `cancel`, `resume`.

## Independently executed foundation evidence

Block D independently executed Conductor 3.32.0 with workflow/worker behavior, retry, timeout, pause/resume and recovery after restart. This evidence establishes the selected durable foundation fit; it does not make every later feature L5 automatically.

## Not claimed by repository unit tests

- production deployment readiness or SLO compliance;
- live LangGraph or CrewAI SDK execution against external models/services;
- a configured Sigstore/Cosign identity/attestation backend;
- hostile-network cryptographic authenticity without that external provider;
- scale/load characteristics not separately measured;
- security certification or penetration-test completion.

## Release gate

The implementation gate is green only when:

1. all repository unit/architecture tests pass;
2. all critical modules import;
3. at least two orchestrator adapters share the neutral contract and evidence normalization boundary;
4. no framework-specific SDK leaks into metaO Core;
5. cryptographic verification remains delegated through `CryptoProviderPort` rather than implemented ad hoc;
6. operator entrypoints and Quickstart are present.

Production release requires separate deployment, real-provider, load, security and operational acceptance appropriate to the target environment.
