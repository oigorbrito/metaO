"""Framework-neutral metaO mission control-plane composition."""





from __future__ import annotations





from dataclasses import dataclass, replace


from enum import StrEnum


from math import isfinite


from time import time


from typing import Callable, Mapping





from .acceptance import AcceptanceContext, AcceptanceDecision, AcceptanceResult, evaluate_acceptance


from .core import ExecutionRequest, ExecutionResult, ExecutionStatus, Mission, ExecutorRegistry


from .governance import AcceptanceBudget, PolicyDecision, PolicyEffect


from .replan import (


    ControlAction,


    FailureClass,


    ReplanLimit,


    classify_failure,


    evaluate as evaluate_replan,


)


from .strategy import SelectionPolicy, executorPoolState, select_orchestrator, select_with_policy


select_executor = select_orchestrator





EvidenceNormalizer = Callable[..., object]


AttemptClock = Callable[[], float]


CancellationCheck = Callable[[], bool]








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


    CANCELLED = "CANCELLED"


from .execution_plan import DefaultLinearPlan, ExecutionPlan, PlanStep, PlanStepStatus







@dataclass(frozen=True)


class AttemptExecutionContext:


    mission_id: str


    attempt_number: int


    execution_id: str


    executor_id: str


    started_at_epoch: float


    cost: float

    @property
    def orchestrator_id(self) -> str:
        return self.executor_id








AttemptStarted = Callable[[AttemptExecutionContext], None]


AttemptFinished = Callable[[AttemptExecutionContext, ExecutionResult, float], None]








@dataclass(frozen=True)


class MissionAttempt:


    attempt_number: int


    execution_id: str


    orchestrator_id: str


    execution_status: ExecutionStatus | None


    acceptance_decision: AcceptanceDecision


    reasons: tuple[str, ...] = ()


    started_at_epoch: float | None = None


    ended_at_epoch: float | None = None


    failure_class: FailureClass | None = None


    cost: float = 0.0





    def __post_init__(self) -> None:


        if self.attempt_number < 1:


            raise ValueError("mission attempt number must be positive")


        if not self.execution_id or not self.orchestrator_id:


            raise ValueError("mission attempt requires execution and executor ids")


        if self.started_at_epoch is not None and not isfinite(self.started_at_epoch):


            raise ValueError("mission attempt start timestamp must be finite")


        if self.ended_at_epoch is not None and not isfinite(self.ended_at_epoch):


            raise ValueError("mission attempt end timestamp must be finite")


        if self.started_at_epoch is not None and self.started_at_epoch < 0:


            raise ValueError("mission attempt start timestamp must be non-negative")


        if self.ended_at_epoch is not None and self.ended_at_epoch < 0:


            raise ValueError("mission attempt end timestamp must be non-negative")


        if (


            self.started_at_epoch is not None


            and self.ended_at_epoch is not None


            and self.ended_at_epoch < self.started_at_epoch


        ):


            raise ValueError("mission attempt end timestamp cannot precede start")


        if not isfinite(self.cost):


            raise ValueError("mission attempt cost must be finite")

        if self.cost < 0:


            raise ValueError("mission attempt cost must be non-negative")

    @property
    def executor_id(self) -> str:
        return self.orchestrator_id








@dataclass(frozen=True)


class MissionState:


    mission_id: str


    status: MissionStatus


    attempts: tuple[MissionAttempt, ...] = ()


    history: tuple[MissionStatus, ...] = (MissionStatus.CREATED,)
    plan: ExecutionPlan | None = None
    completed_steps: frozenset[str] = frozenset()





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

    @property
    def executor_id(self) -> str | None:
        return self.orchestrator_id

    @property
    def attempted_executors(self) -> tuple[str, ...]:
        return self.attempted_orchestrators








def _blocked(reason: str) -> AcceptanceResult:


    return AcceptanceResult(AcceptanceDecision.BLOCK, (reason,))








def _validated_epoch(value: float, name: str) -> float:


    if not isfinite(value):


        raise ValueError(f"{name} must be finite")


    if value < 0:


        raise ValueError(f"{name} must be non-negative")


    return value








def _eligible_pools(mission: Mission, pools: tuple[executorPoolState, ...]) -> tuple[executorPoolState, ...]:


    return tuple(pool for pool in pools if mission.required_capabilities <= pool.capabilities)








