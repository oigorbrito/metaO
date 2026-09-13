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
from metao.project_scheduler import (
    CanonicalProjectExecutorScheduler,
    ExecutorProviderRegistration,
    WorkUnitSchedulingRequirements,
)
from metao.project_supervision import (
    ProjectObjective,
    ProjectTraceKind,
    ProjectVerdict,
    RepositoryCheckpoint,
    WorkGraph,
    WorkUnit,
    WorkVerificationResult,
    supervise_project,
)
from metao.strategy import OrchestratorPoolState, OrchestratorStatus


class ScriptedOrchestrator:
    def __init__(self, orchestrator_id: str, script: list[ExecutionResult]) -> None:
        self.requests: list[ExecutionRequest] = []
        self._script = list(script)
        self._descriptor = OrchestratorDescriptor(
            orchestrator_id,
            "1.0",
            frozenset({"code"}),
        )

    @property
    def descriptor(self) -> OrchestratorDescriptor:
        return self._descriptor

    def health(self) -> HealthReport:
        return HealthReport(HealthStatus.HEALTHY)

    def execute(self, request: ExecutionRequest) -> ExecutionResult:
        self.requests.append(request)
        if not self._script:
            raise AssertionError(f"unexpected execution for {self.descriptor.orchestrator_id}")
        template = self._script.pop(0)
        return ExecutionResult(
            request.execution_id,
            self.descriptor.orchestrator_id,
            template.status,
            output=template.output,
            error=template.error,
            capacity_observation=template.capacity_observation,
        )

    def cancel(self, execution_id: str) -> None:
        pass


class Planner:
    def plan(self, objective: ProjectObjective) -> WorkGraph:
        return WorkGraph(
            "metao",
            (
                WorkUnit("prepare", "prepare repository"),
                WorkUnit("implement", "implement objective", dependencies=("prepare",)),
            ),
        )

    def corrective_work(self, objective, failed_unit, verification, graph):
        raise AssertionError("corrective work is not expected in this integration slice")


class RepositoryBoundary:
    def __init__(self) -> None:
        self.handoffs: list[tuple[str, str, str]] = []
        self.captures = 0

    def initial(self, objective: ProjectObjective) -> RepositoryCheckpoint:
        return RepositoryCheckpoint("checkpoint-0", "repo-metao", "state-0", "git:state-0")

    def capture(self, objective, unit, execution) -> RepositoryCheckpoint:
        self.captures += 1
        return RepositoryCheckpoint(
            f"checkpoint-{self.captures}",
            "repo-metao",
            execution.repository_state_id,
            execution.artifact_ref,
        )

    def handoff(self, checkpoint, *, from_executor_id, to_executor_id):
        self.handoffs.append(
            (checkpoint.checkpoint_id, from_executor_id, to_executor_id)
        )
        return checkpoint


class IndependentVerifier:
    def verify(self, objective, unit, execution, checkpoint):
        return WorkVerificationResult(
            True,
            "project-verifier",
            f"evidence:{unit.work_unit_id}:{checkpoint.state_id}",
            f"test:{unit.work_unit_id}",
        )


def pool(orchestrator_id: str, quality: float) -> OrchestratorPoolState:
    return OrchestratorPoolState(
        orchestrator_id,
        OrchestratorStatus.HEALTHY,
        frozenset({"code"}),
        success_rate=quality,
        quality=quality,
        reliability=quality,
        cost=0.01,
    )


def normalizer(*, request, orchestrator_id, adapter_version, output, attempt_id):
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
        provenance_root="issue-521",
        authority_id=request.context["authority_id"],
        passed=True,
        created_at_epoch=request.context["created_at_epoch"],
    )


