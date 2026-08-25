# Roadmap 4 WU01 — Declarative Certified Runtime Onboarding V1

## Goal

Compose the Roadmap 2 deterministic runtime-feedback work with the Roadmap 3
conformance/certification stack at the declarative runtime-factory boundary.

The desired control-plane path is:

`manifest -> trusted plugin factory -> optional explicit conformance probe -> durable certification -> admission -> governed catalog -> deterministic feedback overlay`

This work does not add another orchestrator framework.

## Authority order

1. Certification/conformance controls whether a runtime can be admitted when certified mode is requested.
2. Live health and durable quarantine control whether an admitted runtime is operationally selectable.
3. Deterministic feedback may replace routing score inputs after observed mission history exists.
4. Feedback never overrides quarantine, health, policy, budget, approval or independent mission acceptance.

## Manifest compatibility

WU01 deliberately avoids silently executing active probes for every existing runtime.
Existing manifests remain legacy-compatible.

A runtime opts into certified onboarding with:

```json
{
  "factory": "my_runtime:create_plugin",
  "cost": 0.25,
  "latency_ms": 100,
  "success_rate": 0.8,
  "quality": 0.8,
  "reliability": 0.8,
  "trust_profile": "local",
  "certification": {
    "mode": "required",
    "probe": {
      "execution_id": "cert-my-runtime-v1",
      "mission_id": "certify-my-runtime",
      "objective": "prove the neutral runtime boundary",
      "required_capabilities": ["workflow"],
      "context": {}
    }
  }
}
```

`certification.mode=required` is fail-closed:

- probe configuration must be valid;
- a durable certification store must exist;
- the active conformance probe must pass;
- certification persistence must succeed;
- only then may registry/catalog admission occur.

`certification.mode=legacy`, or an absent certification section, keeps the previous
Roadmap 2 catalog behavior and does not execute a startup probe.

This compatibility mode is temporary migration support, not a claim that legacy
entries are certified.

## Persistence

Environment/configuration surfaces:

- `METAO_RUNTIME_CATALOG`
- `METAO_RUNTIME_CONTROL_DB`
- `METAO_RUNTIME_FEEDBACK_DB`
- `METAO_RUNTIME_CERTIFICATION_DB`

The generic CLI factory may use one SQLite database for controls, feedback and
certification because each subsystem owns separate tables. Explicit feedback or
certification paths override the shared control DB.

## Feedback semantics carried forward from Roadmap 2 WU05

- immutable observations keyed by mission/execution identity;
- idempotent re-record of identical observations;
- deterministic `HistoricalScore` EMA (`alpha=0.2`);
- cold start keeps static manifest routing metrics;
- once history exists, observed outcome/quality/latency/cost replace only router inputs;
- feedback-storage failure remains advisory after a mission outcome is committed;
- no learned routing, RL, embeddings, sklearn or torch.

## Certification semantics carried forward from Roadmap 3

- active framework-neutral probe;
- exact execution/orchestrator/evidence binding;
- immutable deterministic certificate;
- certification persistence happens before operational admission;
- failed probe may remain auditable but cannot be admitted;
- certificate does not imply health, production readiness or mission acceptance.

## Tests prepared

`tests/unit/test_roadmap_4_work_unit_01.py` covers:

1. required certification probes before registration and records a certificate;
2. failed binding blocks construction/admission;
3. required certification without durable store fails before probe execution;
4. old manifest remains backward compatible and probe-free;
5. explicit legacy mode remains probe-free;
6. deterministic feedback overlays certified runtime routing metrics;
7. quarantine remains authoritative over certification + feedback;
8. malformed probe fails before runtime execution;
9. composed factory remains SDK-neutral and non-learned.

Full repository regression and Roadmap 3 regressions are configured in CI, but
hosted-runner execution is currently not claimed because the repository Actions
runner-allocation issue is being intentionally ignored for forward implementation.

## Non-goals

- no automatic paid-provider probe;
- no mandatory certification migration for old manifests in WU01;
- no third runtime framework;
- no Kubernetes/cloud control plane;
- no external PKI/signing service;
- no learned routing;
- no production SLO claim.

## Gate

```text
DECLARATIVE_CERTIFIED_ONBOARDING = IMPLEMENTED
CERTIFICATION_BEFORE_ADMISSION = YES
CERTIFICATION_FAILS_CLOSED = YES
LEGACY_MANIFEST_COMPATIBILITY = YES
DETERMINISTIC_FEEDBACK_COMPOSED = YES
QUARANTINE_PRECEDENCE = PRESERVED
LEARNED_ROUTING = NO
SDK_NEUTRAL = YES
REMOTE_TEST_EXECUTION = PENDING
MERGE_GATE = PENDING
```
