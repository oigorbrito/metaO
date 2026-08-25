# Roadmap 3 WU05 — Certification Scope Closeout

## Status

```text
ROADMAP_3_FUNCTIONAL_SCOPE = COMPLETE
ROADMAP_3_REMOTE_EXECUTION_GATE = PENDING
ROADMAP_3_MERGE_GATE = PENDING
ROADMAP_3_PRODUCTION_CLAIM = NO
```

Roadmap 3 deliberately closes after building and wiring the runtime certification
subsystem without forcing a conflict into the still-open Roadmap 2 WU05
`runtime_factory.py` work.

## Work units

### WU01 — Runtime Conformance Harness V1

Implemented in PR #40.

Adds an SDK-neutral active probe for:

- `OrchestratorContract` shape;
- descriptor and health-report boundary;
- execution-result type;
- execution-id binding;
- orchestrator-id binding;
- evidence normalizer output;
- mission/execution/orchestrator/adapter/attempt evidence binding;
- required evidence identity/provenance/authority/digest fields.

### WU02 — Runtime Admission Gate V1

Implemented in PR #41, stacked on WU01.

Adds fail-closed operational admission:

- conformance before registry/catalog mutation;
- zero mutation on failed conformance;
- rollback of newly registered runtime when catalog validation fails;
- duplicate runtime-id preservation;
- health kept separate from conformity.

### WU03 — Durable Runtime Certification Ledger V1

Implemented in PR #42, stacked on WU02.

Adds:

- deterministic `RuntimeCertification`;
- immutable probe identity;
- idempotent in-memory store;
- append-only SQLite store;
- conflict detection for changed results under the same probe identity;
- failed-probe audit evidence;
- certification persistence before operational admission mutation.

A passing certificate proves conformance only. It does not prove admission,
health, selection, production readiness, or external-provider behavior.

### WU04 — Real Runtime Certification Regression V1

Implemented in PR #43, stacked on WU03.

Prepared executable evidence for the two real runtimes already proven by Roadmap 2:

- LangGraph 1.2.11;
- CrewAI 1.15.16 with deterministic local `BaseLLM`.

Both use the same conformance, certification, admission, registry, and catalog
boundary. No third framework is added.

## Architecture after Roadmap 3

```text
Candidate Orchestrator Runtime
  -> OrchestratorContract Adapter
  -> Active Conformance Probe
  -> RuntimeConformanceReport
  -> Durable RuntimeCertification
  -> Runtime Admission Gate
  -> OrchestratorRegistry + OrchestratorCatalog
  -> Existing metaO selection / policy / budget / execution / acceptance
```

The certification subsystem remains framework-neutral. Framework SDK imports stay
inside adapters or integration tests.

## Explicitly deferred

The following is intentionally **not** part of Roadmap 3:

- automatic certification/admission while loading the declarative runtime manifest;
- `runtime_factory.py` changes;
- automatic recertification schedules;
- external signing/PKI/Sigstore claims;
- third orchestrator framework;
- learned routing;
- cloud/Kubernetes/distributed-control-plane work;
- production SLO or security certification claims.

## Roadmap 4 entry condition

The next architecture step should be **Declarative Certified Runtime Onboarding**:

```text
runtime manifest
  -> plugin creation
  -> conformance/certification gate
  -> admission
  -> operational catalog
```

That work should begin only from a branch where the Roadmap 2 WU05 deterministic
feedback changes and the Roadmap 3 certification stack have been explicitly
composed, because both eventually need to participate in runtime construction.
Do not independently overwrite either implementation.

## Evidence state

The Roadmap 3 implementation and tests are present in PRs #40-#43, but current
GitHub-hosted Actions jobs have been failing before the first executable step is
allocated. Therefore:

- no new Roadmap 3 test count is claimed;
- no Roadmap 3 PASS/GREEN is claimed;
- prior merged Roadmap 1/Roadmap 2 evidence remains historical evidence only;
- the open stacked PRs must remain unmerged until executable regression evidence
  exists or an explicitly approved alternative execution gate is established.

## Final gate

```text
CONFORMANCE_HARNESS_IMPLEMENTED = YES
ADMISSION_GATE_IMPLEMENTED = YES
DURABLE_CERTIFICATION_IMPLEMENTED = YES
REAL_RUNTIME_CERTIFICATION_TESTS_PREPARED = YES
SDK_NEUTRAL_BOUNDARY_PRESERVED = YES
THIRD_FRAMEWORK_ADDED = NO
RUNTIME_FACTORY_CHANGED_BY_ROADMAP_3 = NO
REMOTE_TEST_EXECUTION = NOT_EXECUTED
ROADMAP_3_GATE = PENDING_EXECUTION
```
