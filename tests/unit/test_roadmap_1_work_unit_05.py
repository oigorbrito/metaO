from __future__ import annotations

from pathlib import Path
import tempfile
import unittest

from metao.acceptance import AcceptanceContext, AcceptanceDecision
from metao.adapters.langgraph import normalize_evidence
from metao.catalog import OrchestratorCatalog
from metao.control_plane import MissionStatus
from metao.core import (
    ExecutionRequest,
    ExecutionResult,
    ExecutionStatus,
    HealthReport,
    HealthStatus,
    Mission,
    OrchestratorDescriptor,
    OrchestratorRegistry,
)
from metao.governance import AcceptanceBudget, ApprovalRecord, evaluate_policy
from metao.mission_store import InMemoryMissionStore, MissionRecord
from metao.operator import (
    MissionApprovalAlreadyDecided,
    MissionApprovalNotGranted,
    MissionNotWaitingApproval,
    MissionOperator,
)
from metao.sqlite_store import SQLiteMissionStore


class Runtime:
    def __init__(self, orchestrator_id: str, *, health: HealthStatus = HealthStatus.HEALTHY) -> None:
        self._descriptor = OrchestratorDescriptor(orchestrator_id, "v1", frozenset({"workflow"}))
        self.health_status = health
        self.calls = 0

    @property
    def descriptor(self):
        return self._descriptor

    def health(self):
        return HealthReport(self.health_status)

    def execute(self, request: ExecutionRequest):
        self.calls += 1
        return ExecutionResult(
            request.execution_id,
            self.descriptor.orchestrator_id,
            ExecutionStatus.SUCCEEDED,
            {"result": f"approved:{self.descriptor.orchestrator_id}"},
        )

    def cancel(self, execution_id: str) -> None:
        pass


