# Roadmap 5 WU03 — Certification Lifecycle CLI V1

## Objective

Expose certificate freshness and revocation as operator-facing control-plane
operations without requiring direct Python calls or SQLite edits.

The existing mission CLI remains delegated to `metao.cli`; the wrapper entrypoint
adds only runtime lifecycle commands.

## Commands

### List certificate generations

```text
metao --db metao.db runtime-certificates <orchestrator_id>
```

Optional deterministic freshness projection:

```text
metao --db metao.db runtime-certificates <orchestrator_id> \
  --now-epoch 1000 \
  --max-age-seconds 3600
```

Both freshness arguments are required together.

Each JSON item contains:

- certificate identity;
- runtime/probe binding;
- PASS/failed checks;
- digest/check count;
- certification time;
- revoked state;
- optional fresh state;
- derived `reusable` state.

`reusable` is false for failed, revoked or explicitly stale certificates.

### Revoke one generation

```text
metao --db metao.db runtime-certificate-revoke <certificate_id> \
  --reason "adapter regression" \
  --actor operator \
  --now-epoch 1000
```

The command:

1. verifies the certificate exists;
2. writes the immutable revocation;
3. returns machine-readable JSON;
4. fails closed for unknown ids or conflicting rewrites.

### List revocations

```text
metao --db metao.db runtime-certificate-revocations <orchestrator_id>
```

Returns immutable revocation history as JSON.

## Database resolution

Certificate DB:

1. `METAO_RUNTIME_CERTIFICATION_DB`;
2. runtime control DB;
3. global `--db`.

Revocation DB:

1. `METAO_RUNTIME_CERTIFICATION_REVOCATION_DB`;
2. certificate DB.

The normal `runtimes --factory ...` path forwards those resolved DBs to factories
that declare the corresponding keyword arguments. Older factories remain
compatible through signature inspection.

## Cross-process lifecycle

The intended operator flow is now:

1. declarative runtime loads and is actively certified;
2. certificate appears in `runtime-certificates`;
3. operator revokes that exact generation;
4. next declarative construction ignores the revoked PASS;
5. active conformance probe executes again;
6. new timestamped PASS generation is persisted;
7. later construction reuses the new generation without another probe.

## Authority separation

- `runtime-certificate-revoke` invalidates one historical reuse credential;
- `runtime-quarantine` immediately makes a runtime operationally ineligible;
- neither command replaces the other.

## Test scenarios prepared

1. combined help exposes lifecycle commands and preserves existing commands;
2. certificate list is machine-readable and computes deterministic freshness;
3. incomplete freshness args fail closed;
4. existing certificate can be revoked and history listed;
5. unknown certificate revoke fails closed;
6. fresh+revoked certificate is reported non-reusable;
7. identical revoke is idempotent and conflicting rewrite fails;
8. CLI revoke forces next declarative load to recertify and later reuse the new generation;
9. entrypoint remains SDK-neutral.

## Non-goals

- interactive UI;
- background recertification;
- remote certificate authority;
- reversible revocation;
- third runtime framework;
- production SLO claims.

## Status

`CERTIFICATION_LIFECYCLE_CLI = IMPLEMENTED`

`MACHINE_READABLE_CERT_HISTORY = YES`

`CLI_REVOCATION = IMPLEMENTED`

`CROSS_PROCESS_RECERTIFICATION_FLOW = PREPARED`

`REMOTE_EXECUTION = PENDING`

No PASS is claimed without executable test output.
