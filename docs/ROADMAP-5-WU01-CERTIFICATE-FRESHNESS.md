# Roadmap 5 WU01 — Certificate Freshness & Deterministic Recertification V1

## Objective

Prevent a durable PASS runtime certificate from being reusable forever.

Roadmap 4 introduced exact persisted certificate reuse. WU01 adds an optional,
explicit freshness window. Once that window expires, metaO runs the same active
conformance probe again and records a new immutable certificate generation.

## Manifest surface

```json
{
  "certification": {
    "mode": "required",
    "reuse_passed": true,
    "max_age_seconds": 86400,
    "probe": {
      "execution_id": "runtime-certification-v1",
      "objective": "prove runtime contract",
      "required_capabilities": ["workflow"]
    }
  }
}
```

`max_age_seconds` is optional. Omitting it preserves Roadmap 4 behavior.
When present it must be positive.

## Semantics

### Legacy compatibility

Certificates created before Roadmap 5 keep:

- the original certificate id;
- `certified_at_epoch = 0` after SQLite migration;
- all original conformance evidence unchanged.

A legacy timestamp-zero certificate is considered stale only when a freshness
policy is enabled. That forces one active recertification and creates the first
timestamped generation.

### Timestamped generations

Legacy identity:

`orchestrator_id:runtime_version:probe_execution_id`

Timestamped identity:

`orchestrator_id:runtime_version:probe_execution_id:certified_at_epoch`

The timestamp is encoded with six decimal places. Previous generations are never
mutated or deleted.

### Freshness decision

A PASS certificate may be reused only when all existing Roadmap 4 bindings pass
and:

`0 < certified_at_epoch <= now_epoch`

and:

`now_epoch - certified_at_epoch <= max_age_seconds`

The validity boundary is inclusive.

Clock reversal does not authorize reuse.

### Expiry behavior

Expired certificate:

1. is retained in history;
2. is not reused;
3. triggers the configured active probe;
4. produces a new immutable generation if the probe completes;
5. only the new PASS can be reused in its own freshness window.

A failed recertification still blocks operational admission exactly as before.

## SQLite migration

`SQLiteRuntimeCertificationStore` upgrades the existing table in place by adding:

`certified_at_epoch REAL NOT NULL DEFAULT 0`

Existing rows are not rewritten beyond the schema default, preserving prior
evidence and making their freshness status explicit.

## Authority boundaries

Freshness does not change:

- quarantine authority;
- live runtime health;
- policy;
- budget;
- human approval;
- independent mission acceptance;
- deterministic feedback scoring.

Freshness controls only whether an old conformance PASS can bypass a new probe.

## Test scenarios prepared

1. legacy identity remains unchanged and is stale under freshness;
2. timestamped identity is append-only and boundary-inclusive;
3. in-window restart reuses without runtime execution;
4. expired PASS forces active recertification;
5. newest exact fresh generation is selected;
6. stale persisted PASS is rejected by admission gate;
7. legacy SQLite schema migrates without evidence rewrite;
8. multiple generations survive SQLite restart;
9. invalid zero/negative max age fails closed before probe;
10. implementation remains SDK-neutral and learned-routing-free.

## Non-goals

- certificate revocation;
- signatures / PKI;
- remote attestation;
- learned freshness thresholds;
- background probes;
- third runtime framework;
- production SLO claims.

Revocation is intentionally deferred to the next work unit because expiry and
explicit operator revocation are different control-plane decisions.

## Status

`CERTIFICATE_FRESHNESS = IMPLEMENTED`

`DETERMINISTIC_RECERTIFICATION = IMPLEMENTED`

`LEGACY_SQLITE_MIGRATION = IMPLEMENTED`

`REMOTE_EXECUTION = PENDING`

No test PASS is claimed until executable output exists.
