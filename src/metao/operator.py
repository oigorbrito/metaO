"""Public operator facades for durable executions and metaO missions.

The module-level functions preserve the existing DurableExecutionPort API.
MissionOperator is the product-facing, framework-neutral facade over the
control-plane plus a MissionStorePort, including durable human approval/resume.
"""

from __future__ import annotations

from dataclasses import replace
from typing import Mapping

from metao.acceptance import AcceptanceContext, AcceptanceDecision, AcceptanceResult
from metao.catalog import OrchestratorCatalog
from metao.control_plane import EvidenceNormalizer, MissionOutcome, MissionState, MissionStatus, execute_mission
from metao.core import Mission, OrchestratorRegistry
from metao.durable import DurableExecutionPort, DurableExecutionSpec, DurableExecutionState
from metao.governance import (
    AcceptanceBudget,
    ApprovalRecord,
    PolicyDecision,
    PolicyEffect,
    require_human,
    resume_after_approval,
)
from metao.mission_store import MissionAlreadyExists, MissionRecord, MissionRunContext, MissionStorePort
from metao.strategy import OrchestratorPoolState


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


class MissionOperator:
    """Configured synchronous mission facade backed by a MissionStorePort.

    Prefer ``catalog=`` for product usage. ``pools`` + ``normalizers`` remain
    supported as the lower-level compatibility path proven by earlier blocks.

    Human approval is durable at the mission-record boundary. A mission stopped
    at WAITING_APPROVAL can therefore be approved and resumed after process
    restart when the store itself is durable.
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

    def _routing_inputs(self) -> tuple[tuple[OrchestratorPoolState, ...], Mapping[str, EvidenceNormalizer]]:
        if self._catalog is not None:
            return self._catalog.pools(), self._catalog.normalizers()
        return self._pools, self._normalizers

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
        )

        approval_request = None
        if outcome.state is not None and outcome.state.status is MissionStatus.WAITING_APPROVAL:
            approval_request = require_human(
                approval_id=f"{mission.mission_id}:approval:1",
                mission_id=mission.mission_id,
                execution_id=f"{prefix}-approval",
                subject_state_id=acceptance_context.subject_state_id,
                policy_bundle_id=policy.policy_bundle_id,
                reason=policy.reason or "human_approval_required",
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
        if current.outcome.state.attempts:
            raise MissionApprovalError("approval resume expects a pre-runtime waiting state")

        context = current.run_context
        resumed_policy = PolicyDecision(
            PolicyEffect.ALLOW,
            context.policy.policy_bundle_id,
            f"approved:{current.approval_record.approval_id}",
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

    def status(self, mission_id: str) -> MissionStatus:
        return self._store.get(mission_id).status

    def inspect(self, mission_id: str) -> MissionRecord:
        return self._store.get(mission_id)

    def list(self) -> tuple[MissionRecord, ...]:
        return self._store.list()


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
    "MissionOperator",
]