def _pool_by_id(pools: tuple[executorPoolState, ...], executor_id: str) -> executorPoolState:


    for pool in pools:


        if pool.executor_id == executor_id:


            return pool


    raise KeyError(f"selected executor pool missing: {executor_id}")








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
    plan: ExecutionPlan | None = None,
    completed_steps: frozenset[str] = frozenset(),
) -> MissionState:
    return MissionState(
        mission_id=mission_id,
        status=status,
        attempts=attempts,
        history=history,
        plan=plan,
        completed_steps=completed_steps,
    )
def _attempt_from_outcome(outcome: MissionOutcome, attempt_number: int, execution_id: str) -> MissionAttempt | None:


    if outcome.state is not None and outcome.state.attempts:


        return outcome.state.attempts[-1]


    if outcome.executor_id is None:


        return None


    return MissionAttempt(


        attempt_number=attempt_number,


        execution_id=execution_id,


        executor_id=outcome.executor_id,


        execution_status=outcome.execution.status if outcome.execution is not None else None,


        acceptance_decision=outcome.acceptance.decision,


        reasons=outcome.acceptance.reasons,


    )








_RUNTIME_ADVISORY_FAILURE_CLASSES = frozenset(


    {


        FailureClass.TRANSIENT,


        FailureClass.TIMEOUT,


        FailureClass.RUNTIME,


    }


)








def _failure_class_for_execution(execution: ExecutionResult) -> FailureClass:


    """Classify runtime failure without delegating metaO hard-gate authority.





    Adapter/runtime error text is advisory. It may identify runtime, timeout or


    transient failures for replanning, but it cannot manufacture authoritative


    metaO POLICY/BUDGET/ACCEPTANCE gates merely by returning matching words.


    """





    if execution.status is ExecutionStatus.CANCELLED:


        return FailureClass.CANCELLED


    if execution.error:


        classified = classify_failure(execution.error)


        if classified in _RUNTIME_ADVISORY_FAILURE_CLASSES:


            return classified


    return FailureClass.RUNTIME








