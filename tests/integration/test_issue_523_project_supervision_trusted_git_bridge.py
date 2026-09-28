from __future__ import annotations

from pathlib import Path
import subprocess
import tempfile
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
from metao.git_checkpoint import GitRepositoryCheckpointPort
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
    WorkGraph,
    WorkUnit,
    WorkVerificationResult,
    supervise_project,
)
from metao.strategy import OrchestratorPoolState, OrchestratorStatus


def git(repo: Path, *args: str) -> str:
    completed = subprocess.run(
        ["git", "-C", str(repo), *args],
        check=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
    )
    return completed.stdout.strip()


class GitMutatingOrchestrator:
    def __init__(
        self,
        orchestrator_id: str,
        repo: Path,
        *,
        capacity_failures: int = 0,
    ) -> None:
        self.requests: list[ExecutionRequest] = []
        self._repo = repo
        self._capacity_failures = capacity_failures
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
        if self._capacity_failures:
            self._capacity_failures -= 1
            return ExecutionResult(
                request.execution_id,
                self.descriptor.orchestrator_id,
                ExecutionStatus.FAILED,
                error="rate limited",
                capacity_observation=CapacityObservation(
                    CapacityStatus.TEMPORARILY_RATE_LIMITED
                ),
            )

        work_unit_id = request.context["work_unit_id"]
        path = self._repo / f"{work_unit_id}.txt"
        path.write_text(
            f"{work_unit_id} by {self.descriptor.orchestrator_id}\n",
            encoding="utf-8",
        )
        git(self._repo, "add", path.name)
        git(
            self._repo,
            "-c",
            "user.name=metaO integration",
            "-c",
            "user.email=metao@example.invalid",
            "commit",
            "-m",
            f"{work_unit_id} via {self.descriptor.orchestrator_id}",
        )
        head = git(self._repo, "rev-parse", "HEAD")
        repository_id = request.context["repository_id"]
        return ExecutionResult(
            request.execution_id,
            self.descriptor.orchestrator_id,
            ExecutionStatus.SUCCEEDED,
            output={
                "repository_state_id": head,
                "artifact_ref": f"git://{repository_id}/{head}",
            },
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
        raise AssertionError("corrective work is not expected")


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
        provenance_root="issue-523",
        authority_id=request.context["authority_id"],
        passed=True,
        created_at_epoch=request.context["created_at_epoch"],
    )


class Issue523ProjectSupervisionTrustedGitBridgeTests(unittest.TestCase):
    def test_provider_failover_handoff_and_progress_use_trusted_git_state(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            repo = Path(temp_dir)
            git(repo, "init")
            (repo / "README.md").write_text("initial\n", encoding="utf-8")
            git(repo, "add", "README.md")
            git(
                repo,
                "-c",
                "user.name=metaO integration",
                "-c",
                "user.email=metao@example.invalid",
                "commit",
                "-m",
                "initial",
            )
            initial_head = git(repo, "rev-parse", "HEAD")

            executor_a = GitMutatingOrchestrator(
                "executor-a",
                repo,
                capacity_failures=1,
            )
            executor_c = GitMutatingOrchestrator("executor-c", repo)
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
            repository = GitRepositoryCheckpointPort(repo, "repo-metao")

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
            self.assertEqual(
                result.providers_used,
                frozenset({"provider-x", "provider-y"}),
            )
            kinds = tuple(event.kind for event in result.trace)
            self.assertIn(ProjectTraceKind.FAILED_CAPACITY, kinds)
            self.assertIn(ProjectTraceKind.HANDED_OFF, kinds)
            self.assertEqual(kinds[-1], ProjectTraceKind.PROJECT_ACCEPTED)

            self.assertEqual(len(executor_c.requests), 1)
            self.assertEqual(
                executor_c.requests[0].context["repository_state_id"],
                initial_head,
            )
            prepare_head = git(repo, "rev-parse", "HEAD~1")
            self.assertNotEqual(prepare_head, initial_head)
            self.assertEqual(len(executor_a.requests), 2)
            self.assertEqual(
                executor_a.requests[1].context["repository_state_id"],
                prepare_head,
            )
            final_head = git(repo, "rev-parse", "HEAD")
            self.assertNotEqual(final_head, prepare_head)
            self.assertEqual(
                result.trace[-1].repository_state_id,
                final_head,
            )


if __name__ == "__main__":
    unittest.main()
