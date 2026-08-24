# Roadmap 3 WU03 — Durable Runtime Certification Ledger V1

## Objective

Make WU01/WU02 runtime conformance evidence durable and auditable without
confusing a conformance certificate with operational admission.

```text
probe
  -> RuntimeConformanceReport
  -> RuntimeCertification
  -> durable certification store
  -> if PASS, continue admission
  -> if FAIL, block admission
```

## Certificate semantics

A `RuntimeCertification` records one explicit probe identity:

- certificate id;
- orchestrator id;
- runtime version;
- probe execution id;
- pass/fail;
- failed check names;
- digest of the complete ordered conformance checks;
- total check count.

Certificate identity is deterministic:

```text
<orchestrator_id>:<runtime_version>:<probe_execution_id>
```

Re-recording the identical certificate is idempotent. Reusing the same probe
identity with a different result/digest fails closed with
`RuntimeCertificationConflict`.

## Persistence

Implementations:

- `InMemoryRuntimeCertificationStore`
- `SQLiteRuntimeCertificationStore`

SQLite is append-only by certificate id and rebuilds the immutable certificate
from stored fields. No orchestrator SDK state, learned model state, or opaque
serialized runtime object is persisted.

## Admission ordering

When a certification store is configured, `RuntimeAdmissionGate` performs:

1. active conformance probe;
2. build deterministic certificate;
3. persist certificate;
4. if report failed: block admission;
5. if report passed: register runtime;
6. register catalog routing metadata.

Therefore a certification-store outage blocks admission before registry/catalog
mutation.

## Certification is not admission

A passing certificate means only:

```text
the runtime/adapter boundary passed the specified conformance probe
```

It does **not** mean:

- the runtime is currently healthy;
- routing metadata is valid;
- catalog registration succeeded;
- the runtime is selected for missions;
- production behavior or SLOs are proven.

If conformance passes but catalog metadata validation fails, the passing
certificate may remain durably stored while the runtime is absent from the
operational registry/catalog. This is intentional and auditable: conformance
proof is immutable history, not admission state.

## Failed probes

Failed conformance reports are also certifiable. This provides durable evidence
of why admission was blocked while still guaranteeing zero operational
registration.

## Required evidence

1. in-memory certificate recording is idempotent;
2. conflicting reuse of a probe identity fails closed;
3. certificate identity and digest are deterministic;
4. SQLite survives process/store restart without duplicate records;
5. successful admission returns and persists a passing certificate;
6. failed conformance persists a failed certificate and does not admit runtime;
7. certification-store failure blocks before registry/catalog mutation;
8. profile validation failure may leave certification evidence but no operational admission;
9. changed result under the same probe identity conflicts before admission;
10. certification/admission modules remain SDK-neutral and factory-independent;
11. WU01/WU02 and the full historical suite remain green when executable CI is available.

## Non-goals

WU03 does not add:

- automatic manifest/factory admission;
- certificate expiration or recertification schedules;
- remote PKI/signatures;
- Sigstore/Cosign integration;
- automatic quarantine from certificate state;
- a third orchestrator framework;
- learned routing;
- production certification claims.

## Gate

```text
DURABLE_RUNTIME_CERTIFICATION = PASS
CERTIFICATE_IDEMPOTENT = YES
PROBE_IDENTITY_CONFLICT_FAILS_CLOSED = YES
SQLITE_CERTIFICATION_DURABLE = YES
FAILED_PROBES_AUDITABLE = YES
CERTIFICATION_STORE_FAILURE_ADMITS_RUNTIME = NO
CERTIFICATION_EQUALS_ADMISSION = NO
RUNTIME_FACTORY_CHANGED = NO
SDK_NEUTRAL = YES
FULL_REGRESSION = GREEN
```

`PASS`/`GREEN` may only be claimed after tests actually execute. A hosted runner
failure before the first step is not test evidence.