class Issue521ProjectSupervisionRealBridgeTests(unittest.TestCase):
    def test_provider_diverse_handoff_and_dependency_progress_use_real_bridge(self):
        executor_a = ScriptedOrchestrator(
            "executor-a",
            [
                ExecutionResult(
                    "template-a1",
                    "executor-a",
                    ExecutionStatus.FAILED,
                    error="rate limited",
                    capacity_observation=CapacityObservation(
                        CapacityStatus.TEMPORARILY_RATE_LIMITED
                    ),
                ),
                ExecutionResult(
                    "template-a2",
                    "executor-a",
                    ExecutionStatus.SUCCEEDED,
                    output={
                        "repository_state_id": "state-2",
                        "artifact_ref": "git:state-2",
                    },
                ),
            ],
        )
        executor_c = ScriptedOrchestrator(
            "executor-c",
            [
                ExecutionResult(
                    "template-c1",
                    "executor-c",
                    ExecutionStatus.SUCCEEDED,
                    output={
                        "repository_state_id": "state-1",
                        "artifact_ref": "git:state-1",
                    },
                )
            ],
        )
        registry = OrchestratorRegistry()
        registry.register(executor_a)
        registry.register(executor_c)
        pools = (pool("executor-a", 0.99), pool("executor-c", 0.80))
        scheduler = CanonicalProjectExecutorScheduler(
            pools=pools,
            requirements=(
                WorkUnitSchedulingRequirements("prepare", frozenset({"code"})),
                WorkUnitSchedulingRequirements("implement", frozenset({"code"})),
            ),
            registrations=(
                ExecutorProviderRegistration("executor-a", "provider-x"),
                ExecutorProviderRegistration("executor-c", "provider-y"),
            ),
            provider_diverse_failover=True,
            now_epoch=100.0,
        )
        runner = MissionControlPlaneWorkUnitRunner(
            registry=registry,
            pools=pools,
            normalizers={"executor-a": normalizer, "executor-c": normalizer},
            policy_for=lambda objective, unit: evaluate_policy(
                policy_bundle_id="policy",
                allowed=True,
            ),
            budget_for=lambda objective, unit: AcceptanceBudget(10.0, 1000, 60.0, 2),
            acceptance_context_for=lambda objective, unit, checkpoint: AcceptanceContext(
                subject_id=unit.work_unit_id,
                subject_state_id=checkpoint.state_id,
                verification_context_id=f"verify:{objective.project_id}:{unit.work_unit_id}",
                policy_bundle_id="policy",
                required_obligations=frozenset({"execution_result"}),
            ),
            now_epoch=100.0,
        )
        repository = RepositoryBoundary()

        result = supervise_project(
            objective=ProjectObjective("project-360", "req-360", "deliver objective"),
            planner=Planner(),
            scheduler=scheduler,
            runner=runner,
            repository=repository,
            verifier=IndependentVerifier(),
            max_executor_attempts_per_unit=3,
        )

        self.assertEqual(result.verdict, ProjectVerdict.PROJECT_ACCEPTED)
        self.assertEqual(result.executors_used, frozenset({"executor-a", "executor-c"}))
        self.assertEqual(result.providers_used, frozenset({"provider-x", "provider-y"}))
        self.assertEqual(
            repository.handoffs,
            [("checkpoint-0", "executor-a", "executor-c")],
        )
        kinds = tuple(event.kind for event in result.trace)
        self.assertIn(ProjectTraceKind.FAILED_CAPACITY, kinds)
        self.assertIn(ProjectTraceKind.HANDED_OFF, kinds)
        self.assertEqual(kinds[-1], ProjectTraceKind.PROJECT_ACCEPTED)
        self.assertEqual(
            [(record.work_unit_id, record.verdict) for record in result.traceability],
            [("prepare", "PASS"), ("implement", "PASS")],
        )

        self.assertEqual(len(executor_c.requests), 1)
        self.assertEqual(
            executor_c.requests[0].context["repository_state_id"],
            "state-0",
        )
        self.assertEqual(len(executor_a.requests), 2)
        self.assertEqual(
            executor_a.requests[1].context["repository_state_id"],
            "state-1",
        )
        self.assertEqual(
            executor_a.requests[1].context["work_unit_id"],
            "implement",
        )


if __name__ == "__main__":
    unittest.main()
