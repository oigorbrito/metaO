"""Deterministic benchmark qualification for executor-market evidence.

Benchmark evidence is advisory. It cannot authorize enrollment, spending,
dispatch, or override hard security/policy gates.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable, Mapping

from .benchmark_evidence import BenchmarkEvidence, is_benchmark_evidence_fresh
from .executor_market import ExecutorQualification, QualificationOutcome


@dataclass(frozen=True, slots=True)
class BenchmarkQualificationPolicy:
    policy_version: str
    required_families: tuple[str, ...]
    minimum_scores: Mapping[str, float]
    max_age_seconds: float

    def __post_init__(self) -> None:
        if not self.policy_version.strip():
            raise ValueError("benchmark qualification policy_version is required")
        if not self.required_families:
            raise ValueError("benchmark qualification requires at least one family")
        if len(set(self.required_families)) != len(self.required_families):
            raise ValueError("required benchmark families must be unique")
        if self.max_age_seconds <= 0:
            raise ValueError("benchmark max age must be positive")
        for family in self.required_families:
            if family not in self.minimum_scores:
                raise ValueError(f"missing minimum score for {family}")
            threshold = self.minimum_scores[family]
            if not 0.0 <= threshold <= 1.0:
                raise ValueError(f"minimum score for {family} must be within [0, 1]")


def _metric_ratio(evidence: BenchmarkEvidence) -> float:
    if len(evidence.metrics) != 1:
        raise ValueError("initial benchmark qualification requires exactly one aggregate metric")
    metric = evidence.metrics[0]
    if metric.unit != "ratio":
        raise ValueError("initial benchmark qualification requires ratio metrics")
    if not 0.0 <= metric.value <= 1.0:
        raise ValueError("benchmark ratio must be within [0, 1]")
    return metric.value


def qualify_benchmark_evidence(
    evidence_set: Iterable[BenchmarkEvidence],
    policy: BenchmarkQualificationPolicy,
    *,
    now_epoch: float,
    hard_gate_blocked: bool = False,
) -> ExecutorQualification:
    """Qualify one exact executor configuration from benchmark evidence."""

    if hard_gate_blocked:
        return ExecutorQualification(
            QualificationOutcome.BLOCKED,
            ("security/policy hard gate blocks benchmark-based qualification",),
        )

    records = tuple(evidence_set)
    if not records:
        return ExecutorQualification(
            QualificationOutcome.BLOCKED,
            ("no benchmark evidence supplied",),
        )

    identity = records[0].executor_configuration_identity
    if any(record.executor_configuration_identity != identity for record in records[1:]):
        return ExecutorQualification(
            QualificationOutcome.BLOCKED,
            ("benchmark evidence mixes executor configurations",),
        )

    by_family: dict[str, BenchmarkEvidence] = {}
    for record in records:
        if record.benchmark_id in by_family:
            return ExecutorQualification(
                QualificationOutcome.BLOCKED,
                (f"duplicate benchmark family evidence: {record.benchmark_id}",),
            )
        by_family[record.benchmark_id] = record

    missing = tuple(f for f in policy.required_families if f not in by_family)
    if missing:
        return ExecutorQualification(
            QualificationOutcome.QUALIFIED_RESTRICTED,
            ("missing required benchmark evidence: " + ",".join(missing),),
        )

    stale = tuple(
        family
        for family in policy.required_families
        if not is_benchmark_evidence_fresh(
            by_family[family],
            now_epoch=now_epoch,
            max_age_seconds=policy.max_age_seconds,
        )
    )
    if stale:
        return ExecutorQualification(
            QualificationOutcome.QUALIFIED_RESTRICTED,
            ("stale benchmark evidence: " + ",".join(stale),),
        )

    below = tuple(
        family
        for family in policy.required_families
        if _metric_ratio(by_family[family]) < policy.minimum_scores[family]
    )
    if below:
        return ExecutorQualification(
            QualificationOutcome.UNQUALIFIED,
            ("benchmark threshold not met: " + ",".join(below),),
        )

    return ExecutorQualification(
        QualificationOutcome.QUALIFIED,
        (
            f"benchmark evidence satisfies policy {policy.policy_version}; "
            "benchmark evidence remains advisory only",
        ),
    )


__all__ = ["BenchmarkQualificationPolicy", "qualify_benchmark_evidence"]
