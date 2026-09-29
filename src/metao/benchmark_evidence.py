"""Framework-neutral benchmark evidence for executor qualification and routing.

Benchmark results are factual/advisory evidence about one exact executable
configuration. They never grant enrollment, dispatch, spending, retry, or
Acceptance authority.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from math import isfinite
from typing import Any, Mapping


class BenchmarkEvidenceSource(str, Enum):
    EXTERNAL_REPORTED = "EXTERNAL_REPORTED"
    METAO_REPRODUCED = "METAO_REPRODUCED"


@dataclass(frozen=True, slots=True)
class BenchmarkMetric:
    name: str
    value: float
    unit: str = "score"

    def __post_init__(self) -> None:
        if not self.name.strip():
            raise ValueError("benchmark metric name is required")
        if not isfinite(self.value):
            raise ValueError("benchmark metric value must be finite")
        if not self.unit.strip():
            raise ValueError("benchmark metric unit is required")


@dataclass(frozen=True, slots=True)
class BenchmarkEvidence:
    evidence_id: str
    benchmark_id: str
    benchmark_version: str
    task_set: str
    executor_id: str
    executor_version: str
    harness_id: str
    harness_version: str
    model_id: str
    provider_id: str
    model_version: str
    runtime_config_digest: str
    tool_policy_digest: str
    environment_id: str
    observed_at_epoch: float
    source: BenchmarkEvidenceSource
    raw_result_ref: str
    metrics: tuple[BenchmarkMetric, ...]

    def __post_init__(self) -> None:
        required = (
            self.evidence_id,
            self.benchmark_id,
            self.benchmark_version,
            self.task_set,
            self.executor_id,
            self.executor_version,
            self.harness_id,
            self.harness_version,
            self.model_id,
            self.provider_id,
            self.model_version,
            self.runtime_config_digest,
            self.tool_policy_digest,
            self.environment_id,
            self.raw_result_ref,
        )
        if any(not value.strip() for value in required):
            raise ValueError("benchmark evidence requires complete stable identity")
        if not isfinite(self.observed_at_epoch) or self.observed_at_epoch < 0:
            raise ValueError("benchmark evidence time must be finite and non-negative")
        if not self.metrics:
            raise ValueError("benchmark evidence requires at least one metric")
        names = [metric.name for metric in self.metrics]
        if len(names) != len(set(names)):
            raise ValueError("benchmark metric names must be unique")

    @property
    def executor_configuration_identity(self) -> tuple[str, ...]:
        return (
            self.executor_id,
            self.executor_version,
            self.harness_id,
            self.harness_version,
            self.model_id,
            self.provider_id,
            self.model_version,
            self.runtime_config_digest,
            self.tool_policy_digest,
            self.environment_id,
        )

    @property
    def benchmark_identity(self) -> tuple[str, str, str]:
        return (
            self.benchmark_id,
            self.benchmark_version,
            self.task_set,
        )


def benchmark_evidence_to_record(evidence: BenchmarkEvidence) -> dict[str, object]:
    """Serialize canonical benchmark evidence without benchmark-specific raw fields."""

    return {
        "evidence_id": evidence.evidence_id,
        "benchmark_id": evidence.benchmark_id,
        "benchmark_version": evidence.benchmark_version,
        "task_set": evidence.task_set,
        "executor_id": evidence.executor_id,
        "executor_version": evidence.executor_version,
        "harness_id": evidence.harness_id,
        "harness_version": evidence.harness_version,
        "model_id": evidence.model_id,
        "provider_id": evidence.provider_id,
        "model_version": evidence.model_version,
        "runtime_config_digest": evidence.runtime_config_digest,
        "tool_policy_digest": evidence.tool_policy_digest,
        "environment_id": evidence.environment_id,
        "observed_at_epoch": evidence.observed_at_epoch,
        "source": evidence.source.value,
        "raw_result_ref": evidence.raw_result_ref,
        "metrics": [
            {"name": metric.name, "value": metric.value, "unit": metric.unit}
            for metric in evidence.metrics
        ],
    }


def benchmark_evidence_from_record(record: Mapping[str, Any]) -> BenchmarkEvidence:
    """Restore validated canonical benchmark evidence from a persisted record."""

    try:
        metrics_raw = record["metrics"]
        if not isinstance(metrics_raw, list):
            raise ValueError("persisted benchmark metrics must be a list")
        metrics = tuple(
            BenchmarkMetric(
                name=str(item["name"]),
                value=float(item["value"]),
                unit=str(item["unit"]),
            )
            for item in metrics_raw
            if isinstance(item, Mapping)
        )
        if len(metrics) != len(metrics_raw):
            raise ValueError("persisted benchmark metrics must be objects")
        return BenchmarkEvidence(
            evidence_id=str(record["evidence_id"]),
            benchmark_id=str(record["benchmark_id"]),
            benchmark_version=str(record["benchmark_version"]),
            task_set=str(record["task_set"]),
            executor_id=str(record["executor_id"]),
            executor_version=str(record["executor_version"]),
            harness_id=str(record["harness_id"]),
            harness_version=str(record["harness_version"]),
            model_id=str(record["model_id"]),
            provider_id=str(record["provider_id"]),
            model_version=str(record["model_version"]),
            runtime_config_digest=str(record["runtime_config_digest"]),
            tool_policy_digest=str(record["tool_policy_digest"]),
            environment_id=str(record["environment_id"]),
            observed_at_epoch=float(record["observed_at_epoch"]),
            source=BenchmarkEvidenceSource(str(record["source"])),
            raw_result_ref=str(record["raw_result_ref"]),
            metrics=metrics,
        )
    except (KeyError, TypeError, ValueError) as exc:
        raise ValueError("invalid persisted benchmark evidence record") from exc


def is_benchmark_evidence_fresh(
    evidence: BenchmarkEvidence,
    *,
    now_epoch: float,
    max_age_seconds: float,
) -> bool:
    if not isfinite(now_epoch) or now_epoch < 0:
        raise ValueError("current benchmark time must be finite and non-negative")
    if not isfinite(max_age_seconds) or max_age_seconds <= 0:
        raise ValueError("benchmark max age must be finite and positive")
    if now_epoch < evidence.observed_at_epoch:
        return False
    return (now_epoch - evidence.observed_at_epoch) <= max_age_seconds


def benchmark_evidence_comparable(
    left: BenchmarkEvidence,
    right: BenchmarkEvidence,
) -> bool:
    """Return whether two results share the exact benchmark contract.

    This deliberately does not compare executor/model identity: different systems
    are expected to be compared under the same benchmark/version/task set.
    """

    return left.benchmark_identity == right.benchmark_identity


__all__ = [
    "BenchmarkEvidence",
    "BenchmarkEvidenceSource",
    "BenchmarkMetric",
    "benchmark_evidence_comparable",
    "benchmark_evidence_from_record",
    "benchmark_evidence_to_record",
    "is_benchmark_evidence_fresh",
]
