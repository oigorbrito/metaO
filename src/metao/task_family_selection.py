"""Task-family-aware benchmark selection without cross-family score aggregation."""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum
from typing import Mapping

from .benchmark_routing import BenchmarkRoutingPolicy
from .benchmark_selection import BenchmarkSelectionPolicy
from .benchmark_store import BenchmarkEvidenceStorePort
from .routing_decision import (
    RoutingCandidateReceipt,
    RoutingDecisionReceipt,
    RoutingDecisionStorePort,
    routing_policy_digest,
    routing_receipt_id,
)
from .strategy import CostQualityRouter, OrchestratorPoolState, SelectionContext


class MissingTaskFamilyPolicy(StrEnum):
    FAIL_CLOSED = "fail_closed"
    BASE_ONLY = "base_only"


@dataclass(frozen=True, slots=True)
class TaskFamilyRoutingPolicy:
    families: Mapping[str, BenchmarkRoutingPolicy]
    missing_family: MissingTaskFamilyPolicy = MissingTaskFamilyPolicy.FAIL_CLOSED

    def __post_init__(self) -> None:
        normalized = dict(self.families)
        if not normalized:
            raise ValueError("task-family routing policy requires at least one family")
        if any(not key.strip() for key in normalized):
            raise ValueError("task-family routing policy requires non-empty family ids")
        object.__setattr__(self, "families", normalized)


@dataclass(frozen=True, slots=True)
class TaskFamilyBenchmarkSelectionPolicy:
    store: BenchmarkEvidenceStorePort
    routing_policy: TaskFamilyRoutingPolicy
    decision_store: RoutingDecisionStorePort | None = None

    def __call__(
        self,
        candidates: tuple[OrchestratorPoolState, ...],
        now_epoch: float | None,
    ) -> str | None:
        if self.routing_policy.missing_family is MissingTaskFamilyPolicy.FAIL_CLOSED:
            return None
        return CostQualityRouter().select(candidates, now_epoch=now_epoch)

    def select_with_context(
        self,
        candidates: tuple[OrchestratorPoolState, ...],
        now_epoch: float | None,
        context: SelectionContext,
    ) -> str | None:
        if now_epoch is None:
            raise ValueError("task-family benchmark selection requires explicit mission time")
        task_family = context.task_family
        policy = None if task_family is None else self.routing_policy.families.get(task_family)
        if policy is not None:
            return BenchmarkSelectionPolicy(
                self.store,
                policy,
                decision_store=self.decision_store,
            ).select_with_context(candidates, now_epoch, context)

        if self.routing_policy.missing_family is MissingTaskFamilyPolicy.FAIL_CLOSED:
            return None

        ranked = CostQualityRouter().rank(candidates, now_epoch=now_epoch)
        if not ranked:
            return None
        selected = ranked[0].orchestrator_id
        if self.decision_store is not None:
            receipt_candidates = tuple(
                RoutingCandidateReceipt(
                    executor_id=item.orchestrator_id,
                    rank=index,
                    total_score=item.score,
                    base_score=item.score,
                    benchmark_score=None,
                    evidence_id=None,
                    reason="missing_task_family_base_only",
                )
                for index, item in enumerate(ranked, start=1)
            )
            policy_digest = routing_policy_digest(
                {
                    "task_family": task_family,
                    "missing_family": self.routing_policy.missing_family.value,
                    "family_ids": sorted(self.routing_policy.families),
                }
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


__all__ = [
    "MissingTaskFamilyPolicy",
    "TaskFamilyRoutingPolicy",
    "TaskFamilyBenchmarkSelectionPolicy",
]