class HumanApprovalResumeV1Tests(unittest.TestCase):
    def setUp(self) -> None:
        self.registry = OrchestratorRegistry()
        self.primary = Runtime("primary")
        self.fallback = Runtime("fallback")
        self.registry.register(self.primary)
        self.registry.register(self.fallback)
        self.catalog = OrchestratorCatalog(self.registry)
        self.catalog.register(
            "primary",
            normalizer=normalize_evidence,
            cost=0.01,
            latency_ms=10.0,
            success_rate=0.99,
            quality=0.99,
            reliability=0.99,
        )
        self.catalog.register(
            "fallback",
            normalizer=normalize_evidence,
            cost=5.0,
            latency_ms=5000.0,
            success_rate=0.2,
            quality=0.2,
            reliability=0.2,
        )
        self.context = AcceptanceContext(
            "subject-1",
            "state-1",
            "verify-1",
            "policy-1",
            frozenset({"execution_result"}),
        )
        self.budget = AcceptanceBudget(5.0, 1000, 60.0, 3)
        self.require_human = evaluate_policy(
            policy_bundle_id="policy-1",
            allowed=True,
            require_human=True,
            reason="operator approval required",
        )

    def _operator(self, store):
        return MissionOperator(registry=self.registry, catalog=self.catalog, store=store)

    def _mission(self, mission_id: str = "approval-mission") -> Mission:
        return Mission(mission_id, "execute only after approval", frozenset({"workflow"}))

    def test_require_human_creates_durable_waiting_request_without_runtime_execution(self):
        store = InMemoryMissionStore()
        operator = self._operator(store)
        outcome = operator.run(
            self._mission(),
            policy=self.require_human,
            budget=self.budget,
            acceptance_context=self.context,
            execution_id_prefix="exec",
        )
        record = operator.inspect("approval-mission")
        self.assertEqual(outcome.state.status, MissionStatus.WAITING_APPROVAL)
        self.assertEqual(self.primary.calls + self.fallback.calls, 0)
        self.assertEqual(record.approval_request.approval_id, "approval-mission:approval:1")
        self.assertEqual(record.approval_request.execution_id, "exec-approval")
        self.assertEqual(record.approval_request.subject_state_id, "state-1")
        self.assertEqual(record.approval_request.policy_bundle_id, "policy-1")
        self.assertEqual(record.run_context.execution_id_prefix, "exec")

    def test_approval_is_bound_and_status_remains_waiting_until_resume(self):
        store = InMemoryMissionStore()
        operator = self._operator(store)
        operator.run(self._mission(), policy=self.require_human, budget=self.budget, acceptance_context=self.context)
        approved = operator.approve("approval-mission", approver_id="human-1")
        self.assertTrue(approved.approval_record.approved)
        self.assertEqual(approved.approval_record.approver_id, "human-1")
        self.assertEqual(approved.status, MissionStatus.WAITING_APPROVAL)
        self.assertEqual(approved.revision, 2)
        self.assertEqual(self.primary.calls + self.fallback.calls, 0)

    def test_duplicate_human_decision_is_rejected(self):
        store = InMemoryMissionStore()
        operator = self._operator(store)
        operator.run(self._mission(), policy=self.require_human, budget=self.budget, acceptance_context=self.context)
        operator.approve("approval-mission", approver_id="human-1")
        with self.assertRaises(MissionApprovalAlreadyDecided):
            operator.approve("approval-mission", approver_id="human-2")

    def test_resume_without_granted_approval_fails_closed(self):
        store = InMemoryMissionStore()
        operator = self._operator(store)
        operator.run(self._mission(), policy=self.require_human, budget=self.budget, acceptance_context=self.context)
        with self.assertRaises(MissionApprovalNotGranted):
            operator.resume("approval-mission")
        self.assertEqual(self.primary.calls + self.fallback.calls, 0)

    def test_denial_terminally_blocks_without_runtime_execution(self):
        store = InMemoryMissionStore()
        operator = self._operator(store)
        operator.run(self._mission(), policy=self.require_human, budget=self.budget, acceptance_context=self.context)
        denied = operator.approve("approval-mission", approver_id="human-1", approved=False)
        self.assertEqual(denied.status, MissionStatus.BLOCKED)
        self.assertIn("approval_denied", denied.outcome.acceptance.reasons)
        self.assertFalse(denied.approval_record.approved)
        self.assertEqual(self.primary.calls + self.fallback.calls, 0)
        with self.assertRaises(MissionNotWaitingApproval):
            operator.resume("approval-mission")

    def test_approved_resume_executes_and_preserves_waiting_history(self):
        store = InMemoryMissionStore()
        operator = self._operator(store)
        operator.run(
            self._mission(),
            policy=self.require_human,
            budget=self.budget,
            acceptance_context=self.context,
            execution_id_prefix="approved-exec",
        )
        operator.approve("approval-mission", approver_id="human-1")
        outcome = operator.resume("approval-mission", now_epoch=100.0)
        record = operator.inspect("approval-mission")
        self.assertEqual(outcome.acceptance.decision, AcceptanceDecision.ACCEPT)
        self.assertEqual(record.status, MissionStatus.ACCEPTED)
        self.assertEqual(record.revision, 3)
        self.assertEqual(self.primary.calls, 1)
        self.assertEqual(self.fallback.calls, 0)
        self.assertEqual(outcome.execution.execution_id, "approved-exec-1")
        history = outcome.state.history
        self.assertIn(MissionStatus.WAITING_APPROVAL, history)
        waiting_index = history.index(MissionStatus.WAITING_APPROVAL)
        self.assertIn(MissionStatus.PLANNING, history[waiting_index + 1:])
        self.assertEqual(history[-1], MissionStatus.ACCEPTED)

    def test_resume_uses_live_catalog_health_after_approval(self):
        store = InMemoryMissionStore()
        operator = self._operator(store)
        operator.run(self._mission(), policy=self.require_human, budget=self.budget, acceptance_context=self.context)
        operator.approve("approval-mission", approver_id="human-1")
        self.primary.health_status = HealthStatus.UNHEALTHY
        outcome = operator.resume("approval-mission", now_epoch=100.0)
        self.assertEqual(outcome.orchestrator_id, "fallback")
        self.assertEqual(self.primary.calls, 0)
        self.assertEqual(self.fallback.calls, 1)

    def test_sqlite_restart_between_wait_approve_and_resume(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "metao.db"
            first = self._operator(SQLiteMissionStore(path))
            first.run(
                self._mission(),
                policy=self.require_human,
                budget=self.budget,
                acceptance_context=self.context,
                execution_id_prefix="restart-exec",
                max_attempts=2,
            )

            second = self._operator(SQLiteMissionStore(path))
            waiting = second.inspect("approval-mission")
            self.assertEqual(waiting.status, MissionStatus.WAITING_APPROVAL)
            self.assertEqual(waiting.run_context.max_attempts, 2)
            self.assertEqual(waiting.run_context.acceptance_context.subject_state_id, "state-1")
            second.approve("approval-mission", approver_id="human-after-restart")

            third = self._operator(SQLiteMissionStore(path))
            approved = third.inspect("approval-mission")
            self.assertEqual(approved.approval_record.approver_id, "human-after-restart")
            outcome = third.resume("approval-mission", now_epoch=100.0)

            fourth = self._operator(SQLiteMissionStore(path))
            final = fourth.inspect("approval-mission")
            self.assertEqual(outcome.acceptance.decision, AcceptanceDecision.ACCEPT)
            self.assertEqual(final.status, MissionStatus.ACCEPTED)
            self.assertEqual(final.revision, 3)
            self.assertTrue(final.approval_record.approved)
            self.assertIn(MissionStatus.WAITING_APPROVAL, final.outcome.state.history)

    def test_mismatched_approval_record_binding_is_rejected_by_mission_record(self):
        store = InMemoryMissionStore()
        operator = self._operator(store)
        operator.run(self._mission(), policy=self.require_human, budget=self.budget, acceptance_context=self.context)
        current = operator.inspect("approval-mission")
        bad = ApprovalRecord(
            approval_id=current.approval_request.approval_id,
            mission_id=current.mission_id,
            execution_id="wrong-execution",
            subject_state_id=current.approval_request.subject_state_id,
            policy_bundle_id=current.approval_request.policy_bundle_id,
            approver_id="human-1",
            approved=True,
        )
        with self.assertRaises(ValueError):
            MissionRecord(
                current.mission,
                current.outcome,
                current.revision,
                current.run_context,
                current.approval_request,
                bad,
            )

    def test_policy_bundle_mismatch_still_blocks_in_control_plane_instead_of_raising(self):
        store = InMemoryMissionStore()
        operator = self._operator(store)
        mismatched = evaluate_policy(policy_bundle_id="other-policy", allowed=True)
        outcome = operator.run(
            self._mission("policy-mismatch"),
            policy=mismatched,
            budget=self.budget,
            acceptance_context=self.context,
        )
        self.assertEqual(outcome.state.status, MissionStatus.BLOCKED)
        self.assertIn("policy_bundle_mismatch", outcome.acceptance.reasons)
        self.assertEqual(self.primary.calls + self.fallback.calls, 0)

    def test_approval_resume_code_remains_orchestrator_sdk_neutral(self):
        root = Path(__file__).resolve().parents[2]
        for relative in ("src/metao/mission_store.py", "src/metao/operator.py"):
            source = (root / relative).read_text(encoding="utf-8").lower()
            for forbidden in ("import langgraph", "from langgraph", "import crewai", "from crewai"):
                self.assertNotIn(forbidden, source)


if __name__ == "__main__":
    unittest.main(verbosity=2)
