"""Deterministic benchmark-evidence overlay for already-eligible routing candidates.

Hard eligibility remains owned by the existing routing/control-plane layers.
This module can only reorder candidates that the base router already considers
routable.
"""

from __future__ import annotations

from dataclasses import dataclass
from math import isfinite
from typing import Iterable, Mapping, Sequence

from .benchmark_evidence import BenchmarkEvidence, is_benchmark_evidence_fresh
from .strategy import CostQualityRouter, OrchestratorPoolState


@dataclass(frozen=True, slots=True)
class BenchmarkRoutingPolicy:
    benchmark_id: str
    benchmark_version: str
    task_set: str
    metric_name: str
    base_weight: float = 1.0
    benchmark_weight: float = 1.0
    require_fresh: bool = True
    max_age_seconds: float = 86_400.0

    def __post_init__(self) -> None:
        if not all(
            value.strip()
            for value in (
                self.benchmark_id,
                self.benchmark_version,
                self.task_set,
                self.metric_name,
            )
        ):
            raise ValueError("benchmark routing policy requires stable benchmark identity")
        weights = (self.base_weight, self.benchmark_weight)
        if not all(isfinite(value) and value >= 0 for value in weights):
            raise ValueError("routing weights must be finite and non-negative")
        if sum(weights) <= 0:
            raise ValueError("routing weights cannot both be zero")
        if not isfinite(self.max_age_seconds) or self.max_age_seconds <= 0:
            raise ValueError("benchmark max age must be finite and positive")


@dataclass(frozen=True, slots=True)
class EvidenceRoutingCandidate:
    orchestrator_id: str
    total_score: float
    base_score: float
    benchmark_score: float | None
    evidence_id: str | None
    reason: str


class EvidenceWeightedRouter:
    """Re-rank already-routable candidates using exact benchmark evidence."""

    def __init__(
        self,
        policy: BenchmarkRoutingPolicy,
        *,
        base_router: CostQualityRouter | None = None,
    ) -> None:
        self.policy = policy
        self.base_router = base_router or CostQualityRouter()

    def _matching_metric(
        self,
        evidence: Sequence[BenchmarkEvidence],
        *,
        now_epoch: float,
    ) -> tuple[float, str] | None:
        matches: list[tuple[float, float, str]] = []
        for item in evidence:
            if (
                item.benchmark_id != self.policy.benchmark_id
                or item.benchmark_version != self.policy.benchmark_version
                or item.task_set != self.policy.task_set
            ):
                continue
            if self.policy.require_fresh and not is_benchmark_evidence_fresh(
                item,
                now_epoch=now_epoch,
                max_age_seconds=self.policy.max_age_seconds,
            ):
                continue
            metric = next(
                (metric for metric in item.metrics if metric.name == self.policy.metric_name),
                None,
            )
            if metric is None:
                continue
            if metric.unit != "ratio" or not 0.0 <= metric.value <= 1.0:
                continue
            matches.append((item.observed_at_epoch, metric.value, item.evidence_id))
        if not matches:
            return None
        _, value, evidence_id = max(matches, key=lambda item: (item[0], item[2]))
        return value, evidence_id

    def rank(
        self,
        pools: Iterable[OrchestratorPoolState],
        evidence_by_executor: Mapping[str, Sequence[BenchmarkEvidence]],
        *,
        now_epoch: float,
    ) -> tuple[EvidenceRoutingCandidate, ...]:
        base = self.base_router.rank(pools, now_epoch=now_epoch)
        denominator = self.policy.base_weight + self.policy.benchmark_weight
        result: list[EvidenceRoutingCandidate] = []
        for candidate in base:
            matched = self._matching_metric(
                evidence_by_executor.get(candidate.orchestrator_id, ()),
                now_epoch=now_epoch,
            )
            if matched is None:
                result.append(
                    EvidenceRoutingCandidate(
                        orchestrator_id=candidate.orchestrator_id,
                        total_score=candidate.score,
                        base_score=candidate.score,
                        benchmark_score=None,
                        evidence_id=None,
                        reason="no_applicable_benchmark_evidence",
                    )
                )
                continue
            benchmark_score, evidence_id = matched
            total = (
                self.policy.base_weight * candidate.score
                + self.policy.benchmark_weight * benchmark_score
            ) / denominator
            result.append(
                EvidenceRoutingCandidate(
                    orchestrator_id=candidate.orchestrator_id,
                    total_score=total,
                    base_score=candidate.score,
                    benchmark_score=benchmark_score,
                    evidence_id=evidence_id,
                    reason="exact_fresh_benchmark_evidence",
                )
            )
        return tuple(
            sorted(
                result,
                key=lambda item: (-item.total_score, item.orchestrator_id),
            )
        )

    def select(
        self,
        pools: Iterable[OrchestratorPoolState],
        evidence_by_executor: Mapping[str, Sequence[BenchmarkEvidence]],
        *,
        now_epoch: float,
    ) -> str | None:
        ranked = self.rank(
            pools,
            evidence_by_executor,
            now_epoch=now_epoch,
        )
        return ranked[0].orchestrator_id if ranked else None


__all__ = [
    "BenchmarkRoutingPolicy",
    "EvidenceRoutingCandidate",
    "EvidenceWeightedRouter",
]
