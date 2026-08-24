"""Observability decorator for MissionOperator.

The decorator does not own mission semantics. It delegates execution, approval,
resume and storage to the existing MissionOperator and projects the resulting
auditable mission state into a uniform append-only event ledger.
"""

from __future__ import annotations

from typing import Any

from .control_plane import MissionOutcome, MissionStatus
from .core import ExecutionStatus, Mission
from .governance import AcceptanceBudget, PolicyDecision
from .acceptance import AcceptanceContext
from .mission_store import MissionAlreadyExists, MissionNotFound, MissionRecord
from .observability import EventLedgerPort, MissionEvent, MissionEventKind
from .operator import MissionOperator


_TERMINAL = frozenset({MissionStatus.ACCEPTED, MissionStatus.BLOCKED, MissionStatus.FAILED})


class ObservableMissionOperator:
    """Project MissionOperator decisions into an EventLedgerPort."""

    def __init__(self, operator: MissionOperator, ledger: EventLedgerPort) -> None:
        self._operator = operator
        self._ledger = ledger

    def _event(
        self,
        mission_id: str,
        kind: MissionEventKind,
        *,
        payload: dict[str, Any] | None = None,
        now_epoch: float = 0.0,
    ) -> MissionEvent:
        return self._ledger.append(
            mission_id,
            kind,
            payload=payload or {},
            occurred_at_epoch=now_epoch,
        )

    def _record_attempts(self, outcome: MissionOutcome, *, now_epoch: float) -> None:
        if outcome.state is None:
            return
        replans_remaining = sum(
            1 for status in outcome.state.history if status is MissionStatus.REPLANNING
        )
        attempts = outcome.state.attempts
        for index, attempt in enumerate(attempts):
            common = {
                "attempt_number": attempt.attempt_number,
                "execution_id": attempt.execution_id,
                "orchestrator_id": attempt.orchestrator_id,
            }
            self._event(
                outcome.mission_id,
                MissionEventKind.ORCHESTRATOR_SELECTED,
                payload=common,
                now_epoch=now_epoch,
            )
            if attempt.execution_status is not None:
                self._event(
                    outcome.mission_id,
                    MissionEventKind.RUNTIME_STARTED,
                    payload=common,
                    now_epoch=now_epoch,
                )
                self._event(
                    outcome.mission_id,
                    MissionEventKind.RUNTIME_COMPLETED,
                    payload={**common, "execution_status": attempt.execution_status.value},
                    now_epoch=now_epoch,
                )
                if attempt.execution_status is ExecutionStatus.SUCCEEDED:
                    self._event(
                        outcome.mission_id,
                        MissionEventKind.EVIDENCE_RECORDED,
                        payload={**common, "attempt_id": f"attempt-{attempt.attempt_number}", "normalized": True},
                        now_epoch=now_epoch,
                    )
            acceptance_payload: dict[str, Any] = {
                **common,
                "decision": attempt.acceptance_decision.value,
                "reasons": list(attempt.reasons),
            }
            if index == len(attempts) - 1 and outcome.acceptance.proof is not None:
                acceptance_payload["proof_digest"] = outcome.acceptance.proof.digest
                acceptance_payload["evidence_ids"] = list(outcome.acceptance.proof.evidence_ids)
            self._event(
                outcome.mission_id,
                MissionEventKind.ACCEPTANCE_EVALUATED,
                payload=acceptance_payload,
                now_epoch=now_epoch,
            )
            if replans_remaining > 0:
                self._event(
                    outcome.mission_id,
                    MissionEventKind.REPLAN_REQUESTED,
                    payload={
                        "after_attempt": attempt.attempt_number,
                        "previous_orchestrator_id": attempt.orchestrator_id,
                        "reasons": list(attempt.reasons),
                    },
                    now_epoch=now_epoch,
                )
                replans_remaining -= 1

    def _record_terminal(self, outcome: MissionOutcome, *, now_epoch: float) -> None:
        if outcome.state is None or outcome.state.status not in _TERMINAL:
            return
        self._event(
            outcome.mission_id,
            MissionEventKind.MISSION_TERMINAL,
            payload={
                "status": outcome.state.status.value,
                "acceptance_decision": outcome.acceptance.decision.value,
                "reasons": list(outcome.acceptance.reasons),
                "attempted_orchestrators": list(outcome.attempted_orchestrators),
                "money_used": outcome.budget.money_used,
                "tokens_used": outcome.budget.tokens_used,
                "wall_time_used_s": outcome.budget.wall_time_used_s,
                "verifier_attempts_used": outcome.budget.verifier_attempts_used,
            },
            now_epoch=now_epoch,
        )

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
        try:
            self._operator.inspect(mission.mission_id)
        except MissionNotFound:
            pass
        else:
            raise MissionAlreadyExists(mission.mission_id)

        self._event(
            mission.mission_id,
            MissionEventKind.MISSION_CREATED,
            payload={
                "objective": mission.objective,
                "required_capabilities": sorted(mission.required_capabilities),
            },
            now_epoch=now_epoch,
        )
        self._event(
            mission.mission_id,
            MissionEventKind.POLICY_EVALUATED,
            payload={
                "effect": policy.effect.value,
                "policy_bundle_id": policy.policy_bundle_id,
                "reason": policy.reason,
            },
            now_epoch=now_epoch,
        )
        outcome = self._operator.run(
            mission,
            policy=policy,
            budget=budget,
            acceptance_context=acceptance_context,
            execution_id_prefix=execution_id_prefix,
            now_epoch=now_epoch,
            max_attempts=max_attempts,
        )
        self._record_attempts(outcome, now_epoch=now_epoch)

        record = self._operator.inspect(mission.mission_id)
        if record.approval_request is not None:
            request = record.approval_request
            self._event(
                mission.mission_id,
                MissionEventKind.APPROVAL_REQUESTED,
                payload={
                    "approval_id": request.approval_id,
                    "execution_id": request.execution_id,
                    "subject_state_id": request.subject_state_id,
                    "policy_bundle_id": request.policy_bundle_id,
                    "reason": request.reason,
                },
                now_epoch=now_epoch,
            )
        self._record_terminal(outcome, now_epoch=now_epoch)
        return outcome

    def approve(
        self,
        mission_id: str,
        *,
        approver_id: str,
        approved: bool = True,
        now_epoch: float = 0.0,
    ) -> MissionRecord:
        record = self._operator.approve(
            mission_id,
            approver_id=approver_id,
            approved=approved,
        )
        assert record.approval_record is not None
        decision = record.approval_record
        self._event(
            mission_id,
            MissionEventKind.APPROVAL_RECORDED,
            payload={
                "approval_id": decision.approval_id,
                "approver_id": decision.approver_id,
                "approved": decision.approved,
            },
            now_epoch=now_epoch,
        )
        if not approved:
            self._record_terminal(record.outcome, now_epoch=now_epoch)
        return record

    def resume(self, mission_id: str, *, now_epoch: float = 0.0) -> MissionOutcome:
        outcome = self._operator.resume(mission_id, now_epoch=now_epoch)
        self._event(
            mission_id,
            MissionEventKind.MISSION_RESUMED,
            payload={"status": outcome.state.status.value if outcome.state is not None else ""},
            now_epoch=now_epoch,
        )
        self._record_attempts(outcome, now_epoch=now_epoch)
        self._record_terminal(outcome, now_epoch=now_epoch)
        return outcome

    def status(self, mission_id: str) -> MissionStatus:
        return self._operator.status(mission_id)

    def inspect(self, mission_id: str) -> MissionRecord:
        return self._operator.inspect(mission_id)

    def list(self) -> tuple[MissionRecord, ...]:
        return self._operator.list()

    def events(self, mission_id: str) -> tuple[MissionEvent, ...]:
        return self._ledger.list(mission_id)


__all__ = ["ObservableMissionOperator"]
