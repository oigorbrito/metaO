"""Public operator facades for durable executions and metaO missions.

The module-level functions preserve the existing DurableExecutionPort API.
MissionOperator is the product-facing, framework-neutral facade over the
control-plane plus a MissionStorePort, including durable approval/resume and
optional cross-process mission cancellation coordination.
"""

from __future__ import annotations

from dataclasses import replace
from threading import Event, Lock, Thread
from typing import Mapping

from metao.acceptance import AcceptanceContext, AcceptanceDecision, AcceptanceResult
from metao.catalog import OrchestratorCatalog
from metao.control_plane import (
    AttemptExecutionContext,
    EvidenceNormalizer,
    MissionOutcome,
    MissionState,
    MissionStatus,
    execute_mission,
    execute_mission_once,
)
from metao.core import ExecutionResult, ExecutionStatus, Mission, OrchestratorRegistry
from metao.durable import DurableExecutionPort, DurableExecutionSpec, DurableExecutionState
from metao.execution_handle import (
    ActiveExecutionHandle,
    ActiveExecutionNotFound,
    ExecutionHandleStatus,
    ExecutionHandleStorePort,
)
from metao.governance import (
    AcceptanceBudget,
    ApprovalRecord,
    PolicyDecision,
    PolicyEffect,
    require_human,
    resume_after_approval,
)
from metao.mission_store import (
    MissionAlreadyExists,
    MissionNotFound,
    MissionRecord,
    MissionRunContext,
    MissionStorePort,
)
from metao.strategy import OrchestratorPoolState, select_orchestrator


def run(port: DurableExecutionPort, spec: DurableExecutionSpec) -> str:
    return port.start(spec)


def status(port: DurableExecutionPort, execution_id: str) -> DurableExecutionState:
    return port.state(execution_id)


def inspect(port: DurableExecutionPort, execution_id: str) -> DurableExecutionState:
    """Return the current authoritative durable execution state."""
    return port.state(execution_id)


def cancel(port: DurableExecutionPort, execution_id: str) -> None:
    port.cancel(execution_id)


def resume(port: DurableExecutionPort, execution_id: str) -> None:
    port.resume(execution_id)


class MissionApprovalError(RuntimeError):
    pass


class MissionNotWaitingApproval(MissionApprovalError):
    pass


class MissionApprovalAlreadyDecided(MissionApprovalError):
    pass


class MissionApprovalNotGranted(MissionApprovalError):
    pass


class MissionCancellationError(RuntimeError):
    pass


class MissionCancellationUnavailable(MissionCancellationError):
    pass


class MissionNotCancellable(MissionCancellationError):
    pass


