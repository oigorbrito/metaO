from __future__ import annotations

from pathlib import Path
import subprocess
import tempfile
import unittest

from metao.git_checkpoint import GitRepositoryCheckpointPort
from metao.project_supervision import (
    ProjectObjective,
    WorkExecutionResult,
    WorkExecutionStatus,
    WorkUnit,
)


def git(repo: Path, *args: str) -> str:
    completed = subprocess.run(
        ["git", "-C", str(repo), *args],
        check=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
    )
    return completed.stdout.strip()


class Issue523GitCheckpointDriftTests(unittest.TestCase):
    def test_capture_rejects_executor_claim_that_does_not_match_host_head(self):
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
            checkpoint_port = GitRepositoryCheckpointPort(repo, "repo-metao")
            objective = ProjectObjective("project-360", "req-360", "deliver objective")
            initial = checkpoint_port.initial(objective)
            execution = WorkExecutionResult(
                "prepare",
                "executor-a",
                "provider-x",
                WorkExecutionStatus.SUCCEEDED,
                "0" * 40,
                f"git://repo-metao/{'0' * 40}",
            )

            with self.assertRaisesRegex(
                ValueError,
                "executor repository state does not match trusted Git HEAD",
            ):
                checkpoint_port.capture(
                    objective,
                    WorkUnit("prepare", "prepare repository"),
                    execution,
                )

            self.assertEqual(git(repo, "rev-parse", "HEAD"), initial.state_id)


if __name__ == "__main__":
    unittest.main()
