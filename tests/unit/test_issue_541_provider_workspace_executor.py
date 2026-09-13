from __future__ import annotations

import subprocess
import tempfile
import unittest
from pathlib import Path

from metao.capacity import CapacityObservation, CapacityStatus
from metao.core import (
    ExecutionRequest,
    ExecutionResult,
    ExecutionStatus,
    HealthReport,
    HealthStatus,
    Mission,
    OrchestratorDescriptor,
)
from metao.provider_workspace_executor import (
    LocalGitWorkProductApplier,
    ProviderWorkspaceOrchestratorAdapter,
    WorkProductUpdate,
)


def git(repo: Path, *args: str) -> str:
    return subprocess.run(
        ["git", "-C", str(repo), *args],
        check=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
    ).stdout.strip()


class Provider:
    def __init__(self, result_factory) -> None:
        self._result_factory = result_factory
        self.cancelled: list[str] = []
        self.calls = 0
        self._descriptor = OrchestratorDescriptor(
            "provider-adapter",
            "v1",
            frozenset({"workflow"}),
        )

    @property
    def descriptor(self):
        return self._descriptor

    def health(self):
        return HealthReport(HealthStatus.HEALTHY)

    def execute(self, request):
        self.calls += 1
        return self._result_factory(request)

    def cancel(self, execution_id):
        self.cancelled.append(execution_id)


class RecordingApplier:
    def __init__(self) -> None:
        self.calls = []

    def apply(self, request, *, provider_output):
        self.calls.append((request, dict(provider_output)))
        return WorkProductUpdate("a" * 40, "git://repo/" + "a" * 40, "applier:evidence")


class ProviderWorkspaceExecutorTests(unittest.TestCase):
    def request(self, state: str = "0" * 40):
        return ExecutionRequest(
            "execution-1",
            Mission("mission-1", "produce work"),
            {
                "work_unit_id": "prepare",
                "repository_state_id": state,
            },
        )

    def test_capacity_failure_passes_through_without_workspace_mutation(self):
        def result(request):
            return ExecutionResult(
                request.execution_id,
                "provider-adapter",
                ExecutionStatus.FAILED,
                error="rate limited",
                capacity_observation=CapacityObservation(
                    CapacityStatus.TEMPORARILY_RATE_LIMITED
                ),
            )

        provider = Provider(result)
        applier = RecordingApplier()
        adapter = ProviderWorkspaceOrchestratorAdapter(
            provider,
            applier,
            executor_id="executor-a",
        )
        observed = adapter.execute(self.request())
        self.assertEqual(observed.orchestrator_id, "executor-a")
        self.assertIs(observed.status, ExecutionStatus.FAILED)
        self.assertEqual(
            observed.capacity_observation.capacity_status,
            CapacityStatus.TEMPORARILY_RATE_LIMITED,
        )
        self.assertEqual(applier.calls, [])

    def test_provider_cannot_supply_reserved_repository_claims(self):
        def result(request):
            return ExecutionResult(
                request.execution_id,
                "provider-adapter",
                ExecutionStatus.SUCCEEDED,
                output={
                    "result": "provider work",
                    "repository_state_id": "f" * 40,
                    "artifact_ref": "git://evil/" + "f" * 40,
                    "evidence_ref": "provider-controlled",
                },
            )

        provider = Provider(result)
        applier = RecordingApplier()
        adapter = ProviderWorkspaceOrchestratorAdapter(
            provider,
            applier,
            executor_id="executor-a",
        )
        observed = adapter.execute(self.request())
        self.assertIs(observed.status, ExecutionStatus.SUCCEEDED)
        self.assertEqual(observed.output["repository_state_id"], "a" * 40)
        self.assertEqual(observed.output["artifact_ref"], "git://repo/" + "a" * 40)
        self.assertEqual(observed.output["evidence_ref"], "applier:evidence")
        self.assertEqual(applier.calls[0][1], {"result": "provider work"})

    def test_local_git_applier_requires_exact_checkpoint_and_commits_controlled_path(self):
        with tempfile.TemporaryDirectory() as root:
            repo = Path(root) / "repo"
            repo.mkdir()
            git(repo, "init")
            git(repo, "config", "user.email", "metao@example.invalid")
            git(repo, "config", "user.name", "metaO")
            (repo / "README.md").write_text("seed\n", encoding="utf-8")
            git(repo, "add", "README.md")
            git(repo, "commit", "-m", "seed")
            initial = git(repo, "rev-parse", "HEAD")

            applier = LocalGitWorkProductApplier(repo, "repo-metao")
            update = applier.apply(
                self.request(initial),
                provider_output={"result": "provider work"},
            )
            self.assertEqual(git(repo, "rev-parse", "HEAD"), update.repository_state_id)
            self.assertNotEqual(update.repository_state_id, initial)
            self.assertEqual(
                update.artifact_ref,
                f"git://repo-metao/{update.repository_state_id}",
            )
            artifact = repo / ".metao" / "work-products" / "prepare.json"
            self.assertTrue(artifact.is_file())
            self.assertIn("provider work", artifact.read_text(encoding="utf-8"))
            self.assertEqual(git(repo, "status", "--porcelain"), "")

    def test_local_git_applier_rejects_checkpoint_drift_before_mutation(self):
        with tempfile.TemporaryDirectory() as root:
            repo = Path(root) / "repo"
            repo.mkdir()
            git(repo, "init")
            git(repo, "config", "user.email", "metao@example.invalid")
            git(repo, "config", "user.name", "metaO")
            (repo / "README.md").write_text("seed\n", encoding="utf-8")
            git(repo, "add", "README.md")
            git(repo, "commit", "-m", "seed")
            actual = git(repo, "rev-parse", "HEAD")
            applier = LocalGitWorkProductApplier(repo, "repo-metao")
            with self.assertRaisesRegex(ValueError, "HEAD does not match"):
                applier.apply(
                    self.request("f" * 40 if actual != "f" * 40 else "e" * 40),
                    provider_output={"result": "must not be written"},
                )
            self.assertFalse((repo / ".metao").exists())


if __name__ == "__main__":
    unittest.main()
