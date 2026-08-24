"""Minimal metaO mission composition path."""

from __future__ import annotations

from dataclasses import dataclass, replace
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
    attempted_orchestrators: tuple[str, ...] = ()


def _blocked(reason: str) -> AcceptanceResult:
    return AcceptanceResult(AcceptanceDecision.BLOCK, (reason,))


def _eligible_pools(mission: Mission, pools: tuple[OrchestratorPoolState, ...]) -> tuple[OrchestratorPoolState, ...]:
    return tuple(pool for pool in pools if mission.required_capabilities <= pool.capabilities)


def _budget_has_capacity(budget: AcceptanceBudget) -> bool:
    return (
        budget.money_used < budget.money_limit
        and budget.tokens_used < budget.token_limit
        and budget.wall_time_used_s < budget.wall_time_limit_s
        and budget.verifier_attempts_used < budget.verifier_attempt_limit
    )


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
    """Execute one independently accepted mission attempt."""

    if policy.effect is not PolicyEffect.ALLOW:
        return MissionOutcome(mission.mission_id, None, None, _blocked(f"policy:{policy.effect.value.lower()}"), budget)
    if policy.policy_bundle_id != acceptance_context.policy_bundle_id:
        return MissionOutcome(mission.mission_id, None, None, _blocked("policy_bundle_mismatch"), budget)
    if not _budget_has_capacity(budget):
        return MissionOutcome(mission.mission_id, None, None, _blocked("budget_exhausted"), budget)

    selected = select_orchestrator(_eligible_pools(mission, pools))
    if selected is None:
        return MissionOutcome(mission.mission_id, None, None, _blocked("no_eligible_orchestrator"), budget)

    orchestrator = registry.get(selected)
    normalizer = normalizers.get(selected)
    if normalizer is None:
        return MissionOutcome(mission.mission_id, selected, None, _blocked("missing_evidence_normalizer"), budget, (selected,))

    obligation_ids = tuple(sorted(acceptance_context.required_obligations))
    if len(obligation_ids) != 1:
        return MissionOutcome(mission.mission_id, selected, None, _blocked("single_attempt_requires_one_obligation"), budget, (selected,))

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
            (selected,),
        )

    budget_after = budget.consume(verifier_attempts=1)
    evidence = normalizer(
        request=request,
        orchestrator_id=selected,
        adapter_version=orchestrator.descriptor.version,
        output=dict(execution.output),
        attempt_id="attempt-1",
    )
    acceptance = evaluate_acceptance(acceptance_context, (evidence,), now_epoch=now_epoch, executor_done=True)
    return MissionOutcome(mission.mission_id, selected, execution, acceptance, budget_after, (selected,))


def execute_mission(
    *,
    mission: Mission,
    registry: OrchestratorRegistry,
    pools: tuple[OrchestratorPoolState, ...],
    normalizers: Mapping[str, EvidenceNormalizer],
    policy: PolicyDecision,
    budget: AcceptanceBudget,
    acceptance_context: AcceptanceContext,
    execution_id_prefix: str,
    now_epoch: float = 0.0,
    max_attempts: int = 2,
) -> MissionOutcome:
    """Run a mission with bounded orchestrator failover."""

    if max_attempts < 1:
        raise ValueError("max_attempts must be at least 1")

    attempted: list[str] = []
    current_budget = budget
    last: MissionOutcome | None = None

    for attempt_index in range(max_attempts):
        remaining = tuple(pool for pool in pools if pool.orchestrator_id not in attempted)
        outcome = execute_mission_once(
            mission=mission,
            registry=registry,
            pools=remaining,
            normalizers=normalizers,
            policy=policy,
            budget=current_budget,
            acceptance_context=acceptance_context,
            execution_id=f"{execution_id_prefix}-{attempt_index + 1}",
            now_epoch=now_epoch,
        )
        if outcome.orchestrator_id is not None and outcome.orchestrator_id not in attempted:
            attempted.append(outcome.orchestrator_id)
        current_budget = outcome.budget
        last = replace(outcome, attempted_orchestrators=tuple(attempted))

        if outcome.acceptance.decision is AcceptanceDecision.ACCEPT:
            return last
        if outcome.orchestrator_id is None:
            return last

    assert last is not None
    return last


__all__ = ["EvidenceNormalizer", "MissionOutcome", "execute_mission_once", "execute_mission"]
