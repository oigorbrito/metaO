"""Deterministic synthetic calibration harness for issue #358.

This harness measures trade-offs. It does not select or mutate production
runtime-health defaults and does not claim real-provider performance.
"""

from __future__ import annotations

import argparse
from dataclasses import asdict, dataclass
import json
from pathlib import Path
from typing import Iterable

from metao.core import ExecutionStatus
from metao.runtime_health import (
    RuntimeHealthPolicy,
    RuntimeHealthState,
    RuntimeHealthTracker,
)

DEFAULT_SUPERVISION_INTERVALS_S = (30, 60, 180, 300)
DEFAULT_WINDOW_SIZES = (3, 5, 8)
DEFAULT_QUARANTINE_THRESHOLDS = (2, 3, 4)
DEFAULT_UNHEALTHY_PERCENTAGES = (50, 60, 75)
DEFAULT_RECOVERY_SUCCESSES = (1, 2, 3)

TRANSIENT_SEQUENCE = ("S", "F", "S", "S", "S")
BURST_SEQUENCE = ("S", "F", "F", "F", "F")
RECOVERY_SEQUENCE = ("F", "F", "F") + ("S",) * 8


@dataclass(frozen=True, slots=True)
class SupervisionIntervalMeasurement:
    interval_s: int
    mean_detection_latency_s: float
    p95_detection_latency_s: float
    worst_case_detection_latency_s: float
    observations_per_hour: float


@dataclass(frozen=True, slots=True)
class HealthPolicyMeasurement:
    window_size: int
    quarantine_consecutive_failures: int
    unhealthy_failure_percent: int
    recovery_successes_required: int
    transient_states: tuple[str, ...]
    transient_quarantined: bool
    burst_states: tuple[str, ...]
    burst_first_unhealthy_or_quarantined_observation: int | None
    recovery_states: tuple[str, ...]
    recovery_successes_until_healthy: int | None


def measure_supervision_interval(interval_s: int) -> SupervisionIntervalMeasurement:
    if interval_s <= 0:
        raise ValueError("supervision interval must be positive")
    # Synthetic assumption: failure onset is uniformly distributed between
    # reconciliation observations. This is not a real-provider latency claim.
    return SupervisionIntervalMeasurement(
        interval_s=interval_s,
        mean_detection_latency_s=interval_s / 2,
        p95_detection_latency_s=interval_s * 0.95,
        worst_case_detection_latency_s=float(interval_s),
        observations_per_hour=3600 / interval_s,
    )


def _pareto_intervals(
    measurements: Iterable[SupervisionIntervalMeasurement],
) -> tuple[int, ...]:
    values = tuple(measurements)
    frontier: list[int] = []
    for candidate in values:
        dominated = any(
            other.interval_s != candidate.interval_s
            and other.mean_detection_latency_s <= candidate.mean_detection_latency_s
            and other.observations_per_hour <= candidate.observations_per_hour
            and (
                other.mean_detection_latency_s < candidate.mean_detection_latency_s
                or other.observations_per_hour < candidate.observations_per_hour
            )
            for other in values
        )
        if not dominated:
            frontier.append(candidate.interval_s)
    return tuple(sorted(frontier))


def _run_sequence(
    policy: RuntimeHealthPolicy,
    sequence: tuple[str, ...],
) -> tuple[RuntimeHealthState, ...]:
    tracker = RuntimeHealthTracker(
        runtime_id="synthetic-runtime",
        runtime_version="1",
        config_id="issue-358",
        policy=policy,
    )
    states: list[RuntimeHealthState] = []
    for index, item in enumerate(sequence, start=1):
        status = (
            ExecutionStatus.SUCCEEDED
            if item == "S"
            else ExecutionStatus.FAILED
        )
        states.append(
            tracker.record_execution(
                status,
                execution_id=f"synthetic-{index}",
            ).state
        )
    return tuple(states)


def measure_health_policy(policy: RuntimeHealthPolicy) -> HealthPolicyMeasurement:
    transient = _run_sequence(policy, TRANSIENT_SEQUENCE)
    burst = _run_sequence(policy, BURST_SEQUENCE)
    recovery = _run_sequence(policy, RECOVERY_SEQUENCE)

    burst_detection = next(
        (
            index
            for index, state in enumerate(burst, start=1)
            if state
            in {
                RuntimeHealthState.UNHEALTHY,
                RuntimeHealthState.QUARANTINED,
            }
        ),
        None,
    )

    failure_prefix = 3
    recovery_successes = next(
        (
            index - failure_prefix
            for index, state in enumerate(recovery, start=1)
            if index > failure_prefix and state is RuntimeHealthState.HEALTHY
        ),
        None,
    )

    return HealthPolicyMeasurement(
        window_size=policy.window_size,
        quarantine_consecutive_failures=policy.quarantine_consecutive_failures,
        unhealthy_failure_percent=policy.unhealthy_failure_percent,
        recovery_successes_required=policy.recovery_successes_required,
        transient_states=tuple(state.value for state in transient),
        transient_quarantined=RuntimeHealthState.QUARANTINED in transient,
        burst_states=tuple(state.value for state in burst),
        burst_first_unhealthy_or_quarantined_observation=burst_detection,
        recovery_states=tuple(state.value for state in recovery),
        recovery_successes_until_healthy=recovery_successes,
    )


def build_report() -> dict[str, object]:
    intervals = tuple(
        measure_supervision_interval(value)
        for value in DEFAULT_SUPERVISION_INTERVALS_S
    )
    health_candidates = tuple(
        measure_health_policy(
            RuntimeHealthPolicy(
                window_size=window_size,
                quarantine_consecutive_failures=quarantine_threshold,
                unhealthy_failure_percent=unhealthy_percentage,
                recovery_successes_required=recovery_successes,
            )
        )
        for window_size in DEFAULT_WINDOW_SIZES
        for quarantine_threshold in DEFAULT_QUARANTINE_THRESHOLDS
        for unhealthy_percentage in DEFAULT_UNHEALTHY_PERCENTAGES
        for recovery_successes in DEFAULT_RECOVERY_SUCCESSES
    )

    return {
        "schema": "metao-runtime-calibration-synthetic-v1",
        "issue": 358,
        "evidence_classification": "SYNTHETIC_ONLY",
        "real_provider_execution": False,
        "selects_product_defaults": False,
        "assumptions": {
            "supervision_failure_onset": "uniform_between_observations",
            "observation_cost_unit": "one_reconciliation_observation",
            "health_sequences": {
                "transient": list(TRANSIENT_SEQUENCE),
                "failure_burst": list(BURST_SEQUENCE),
                "recovery": list(RECOVERY_SEQUENCE),
            },
        },
        "supervision_intervals": [asdict(item) for item in intervals],
        "supervision_pareto_frontier_s": list(_pareto_intervals(intervals)),
        "health_policy_candidates": [asdict(item) for item in health_candidates],
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()

    report = build_report()
    encoded = json.dumps(report, indent=2, sort_keys=True) + "\n"
    if args.output is None:
        print(encoded, end="")
    else:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(encoded, encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
