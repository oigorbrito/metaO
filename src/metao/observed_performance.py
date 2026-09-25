"""Canonical metaO-observed executor performance evidence.

This evidence is routing/audit input only. It cannot mint eligibility, dispatch,
spending, retry, verification or Acceptance authority.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum
from math import isfinite
from typing import Iterable


class ObservedPerformanceSource(StrEnum):
    METAO_EXECUTION = "metao_execution"
    METAO_REPLAY = "metao_replay"


@dataclass(frozen=True, slots=True)
class ObservedPerformanceMetric:
    name: str
    value: float
    unit: str

    def __post_init__(self) -> None:
        if not self.name.strip() or not self.unit.strip():
            raise ValueError("observed performance metric requires name and unit")
        if not isfinite(self.value):
            raise ValueError("observed performance metric value must be finite")


@dataclass(frozen=True, slots=True)
class ObservedPerformanceEvidence:
    evidence_id: str
    executor_id: str
    executor_version: str
    task_family: str
    runtime_config_digest: str
    tool_policy_digest: str
    environment_id: str
    observed_at_epoch: float
    source: ObservedPerformanceSource
    raw_result_ref: str
    sample_count: int
    metrics: tuple[ObservedPerformanceMetric, ...]

    def __post_init__(self) -> None:
        required = (
            self.evidence_id,
            self.executor_id,
            self.executor_version,
            self.task_family,
            self.runtime_config_digest,
            self.tool_policy_digest,
            self.environment_id,
            self.raw_result_ref,
        )
        if not all(value.strip() for value in required):
            raise ValueError("observed performance evidence requires stable identity")
        if not isfinite(self.observed_at_epoch) or self.observed_at_epoch < 0:
            raise ValueError("observed performance time must be finite and non-negative")
        if self.sample_count < 1:
            raise ValueError("observed performance sample_count must be positive")
        if not self.metrics:
            raise ValueError("observed performance evidence requires metrics")
        names = [metric.name for metric in self.metrics]
        if len(names) != len(set(names)):
            raise ValueError("observed performance metric names must be unique")

    def metric(self, name: str) -> ObservedPerformanceMetric | None:
        return next((item for item in self.metrics if item.name == name), None)


def is_observed_performance_fresh(
    evidence: ObservedPerformanceEvidence,
    *,
    now_epoch: float,
    max_age_seconds: float,
) -> bool:
    if not isfinite(now_epoch) or now_epoch < 0:
        raise ValueError("current time must be finite and non-negative")
    if not isfinite(max_age_seconds) or max_age_seconds <= 0:
        raise ValueError("max age must be finite and positive")
    age = now_epoch - evidence.observed_at_epoch
    return 0.0 <= age <= max_age_seconds


def latest_compatible_observation(
    evidence: Iterable[ObservedPerformanceEvidence],
    *,
    task_family: str,
    metric_name: str,
    now_epoch: float,
    max_age_seconds: float,
    min_samples: int,
) -> tuple[ObservedPerformanceEvidence, ObservedPerformanceMetric] | None:
    matches: list[tuple[float, str, ObservedPerformanceEvidence, ObservedPerformanceMetric]] = []
    for item in evidence:
        if item.task_family != task_family or item.sample_count < min_samples:
            continue
        if not is_observed_performance_fresh(
            item,
            now_epoch=now_epoch,
            max_age_seconds=max_age_seconds,
        ):
            continue
        metric = item.metric(metric_name)
        if metric is None:
            continue
        matches.append((item.observed_at_epoch, item.evidence_id, item, metric))
    if not matches:
        return None
    _, _, item, metric = max(matches, key=lambda value: (value[0], value[1]))
    return item, metric


__all__ = [
    "ObservedPerformanceSource",
    "ObservedPerformanceMetric",
    "ObservedPerformanceEvidence",
    "is_observed_performance_fresh",
    "latest_compatible_observation",
]
