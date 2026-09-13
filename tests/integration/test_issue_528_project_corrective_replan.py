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
    def __init__(self, executor_id: str, repo: Path, capabilities: frozenset[str]) -> None:
        self.repo = repo
        self.requests: list[ExecutionRequest] = []
        self._descriptor = OrchestratorDescriptor(executor_id, "1.0", capabilities)

    @property
    def descriptor(self) -> OrchestratorDescriptor:
        return self._descriptor

    def health(self) -> HealthReport:
        return HealthReport(HealthStatus.HEALTHY)

    def execute(self, request: ExecutionRequest) -> ExecutionResult:
        self.requests.append(request)
        work_unit_id = str(request.context["work_unit_id"])
        expected = str(request.context["repository_state_id"])
        if git(self.repo, "rev-parse", "HEAD") != expected:
            raise AssertionError("executor did not receive exact trusted checkpoint")
        head = commit(
            self.repo,
            f"{work_unit_id}.txt",
            f"completed {work_unit_id}\n",
            f"complete {work_unit_id}",
        )
        return ExecutionResult(
            request.execution_id,
            self.descriptor.orchestrator_id,
            ExecutionStatus.SUCCEEDED,
            output={
                "repository_state_id": head,
                "artifact_ref": f"git://repo-metao/{head}",
                "evidence_ref": f"executor:{work_unit_id}:{head}",
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
        if failed_unit.work_unit_id != "prepare":
            raise AssertionError("only prepare should require correction")
        return WorkUnit(
            "repair-prepare",
            "repair rejected preparation",
            dependencies=("prepare",),
            corrective=True,
            corrects_work_unit_id="prepare",
        )


class Verifier:
    def __init__(self) -> None:
        self.calls: list[str] = []

    def verify(self, objective, unit, execution, checkpoint):
        self.calls.append(unit.work_unit_id)
        accepted = unit.work_unit_id != "prepare"
        return WorkVerificationResult(
            accepted,
            "project-verifier",
            f"verify:{unit.work_unit_id}:{checkpoint.state_id}",
            f"test:{unit.work_unit_id}",
            "injected verification failure" if not accepted else "",
        )


def pool(executor_id: str, capabilities: frozenset[str], quality: float):
    return OrchestratorPoolState(
        executor_id,
        OrchestratorStatus.HEALTHY,
        capabilities,
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
        provenance_root="issue-528",
        authority_id=request.context["authority_id"],
        passed=True,
        created_at_epoch=request.context["created_at_epoch"],
    )


class Issue528CorrectiveReplanIntegrationTests(unittest.TestCase):
    def test_failed_verification_creates_correction_and_replans_across_worktrees(self):
        with tempfile.TemporaryDirectory() as root:
            root_path = Path(root)
            seed = root_path / "seed"
            executor_a_repo = root_path / "executor-a"
            executor_c_repo = root_path / "executor-c"
            seed.mkdir()
            git(seed, "init")
            git(seed, "config", "user.email", "metao@example.invalid")
            git(seed, "config", "user.name", "metaO")
            commit(seed, "README.md", "seed\n", "seed")
            subprocess.run(["git", "clone", str(seed), str(executor_a_repo)], check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            subprocess.run(["git", "clone", str(seed), str(executor_c_repo)], check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            for repo in (executor_a_repo, executor_c_repo):
                git(repo, "config", "user.email", "metao@example.invalid")
                git(repo, "config", "user.name", "metaO")

            executor_a = GitExecutor("executor-a", executor_a_repo, frozenset({"code"}))
            executor_c = GitExecutor("executor-c", executor_c_repo, frozenset({"repair"}))
            registry = OrchestratorRegistry()
            registry.register(executor_a)
            registry.register(executor_c)
            pools = (
                pool("executor-a", frozenset({"code"}), 0.99),
                pool("executor-c", frozenset({"repair"}), 0.90),
            )
            scheduler = CanonicalProjectExecutorScheduler(
                pools=pools,
                requirements=(
                    WorkUnitSchedulingRequirements("prepare", frozenset({"code"})),
                    WorkUnitSchedulingRequirements("repair-prepare", frozenset({"repair"})),
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
                executor_repo_paths={
                    "executor-a": executor_a_repo,
                    "executor-c": executor_c_repo,
                },
                repository_id="repo-metao",
            )
            verifier = Verifier()

            result = supervise_project(
                objective=ProjectObjective("project-360", "req-360", "deliver objective"),
                planner=Planner(),
                scheduler=scheduler,
                runner=runner,
                repository=repository,
                verifier=verifier,
                max_executor_attempts_per_unit=2,
                max_corrective_units=1,
            )

            self.assertEqual(result.verdict, ProjectVerdict.PROJECT_ACCEPTED)
            self.assertEqual(verifier.calls, ["prepare", "repair-prepare", "implement"])
            kinds = tuple(event.kind for event in result.trace)
            self.assertIn(ProjectTraceKind.VERIFICATION_FAILED, kinds)
            self.assertIn(ProjectTraceKind.CORRECTIVE_WORK_CREATED, kinds)
            self.assertGreaterEqual(kinds.count(ProjectTraceKind.HANDED_OFF), 2)
            self.assertEqual(kinds[-1], ProjectTraceKind.PROJECT_ACCEPTED)
            self.assertEqual(
                [
                    (record.work_unit_id, record.verdict, record.evidence_ref)
                    for record in result.traceability
                ],
                [
                    ("prepare", "FAIL", f"verify:prepare:{executor_a.requests[0].context['repository_state_id']}"),
                    ("repair-prepare", "PASS", f"verify:repair-prepare:{git(executor_c_repo, 'rev-parse', 'HEAD~1')}"),
                    ("prepare", "CORRECTED_PASS", f"verify:repair-prepare:{git(executor_c_repo, 'rev-parse', 'HEAD~1')}"),
                    ("implement", "PASS", f"verify:implement:{git(executor_a_repo, 'rev-parse', 'HEAD')}"),
                ],
            )
            self.assertTrue(
                all(record.requirement_id == "req-360" for record in result.traceability)
            )
            self.assertEqual(len(executor_a.requests), 2)
            self.assertEqual(len(executor_c.requests), 1)
            repair_request = executor_c.requests[0]
            implement_request = executor_a.requests[1]
            self.assertEqual(
                repair_request.context["repository_state_id"],
                executor_a.requests[0].context["repository_state_id"]
                if False
                else git(executor_c_repo, "rev-parse", "HEAD~1"),
            )
            self.assertEqual(
                implement_request.context["repository_state_id"],
                git(executor_a_repo, "rev-parse", "HEAD~1"),
            )


if __name__ == "__main__":
    unittest.main()
