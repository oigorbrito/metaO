# Roadmap 4 WU02 — Passed Certificate Reuse V1

## Goal

Avoid repeating an active runtime conformance probe on every process startup when
an operator explicitly opts into reuse and the exact prior PASS certificate is
already durable.

## Manifest surface

Certified entries may add:

```json
{
  "certification": {
    "mode": "required",
    "reuse_passed": true,
    "probe": {
      "execution_id": "cert-runtime-v1",
      "objective": "prove runtime boundary",
      "required_capabilities": ["workflow"]
    }
  }
}
```

`reuse_passed` defaults to `false` and must be a JSON boolean.

## Binding required for reuse

A persisted certificate is reusable only when all of the following are true:

- certificate is `passed=true`;
- certificate is present in the configured durable certification store;
- certificate `orchestrator_id` equals the current plugin descriptor id;
- certificate `runtime_version` equals the current plugin descriptor version;
- certificate `probe_execution_id` equals the current manifest probe execution id;
- the complete persisted certificate equals the supplied certificate.

The lookup identity remains:

`<orchestrator_id>:<runtime_version>:<probe_execution_id>`

A version or probe-id change therefore forces a new active probe automatically.

## Failure semantics

- missing certificate -> run normal active probe;
- failed certificate -> never reuse; normal active certification path executes;
- unpersisted certificate -> block reuse;
- runtime-version mismatch -> block reuse;
- probe-id mismatch -> block reuse;
- persisted-content mismatch -> block reuse;
- registration/catalog error after reuse still rolls back the newly registered runtime.

Failed certificates are immutable evidence. If runtime behavior changes from a
previous FAIL to PASS while version and probe id stay unchanged, the existing
certificate identity conflicts. The operator must bump runtime version or probe
execution id rather than rewrite history.

## Trust boundary

Reuse is an operational optimization, not stronger trust. It assumes the runtime
version is part of the plugin contract and must change when behavior affecting
conformance changes.

WU02 does not add code-signing, source hashing or remote attestation.

## Tests prepared

`tests/unit/test_roadmap_4_work_unit_02.py` covers:

1. first load probes, second load reuses without execute;
2. SQLite restart preserves reusable PASS;
3. runtime-version change forces new probe;
4. probe execution-id change forces new probe;
5. failed certificate is never reused;
6. non-boolean reuse flag fails before execute;
7. unpersisted and version-mismatched certificates are rejected without execute;
8. reuse implementation remains SDK-neutral.

## Gate

```text
PASSED_CERTIFICATE_REUSE = IMPLEMENTED
REUSE_OPT_IN = YES
PASS_REQUIRED = YES
DURABLE_PRESENCE_REQUIRED = YES
RUNTIME_VERSION_BOUND = YES
PROBE_ID_BOUND = YES
FAILED_CERT_REUSED = NO
ACTIVE_PROBE_SKIPPED_ON_EXACT_PASS = YES
SDK_NEUTRAL = YES
REMOTE_TEST_EXECUTION = PENDING
MERGE_GATE = PENDING
```
