"""Fuse benchmark and metaO-observed performance after hard eligibility."""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum
from math import isfinite
from typing import Mapping

from .benchmark_routing import BenchmarkRoutingPolicy, EvidenceWeightedRouter
from .benchmark_store import BenchmarkEvidenceStorePort
from .observed_performance import aggregate_compatible_observations
from .observed_performance_store import ObservedPerformanceStorePort
from .routing_decision import (
    RoutingCandidateReceipt,
    RoutingDecisionReceipt,
    RoutingDecisionStorePort,
    routing_policy_digest,
    routing_receipt_id,
)
from .strategy import OrchestratorPoolState, SelectionContext


class MissingObservedEvidencePolicy(StrEnum):
    PRIOR_ONLY = "prior_only"
    EXCLUDE_CANDIDATE = "exclude_candidate"


@dataclass(frozen=True, slots=True)
class ObservedPerformanceRoutingPolicy:
    metric_name: str = "success_rate"
    prior_weight: float = 1.0
    observed_weight: float = 1.0
    max_age_seconds: float = 86_400.0
    min_samples: int = 1
    missing_evidence: MissingObservedEvidencePolicy = MissingObservedEvidencePolicy.PRIOR_ONLY

    def __post_init__(self) -> None:
        if self.metric_name not in {"success_rate", "quality", "reliability"}:
            raise ValueError(
                "observed routing v1 supports only normalized success/quality/reliability metrics"
            )
        if not all(
            isfinite(value) and value >= 0
            for value in (self.prior_weight, self.observed_weight)
        ):
            raise ValueError("observed routing weights must be finite and non-negative")
        if self.prior_weight + self.observed_weight <= 0:
            raise ValueError("observed routing weights cannot both be zero")
        if not isfinite(self.max_age_seconds) or self.max_age_seconds <= 0:
            raise ValueError("observed routing max age must be positive")
        if self.min_samples < 1:
            raise ValueError("observed routing min_samples must be positive")


@dataclass(frozen=True, slots=True)
class EmpiricalExecutorIdentity:
    executor_version: str
    runtime_config_digest: str
    tool_policy_digest: str
    environment_id: str

    def __post_init__(self) -> None:
        if not all(
            value.strip()
            for value in (
                self.executor_version,
                self.runtime_config_digest,
                self.tool_policy_digest,
                self.environment_id,
            )
        ):
            raise ValueError("empirical executor identity requires exact non-empty fields")


@dataclass(frozen=True, slots=True)
class EmpiricalFamilyRoutingPolicy:
    benchmark: BenchmarkRoutingPolicy
    observed: ObservedPerformanceRoutingPolicy


@dataclass(frozen=True, slots=True)
class EmpiricalTaskFamilyRoutingPolicy:
    families: Mapping[str, EmpiricalFamilyRoutingPolicy]

    def __post_init__(self) -> None:
        normalized = dict(self.families)
        if not normalized or any(not key.strip() for key in normalized):
            raise ValueError("empirical task-family routing policy requires family mappings")
        object.__setattr__(self, "families", normalized)


