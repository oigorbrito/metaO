from __future__ import annotations

import unittest

from metao.acceptance import AcceptanceContext, EvidenceEnvelope
from metao.capacity import CapacityObservation, CapacityStatus
from metao.core import (
    ExecutionRequest,
    ExecutionResult,
    ExecutionStatus,
    HealthReport,
    HealthStatus,
    OrchestratorDescriptor,
    OrchestratorRegistry,
)
from metao.governance import AcceptanceBudget, evaluate_policy
from metao.project_runner import MissionControlPlaneWorkUnitRunner
from metao.project_supervision import (
    ExecutorTarget,
    ProjectObjective,
    RepositoryCheckpoint,
    WorkExecutionStatus,
    WorkUnit,
)
from metao.strategy import OrchestratorPoolState, OrchestratorStatus


class FakeOrchestrator:
    def __init__(
        self,
        orchestrator_id: str,
        *,
        status: ExecutionStatus = ExecutionStatus.SUCCEEDED,
        capacity_observation: CapacityObservation | None = None,
    ) -> None:
        self.requests: list[ExecutionRequest] = []
        self._status = status
        self._capacity_observation = capacity_observation
        self._descriptor = OrchestratorDescriptor(
            orchestrator_id,
            "1.0",
            frozenset({"workflow"}),
        )

    @property
    def descriptor(self) -> OrchestratorDescriptor:
        return self._descriptor

    def health(self) -> HealthReport:
        return HealthReport(HealthStatus.HEALTHY)

    def execute(self, request: ExecutionRequest) -> ExecutionResult:
        self.requests.append(request)
        output = (
            {
                "repository_state_id": "new-state",
                "artifact_ref": "git:new-state",
                "evidence_ref": "executor-evidence",
            }
            if self._status is ExecutionStatus.SUCCEEDED
            else {}
        )
        return ExecutionResult(
            request.execution_id,
            self.descriptor.orchestrator_id,
            self._status,
            output=output,
            error="runtime unavailable" if self._status is ExecutionStatus.FAILED else "",
            capacity_observation=self._capacity_observation,
        )

    def cancel(self, execution_id: str) -> None:
        pass


def pool(orchestrator_id: str, *, quality: float) -> OrchestratorPoolState:
    return OrchestratorPoolState(
        orchestrator_id,
        OrchestratorStatus.HEALTHY,
        frozenset({"workflow"}),
        success_rate=quality,
        quality=quality,
        reliability=quality,
        cost=0.01,
    )


def normalizer(*, passed: bool = True):
    def normalize(*, request, orchestrator_id, adapter_version, output, attempt_id):
        return EvidenceEnvelope(
            evidence_id=f"{request.execution_id}:{attempt_id}",
            obligation_id=request.context["obligation_id"],
            mission_id=request.mission.mission_id,
            execution_id=request.execution_id,
            orchestrator_id=orchestrator_id,
            adapter_version=adapter_version,
            attempt_id=attempt_id,
            subject_id=request.context["subject_id"],
            subject_state_id=request.context["subject_state_id"],
            verification_context_id=request.context["verification_context_id"],
            policy_bundle_id=request.context["policy_bundle_id"],
            verifier_id=request.context["verifier_id"],
            payload_digest="digest",
            provenance_root="issue-519",
            authority_id=request.context["authority_id"],
            passed=passed,
            created_at_epoch=request.context["created_at_epoch"],
        )

    return normalize