class MissionOperator:
    """Configured synchronous mission facade backed by a MissionStorePort.

    Cancellation remains cooperative at the runtime boundary: metaO persists the
    active execution/cancel request and delegates ``cancel(execution_id)`` to the
    selected orchestrator. A runtime that cannot interrupt an in-flight call may
    still complete, but metaO will fail closed and never accept that late result.
    """

    def __init__(
        self,
        *,
        registry: OrchestratorRegistry,
        store: MissionStorePort,
        catalog: OrchestratorCatalog | None = None,
        pools: tuple[OrchestratorPoolState, ...] = (),
        normalizers: Mapping[str, EvidenceNormalizer] | None = None,
    ) -> None:
        if catalog is not None and (pools or normalizers is not None):
            raise ValueError("configure MissionOperator with catalog or pools/normalizers, not both")
        if catalog is None and normalizers is None:
            raise ValueError("MissionOperator requires catalog or normalizers")

        self._registry = registry
        self._catalog = catalog
        self._pools = tuple(pools)
        self._normalizers = dict(normalizers or {})
        self._store = store
        self._execution_handles: ExecutionHandleStorePort | None = None
        self._cancel_poll_interval_s = 0.05
        self._watchers: dict[str, tuple[Event, Thread]] = {}
        self._watchers_lock = Lock()

    def configure_execution_handles(
        self,
        store: ExecutionHandleStorePort,
        *,
        poll_interval_s: float = 0.05,
    ) -> "MissionOperator":
        if poll_interval_s <= 0:
            raise ValueError("cancellation poll interval must be positive")
        self._execution_handles = store
        self._cancel_poll_interval_s = poll_interval_s
        return self

    def _routing_inputs(self) -> tuple[tuple[OrchestratorPoolState, ...], Mapping[str, EvidenceNormalizer]]:
        if self._catalog is not None:
            return self._catalog.pools(), self._catalog.normalizers()
        return self._pools, self._normalizers

    def _remaining_routable_pools(
        self,
        mission: Mission,
        attempted_orchestrators: tuple[str, ...],
    ) -> tuple[OrchestratorPoolState, ...]:
        """Return a fresh live snapshot containing only unattempted candidates."""

        attempted = set(attempted_orchestrators)
        pools, _ = self._routing_inputs()
        remaining = tuple(
            pool
            for pool in pools
            if pool.orchestrator_id not in attempted
            and mission.required_capabilities <= pool.capabilities
        )
        if select_orchestrator(remaining) is None:
            return ()
        return remaining

    @staticmethod
    def _is_replan_limit_outcome(outcome: MissionOutcome) -> bool:
        return (
            outcome.state is not None
            and bool(outcome.state.attempts)
            and "replan_limit_reached" in outcome.acceptance.reasons
        )

    def _promote_replan_escalation(
        self,
        mission: Mission,
        outcome: MissionOutcome,
    ) -> MissionOutcome:
        """Project a replan-limit terminal result into durable human waiting.

        The projection is allowed only when a currently routable unattempted
        runtime exists. Human approval never authorizes retrying a runtime that
        already failed in the current mission lineage.
        """

        if not self._is_replan_limit_outcome(outcome):
            return outcome
        if outcome.state is None:
            return outcome
        if not self._remaining_routable_pools(mission, outcome.attempted_orchestrators):
            return outcome

        history = outcome.state.history
        if history and history[-1] in {
            MissionStatus.FAILED,
            MissionStatus.BLOCKED,
            MissionStatus.CANCELLED,
        }:
            history = history[:-1] + (MissionStatus.WAITING_APPROVAL,)
        elif not history or history[-1] is not MissionStatus.WAITING_APPROVAL:
            history = history + (MissionStatus.WAITING_APPROVAL,)

        acceptance = AcceptanceResult(
            AcceptanceDecision.REQUIRE_HUMAN,
            outcome.acceptance.reasons,
            outcome.acceptance.proof,
        )
        state = MissionState(
            mission.mission_id,
            MissionStatus.WAITING_APPROVAL,
            outcome.state.attempts,
            history,
        )
        return replace(outcome, acceptance=acceptance, state=state)

    def _cancel_requested(self, mission_id: str) -> bool:
        if self._execution_handles is None:
            return False
        try:
            return self._execution_handles.get(mission_id).cancel_requested
        except ActiveExecutionNotFound:
            return False

    def _delegate_cancel(self, handle: ActiveExecutionHandle) -> ActiveExecutionHandle:
        if self._execution_handles is None:
            raise MissionCancellationUnavailable("mission cancellation is not configured")
        if handle.cancel_delegated:
            return handle
        self._registry.get(handle.orchestrator_id).cancel(handle.execution_id)
        return self._execution_handles.mark_cancel_delegated(handle.mission_id)

    def _start_cancel_watcher(self, handle: ActiveExecutionHandle) -> None:
        if self._execution_handles is None:
            return
        stop = Event()

        def watch() -> None:
            while not stop.wait(self._cancel_poll_interval_s):
                try:
                    current = self._execution_handles.get(handle.mission_id)
                except ActiveExecutionNotFound:
                    return
                if current.execution_id != handle.execution_id:
                    return
                if current.status is not ExecutionHandleStatus.ACTIVE:
                    return
                if current.cancel_requested and not current.cancel_delegated:
                    try:
                        self._delegate_cancel(current)
                    except Exception:
                        continue
                    return

        thread = Thread(target=watch, name=f"metao-cancel-{handle.execution_id}", daemon=True)
        with self._watchers_lock:
            self._watchers[handle.execution_id] = (stop, thread)
        thread.start()

    def _attempt_started(self, context: AttemptExecutionContext) -> None:
        if self._execution_handles is None:
            return
        handle = self._execution_handles.activate(
            ActiveExecutionHandle(
                mission_id=context.mission_id,
                execution_id=context.execution_id,
                orchestrator_id=context.orchestrator_id,
                attempt_number=context.attempt_number,
                started_at_epoch=context.started_at_epoch,
                cost=context.cost,
            )
        )
        if handle.cancel_requested and not handle.cancel_delegated:
            self._delegate_cancel(handle)
        self._start_cancel_watcher(handle)

    def _attempt_finished(
        self,
        context: AttemptExecutionContext,
        execution: ExecutionResult,
        ended_at_epoch: float,
    ) -> None:
        if self._execution_handles is None:
            return
        with self._watchers_lock:
            watcher = self._watchers.pop(context.execution_id, None)
        if watcher is not None:
            stop, thread = watcher
            stop.set()
            thread.join(timeout=max(self._cancel_poll_interval_s * 4, 0.05))
        self._execution_handles.complete(
            context.mission_id,
            ended_at_epoch=ended_at_epoch,
            execution_status=execution.status,
        )

    def _execution_kwargs(self, mission_id: str) -> dict[str, object]:
        if self._execution_handles is None:
            return {}
        return {
            "cancellation_requested": lambda: self._cancel_requested(mission_id),
            "on_attempt_started": self._attempt_started,
            "on_attempt_finished": self._attempt_finished,
        }

    def run(
        self,
        mission: Mission,
        *,
        policy: PolicyDecision,
        budget: AcceptanceBudget,
        acceptance_context: AcceptanceContext,
        execution_id_prefix: str | None = None,
        now_epoch: float = 0.0,
        max_attempts: int = 2,
    ) -> MissionOutcome:
        """Execute and atomically register one canonical mission outcome."""
        if self._store.contains(mission.mission_id):
            raise MissionAlreadyExists(mission.mission_id)
        if self._execution_handles is not None:
            try:
                self._execution_handles.get(mission.mission_id)
            except ActiveExecutionNotFound:
                pass
            else:
                raise MissionAlreadyExists(mission.mission_id)

        prefix = execution_id_prefix or f"{mission.mission_id}-exec"
        run_context = MissionRunContext(policy, budget, acceptance_context, prefix, max_attempts)
        pools, normalizers = self._routing_inputs()
        outcome = execute_mission(
            mission=mission,
            registry=self._registry,
            pools=pools,
            normalizers=normalizers,
            policy=policy,
            budget=budget,
            acceptance_context=acceptance_context,
            execution_id_prefix=prefix,
            now_epoch=now_epoch,
            max_attempts=max_attempts,
            **self._execution_kwargs(mission.mission_id),
        )
        outcome = self._promote_replan_escalation(mission, outcome)

        approval_request = None
        if outcome.state is not None and outcome.state.status is MissionStatus.WAITING_APPROVAL:
            escalation = bool(outcome.state.attempts) and "replan_limit_reached" in outcome.acceptance.reasons
            approval_request = require_human(
                approval_id=f"{mission.mission_id}:approval:1",
                mission_id=mission.mission_id,
                execution_id=f"{prefix}-approval",
                subject_state_id=acceptance_context.subject_state_id,
                policy_bundle_id=policy.policy_bundle_id,
                reason="replan_limit_reached" if escalation else (policy.reason or "human_approval_required"),
            )

        self._store.create(
            MissionRecord(
                mission,
                outcome,
                run_context=run_context,
                approval_request=approval_request,
            )
        )
        return outcome

    def approve(self, mission_id: str, *, approver_id: str, approved: bool = True) -> MissionRecord:
        """Record one bound, durable human decision for a waiting mission."""
        if not approver_id:
            raise ValueError("approver_id is required")
        current = self._store.get(mission_id)
        if current.status is not MissionStatus.WAITING_APPROVAL or current.approval_request is None:
            raise MissionNotWaitingApproval(mission_id)
        if current.approval_record is not None:
            raise MissionApprovalAlreadyDecided(mission_id)

        request = current.approval_request
        record = ApprovalRecord(
            approval_id=request.approval_id,
            mission_id=request.mission_id,
            execution_id=request.execution_id,
            subject_state_id=request.subject_state_id,
            policy_bundle_id=request.policy_bundle_id,
            approver_id=approver_id,
            approved=approved,
        )

        if approved:
            return self._store.replace(replace(current, approval_record=record))

        assert current.outcome.state is not None
        denied_acceptance = AcceptanceResult(
            AcceptanceDecision.BLOCK,
            current.outcome.acceptance.reasons + ("approval_denied",),
            current.outcome.acceptance.proof,
        )
        denied_state = MissionState(
            mission_id,
            MissionStatus.BLOCKED,
            current.outcome.state.attempts,
            current.outcome.state.history + (MissionStatus.BLOCKED,),
        )
        denied_outcome = replace(current.outcome, acceptance=denied_acceptance, state=denied_state)
        return self._store.replace(replace(current, outcome=denied_outcome, approval_record=record))

    def _resume_replan_escalation(
        self,
        current: MissionRecord,
        *,
        resumed_policy: PolicyDecision,
        now_epoch: float,
    ) -> MissionOutcome:
        """Use one approved extra attempt against an unattempted live runtime."""

        if current.run_context is None or current.outcome.state is None:
            raise MissionApprovalError("mission is missing persisted escalation context")

        context = current.run_context
        prior_state = current.outcome.state
        remaining = self._remaining_routable_pools(
            current.mission,
            current.outcome.attempted_orchestrators,
        )
        if not remaining:
            acceptance = AcceptanceResult(
                AcceptanceDecision.BLOCK,
                current.outcome.acceptance.reasons + ("approved_escalation_no_remaining_runtime",),
                current.outcome.acceptance.proof,
            )
            state = MissionState(
                current.mission_id,
                MissionStatus.BLOCKED,
                prior_state.attempts,
                prior_state.history + (MissionStatus.BLOCKED,),
            )
            outcome = replace(current.outcome, acceptance=acceptance, state=state)
            self._store.replace(replace(current, outcome=outcome))
            return outcome

        _, normalizers = self._routing_inputs()
        next_attempt = len(prior_state.attempts) + 1
        continued = execute_mission_once(
            mission=current.mission,
            registry=self._registry,
            pools=remaining,
            normalizers=normalizers,
            policy=resumed_policy,
            budget=current.outcome.budget,
            acceptance_context=context.acceptance_context,
            execution_id=f"{context.execution_id_prefix}-{next_attempt}",
            now_epoch=now_epoch,
            attempt_number=next_attempt,
            **self._execution_kwargs(current.mission_id),
        )
        assert continued.state is not None

        attempted = list(current.outcome.attempted_orchestrators)
        for orchestrator_id in continued.attempted_orchestrators:
            if orchestrator_id not in attempted:
                attempted.append(orchestrator_id)

        combined_state = MissionState(
            current.mission_id,
            continued.state.status,
            prior_state.attempts + continued.state.attempts,
            prior_state.history + continued.state.history[1:],
        )
        acceptance = continued.acceptance
        if acceptance.decision is not AcceptanceDecision.ACCEPT:
            acceptance = AcceptanceResult(
                acceptance.decision,
                acceptance.reasons + ("approved_escalation_attempt_exhausted",),
                acceptance.proof,
            )
        outcome = replace(
            continued,
            acceptance=acceptance,
            attempted_orchestrators=tuple(attempted),
            state=combined_state,
        )
        self._store.replace(replace(current, outcome=outcome))
        return outcome

    def resume(self, mission_id: str, *, now_epoch: float = 0.0) -> MissionOutcome:
        """Resume an approved mission using its persisted original run context."""
        current = self._store.get(mission_id)
        if current.status is not MissionStatus.WAITING_APPROVAL or current.approval_request is None:
            raise MissionNotWaitingApproval(mission_id)
        if current.approval_record is None or not current.approval_record.approved:
            raise MissionApprovalNotGranted(mission_id)
        if resume_after_approval(current.approval_request, current.approval_record) is not AcceptanceDecision.ACCEPT:
            raise MissionApprovalNotGranted(mission_id)
        if current.run_context is None:
            raise MissionApprovalError("mission is missing persisted run context")
        assert current.outcome.state is not None

        context = current.run_context
        resumed_policy = PolicyDecision(
            PolicyEffect.ALLOW,
            context.policy.policy_bundle_id,
            f"approved:{current.approval_record.approval_id}",
        )

        if current.outcome.state.attempts:
            if not self._is_replan_limit_outcome(current.outcome):
                raise MissionApprovalError("runtime-attempt approval is not a recognized replan escalation")
            return self._resume_replan_escalation(
                current,
                resumed_policy=resumed_policy,
                now_epoch=now_epoch,
            )

        pools, normalizers = self._routing_inputs()
        outcome = execute_mission(
            mission=current.mission,
            registry=self._registry,
            pools=pools,
            normalizers=normalizers,
            policy=resumed_policy,
            budget=context.budget,
            acceptance_context=context.acceptance_context,
            execution_id_prefix=context.execution_id_prefix,
            now_epoch=now_epoch,
            max_attempts=context.max_attempts,
            **self._execution_kwargs(mission_id),
        )
        assert outcome.state is not None
        combined_state = MissionState(
            mission_id,
            outcome.state.status,
            outcome.state.attempts,
            current.outcome.state.history + outcome.state.history[1:],
        )
        outcome = replace(outcome, state=combined_state)
        self._store.replace(replace(current, outcome=outcome))
        return outcome

    def cancel(self, mission_id: str) -> ActiveExecutionHandle | MissionRecord:
        """Request cancellation and delegate it only from the executing owner.

        Every caller persists the request. Only the MissionOperator instance that
        owns the active execution watcher may set ``cancel_delegated``; a second
        CLI process can call a fresh runtime instance as best effort but leaves
        the durable flag open for the executing process to confirm delegation.
        """
        try:
            current = self._store.get(mission_id)
        except MissionNotFound:
            current = None

        if current is not None:
            if current.status is MissionStatus.WAITING_APPROVAL:
                assert current.outcome.state is not None
                acceptance = AcceptanceResult(
                    AcceptanceDecision.BLOCK,
                    current.outcome.acceptance.reasons + ("operator_cancelled",),
                    current.outcome.acceptance.proof,
                )
                state = MissionState(
                    mission_id,
                    MissionStatus.CANCELLED,
                    current.outcome.state.attempts,
                    current.outcome.state.history + (MissionStatus.CANCELLED,),
                )
                outcome = replace(current.outcome, acceptance=acceptance, state=state)
                return self._store.replace(replace(current, outcome=outcome))
            raise MissionNotCancellable(f"mission is already terminal: {current.status.value}")

        if self._execution_handles is None:
            raise MissionCancellationUnavailable("mission cancellation is not configured")
        try:
            handle = self._execution_handles.get(mission_id)
        except ActiveExecutionNotFound as exc:
            raise MissionNotCancellable(f"mission has no active execution: {mission_id}") from exc
        if handle.status is not ExecutionHandleStatus.ACTIVE:
            raise MissionNotCancellable(f"mission execution is already complete: {mission_id}")

        requested = self._execution_handles.request_cancel(mission_id)
        with self._watchers_lock:
            owns_execution = requested.execution_id in self._watchers
        if owns_execution:
            try:
                return self._delegate_cancel(requested)
            except Exception:
                return self._execution_handles.get(mission_id)

        try:
            self._registry.get(requested.orchestrator_id).cancel(requested.execution_id)
        except Exception:
            pass
        return self._execution_handles.get(mission_id)

    def status(self, mission_id: str) -> MissionStatus:
        try:
            return self._store.get(mission_id).status
        except MissionNotFound:
            if self._execution_handles is None:
                raise
            handle = self._execution_handles.get(mission_id)
            if handle.status is ExecutionHandleStatus.ACTIVE:
                return MissionStatus.RUNNING
            if handle.execution_status is ExecutionStatus.CANCELLED:
                return MissionStatus.CANCELLED
            if handle.execution_status is ExecutionStatus.FAILED:
                return MissionStatus.FAILED
            return MissionStatus.VERIFYING

    def active_execution(self, mission_id: str) -> ActiveExecutionHandle:
        if self._execution_handles is None:
            raise MissionCancellationUnavailable("mission cancellation is not configured")
        return self._execution_handles.get(mission_id)

    def inspect(self, mission_id: str) -> MissionRecord:
        return self._store.get(mission_id)

    def list(self) -> tuple[MissionRecord, ...]:
        return self._store.list()

    def runtime_entries(self):
        if self._catalog is None:
            raise AttributeError("runtime_entries requires a catalog-backed MissionOperator")
        return self._catalog.entries()


__all__ = [
    "run",
    "status",
    "inspect",
    "cancel",
    "resume",
    "MissionApprovalError",
    "MissionNotWaitingApproval",
    "MissionApprovalAlreadyDecided",
    "MissionApprovalNotGranted",
    "MissionCancellationError",
    "MissionCancellationUnavailable",
    "MissionNotCancellable",
    "MissionOperator",
]