@dataclass(frozen=True, slots=True)
class EmpiricalTaskFamilySelectionPolicy:
    benchmark_store: BenchmarkEvidenceStorePort
    observed_store: ObservedPerformanceStorePort
    families: Mapping[str, EmpiricalFamilyRoutingPolicy]
    identities: Mapping[str, EmpiricalExecutorIdentity]
    decision_store: RoutingDecisionStorePort | None = None

    def __post_init__(self) -> None:
        if not self.families or any(not key.strip() for key in self.families):
            raise ValueError("empirical task-family policy requires family mappings")
        if not self.identities or any(not key.strip() for key in self.identities):
            raise ValueError("empirical task-family policy requires executor identities")

    def __call__(
        self,
        candidates: tuple[OrchestratorPoolState, ...],
        now_epoch: float | None,
    ) -> str | None:
        return None

    def select_with_context(
        self,
        candidates: tuple[OrchestratorPoolState, ...],
        now_epoch: float | None,
        context: SelectionContext,
    ) -> str | None:
        if now_epoch is None:
            raise ValueError("empirical routing requires explicit mission time")
        if context.task_family is None:
            return None
        family = self.families.get(context.task_family)
        if family is None:
            return None

        benchmark_by_executor = {}
        for candidate in candidates:
            identity = self.identities.get(candidate.orchestrator_id)
            if identity is None:
                benchmark_by_executor[candidate.orchestrator_id] = ()
                continue
            benchmark_by_executor[candidate.orchestrator_id] = tuple(
                item
                for item in self.benchmark_store.history(candidate.orchestrator_id)
                if (
                    item.executor_version == identity.executor_version
                    and item.runtime_config_digest == identity.runtime_config_digest
                    and item.tool_policy_digest == identity.tool_policy_digest
                    and item.environment_id == identity.environment_id
                )
            )
        benchmark_ranked = EvidenceWeightedRouter(family.benchmark).rank(
            candidates,
            benchmark_by_executor,
            now_epoch=now_epoch,
        )

        observed_by_executor = {}
        for candidate in candidates:
            identity = self.identities.get(candidate.orchestrator_id)
            if identity is None:
                observed_by_executor[candidate.orchestrator_id] = ()
                continue
            observed_by_executor[candidate.orchestrator_id] = tuple(
                item
                for item in self.observed_store.history(candidate.orchestrator_id)
                if (
                    item.executor_version == identity.executor_version
                    and item.runtime_config_digest == identity.runtime_config_digest
                    and item.tool_policy_digest == identity.tool_policy_digest
                    and item.environment_id == identity.environment_id
                )
            )
        fused: list[
            tuple[
                float,
                str,
                float,
                float,
                float | None,
                str | None,
                tuple[str, ...],
                str,
            ]
        ] = []
        denominator = family.observed.prior_weight + family.observed.observed_weight
        for item in benchmark_ranked:
            observed_match = aggregate_compatible_observations(
                observed_by_executor.get(item.orchestrator_id, ()),
                task_family=context.task_family,
                metric_name=family.observed.metric_name,
                now_epoch=now_epoch,
                max_age_seconds=family.observed.max_age_seconds,
                min_samples=family.observed.min_samples,
            )
            if observed_match is None:
                if (
                    family.observed.missing_evidence
                    is MissingObservedEvidencePolicy.EXCLUDE_CANDIDATE
                ):
                    continue
                fused_score = item.total_score
                observed_score = None
                observed_evidence_ids: tuple[str, ...] = ()
                reason = item.reason + "+missing_observed_prior_only"
            else:
                if observed_match.metric_unit != "ratio" or not 0.0 <= observed_match.value <= 1.0:
                    fused_score = item.total_score
                    observed_score = None
                    observed_evidence_ids = ()
                    reason = item.reason + "+invalid_observed_metric"
                else:
                    observed_score = observed_match.value
                    observed_evidence_ids = observed_match.evidence_ids
                    fused_score = (
                        family.observed.prior_weight * item.total_score
                        + family.observed.observed_weight * observed_score
                    ) / denominator
                    reason = item.reason + "+fresh_observed_performance"
            fused.append(
                (
                    fused_score,
                    item.orchestrator_id,
                    item.base_score,
                    item.benchmark_score if item.benchmark_score is not None else -1.0,
                    observed_score,
                    item.evidence_id,
                    observed_evidence_ids,
                    reason,
                )
            )

        fused.sort(key=lambda value: (-value[0], value[1]))
        if not fused:
            return None
        selected = fused[0][1]

        if self.decision_store is not None:
            receipt_candidates = tuple(
                RoutingCandidateReceipt(
                    executor_id=executor_id,
                    rank=index,
                    total_score=total_score,
                    base_score=base_score,
                    benchmark_score=None if benchmark_score < 0 else benchmark_score,
                    evidence_id=benchmark_evidence_id,
                    observed_evidence_ids=observed_evidence_ids,
                    reason=reason,
                )
                for index, (
                    total_score,
                    executor_id,
                    base_score,
                    benchmark_score,
                    _observed_score,
                    benchmark_evidence_id,
                    observed_evidence_ids,
                    reason,
                ) in enumerate(fused, start=1)
            )
            policy_digest = routing_policy_digest(
                {
                    "task_family": context.task_family,
                    "benchmark": {
                        "benchmark_id": family.benchmark.benchmark_id,
                        "benchmark_version": family.benchmark.benchmark_version,
                        "task_set": family.benchmark.task_set,
                        "metric_name": family.benchmark.metric_name,
                        "base_weight": family.benchmark.base_weight,
                        "benchmark_weight": family.benchmark.benchmark_weight,
                        "require_fresh": family.benchmark.require_fresh,
                        "max_age_seconds": family.benchmark.max_age_seconds,
                    },
                    "executor_identities": {
                        executor_id: {
                            "executor_version": identity.executor_version,
                            "runtime_config_digest": identity.runtime_config_digest,
                            "tool_policy_digest": identity.tool_policy_digest,
                            "environment_id": identity.environment_id,
                        }
                        for executor_id, identity in sorted(self.identities.items())
                    },
                    "observed": {
                        "metric_name": family.observed.metric_name,
                        "prior_weight": family.observed.prior_weight,
                        "observed_weight": family.observed.observed_weight,
                        "max_age_seconds": family.observed.max_age_seconds,
                        "min_samples": family.observed.min_samples,
                        "missing_evidence": family.observed.missing_evidence.value,
                    },
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
    "EmpiricalExecutorIdentity",
    "MissingObservedEvidencePolicy",
    "ObservedPerformanceRoutingPolicy",
    "EmpiricalFamilyRoutingPolicy",
    "EmpiricalTaskFamilyRoutingPolicy",
    "EmpiricalTaskFamilySelectionPolicy",
]
