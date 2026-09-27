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
from metao.governance import AcceptanceBudget, evaluate_policy
from metao.mission_store import InMemoryMissionStore
from metao.operator import MissionNotWaitingApproval, MissionOperator
from metao.sqlite_store import SQLiteMissionStore


class Runtime:
    def __init__(
        self,
        orchestrator_id: str,
        *,
        status: ExecutionStatus,
        error: str = "",
        result: str = "ok",
    ) -> None:
        self._descriptor = OrchestratorDescriptor(
            orchestrator_id,
            "v1",
            frozenset({"workflow"}),
        )
        self.status = status
        self.error = error
        self.result = result
        self.health_status = HealthStatus.HEALTHY
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
            self.status,
            {"result": self.result} if self.status is ExecutionStatus.SUCCEEDED else {},
            error=self.error,
        )

    def cancel(self, execution_id: str) -> None:
        pass


def add_runtime(
    registry: OrchestratorRegistry,
    catalog: OrchestratorCatalog,
    runtime: Runtime,
    *,
    rank: int,
) -> None:
    registry.register(runtime)
    catalog.register(
        runtime.descriptor.orchestrator_id,
        normalizer=normalize_evidence,
        cost=0.01 * rank,
        latency_ms=10.0 * rank,
        success_rate=1.0 - (0.1 * (rank - 1)),
        quality=1.0 - (0.1 * (rank - 1)),
        reliability=1.0 - (0.1 * (rank - 1)),
    )


