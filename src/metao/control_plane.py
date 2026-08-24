"""Framework-neutral metaO mission control-plane composition."""

from __future__ import annotations

from dataclasses import dataclass, replace
from enum import StrEnum
from typing import Callable, Mapping

from .acceptance import AcceptanceContext, AcceptanceDecision, AcceptanceResult, evaluate_acceptance
from .core import ExecutionRequest, ExecutionResult, ExecutionStatus, Mission, OrchestratorRegistry
from .governance import AcceptanceBudget, PolicyDecision, PolicyEffect
from .strategy import OrchestratorPoolState, select_orchestrator

EvidenceNormalizer = Callable[..., object]


class MissionStatus(StrEnum):
    CREATED = "CREATED"
    PLANNING = "PLANNING"
    SELECTING = "SELECTING"
    RUNNING = "RUNNING"
    VERIFYING = "VERIFYING"
    ACCEPTED = "ACCEPTED"
    REPLANNING = "REPLANNING"
    WAITING_APPROVAL = "WAITING_APPROVAL"
    BLOCKED = "BLOCKED"
    FAILED = "FAILED"


@dataclass(frozen=True)
class MissionAttempt:
    attempt_number: int
    execution_id: str
    orchestrator_id: str
    execution_status: ExecutionStatus | None
    acceptance_decision: AcceptanceDecision
    reasons: tuple[str, ...] = ()


@dataclass(frozen=True)
class MissionState:
    mission_id: str
    status: MissionStatus
    attempts: tuple[MissionAttempt, ...] = ()
    history: tuple[MissionStatus, ...] = (MissionStatus.CREATED,)

    def __post_init__(self) -> None:
        if not self.mission_id:
            raise ValueError("mission state requires mission_id")
        if not self.history or self.history[-1] is not self.status:
            raise ValueError("mission state history must end at current status")


@dataclass(frozen=True)
class MissionOutcome:
    mission_id: str
    orchestrator_id: str | None
    execution: ExecutionResult | None
    acceptance: AcceptanceResult
    budget: AcceptanceBudget
    attempted_orchestrators: tuple[str, ...] = ()
    state: MissionState | None = None


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


def _state(
    mission_id: str,
    status: MissionStatus,
    *,
    attempts: tuple[MissionAttempt, ...] = (),
    history: tuple[MissionStatus, ...],
) -> MissionState:
    return MissionState(mission_id, status, attempts, history)