def execute_mission_once(


    *,


    mission: Mission,


    registry: ExecutorRegistry,


    pools: tuple[executorPoolState, ...],


    normalizers: Mapping[str, EvidenceNormalizer],


    policy: PolicyDecision,


    budget: AcceptanceBudget,


    acceptance_context: AcceptanceContext,


    execution_id: str,


    now_epoch: float = 0.0,


    attempt_number: int = 1,


    attempt_clock: AttemptClock | None = None,


    cancellation_requested: CancellationCheck | None = None,


    on_attempt_started: AttemptStarted | None = None,


    on_attempt_finished: AttemptFinished | None = None,


    selection_policy: SelectionPolicy | None = None,


) -> MissionOutcome:


    """Execute one independently accepted mission attempt."""





    _validated_epoch(now_epoch, "mission current time")


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





    eligible = _eligible_pools(mission, pools)


    selected = select_with_policy(
        eligible,
        selection_policy,
        now_epoch=now_epoch,
    )


    selecting_history = base_history + (MissionStatus.SELECTING,)


    if selected is None:


        state = _state(


            mission.mission_id,


            MissionStatus.FAILED,


            history=selecting_history + (MissionStatus.FAILED,),
        )


        return MissionOutcome(mission.mission_id, None, None, _blocked("no_eligible_orchestrator"), budget, state=state)





    selected_pool = _pool_by_id(eligible, selected)


    executor = registry.get(selected)


    normalizer = normalizers.get(selected)


    if normalizer is None:


        acceptance = _blocked("missing_evidence_normalizer")


        attempt = MissionAttempt(


            attempt_number,


            execution_id,


            selected,


            None,


            acceptance.decision,


            acceptance.reasons,


            failure_class=FailureClass.ACCEPTANCE,


        )


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


        attempt = MissionAttempt(


            attempt_number,


            execution_id,


            selected,


            None,


            acceptance.decision,


            acceptance.reasons,


            failure_class=FailureClass.ACCEPTANCE,


        )


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


    clock = attempt_clock or time


    started_at_epoch = _validated_epoch(clock(), "mission attempt start timestamp")


    attempt_context = AttemptExecutionContext(


        mission.mission_id,


        attempt_number,


        execution_id,


        selected,


        started_at_epoch,


        selected_pool.cost,


    )


    if on_attempt_started is not None:


        on_attempt_started(attempt_context)


    if cancellation_requested is not None and cancellation_requested():


        executor.cancel(execution_id)





    try:


        execution = executor.execute(request)


    except Exception as exc:


        execution = ExecutionResult(


            execution_id,


            selected,


            ExecutionStatus.FAILED,


            error=f"{type(exc).__name__}: {exc}",


        )


    ended_at_epoch = _validated_epoch(clock(), "mission attempt end timestamp")


    if ended_at_epoch < started_at_epoch:


        raise ValueError("mission attempt end timestamp cannot precede start")


    if on_attempt_finished is not None:


        on_attempt_finished(attempt_context, execution, ended_at_epoch)





    running_history = selecting_history + (MissionStatus.RUNNING,)


    cancelled = cancellation_requested is not None and cancellation_requested()


    if cancelled:


        runtime_cancelled = execution.status is ExecutionStatus.CANCELLED


        terminal = MissionStatus.CANCELLED if runtime_cancelled else MissionStatus.BLOCKED


        reason = "operator_cancelled" if runtime_cancelled else "cancel_requested_runtime_completed"


        acceptance = AcceptanceResult(AcceptanceDecision.BLOCK, (reason,))


        attempt = MissionAttempt(


            attempt_number,


            execution_id,


            selected,


            execution.status,


            acceptance.decision,


            acceptance.reasons,


            started_at_epoch=started_at_epoch,


            ended_at_epoch=ended_at_epoch,


            failure_class=FailureClass.RUNTIME if not runtime_cancelled else FailureClass.CANCELLED,


            cost=selected_pool.cost,


        )


        state = _state(


            mission.mission_id,


            terminal,


            attempts=(attempt,),


            history=running_history + (terminal,),
        )


        return MissionOutcome(mission.mission_id, selected, execution, acceptance, budget, (selected,), state)





    if execution.status is not ExecutionStatus.SUCCEEDED:


        acceptance = AcceptanceResult(AcceptanceDecision.NOT_DONE, ("execution_not_succeeded",))


        attempt = MissionAttempt(


            attempt_number,


            execution_id,


            selected,


            execution.status,


            acceptance.decision,


            acceptance.reasons,


            started_at_epoch=started_at_epoch,


            ended_at_epoch=ended_at_epoch,


            failure_class=_failure_class_for_execution(execution),


            cost=selected_pool.cost,


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


        adapter_version=executor.descriptor.version,


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


        started_at_epoch=started_at_epoch,


        ended_at_epoch=ended_at_epoch,


        failure_class=None if acceptance.decision is AcceptanceDecision.ACCEPT else FailureClass.ACCEPTANCE,


        cost=selected_pool.cost,


    )


    state = _state(


        mission.mission_id,


        terminal_status,


        attempts=(attempt,),


        history=running_history + (MissionStatus.VERIFYING, terminal_status),
    )


    return MissionOutcome(mission.mission_id, selected, execution, acceptance, budget_after, (selected,), state)








def _terminal_from_failed_outcome(outcome: MissionOutcome) -> MissionStatus:


    if outcome.execution is not None and outcome.execution.status is ExecutionStatus.CANCELLED:


        return MissionStatus.CANCELLED


    if outcome.execution is not None and outcome.execution.status is ExecutionStatus.SUCCEEDED:


        return MissionStatus.BLOCKED


    return MissionStatus.FAILED