class DurableReplanEscalationV1Tests(unittest.TestCase):
    def setUp(self) -> None:
        self.registry = OrchestratorRegistry()
        self.catalog = OrchestratorCatalog(self.registry)
        self.first = Runtime(
            "runtime-a",
            status=ExecutionStatus.FAILED,
            error="worker runtime crashed",
        )
        self.second = Runtime(
            "runtime-b",
            status=ExecutionStatus.FAILED,
            error="request timed out",
        )
        self.third = Runtime(
            "runtime-c",
            status=ExecutionStatus.SUCCEEDED,
            result="human-approved-recovery",
        )
        add_runtime(self.registry, self.catalog, self.first, rank=1)
        add_runtime(self.registry, self.catalog, self.second, rank=2)
        add_runtime(self.registry, self.catalog, self.third, rank=3)
        self.context = AcceptanceContext(
            "subject-r7",
            "state-r7",
            "verify-r7",
            "policy-r7",
            frozenset({"execution_result"}),
        )
        self.policy = evaluate_policy(policy_bundle_id="policy-r7", allowed=True)
        self.budget = AcceptanceBudget(10.0, 10_000, 60.0, 10)

    def operator(self, store):
        return MissionOperator(
            registry=self.registry,
            catalog=self.catalog,
            store=store,
        )

    def mission(self, mission_id: str = "escalation-mission") -> Mission:
        return Mission(
            mission_id,
            "recover with bounded human escalation",
            frozenset({"workflow"}),
        )

    def start(self, operator: MissionOperator, mission_id: str = "escalation-mission"):
        return operator.run(
            self.mission(mission_id),
            policy=self.policy,
            budget=self.budget,
            acceptance_context=self.context,
            execution_id_prefix="r7-escalate",
            max_attempts=2,
            now_epoch=100.0,
        )

    def test_replan_limit_with_unattempted_runtime_becomes_durable_waiting_approval(self):
        store = InMemoryMissionStore()
        operator = self.operator(store)

        outcome = self.start(operator)
        record = operator.inspect("escalation-mission")

        self.assertEqual(outcome.state.status, MissionStatus.WAITING_APPROVAL)
        self.assertEqual(outcome.acceptance.decision, AcceptanceDecision.REQUIRE_HUMAN)
        self.assertEqual(outcome.attempted_orchestrators, ("runtime-a", "runtime-b"))
        self.assertEqual([item.attempt_number for item in outcome.state.attempts], [1, 2])
        self.assertEqual(record.approval_request.reason, "replan_limit_reached")
        self.assertEqual(record.approval_request.execution_id, "r7-escalate-approval")
        self.assertEqual(self.first.calls, 1)
        self.assertEqual(self.second.calls, 1)
        self.assertEqual(self.third.calls, 0)

    def test_approved_escalation_uses_exactly_one_unattempted_runtime_and_preserves_lineage(self):
        store = InMemoryMissionStore()
        operator = self.operator(store)
        self.start(operator)
        operator.approve("escalation-mission", approver_id="human-r7")

        outcome = operator.resume("escalation-mission", now_epoch=120.0)
        record = operator.inspect("escalation-mission")

        self.assertEqual(outcome.acceptance.decision, AcceptanceDecision.ACCEPT)
        self.assertEqual(outcome.state.status, MissionStatus.ACCEPTED)
        self.assertEqual(outcome.attempted_orchestrators, ("runtime-a", "runtime-b", "runtime-c"))
        self.assertEqual([item.attempt_number for item in outcome.state.attempts], [1, 2, 3])
        self.assertEqual([item.orchestrator_id for item in outcome.state.attempts], ["runtime-a", "runtime-b", "runtime-c"])
        self.assertEqual(outcome.execution.execution_id, "r7-escalate-3")
        self.assertEqual(outcome.execution.output["result"], "human-approved-recovery")
        self.assertEqual(self.first.calls, 1)
        self.assertEqual(self.second.calls, 1)
        self.assertEqual(self.third.calls, 1)
        self.assertEqual(record.revision, 3)
        self.assertTrue(record.approval_record.approved)
        self.assertIn(MissionStatus.WAITING_APPROVAL, outcome.state.history)
        self.assertEqual(outcome.state.history[-1], MissionStatus.ACCEPTED)

    def test_denied_escalation_blocks_without_executing_remaining_runtime(self):
        store = InMemoryMissionStore()
        operator = self.operator(store)
        self.start(operator)

        denied = operator.approve(
            "escalation-mission",
            approver_id="human-r7",
            approved=False,
        )

        self.assertEqual(denied.status, MissionStatus.BLOCKED)
        self.assertIn("approval_denied", denied.outcome.acceptance.reasons)
        self.assertEqual(self.third.calls, 0)
        with self.assertRaises(MissionNotWaitingApproval):
            operator.resume("escalation-mission")

    def test_escalation_resume_uses_fresh_health_and_never_retries_attempted_runtimes(self):
        store = InMemoryMissionStore()
        operator = self.operator(store)
        self.start(operator)
        operator.approve("escalation-mission", approver_id="human-r7")
        self.third.health_status = HealthStatus.UNHEALTHY

        outcome = operator.resume("escalation-mission", now_epoch=120.0)

        self.assertEqual(outcome.state.status, MissionStatus.BLOCKED)
        self.assertIn("approved_escalation_no_remaining_runtime", outcome.acceptance.reasons)
        self.assertEqual(self.first.calls, 1)
        self.assertEqual(self.second.calls, 1)
        self.assertEqual(self.third.calls, 0)

    def test_no_remaining_runtime_means_no_pointless_human_escalation(self):
        registry = OrchestratorRegistry()
        catalog = OrchestratorCatalog(registry)
        first = Runtime("only-a", status=ExecutionStatus.FAILED, error="worker runtime crashed")
        second = Runtime("only-b", status=ExecutionStatus.FAILED, error="request timed out")
        add_runtime(registry, catalog, first, rank=1)
        add_runtime(registry, catalog, second, rank=2)
        operator = MissionOperator(
            registry=registry,
            catalog=catalog,
            store=InMemoryMissionStore(),
        )

        outcome = operator.run(
            Mission("no-remaining", "exhaust all runtimes", frozenset({"workflow"})),
            policy=self.policy,
            budget=self.budget,
            acceptance_context=self.context,
            max_attempts=2,
            now_epoch=100.0,
        )
        record = operator.inspect("no-remaining")

        self.assertEqual(outcome.state.status, MissionStatus.FAILED)
        self.assertIn("replan_limit_reached", outcome.acceptance.reasons)
        self.assertIsNone(record.approval_request)

    def test_sqlite_restart_preserves_escalation_approval_and_continues_attempt_numbering(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "metao.db"
            first_operator = self.operator(SQLiteMissionStore(path))
            self.start(first_operator)

            second_operator = self.operator(SQLiteMissionStore(path))
            waiting = second_operator.inspect("escalation-mission")
            self.assertEqual(waiting.status, MissionStatus.WAITING_APPROVAL)
            self.assertEqual(len(waiting.outcome.state.attempts), 2)
            second_operator.approve("escalation-mission", approver_id="human-after-restart")

            third_operator = self.operator(SQLiteMissionStore(path))
            outcome = third_operator.resume("escalation-mission", now_epoch=120.0)

            final = self.operator(SQLiteMissionStore(path)).inspect("escalation-mission")
            self.assertEqual(outcome.acceptance.decision, AcceptanceDecision.ACCEPT)
            self.assertEqual(final.status, MissionStatus.ACCEPTED)
            self.assertEqual([item.attempt_number for item in final.outcome.state.attempts], [1, 2, 3])
            self.assertEqual(final.approval_record.approver_id, "human-after-restart")
            self.assertEqual(final.revision, 3)

    def test_existing_pre_runtime_human_approval_path_remains_unchanged(self):
        registry = OrchestratorRegistry()
        catalog = OrchestratorCatalog(registry)
        runtime = Runtime("pre-approved", status=ExecutionStatus.SUCCEEDED, result="ok")
        add_runtime(registry, catalog, runtime, rank=1)
        operator = MissionOperator(
            registry=registry,
            catalog=catalog,
            store=InMemoryMissionStore(),
        )
        policy = evaluate_policy(
            policy_bundle_id="policy-r7",
            allowed=True,
            require_human=True,
            reason="operator approval required",
        )
        mission = Mission("pre-runtime", "existing approval contract", frozenset({"workflow"}))

        waiting = operator.run(
            mission,
            policy=policy,
            budget=self.budget,
            acceptance_context=self.context,
            execution_id_prefix="pre-exec",
        )
        operator.approve("pre-runtime", approver_id="human-existing")
        outcome = operator.resume("pre-runtime", now_epoch=120.0)

        self.assertEqual(waiting.state.status, MissionStatus.WAITING_APPROVAL)
        self.assertEqual(outcome.acceptance.decision, AcceptanceDecision.ACCEPT)
        self.assertEqual(outcome.execution.execution_id, "pre-exec-1")
        self.assertEqual(runtime.calls, 1)


if __name__ == "__main__":
    unittest.main(verbosity=2)
