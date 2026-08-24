"""Minimal metaO mission composition path.

This module composes already-proven framework-neutral pieces: registry,
strategy, global policy/budget, orchestrator execution, evidence normalization,
and final metaO acceptance. It intentionally knows nothing about LangGraph,
CrewAI, or any other orchestrator SDK.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Callable, Mapping

from .acceptance import AcceptanceContext, AcceptanceDecision, AcceptanceResult, evaluate_acceptance
from .core import ExecutionRequest, ExecutionResult, ExecutionStatus, Mission, OrchestratorRegistry
from .governance import AcceptanceBudget, PolicyDecision, PolicyEffect
from .strategy import OrchestratorPoolState, select_orchestrator

EvidenceNormalizer = Callable[..., object]


@dataclass(frozen=True)
class MissionOutcome:
    mission_id: str
    orchestrator_id: str | None
    execution: ExecutionResult | None
    acceptance: AcceptanceResult
    budget: AcceptanceBudget


def _blocked(reason: str) -> AcceptanceResult:
    return AcceptanceResult(AcceptanceDecision.BLOCK, (reason,))


def execute_mission_once(
    *,
    mission: Mission,
    registry: OrchestratorRegistry,
    pools: tuple[OrchestratorPoolState, ...],
    normalizers: Mapping[str, EvidenceNormalizer],
    policy: PolicyDecision,
    budget: AcceptanceBudget,
    acceptance_context: AcceptanceContext,
    execution_id: str,
    now_epoch: float = 0.0,
) -> MissionOutcome:
    """Execute one independently accepted mission attempt.

    Hard policy gates run before strategy. The chosen orchestrator executes
    through the neutral contract. Its adapter-specific result is normalized at
    the boundary, then metaO performs final acceptance independently.
    """

    if policy.effect is not PolicyEffect.ALLOW:
        return MissionOutcome(
            mission.mission_id,
            None,
            None,
            _blocked(f"policy:{policy.effect.value.lower()}"),
            budget,
        )
    if policy.policy_bundle_id != acceptance_context.policy_bundle_id:
        return MissionOutcome(
            mission.mission_id,
            None,
            None,
            _blocked("policy_bundle_mismatch"),
            budget,
        )

    selected = select_orchestrator(pools)
    if selected is None:
        return MissionOutcome(mission.mission_id, None, None, _blocked("no_eligible_orchestrator"), budget)

    orchestrator = registry.get(selected)
    normalizer = normalizers.get(selected)
    if normalizer is None:
        return MissionOutcome(mission.mission_id, selected, None, _blocked("missing_evidence_normalizer"), budget)

    obligation_ids = tuple(sorted(acceptance_context.required_obligations))
    if len(obligation_ids) != 1:
        return MissionOutcome(mission.mission_id, selected, None, _blocked("single_attempt_requires_one_obligation"), budget)

    request = ExecutionRequest(
        execution_id=execution_id,
        mission=mission,
        context={
            "obligation_id": obligation_ids[0],
            "subject_id": acceptance_context.subject_id,
            "subject_state_id": acceptance_context.subject_state_id,
            "verification_context_id": acceptance_context.verification_context_id,
            "policy_bundle_id": acceptance_context.policy_bundle_id,
            "verifier_id": "adapter-observer",
            "authority_id": "metao-runtime",
            "created_at_epoch": now_epoch,
        },
    )
    execution = orchestrator.execute(request)
    if execution.status is not ExecutionStatus.SUCCEEDED:
        return MissionOutcome(
            mission.mission_id,
            selected,
            execution,
            AcceptanceResult(AcceptanceDecision.NOT_DONE, ("execution_not_succeeded",)),
            budget,
        )

    budget_after = budget.consume(verifier_attempts=1)
    evidence = normalizer(
        request=request,
        orchestrator_id=selected,
        adapter_version=orchestrator.descriptor.version,
        output=dict(execution.output),
        attempt_id="attempt-1",
    )
    acceptance = evaluate_acceptance(
        acceptance_context,
        (evidence,),
        now_epoch=now_epoch,
        executor_done=True,
    )
    return MissionOutcome(mission.mission_id, selected, execution, acceptance, budget_after)


__all__ = ["EvidenceNormalizer", "MissionOutcome", "execute_mission_once"]
