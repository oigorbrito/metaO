"""Deterministic orchestrator strategy and historical scoring.

Composition sources frozen in Block C:
- Network-AI: system snapshot / pool / budget state scaffolding (adapted).
- ORCH: EMA-style historical outcome scoring (adapted).
- RouteLLM / RouterBench: cost-quality tradeoff methodology (reference/adapt).

No orchestrator SDK types are imported here.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from math import exp, isfinite
from time import time
from typing import Callable, Dict, Iterable, Optional, Protocol, Tuple, runtime_checkable

from .capacity import CapacityRecovery, CapacityStatus, RecoveryEvidenceBasis


class OrchestratorStatus(str, Enum):
    UNKNOWN = "unknown"
    HEALTHY = "healthy"
    DEGRADED = "degraded"
    UNHEALTHY = "unhealthy"
    QUARANTINED = "quarantined"
    RECOVERING = "recovering"


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
    capacity_status: CapacityStatus = CapacityStatus.AVAILABLE
    recover_at_epoch: float | None = None
    recovery: CapacityRecovery | None = None

    @property
    def executor_id(self) -> str:
        """Compatibility name used by the executor-facing control plane."""
        return self.orchestrator_id

    def capacity_available(self, *, now_epoch: float | None = None) -> bool:
        if self.capacity_status is CapacityStatus.AVAILABLE:
            return True
        if self.capacity_status not in {
            CapacityStatus.TEMPORARILY_RATE_LIMITED,
            CapacityStatus.TEMPORARILY_QUOTA_EXHAUSTED,
        }:
            return False
        if self.recovery is None or not self.recovery.valid():
            return False
        observed_now = time() if now_epoch is None else now_epoch
        return observed_now >= self.recovery.recover_at_epoch


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

    def update(self, *, outcome: float, quality: float, latency_ms: float, cost: float, alpha: float = 0.2) -> "HistoricalScore":
        if not 0 < alpha <= 1:
            raise ValueError("alpha must be in (0, 1]")
        if self.samples == 0:
            return HistoricalScore(outcome, quality, latency_ms, cost, 1)
        blend = lambda old, new: alpha * new + (1 - alpha) * old
        return HistoricalScore(blend(self.outcome_ema, outcome), blend(self.quality_ema, quality), blend(self.latency_ema_ms, latency_ms), blend(self.cost_ema, cost), self.samples + 1)


@dataclass(frozen=True)
class ScoreBreakdown:
    total: float
    outcome_component: float
    quality_component: float
    latency_component: float
    cost_component: float


class DeterministicScorer:
    def __init__(self, *, outcome_weight: float = 0.35, quality_weight: float = 0.35, latency_weight: float = 0.15, cost_weight: float = 0.15, latency_scale_ms: float = 1_000.0, cost_scale: float = 1.0) -> None:
        weights = (outcome_weight, quality_weight, latency_weight, cost_weight)
        if not all(isfinite(value) for value in (*weights, latency_scale_ms, cost_scale)):
            raise ValueError("scorer weights and scales must be finite")
        if any(w < 0 for w in weights) or sum(weights) <= 0:
            raise ValueError("weights must be non-negative and not all zero")
        self.outcome_weight, self.quality_weight = outcome_weight, quality_weight
        self.latency_weight, self.cost_weight = latency_weight, cost_weight
        self.latency_scale_ms, self.cost_scale = max(latency_scale_ms, 1e-9), max(cost_scale, 1e-9)

    @staticmethod
    def _clamp01(value: float) -> float:
        return max(0.0, min(1.0, value))

    def score(self, *, outcome: float, quality: float, latency_ms: float, cost: float) -> ScoreBreakdown:
        if not all(isfinite(value) for value in (outcome, quality, latency_ms, cost)):
            raise ValueError("scorer inputs must be finite")
        outcome_component = self.outcome_weight * self._clamp01(outcome)
        quality_component = self.quality_weight * self._clamp01(quality)
        latency_component = self.latency_weight * exp(-max(latency_ms, 0.0) / self.latency_scale_ms)
        cost_component = self.cost_weight * exp(-max(cost, 0.0) / self.cost_scale)
        return ScoreBreakdown(outcome_component + quality_component + latency_component + cost_component, outcome_component, quality_component, latency_component, cost_component)

    def score_history(self, history: HistoricalScore) -> ScoreBreakdown:
        return self.score(outcome=history.outcome_ema, quality=history.quality_ema, latency_ms=history.latency_ema_ms, cost=history.cost_ema)


@dataclass(frozen=True)
class RoutingCandidate:
    orchestrator_id: str
    score: float


class CostQualityRouter:
    _NORMAL_ROUTABLE = frozenset({OrchestratorStatus.HEALTHY, OrchestratorStatus.DEGRADED})

    def __init__(self, scorer: Optional[DeterministicScorer] = None) -> None:
        self.scorer = scorer or DeterministicScorer()

    def rank(self, pools: Iterable[OrchestratorPoolState], *, now_epoch: float | None = None) -> Tuple[RoutingCandidate, ...]:
        available = tuple(pool for pool in pools if pool.capacity_available(now_epoch=now_epoch))
        normal = tuple(pool for pool in available if pool.status in self._NORMAL_ROUTABLE)
        recovering = tuple(pool for pool in available if pool.status is OrchestratorStatus.RECOVERING)
        unknown = tuple(pool for pool in available if pool.status is OrchestratorStatus.UNKNOWN)
        routable = normal or recovering or unknown
        candidates = [RoutingCandidate(pool.orchestrator_id, self.scorer.score(outcome=pool.success_rate, quality=pool.quality, latency_ms=pool.latency_ms, cost=pool.cost).total) for pool in routable]
        return tuple(sorted(candidates, key=lambda item: (-item.score, item.orchestrator_id)))

    def select(self, pools: Iterable[OrchestratorPoolState], *, now_epoch: float | None = None) -> Optional[str]:
        ranked = self.rank(pools, now_epoch=now_epoch)
        return ranked[0].orchestrator_id if ranked else None


def select_orchestrator(pools: Iterable[OrchestratorPoolState], scorer: Optional[DeterministicScorer] = None, *, now_epoch: float | None = None) -> Optional[str]:
    return CostQualityRouter(scorer).select(pools, now_epoch=now_epoch)


@dataclass(frozen=True, slots=True)
class SelectionContext:
    mission_id: str
    execution_id: str
    attempt_number: int
    task_family: str | None = None

    def __post_init__(self) -> None:
        if not self.mission_id.strip() or not self.execution_id.strip():
            raise ValueError("selection context requires mission and execution ids")
        if self.attempt_number < 1:
            raise ValueError("selection context attempt number must be positive")
        if self.task_family is not None and not self.task_family.strip():
            raise ValueError("selection context task_family must be non-empty when provided")


SelectionPolicy = Callable[[tuple[OrchestratorPoolState, ...], float | None], Optional[str]]


@runtime_checkable
class ContextualSelectionPolicy(Protocol):
    def select_with_context(
        self,
        candidates: tuple[OrchestratorPoolState, ...],
        now_epoch: float | None,
        context: SelectionContext,
    ) -> Optional[str]: ...


def select_with_policy(
    pools: Iterable[OrchestratorPoolState],
    policy: SelectionPolicy | None = None,
    *,
    now_epoch: float | None = None,
    context: SelectionContext | None = None,
) -> Optional[str]:
    ranked = CostQualityRouter().rank(pools, now_epoch=now_epoch)
    if not ranked:
        return None
    if policy is None:
        return ranked[0].orchestrator_id
    pool_by_id = {pool.orchestrator_id: pool for pool in pools}
    routable = tuple(pool_by_id[item.orchestrator_id] for item in ranked)
    if context is not None and isinstance(policy, ContextualSelectionPolicy):
        selected = policy.select_with_context(routable, now_epoch, context)
    else:
        selected = policy(routable, now_epoch)
    if selected is None:
        return None
    if selected not in {item.orchestrator_id for item in ranked}:
        raise ValueError("selection policy returned non-routable orchestrator")
    return selected


# The control-plane refactor uses executor terminology while the routing
# contract historically used orchestrator terminology. Keep one state type and
# one selector until the public naming migration is complete.
executorPoolState = OrchestratorPoolState
select_executor = select_orchestrator


__all__ = ["SystemSnapshot", "OrchestratorPoolState", "BudgetState", "OrchestratorStatus", "CapacityStatus", "RecoveryEvidenceBasis", "CapacityRecovery", "HistoricalScore", "ScoreBreakdown", "DeterministicScorer", "SelectionContext", "SelectionPolicy", "ContextualSelectionPolicy", "RoutingCandidate", "CostQualityRouter", "select_orchestrator", "select_with_policy", "executorPoolState", "select_executor"]