class Issue519ProjectWorkUnitRunnerTests(unittest.TestCase):
    def setUp(self) -> None:
        self.objective = ProjectObjective("project-360", "req-360", "ship project")
        self.unit = WorkUnit("wu-1", "implement work")
        self.checkpoint = RepositoryCheckpoint(
            "checkpoint-1",
            "repo-metao",
            "old-state",
            "git:old-state",
        )

    @staticmethod
    def _registry(*runtimes: FakeOrchestrator) -> OrchestratorRegistry:
        registry = OrchestratorRegistry()
        for runtime in runtimes:
            registry.register(runtime)
        return registry

    @staticmethod
    def _acceptance_context(
        objective: ProjectObjective,
        unit: WorkUnit,
        checkpoint: RepositoryCheckpoint,
    ) -> AcceptanceContext:
        return AcceptanceContext(
            subject_id=unit.work_unit_id,
            subject_state_id=checkpoint.state_id,
            verification_context_id=f"verify:{objective.project_id}:{unit.work_unit_id}",
            policy_bundle_id="policy",
            required_obligations=frozenset({"execution_result"}),
        )

    def _runner(
        self,
        *runtimes: FakeOrchestrator,
        passed: bool = True,
    ) -> MissionControlPlaneWorkUnitRunner:
        pools = tuple(
            pool(runtime.descriptor.orchestrator_id, quality=0.99 - index * 0.1)
            for index, runtime in enumerate(runtimes)
        )
        return MissionControlPlaneWorkUnitRunner(
            registry=self._registry(*runtimes),
            pools=pools,
            normalizers={
                runtime.descriptor.orchestrator_id: normalizer(passed=passed)
                for runtime in runtimes
            },
            policy_for=lambda objective, unit: evaluate_policy(
                policy_bundle_id="policy",
                allowed=True,
            ),
            budget_for=lambda objective, unit: AcceptanceBudget(10.0, 1000, 60.0, 2),
            acceptance_context_for=self._acceptance_context,
            now_epoch=100.0,
        )

    def test_runner_dispatches_only_scheduler_selected_executor_with_checkpoint_context(self):
        preferred = FakeOrchestrator("executor-a")
        selected = FakeOrchestrator("executor-b")
        runner = self._runner(preferred, selected)

        result = runner.run(
            self.objective,
            self.unit,
            ExecutorTarget("executor-b", "provider-y"),
            self.checkpoint,
        )

        self.assertEqual(result.status, WorkExecutionStatus.SUCCEEDED)
        self.assertEqual(result.executor_id, "executor-b")
        self.assertEqual(result.provider_id, "provider-y")
        self.assertEqual(result.repository_state_id, "new-state")
        self.assertEqual(result.artifact_ref, "git:new-state")
        self.assertEqual(preferred.requests, [])
        self.assertEqual(len(selected.requests), 1)
        request = selected.requests[0]
        self.assertEqual(request.context["project_id"], "project-360")
        self.assertEqual(request.context["work_unit_id"], "wu-1")
        self.assertEqual(request.context["checkpoint_id"], "checkpoint-1")
        self.assertEqual(request.context["repository_id"], "repo-metao")
        self.assertEqual(request.context["repository_state_id"], "old-state")
        self.assertEqual(request.context["artifact_ref"], "git:old-state")

    def test_capacity_failure_is_project_failover_signal_and_preserves_checkpoint(self):
        selected = FakeOrchestrator(
            "executor-a",
            status=ExecutionStatus.FAILED,
            capacity_observation=CapacityObservation(
                CapacityStatus.TEMPORARILY_RATE_LIMITED
            ),
        )
        runner = self._runner(selected)

        result = runner.run(
            self.objective,
            self.unit,
            ExecutorTarget("executor-a", "provider-x"),
            self.checkpoint,
        )

        self.assertEqual(result.status, WorkExecutionStatus.CAPACITY_FAILED)
        self.assertEqual(result.repository_state_id, "old-state")
        self.assertEqual(result.artifact_ref, "git:old-state")
        self.assertEqual(len(selected.requests), 1)

    def test_authentication_failure_does_not_masquerade_as_capacity_failover(self):
        selected = FakeOrchestrator(
            "executor-a",
            status=ExecutionStatus.FAILED,
            capacity_observation=CapacityObservation(CapacityStatus.AUTHENTICATION_FAILURE),
        )
        runner = self._runner(selected)

        result = runner.run(
            self.objective,
            self.unit,
            ExecutorTarget("executor-a", "provider-x"),
            self.checkpoint,
        )

        self.assertEqual(result.status, WorkExecutionStatus.FAILED)

    def test_mission_acceptance_failure_is_not_reported_as_success(self):
        selected = FakeOrchestrator("executor-a")
        runner = self._runner(selected, passed=False)

        result = runner.run(
            self.objective,
            self.unit,
            ExecutorTarget("executor-a", "provider-x"),
            self.checkpoint,
        )

        self.assertEqual(result.status, WorkExecutionStatus.FAILED)
        self.assertEqual(result.repository_state_id, "old-state")
        self.assertEqual(result.artifact_ref, "git:old-state")


if __name__ == "__main__":
    unittest.main()
