from __future__ import annotations

import subprocess
import tempfile
import unittest
from pathlib import Path

from metao.acceptance import AcceptanceContext, EvidenceEnvelope
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
    return subprocess.run(
        ["git", "-C", str(repo), *args],
        check=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
    ).stdout.strip()


def commit(repo: Path, filename: str, content: str, message: str) -> str:
    (repo / filename).write_text(content, encoding="utf-8")
    git(repo, "add", filename)
    git(repo, "commit", "-m", message)
    return git(repo, "rev-parse", "HEAD")


class GitExecutor:
    def __init__(self, repo: Path) -> None:
        self.repo = repo
        self.requests: list[ExecutionRequest] = []
        self._descriptor = OrchestratorDescriptor("executor-a", "1.0", frozenset({"code"}))

    @property
    def descriptor(self):
        return self._descriptor

    def health(self):
        return HealthReport(HealthStatus.HEALTHY)

    def execute(self, request: ExecutionRequest):
        self.requests.append(request)
        expected = str(request.context["repository_state_id"])
        if git(self.repo, "rev-parse", "HEAD") != expected:
            raise AssertionError("first executor was not bootstrapped to trusted checkpoint")
        head = commit(self.repo, "work.txt", "done\n", "complete work")
        return ExecutionResult(
            request.execution_id,
            "executor-a",
            ExecutionStatus.SUCCEEDED,
            output={
                "repository_state_id": head,
                "artifact_ref": f"git://repo-metao/{head}",
            },
        )

    def cancel(self, execution_id: str):
        pass


class Planner:
    def plan(self, objective):
        return WorkGraph("metao", (WorkUnit("work", "do work"),))

    def corrective_work(self, objective, failed_unit, verification, graph):
        return None


class Verifier:
    def verify(self, objective, unit, execution, checkpoint):
        return WorkVerificationResult(True, "project-verifier", "verify-evidence", "test-ref")


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
        provenance_root="issue-530",
        authority_id=request.context["authority_id"],
        passed=True,
        created_at_epoch=request.context["created_at_epoch"],
    )


class Issue530InitialCheckpointBootstrapIntegrationTests(unittest.TestCase):
    def test_divergent_first_executor_is_materialized_before_real_runner_dispatch(self):
        with tempfile.TemporaryDirectory() as root:
            root_path = Path(root)
            seed = root_path / "seed"
            executor_repo = root_path / "executor-a"
            seed.mkdir()
            git(seed, "init")
            git(seed, "config", "user.email", "metao@example.invalid")
            git(seed, "config", "user.name", "metaO")
            trusted_initial = commit(seed, "README.md", "seed\n", "seed")
            subprocess.run(
                ["git", "clone", str(seed), str(executor_repo)],
                check=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
            )
            git(executor_repo, "config", "user.email", "metao@example.invalid")
            git(executor_repo, "config", "user.name", "metaO")
            divergent = commit(executor_repo, "divergent.txt", "divergent\n", "divergent")
            self.assertNotEqual(divergent, trusted_initial)

            executor = GitExecutor(executor_repo)
            registry = OrchestratorRegistry()
            registry.register(executor)
            pool = OrchestratorPoolState(
                "executor-a",
                OrchestratorStatus.HEALTHY,
                frozenset({"code"}),
                success_rate=0.99,
                quality=0.99,
                reliability=0.99,
                cost=0.01,
            )
            scheduler = CanonicalProjectExecutorScheduler(
                pools=(pool,),
                requirements=(WorkUnitSchedulingRequirements("work", frozenset({"code"})),),
                registrations=(ExecutorProviderRegistration("executor-a", "provider-x"),),
                now_epoch=100.0,
            )
            runner = MissionControlPlaneWorkUnitRunner(
                registry=registry,
                pools=(pool,),
                normalizers={"executor-a": normalizer},
                policy_for=lambda objective, unit: evaluate_policy(policy_bundle_id="policy", allowed=True),
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
                initial_repo_path=seed,
                executor_repo_paths={"executor-a": executor_repo},
                repository_id="repo-metao",
            )

            result = supervise_project(
                objective=ProjectObjective("project-360", "req-360", "deliver"),
                planner=Planner(),
                scheduler=scheduler,
                runner=runner,
                repository=repository,
                verifier=Verifier(),
                initial_checkpoint_materializer=repository,
            )

            self.assertEqual(result.verdict, ProjectVerdict.PROJECT_ACCEPTED)
            self.assertEqual(len(executor.requests), 1)
            self.assertEqual(executor.requests[0].context["repository_state_id"], trusted_initial)
            kinds = tuple(event.kind for event in result.trace)
            self.assertLess(kinds.index(ProjectTraceKind.MATERIALIZED), kinds.index(ProjectTraceKind.DISPATCHED))
            self.assertEqual(kinds[-1], ProjectTraceKind.PROJECT_ACCEPTED)


if __name__ == "__main__":
    unittest.main()
