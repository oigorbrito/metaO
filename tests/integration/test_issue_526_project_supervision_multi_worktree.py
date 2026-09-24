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
from metao.executor_git_checkpoint import ExecutorGitCheckpointPort
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


def commit_file(repo: Path, name: str, content: str, message: str) -> str:
    (repo / name).write_text(content, encoding="utf-8")
    git(repo, "add", name)
    git(
        repo,
        "-c",
        "user.name=metaO integration",
        "-c",
        "user.email=metao@example.invalid",
        "commit",
        "-m",
        message,
    )
    return git(repo, "rev-parse", "HEAD")


class WorktreeOrchestrator:
    def __init__(
        self,
        orchestrator_id: str,
        repo: Path,
        *,
        capacity_failures: int = 0,
    ) -> None:
        self.requests: list[ExecutionRequest] = []
        self.repo = repo
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

        expected_checkpoint = request.context["repository_state_id"]
        observed_head = git(self.repo, "rev-parse", "HEAD")
        if observed_head != expected_checkpoint:
            raise AssertionError(
                f"executor worktree not transferred to checkpoint: {observed_head} != {expected_checkpoint}"
            )
        work_unit_id = request.context["work_unit_id"]
        head = commit_file(
            self.repo,
            f"{work_unit_id}.txt",
            f"{work_unit_id} by {self.descriptor.orchestrator_id}\n",
            f"{work_unit_id} via {self.descriptor.orchestrator_id}",
        )
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
        provenance_root="issue-526",
        authority_id=request.context["authority_id"],
        passed=True,
        created_at_epoch=request.context["created_at_epoch"],
    )


class Issue526ProjectSupervisionMultiWorktreeTests(unittest.TestCase):
    def test_capacity_failover_and_next_unit_cross_distinct_worktrees(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            seed = root / "seed"
            executor_a_repo = root / "executor-a"
            executor_c_repo = root / "executor-c"
            seed.mkdir()
            git(seed, "init")
            initial_head = commit_file(seed, "README.md", "initial\n", "initial")
            for destination in (executor_a_repo, executor_c_repo):
                subprocess.run(
                    ["git", "clone", str(seed), str(destination)],
                    check=True,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    text=True,
                )

            executor_a = WorktreeOrchestrator(
                "executor-a",
                executor_a_repo,
                capacity_failures=1,
            )
            executor_c = WorktreeOrchestrator("executor-c", executor_c_repo)
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
            repository = ExecutorGitCheckpointPort(
                seed,
                {
                    "executor-a": executor_a_repo,
                    "executor-c": executor_c_repo,
                },
                "repo-metao",
            )

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
            self.assertEqual(kinds.count(ProjectTraceKind.HANDED_OFF), 2)
            self.assertIn(ProjectTraceKind.FAILED_CAPACITY, kinds)
            self.assertEqual(kinds[-1], ProjectTraceKind.PROJECT_ACCEPTED)

            self.assertEqual(executor_c.requests[0].context["repository_state_id"], initial_head)
            prepare_head = executor_a.requests[1].context["repository_state_id"]
            self.assertNotEqual(prepare_head, initial_head)
            self.assertEqual(git(executor_a_repo, "rev-parse", "HEAD~1"), prepare_head)
            final_head = git(executor_a_repo, "rev-parse", "HEAD")
            self.assertEqual(result.trace[-1].repository_state_id, final_head)
            self.assertEqual(git(executor_c_repo, "rev-parse", "HEAD"), prepare_head)


if __name__ == "__main__":
    unittest.main()
