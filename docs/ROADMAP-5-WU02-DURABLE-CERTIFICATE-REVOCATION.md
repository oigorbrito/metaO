# Roadmap 5 WU02 — Durable Certificate Revocation V1

## Objective

Allow an operator to invalidate one specific runtime certificate generation
without quarantining the runtime itself and without deleting audit evidence.

## Why revocation is separate from quarantine

Runtime quarantine answers:

> Should this runtime be eligible for operational selection now?

Certificate revocation answers:

> May this historical conformance PASS be reused to skip a new probe?

Those are different control-plane authorities and are stored separately.

## Revocation model

`RuntimeCertificationRevocation` contains:

- `certificate_id`
- `orchestrator_id`
- `reason`
- `actor_id`
- `revoked_at_epoch`

A revocation is immutable and one-way for that certificate generation.

There is intentionally no `restore_certificate` operation. If trust should be
restored, metaO must run the deterministic conformance probe again and produce a
new certificate generation.

## Durable stores

Reference implementations:

- `InMemoryRuntimeCertificationRevocationStore`
- `SQLiteRuntimeCertificationRevocationStore`

SQLite table:

`runtime_certification_revocations`

Primary key:

`certificate_id`

Identical repeated writes are idempotent. A conflicting rewrite of an existing
revocation fails closed.

## Operator helper

`revoke_certificate(...)` first verifies that the referenced certificate exists.
Unknown certificate ids cannot be revoked through the helper.

## Admission precedence

For certificate reuse:

1. certificate must be PASS;
2. orchestrator/version/probe bindings must match;
3. certificate must not be revoked;
4. freshness must pass when configured;
5. certificate must exactly match durable certification state;
6. only then may operational registration occur.

`REVOKED` always wins over `FRESH`.

## Recertification behavior

When a reusable certificate is revoked:

1. the old certificate remains in certification history;
2. the revocation remains in revocation history;
3. declarative onboarding skips that generation;
4. metaO runs the configured active conformance probe;
5. a successful probe creates a new timestamped certificate generation;
6. later startups may reuse the new unrevoked PASS.

When revocation storage is configured, active certifications receive timestamped
generation ids even if no TTL is configured. This prevents a fresh probe from
colliding with the exact identity of a revoked legacy generation.

## Existing admitted runtimes

Revocation does not retroactively remove a runtime from an already constructed
operator/catalog. Runtime quarantine remains the authority for immediate runtime
ineligibility.

This separation avoids revocation silently changing live mission state.

## Persistence defaults

The CLI-compatible runtime factory may store revocations in:

1. explicit `runtime_certification_revocation_db` argument;
2. `METAO_RUNTIME_CERTIFICATION_REVOCATION_DB`;
3. otherwise the same SQLite database used for certifications.

## Test scenarios prepared

1. unknown certificate cannot be revoked;
2. in-memory revocation is immutable/idempotent;
3. SQLite revocation survives restart;
4. admission rejects a revoked persisted PASS;
5. revoked generation forces a new active probe;
6. new unrevoked generation is reusable;
7. active probe cannot reuse the exact revoked generation identity;
8. revocation does not mutate an already admitted catalog;
9. revocation modules remain SDK-neutral.

## Non-goals

- reversible certificate revocation;
- runtime quarantine replacement;
- remote CRL/OCSP;
- PKI/signatures;
- learned trust scoring;
- background recertification;
- third framework.

## Status

`DURABLE_CERTIFICATE_REVOCATION = IMPLEMENTED`

`REVOCATION_IS_IMMUTABLE = YES`

`REVOKED_CERTIFICATE_REUSE = BLOCKED`

`RECERTIFICATION_AFTER_REVOKE = IMPLEMENTED`

`REMOTE_EXECUTION = PENDING`

No PASS is claimed without executable test output.
