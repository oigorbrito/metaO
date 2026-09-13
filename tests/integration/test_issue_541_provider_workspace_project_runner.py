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
from metao.git_checkpoint import GitRepositoryCheckpointPort
from metao.governance import AcceptanceBudget, evaluate_policy
from metao.project_runner import MissionControlPlaneWorkUnitRunner
from metao.project_supervision import ExecutorTarget, ProjectObjective, WorkExecutionStatus, WorkUnit
from metao.provider_workspace_executor import (
    LocalGitWorkProductApplier,
    ProviderWorkspaceOrchestratorAdapter,
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


class SuccessfulProvider:
    def __init__(self) -> None:
        self._descriptor = OrchestratorDescriptor(
            "provider-adapter",
            "provider-v1",
            frozenset({"workflow"}),
        )

    @property
    def descriptor(self):
        return self._descriptor

    def health(self):
        return HealthReport(HealthStatus.HEALTHY)

    def execute(self, request: ExecutionRequest):
        return ExecutionResult(
            request.execution_id,
            self.descriptor.orchestrator_id,
            ExecutionStatus.SUCCEEDED,
            output={"result": "provider-backed work product"},
        )

    def cancel(self, execution_id: str):
        pass


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
        provenance_root="issue-541",
        authority_id=request.context["authority_id"],
        passed=True,
        created_at_epoch=request.context["created_at_epoch"],
    )


class ProviderWorkspaceProjectRunnerIntegrationTests(unittest.TestCase):
    def test_provider_success_is_applied_then_reobserved_by_git_checkpoint_port(self):
        with tempfile.TemporaryDirectory() as root:
            repo = Path(root) / "repo"
            repo.mkdir()
            git(repo, "init")
            git(repo, "config", "user.email", "metao@example.invalid")
            git(repo, "config", "user.name", "metaO")
            (repo / "README.md").write_text("seed\n", encoding="utf-8")
            git(repo, "add", "README.md")
            git(repo, "commit", "-m", "seed")

            provider = SuccessfulProvider()
            executor = ProviderWorkspaceOrchestratorAdapter(
                provider,
                LocalGitWorkProductApplier(repo, "repo-metao"),
                executor_id="executor-a",
                capabilities=frozenset({"code"}),
            )
            registry = OrchestratorRegistry()
            registry.register(executor)
            pool = OrchestratorPoolState(
                "executor-a",
                OrchestratorStatus.HEALTHY,
                frozenset({"code"}),
                success_rate=1.0,
                quality=1.0,
                reliability=1.0,
                cost=0.01,
            )
            runner = MissionControlPlaneWorkUnitRunner(
                registry=registry,
                pools=(pool,),
                normalizers={"executor-a": normalizer},
                policy_for=lambda objective, unit: evaluate_policy(
                    policy_bundle_id="policy",
                    allowed=True,
                ),
                budget_for=lambda objective, unit: AcceptanceBudget(10.0, 1000, 60.0, 1),
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
            objective = ProjectObjective("project-360", "req-360", "produce artifact")
            unit = WorkUnit("prepare", "prepare provider-backed artifact")
            checkpoint = repository.initial(objective)

            execution = runner.run(
                objective,
                unit,
                ExecutorTarget("executor-a", "provider-x"),
                checkpoint,
            )
            self.assertIs(execution.status, WorkExecutionStatus.SUCCEEDED)
            self.assertNotEqual(execution.repository_state_id, checkpoint.state_id)
            captured = repository.capture(objective, unit, execution)
            self.assertEqual(captured.state_id, execution.repository_state_id)
            self.assertEqual(captured.artifact_ref, execution.artifact_ref)
            self.assertEqual(git(repo, "rev-parse", "HEAD"), captured.state_id)
            self.assertTrue((repo / ".metao" / "work-products" / "prepare.json").is_file())


if __name__ == "__main__":
    unittest.main()
