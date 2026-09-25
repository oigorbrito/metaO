"""Canonical metaO-observed executor performance evidence.

Evidence aggregation is deterministic over exact compatible identity.

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
        if isinstance(self.sample_count, bool) or not isinstance(self.sample_count, int):
            raise ValueError("observed performance sample_count must be an integer")
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


@dataclass(frozen=True, slots=True)
class ObservedPerformanceAggregate:
    executor_id: str
    executor_version: str
    task_family: str
    runtime_config_digest: str
    tool_policy_digest: str
    environment_id: str
    metric_name: str
    metric_unit: str
    value: float
    sample_count: int
    observed_at_epoch: float
    evidence_ids: tuple[str, ...]


def aggregate_compatible_observations(
    evidence: Iterable[ObservedPerformanceEvidence],
    *,
    task_family: str,
    metric_name: str,
    now_epoch: float,
    max_age_seconds: float,
    min_samples: int,
) -> ObservedPerformanceAggregate | None:
    compatible: list[tuple[ObservedPerformanceEvidence, ObservedPerformanceMetric]] = []
    for item in evidence:
        if item.task_family != task_family:
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
        compatible.append((item, metric))
    if not compatible:
        return None

    identities = {
        (
            item.executor_id,
            item.executor_version,
            item.runtime_config_digest,
            item.tool_policy_digest,
            item.environment_id,
            metric.unit,
        )
        for item, metric in compatible
    }
    if len(identities) != 1:
        return None

    total_samples = sum(item.sample_count for item, _ in compatible)
    if total_samples < min_samples:
        return None
    weighted = sum(metric.value * item.sample_count for item, metric in compatible)
    latest = max(item.observed_at_epoch for item, _ in compatible)
    ordered_ids = tuple(
        item.evidence_id
        for item, _ in sorted(
            compatible,
            key=lambda pair: (pair[0].observed_at_epoch, pair[0].evidence_id),
        )
    )
    executor_id, executor_version, runtime_digest, tool_digest, environment_id, unit = next(
        iter(identities)
    )
    return ObservedPerformanceAggregate(
        executor_id=executor_id,
        executor_version=executor_version,
        task_family=task_family,
        runtime_config_digest=runtime_digest,
        tool_policy_digest=tool_digest,
        environment_id=environment_id,
        metric_name=metric_name,
        metric_unit=unit,
        value=weighted / total_samples,
        sample_count=total_samples,
        observed_at_epoch=latest,
        evidence_ids=ordered_ids,
    )


__all__ = [
    "ObservedPerformanceSource",
    "ObservedPerformanceMetric",
    "ObservedPerformanceEvidence",
    "is_observed_performance_fresh",
    "ObservedPerformanceAggregate",
    "aggregate_compatible_observations",
]
