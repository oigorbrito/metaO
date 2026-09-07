"""Deterministic orchestrator strategy and historical scoring.

Composition sources frozen in Block C:
- Network-AI: system snapshot / pool / budget state scaffolding (adapted).
- ORCH: EMA-style historical outcome scoring (adapted).
- RouteLLM / RouterBench: cost-quality tradeoff methodology (reference/adapt).

No orchestrator SDK types are imported here.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from math import exp
from typing import Dict, Iterable, Mapping, Optional, Sequence, Tuple


class OrchestratorStatus(str, Enum):
    HEALTHY = "healthy"
    DEGRADED = "degraded"
    TEMPORARILY_QUOTA_EXHAUSTED = "temporarily_quota_exhausted"
    UNHEALTHY = "unhealthy"
    QUARANTINED = "quarantined"


@dataclass(frozen=True)
class BudgetState:
    money_remaining: float
    tokens_remaining: int
    wall_time_remaining_s: float

    def exhausted(self) -> bool:
        return (
            self.money_remaining <= 0
            or self.tokens_remaining <= 0
            or self.wall_time_remaining_s <= 0
        )


@dataclass(frozen=True)
class OrchestratorPoolState:
    orchestrator_id: str
    status: OrchestratorStatus
    capabilities: frozenset[str] = frozenset()
    success_rate: float = 0.5
    quality: float = 0.5
    reliability: float = 0.5
    latency_ms: float = 1_000.0
    cost: float = 0.0


@dataclass(frozen=True)
class SystemSnapshot:
    mission_id: str
    pools: Tuple[OrchestratorPoolState, ...]
    budget: BudgetState
    sequence: int = 0

    def by_id(self) -> Dict[str, OrchestratorPoolState]:
        return {pool.orchestrator_id: pool for pool in self.pools}


@dataclass(frozen=True)
class HistoricalScore:
    outcome_ema: float = 0.5
    quality_ema: float = 0.5
    latency_ema_ms: float = 1_000.0
    cost_ema: float = 0.0
    samples: int = 0

    def update(
        self,
        *,
        outcome: float,
        quality: float,
        latency_ms: float,
        cost: float,
        alpha: float = 0.2,
    ) -> "HistoricalScore":
        if not 0 < alpha <= 1:
            raise ValueError("alpha must be in (0, 1]")
        if self.samples == 0:
            return HistoricalScore(outcome, quality, latency_ms, cost, 1)
        blend = lambda old, new: alpha * new + (1 - alpha) * old
        return HistoricalScore(
            outcome_ema=blend(self.outcome_ema, outcome),
            quality_ema=blend(self.quality_ema, quality),
            latency_ema_ms=blend(self.latency_ema_ms, latency_ms),
            cost_ema=blend(self.cost_ema, cost),
            samples=self.samples + 1,
        )


@dataclass(frozen=True)
class ScoreBreakdown:
    total: float
    outcome_component: float
    quality_component: float
    latency_component: float
    cost_component: float


class DeterministicScorer:
    """Simple deterministic cost-quality scorer.

    Higher outcome/quality are rewarded. Latency and cost are monotonically
    penalized with bounded transforms so one unbounded signal cannot dominate.
    """

    def __init__(
        self,
        *,
        outcome_weight: float = 0.35,
        quality_weight: float = 0.35,
        latency_weight: float = 0.15,
        cost_weight: float = 0.15,
        latency_scale_ms: float = 1_000.0,
        cost_scale: float = 1.0,
    ) -> None:
        weights = (outcome_weight, quality_weight, latency_weight, cost_weight)
        if any(w < 0 for w in weights) or sum(weights) <= 0:
            raise ValueError("weights must be non-negative and not all zero")
        self.outcome_weight = outcome_weight
        self.quality_weight = quality_weight
        self.latency_weight = latency_weight
        self.cost_weight = cost_weight
        self.latency_scale_ms = max(latency_scale_ms, 1e-9)
        self.cost_scale = max(cost_scale, 1e-9)

    @staticmethod
    def _clamp01(value: float) -> float:
        return max(0.0, min(1.0, value))

    def score(
        self,
        *,
        outcome: float,
        quality: float,
        latency_ms: float,
        cost: float,
    ) -> ScoreBreakdown:
        outcome_component = self.outcome_weight * self._clamp01(outcome)
        quality_component = self.quality_weight * self._clamp01(quality)
        latency_utility = exp(-max(latency_ms, 0.0) / self.latency_scale_ms)
        cost_utility = exp(-max(cost, 0.0) / self.cost_scale)
        latency_component = self.latency_weight * latency_utility
        cost_component = self.cost_weight * cost_utility
        total = (
            outcome_component
            + quality_component
            + latency_component
            + cost_component
        )
        return ScoreBreakdown(
            total=total,
            outcome_component=outcome_component,
            quality_component=quality_component,
            latency_component=latency_component,
            cost_component=cost_component,
        )

    def score_history(self, history: HistoricalScore) -> ScoreBreakdown:
        return self.score(
            outcome=history.outcome_ema,
            quality=history.quality_ema,
            latency_ms=history.latency_ema_ms,
            cost=history.cost_ema,
        )


@dataclass(frozen=True)
class RoutingCandidate:
    orchestrator_id: str
    score: float


class CostQualityRouter:
    def __init__(self, scorer: Optional[DeterministicScorer] = None) -> None:
        self.scorer = scorer or DeterministicScorer()

    def rank(self, pools: Iterable[OrchestratorPoolState]) -> Tuple[RoutingCandidate, ...]:
        candidates = []
        for pool in pools:
            if pool.status not in {
                OrchestratorStatus.HEALTHY,
                OrchestratorStatus.DEGRADED,
            }:
                continue
            score = self.scorer.score(
                outcome=pool.success_rate,
                quality=pool.quality,
                latency_ms=pool.latency_ms,
                cost=pool.cost,
            ).total
            candidates.append(RoutingCandidate(pool.orchestrator_id, score))
        return tuple(sorted(candidates, key=lambda item: (-item.score, item.orchestrator_id)))

    def select(self, pools: Iterable[OrchestratorPoolState]) -> Optional[str]:
        ranked = self.rank(pools)
        return ranked[0].orchestrator_id if ranked else None


def select_orchestrator(
    pools: Iterable[OrchestratorPoolState],
    scorer: Optional[DeterministicScorer] = None,
) -> Optional[str]:
    return CostQualityRouter(scorer).select(pools)


__all__ = [
    "SystemSnapshot",
    "OrchestratorPoolState",
    "BudgetState",
    "OrchestratorStatus",
    "HistoricalScore",
    "ScoreBreakdown",
    "DeterministicScorer",
    "RoutingCandidate",
    "CostQualityRouter",
    "select_orchestrator",
]
