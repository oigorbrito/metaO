"""SelectionPolicy adapter backed by durable benchmark evidence."""

from __future__ import annotations

from dataclasses import dataclass, field

from .benchmark_routing import BenchmarkRoutingPolicy, EvidenceWeightedRouter
from .benchmark_store import BenchmarkEvidenceStorePort
from .routing_decision import (
    RoutingCandidateReceipt,
    RoutingDecisionReceipt,
    RoutingDecisionStorePort,
    routing_policy_digest,
    routing_receipt_id,
)
from .strategy import OrchestratorPoolState, SelectionContext


@dataclass(frozen=True, slots=True)
class BenchmarkSelectionPolicy:
    store: BenchmarkEvidenceStorePort
    routing_policy: BenchmarkRoutingPolicy
    decision_store: RoutingDecisionStorePort | None = None
    _router: EvidenceWeightedRouter = field(init=False, repr=False, compare=False)

    def __post_init__(self) -> None:
        object.__setattr__(self, "_router", EvidenceWeightedRouter(self.routing_policy))

    def __call__(
        self,
        candidates: tuple[OrchestratorPoolState, ...],
        now_epoch: float | None,
    ) -> str | None:
        if now_epoch is None:
            raise ValueError("benchmark selection requires explicit mission time")
        evidence_by_executor = {
            candidate.orchestrator_id: self.store.history(candidate.orchestrator_id)
            for candidate in candidates
        }
        return self._router.select(
            candidates,
            evidence_by_executor,
            now_epoch=now_epoch,
        )

    def select_with_context(
        self,
        candidates: tuple[OrchestratorPoolState, ...],
        now_epoch: float | None,
        context: SelectionContext,
    ) -> str | None:
        if now_epoch is None:
            raise ValueError("benchmark selection requires explicit mission time")
        evidence_by_executor = {
            candidate.orchestrator_id: self.store.history(candidate.orchestrator_id)
            for candidate in candidates
        }
        ranked = self._router.rank(
            candidates,
            evidence_by_executor,
            now_epoch=now_epoch,
        )
        if not ranked:
            return None
        selected = ranked[0].orchestrator_id
        if self.decision_store is not None:
            policy_payload = {
                "task_family": context.task_family,
                "benchmark_id": self.routing_policy.benchmark_id,
                "benchmark_version": self.routing_policy.benchmark_version,
                "task_set": self.routing_policy.task_set,
                "metric_name": self.routing_policy.metric_name,
                "base_weight": self.routing_policy.base_weight,
                "benchmark_weight": self.routing_policy.benchmark_weight,
                "require_fresh": self.routing_policy.require_fresh,
                "max_age_seconds": self.routing_policy.max_age_seconds,
            }
            policy_digest = routing_policy_digest(policy_payload)
            receipt_candidates = tuple(
                RoutingCandidateReceipt(
                    executor_id=item.orchestrator_id,
                    rank=index,
                    total_score=item.total_score,
                    base_score=item.base_score,
                    benchmark_score=item.benchmark_score,
                    evidence_id=item.evidence_id,
                    reason=item.reason,
                )
                for index, item in enumerate(ranked, start=1)
            )
            receipt_id = routing_receipt_id(
                mission_id=context.mission_id,
                execution_id=context.execution_id,
                attempt_number=context.attempt_number,
                now_epoch=now_epoch,
                policy_digest=policy_digest,
                selected_executor_id=selected,
                candidates=receipt_candidates,
            )
            self.decision_store.record(
                RoutingDecisionReceipt(
                    receipt_id=receipt_id,
                    mission_id=context.mission_id,
                    execution_id=context.execution_id,
                    attempt_number=context.attempt_number,
                    now_epoch=now_epoch,
                    policy_digest=policy_digest,
                    selected_executor_id=selected,
                    candidates=receipt_candidates,
                )
            )
        return selected


__all__ = ["BenchmarkSelectionPolicy"]
