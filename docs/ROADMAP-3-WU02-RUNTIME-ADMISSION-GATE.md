# Roadmap 3 WU02 — Runtime Admission Gate V1

## Objective

Turn the WU01 conformance harness into an explicit admission boundary without
coupling it to the declarative runtime factory yet.

A new runtime is operationally registered only after an active, safe probe proves
that its neutral runtime/adapter boundary is conformant.

```text
candidate runtime
  -> active conformance probe
  -> PASS: register in OrchestratorRegistry + OrchestratorCatalog
  -> FAIL: no registry/catalog mutation
```

## Why this is separate from runtime_factory

Roadmap 2 WU05 currently has an open change to `runtime_factory.py`. WU02 avoids
creating an artificial integration conflict by implementing the admission gate as
independent framework-neutral infrastructure.

A later work unit can compose this gate into declarative manifest loading after
the open Roadmap 2 integration work is reconciled.

## Admission semantics

`RuntimeAdmissionGate.admit(...)`:

1. executes exactly one WU01 conformance probe;
2. blocks on any contract/execution/evidence-binding conformance failure;
3. only after PASS registers the runtime in `OrchestratorRegistry`;
4. registers routing metadata and normalizer in `OrchestratorCatalog`;
5. rolls the new registry entry back if catalog validation/registration fails.

There is no state where a newly admitted runtime exists only in the registry
because catalog registration failed.

## Health is not conformity

WU02 deliberately does not require the probe runtime to report `HEALTHY`.

A runtime can be structurally and behaviorally conformant while currently
`DEGRADED` or `UNHEALTHY`. The catalog continues to project live health, and the
router remains responsible for excluding operationally ineligible runtimes.

This preserves the architectural distinction:

```text
conformance = may this runtime participate in metaO at all?
health      = is this admitted runtime currently selectable?
```

## Failure model

Conformance failure:

- raises `RuntimeAdmissionError`;
- retains the exact `RuntimeConformanceReport`;
- mutates neither registry nor catalog.

Catalog/profile validation failure after a successful probe:

- propagates the existing catalog validation error;
- unregisters the newly added runtime;
- leaves no partial admission behind.

Duplicate orchestrator ids remain governed by the existing registry uniqueness
rule; an existing admitted runtime is never replaced implicitly.

## Required evidence

1. conformant runtime is admitted only after one probe;
2. execution-id binding failure blocks admission with zero registry/catalog mutation;
3. evidence misbinding blocks admission with zero mutation;
4. invalid routing metadata rolls back the new registry entry;
5. duplicate ids preserve the existing admitted runtime;
6. an unhealthy but conformant runtime may be admitted while remaining `UNHEALTHY` in the catalog;
7. the exact evidence normalizer boundary is preserved in the catalog;
8. failure diagnostics retain the conformance report;
9. the admission module is SDK-neutral and independent from `runtime_factory.py`;
10. WU01 and the full historical suite remain green when executable CI is available.

## Non-goals

WU02 does not add:

- manifest/factory auto-admission;
- a third orchestrator framework;
- learned routing;
- automatic quarantine;
- remote certification services;
- production deployment or SLO claims.

## Gate

```text
RUNTIME_ADMISSION_GATE = PASS
CONFORMANCE_REQUIRED_BEFORE_REGISTRATION = YES
FAILED_CONFORMANCE_MUTATES_CATALOG = NO
PARTIAL_REGISTRATION_ROLLBACK = YES
HEALTH_SEPARATE_FROM_CONFORMANCE = YES
RUNTIME_FACTORY_CHANGED = NO
SDK_NEUTRAL = YES
FULL_REGRESSION = GREEN
```

`PASS`/`GREEN` may only be claimed after tests actually execute. Hosted-runner
allocation failure before the first step is not functional test evidence.