def execute_mission(


    *,


    mission: Mission,


    registry: ExecutorRegistry,


    pools: tuple[executorPoolState, ...],


    normalizers: Mapping[str, EvidenceNormalizer],


    policy: PolicyDecision,


    budget: AcceptanceBudget,


    acceptance_context: AcceptanceContext,


    execution_id_prefix: str,


    now_epoch: float = 0.0,


    max_attempts: int = 2,


    attempt_clock: AttemptClock | None = None,


    cancellation_requested: CancellationCheck | None = None,


    on_attempt_started: AttemptStarted | None = None,


    on_attempt_finished: AttemptFinished | None = None,


    selection_policy: SelectionPolicy | None = None,


) -> MissionOutcome:


    """Run a mission with failure-aware, auditable, bounded failover."""





    if max_attempts < 1:


        raise ValueError("max_attempts must be at least 1")





    attempted: list[str] = []


    attempt_records: list[MissionAttempt] = []


    current_budget = budget


    last: MissionOutcome | None = None


    history: list[MissionStatus] = [MissionStatus.CREATED, MissionStatus.PLANNING]


    replan_limit = ReplanLimit(max_attempts=max_attempts)




    plan = DefaultLinearPlan(plan_id=execution_id_prefix, max_attempts=max_attempts)
    completed_steps = frozenset()
    attempt_index = 0
    while (step := plan.get_next_step(completed_steps)) is not None:
        attempt_index = int(step.step_id.split('_')[1]) - 1

        history.append(MissionStatus.SELECTING)


        remaining = tuple(pool for pool in pools if pool.executor_id not in attempted)


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


            attempt_clock=attempt_clock,


            cancellation_requested=cancellation_requested,


            on_attempt_started=on_attempt_started,


            on_attempt_finished=on_attempt_finished,


            selection_policy=selection_policy,


        )


        record = _attempt_from_outcome(outcome, attempt_index + 1, execution_id)


        if record is not None:


            attempt_records.append(record)


        if outcome.executor_id is not None and outcome.executor_id not in attempted:


            attempted.append(outcome.executor_id)


        current_budget = outcome.budget





        if outcome.executor_id is None:


            terminal = outcome.state.status if outcome.state is not None else MissionStatus.BLOCKED


            history.append(terminal)


            state = _state(mission.mission_id, terminal, attempts=tuple(attempt_records), history=tuple(history), plan=plan, completed_steps=completed_steps)


            return replace(outcome, attempted_orchestrators=tuple(attempted), state=state)





        history.append(MissionStatus.RUNNING)


        if outcome.execution is not None and outcome.execution.status is ExecutionStatus.SUCCEEDED:


            history.append(MissionStatus.VERIFYING)





        if cancellation_requested is not None and cancellation_requested():


            terminal = outcome.state.status if outcome.state is not None else MissionStatus.BLOCKED


            history.append(terminal)


            state = _state(


                mission.mission_id,


                terminal,


                attempts=tuple(attempt_records),


                history=tuple(history),
                plan=plan,
                completed_steps=completed_steps,
            )


            return replace(outcome, attempted_orchestrators=tuple(attempted), state=state)





        if outcome.acceptance.decision is AcceptanceDecision.ACCEPT:
            completed_steps |= {step.step_id}


            history.append(MissionStatus.ACCEPTED)


            state = _state(


                mission.mission_id,


                MissionStatus.ACCEPTED,


                attempts=tuple(attempt_records),


                history=tuple(history),
                plan=plan,
                completed_steps=completed_steps,
            )


            return replace(outcome, attempted_orchestrators=tuple(attempted), state=state)





        last = outcome


        failure_class = record.failure_class if record is not None else FailureClass.UNKNOWN


        decision = evaluate_replan(


            failure_class,


            attempts=attempt_index + 1,


            limit=replan_limit,


        )





        if decision.action is ControlAction.REPLAN:


            history.append(MissionStatus.REPLANNING)


            completed_steps |= {step.step_id}


            continue





        terminal = _terminal_from_failed_outcome(outcome)


        if decision.action is ControlAction.HALT:


            reason = f"replan_halt:{failure_class.value}"


        elif decision.action is ControlAction.ESCALATE:


            reason = "replan_limit_reached"


        else:


            reason = f"replan_unexpected_action:{decision.action.value}"





        acceptance = AcceptanceResult(


            AcceptanceDecision.BLOCK if decision.action is ControlAction.HALT else outcome.acceptance.decision,


            outcome.acceptance.reasons + (reason,),


            outcome.acceptance.proof,


        )


        history.append(terminal)


        state = _state(


            mission.mission_id,


            terminal,


            attempts=tuple(attempt_records),


            history=tuple(history),
            plan=plan,
            completed_steps=completed_steps,
            )


        return replace(


            outcome,


            acceptance=acceptance,


            attempted_orchestrators=tuple(attempted),


            state=state,


        )





    assert last is not None


    terminal = _terminal_from_failed_outcome(last)


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
        plan=plan,
        completed_steps=completed_steps,
            )


    return replace(


        last,


        acceptance=acceptance,


        attempted_orchestrators=tuple(attempted),


        state=state,


    )








__all__ = [


    "EvidenceNormalizer",


    "AttemptClock",


    "CancellationCheck",


    "AttemptExecutionContext",


    "AttemptStarted",


    "AttemptFinished",


    "MissionStatus",


    "MissionAttempt",


    "MissionState",


    "MissionOutcome",


    "execute_mission_once",


    "execute_mission",


]
