# Synthetic runtime calibration lane

This experiment advances #358 without claiming real-provider calibration.

It evaluates two bounded questions:

1. the analytic trade-off between reconciliation interval and observation pressure for the candidate intervals 30, 60, 180 and 300 seconds;
2. deterministic runtime-health behavior across a grid of existing `RuntimeHealthPolicy` parameters.

Run:

```console
python scripts/runtime_calibration_experiment.py --output .artifacts/runtime-calibration-synthetic-v1.json
```

The report is deliberately classified:

```text
EVIDENCE = SYNTHETIC_ONLY
REAL_PROVIDER_EXECUTION = NO
SELECTS_PRODUCT_DEFAULTS = NO
```

The supervision calculation assumes failure onset is uniformly distributed between reconciliation observations. Therefore mean detection latency is `interval/2`, p95 is `0.95 * interval`, and observation pressure is `3600/interval` observations per hour. These are analytical quantities under the stated assumption, not provider measurements.

The health-policy matrix executes the repository's actual Python `RuntimeHealthTracker` over deterministic transient-failure, burst-failure and recovery sequences. It records behavior for 81 parameter combinations and does not mutate `RuntimeHealthPolicy` defaults.

Real-provider API/quota overhead, retry/backoff behavior, handoff cost, MTTR, task completion time, acceptance failure rate and monetary cost remain separate empirical work. No production default should be selected from this synthetic report alone.

## Integration baseline

This branch has been synchronized with current `main@663ad81b4e53665d573487226689a4a48fbd1a1b` without force-push. Exact-head CI evidence must be taken from the post-synchronization PR head.