def _attempt_from_outcome(outcome: MissionOutcome, attempt_number: int, execution_id: str) -> MissionAttempt | None:
    if outcome.orchestrator_id is None:
        return None
    return MissionAttempt(
        attempt_number=attempt_number,
        execution_id=execution_id,
        orchestrator_id=outcome.orchestrator_id,
        execution_status=outcome.execution.status if outcome.execution is not None else None,
        acceptance_decision=outcome.acceptance.decision,
        reasons=outcome.acceptance.reasons,
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
    attempt_number: int = 1,
) -> MissionOutcome:
    """Execute one independently accepted mission attempt."""

    base_history = (MissionStatus.CREATED, MissionStatus.PLANNING)
    if policy.effect is PolicyEffect.REQUIRE_HUMAN:
        state = _state(
            mission.mission_id,
            MissionStatus.WAITING_APPROVAL,
            history=base_history + (MissionStatus.WAITING_APPROVAL,),
        )
        return MissionOutcome(
            mission.mission_id,
            None,
            None,
            _blocked("policy:require_human"),
            budget,
            state=state,
        )
    if policy.effect is not PolicyEffect.ALLOW:
        state = _state(
            mission.mission_id,
            MissionStatus.BLOCKED,
            history=base_history + (MissionStatus.BLOCKED,),
        )
        return MissionOutcome(
            mission.mission_id,
            None,
            None,
            _blocked(f"policy:{policy.effect.value.lower()}"),
            budget,
            state=state,
        )
    if policy.policy_bundle_id != acceptance_context.policy_bundle_id:
        state = _state(
            mission.mission_id,
            MissionStatus.BLOCKED,
            history=base_history + (MissionStatus.BLOCKED,),
        )
        return MissionOutcome(mission.mission_id, None, None, _blocked("policy_bundle_mismatch"), budget, state=state)
    if not _budget_has_capacity(budget):
        state = _state(
            mission.mission_id,
            MissionStatus.BLOCKED,
            history=base_history + (MissionStatus.BLOCKED,),
        )
        return MissionOutcome(mission.mission_id, None, None, _blocked("budget_exhausted"), budget, state=state)

    selected = select_orchestrator(_eligible_pools(mission, pools))
    selecting_history = base_history + (MissionStatus.SELECTING,)
    if selected is None:
        state = _state(
            mission.mission_id,
            MissionStatus.FAILED,
            history=selecting_history + (MissionStatus.FAILED,),
        )
        return MissionOutcome(mission.mission_id, None, None, _blocked("no_eligible_orchestrator"), budget, state=state)

    orchestrator = registry.get(selected)
    normalizer = normalizers.get(selected)
    if normalizer is None:
        acceptance = _blocked("missing_evidence_normalizer")
        attempt = MissionAttempt(attempt_number, execution_id, selected, None, acceptance.decision, acceptance.reasons)
        state = _state(
            mission.mission_id,
            MissionStatus.BLOCKED,
            attempts=(attempt,),
            history=selecting_history + (MissionStatus.BLOCKED,),
        )
        return MissionOutcome(mission.mission_id, selected, None, acceptance, budget, (selected,), state)

    obligation_ids = tuple(sorted(acceptance_context.required_obligations))
    if len(obligation_ids) != 1:
        acceptance = _blocked("single_attempt_requires_one_obligation")
        attempt = MissionAttempt(attempt_number, execution_id, selected, None, acceptance.decision, acceptance.reasons)
        state = _state(
            mission.mission_id,
            MissionStatus.BLOCKED,
            attempts=(attempt,),
            history=selecting_history + (MissionStatus.BLOCKED,),
        )
        return MissionOutcome(mission.mission_id, selected, None, acceptance, budget, (selected,), state)

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
    running_history = selecting_history + (MissionStatus.RUNNING,)
    if execution.status is not ExecutionStatus.SUCCEEDED:
        acceptance = AcceptanceResult(AcceptanceDecision.NOT_DONE, ("execution_not_succeeded",))
        attempt = MissionAttempt(
            attempt_number,
            execution_id,
            selected,
            execution.status,
            acceptance.decision,
            acceptance.reasons,
        )
        state = _state(
            mission.mission_id,
            MissionStatus.FAILED,
            attempts=(attempt,),
            history=running_history + (MissionStatus.FAILED,),
        )
        return MissionOutcome(mission.mission_id, selected, execution, acceptance, budget, (selected,), state)

    budget_after = budget.consume(verifier_attempts=1)
    evidence = normalizer(
        request=request,
        orchestrator_id=selected,
        adapter_version=orchestrator.descriptor.version,
        output=dict(execution.output),
        attempt_id=f"attempt-{attempt_number}",
    )
    acceptance = evaluate_acceptance(acceptance_context, (evidence,), now_epoch=now_epoch, executor_done=True)
    terminal_status = MissionStatus.ACCEPTED if acceptance.decision is AcceptanceDecision.ACCEPT else MissionStatus.BLOCKED
    attempt = MissionAttempt(
        attempt_number,
        execution_id,
        selected,
        execution.status,
        acceptance.decision,
        acceptance.reasons,
    )
    state = _state(
        mission.mission_id,
        terminal_status,
        attempts=(attempt,),
        history=running_history + (MissionStatus.VERIFYING, terminal_status),
    )
    return MissionOutcome(mission.mission_id, selected, execution, acceptance, budget_after, (selected,), state)


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
    """Run a mission with auditable, bounded orchestrator failover."""

    if max_attempts < 1:
        raise ValueError("max_attempts must be at least 1")

    attempted: list[str] = []
    attempt_records: list[MissionAttempt] = []
    current_budget = budget
    last: MissionOutcome | None = None
    history: list[MissionStatus] = [MissionStatus.CREATED, MissionStatus.PLANNING]

    for attempt_index in range(max_attempts):
        history.append(MissionStatus.SELECTING)
        remaining = tuple(pool for pool in pools if pool.orchestrator_id not in attempted)
        execution_id = f"{execution_id_prefix}-{attempt_index + 1}"
        outcome = execute_mission_once(
            mission=mission,
            registry=registry,
            pools=remaining,
            normalizers=normalizers,
            policy=policy,
            budget=current_budget,
            acceptance_context=acceptance_context,
            execution_id=execution_id,
            now_epoch=now_epoch,
            attempt_number=attempt_index + 1,
        )
        record = _attempt_from_outcome(outcome, attempt_index + 1, execution_id)
        if record is not None:
            attempt_records.append(record)
        if outcome.orchestrator_id is not None and outcome.orchestrator_id not in attempted:
            attempted.append(outcome.orchestrator_id)
        current_budget = outcome.budget

        if outcome.orchestrator_id is None:
            terminal = outcome.state.status if outcome.state is not None else MissionStatus.BLOCKED
            history.append(terminal)
            state = _state(mission.mission_id, terminal, attempts=tuple(attempt_records), history=tuple(history))
            return replace(outcome, attempted_orchestrators=tuple(attempted), state=state)

        history.append(MissionStatus.RUNNING)
        if outcome.execution is not None and outcome.execution.status is ExecutionStatus.SUCCEEDED:
            history.append(MissionStatus.VERIFYING)

        if outcome.acceptance.decision is AcceptanceDecision.ACCEPT:
            history.append(MissionStatus.ACCEPTED)
            state = _state(
                mission.mission_id,
                MissionStatus.ACCEPTED,
                attempts=tuple(attempt_records),
                history=tuple(history),
            )
            return replace(outcome, attempted_orchestrators=tuple(attempted), state=state)

        last = outcome
        if attempt_index + 1 < max_attempts:
            history.append(MissionStatus.REPLANNING)

    assert last is not None
    terminal = MissionStatus.BLOCKED if last.execution is not None and last.execution.status is ExecutionStatus.SUCCEEDED else MissionStatus.FAILED
    acceptance = AcceptanceResult(
        last.acceptance.decision,
        last.acceptance.reasons + ("replan_limit_reached",),
        last.acceptance.proof,
    )
    history.append(terminal)
    state = _state(
        mission.mission_id,
        terminal,
        attempts=tuple(attempt_records),
        history=tuple(history),
    )
    return replace(
        last,
        acceptance=acceptance,
        attempted_orchestrators=tuple(attempted),
        state=state,
    )


__all__ = [
    "EvidenceNormalizer",
    "MissionStatus",
    "MissionAttempt",
    "MissionState",
    "MissionOutcome",
    "execute_mission_once",
    "execute_mission",
]
