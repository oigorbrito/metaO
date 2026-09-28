# Envoy runtime-health donor pin (#160)

This repository uses Envoy only as a **semantic reference donor** for runtime-health/outlier concepts.

Pinned source:

- Envoy release: `v1.39.1`
- release commit: `b579d07d3ad7ee11d32b105e91a5a39ad24718d7`
- outlier-detection API blob: `2cd3bb943e47ceee3e05fa696b778ccf7a1ee99c`
- outlier implementation blob: `d610d2163e87cc1bab72980cb49c7f86480d7f0d`
- circuit-breaker API blob: `fdc0af5460a08d7b63b852a5da37af5961eb9ff6`

Validate the pin with:

```console
python scripts/validate_runtime_health_envoy_donor.py
```

## Fit classification

```text
OUTLIER_DETECTION = ADAPT_SEMANTICS
ACTIVE_HEALTH_CHECK = OBSERVATION_REFERENCE_ONLY
CIRCUIT_BREAKER = PRESSURE_BOUNDARY_REFERENCE_ONLY
ENVOY_RUNTIME_DEPENDENCY = REJECT
ENVOY_TYPES_IN_CORE = REJECT
HEALTH_AS_ACCEPTANCE_AUTHORITY = REJECT
```

The relevant donor concepts are bounded failure windows, consecutive failures, success-rate/outlier observations, temporary ejection/recovery, maximum ejection percentage, and separation between local-origin and externally-originated failures.

metaO remains authoritative for its own runtime-health projection and policy/strategy use. The donor does not select runtimes, dispatch work, authorize retries, or accept missions.

This pin satisfies only the donor/reference portion of #160. Empirical threshold calibration remains #358, and equivalent factual health evidence from real runtime adapters remains separate execution evidence.
