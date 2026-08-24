# Roadmap 5 WU05 — Latest Certification Verdict Authority V1

## Objective

Prevent metaO from falling backward to an older PASS after a newer conformance
probe has failed or its newer PASS generation has been revoked.

This is a lifecycle hardening rule, not a new routing heuristic.

## Rule

For one exact binding:

`orchestrator_id + runtime_version + probe_execution_id`

only the newest certificate generation is the current conformance verdict.

The current generation may be reused only if it is:

1. `passed=true`;
2. not revoked;
3. fresh when freshness is configured;
4. durably persisted and identity-bound as already required.

If the newest generation fails any of those checks, metaO runs a new active probe.
It never scans backward for an older reusable PASS.

## Why this matters

Unsafe history:

```text
100 PASS
120 FAIL
```

At time 130 the PASS from 100 may still be inside a 60-second freshness window.
Reusing it would ignore the newer negative evidence. WU05 forbids that fallback.

The same applies to:

```text
100 PASS
120 PASS (REVOKED)
```

Revoking the latest generation must force recertification, not resurrect the PASS
from 100.

## API

`latest_certificate(...)` returns the newest exact generation regardless of
PASS/FAIL.

`latest_passing_certificate(...)` remains available as a low-level historical
query for compatibility, but declarative onboarding no longer uses it as the
trust authority.

## Generational continuity

Once a runtime/version/probe binding has timestamped generations, active
recertification continues to produce timestamped generations even if the TTL or
revocation configuration is later removed.

This prevents a new probe from collapsing back into the legacy fixed certificate
identity and allows newer verdicts to supersede older ones deterministically.

## Prepared regressions

1. latest exact generation is returned even when it is FAIL;
2. newer FAIL blocks fallback to older still-fresh PASS;
3. revoked newest PASS blocks fallback to older unrevoked PASS;
4. newer recovery PASS can be reused after a FAIL;
5. timestamped history stays generational after TTL removal;
6. implementation remains SDK-neutral.

## Preserved authority boundaries

- revocation still invalidates an exact generation;
- freshness still limits age;
- quarantine still controls immediate runtime eligibility;
- mission acceptance remains independent;
- feedback remains deterministic/advisory;
- no learned routing is introduced.

## Status

`LATEST_CERTIFICATION_VERDICT_AUTHORITY = IMPLEMENTED`

`FALLBACK_TO_OLDER_PASS = FORBIDDEN`

`NEWER_FAIL_SUPERSEDES_OLDER_PASS = YES`

`NEWER_REVOKED_PASS_SUPERSEDES_OLDER_PASS = YES`

`REMOTE_EXECUTION = PENDING`

No PASS is claimed without executable test output.
