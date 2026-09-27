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


def _git(repo: Path, *args: str) -> str:
    completed = subprocess.run(
        ["git", "-C", str(repo), *args],
        check=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
    )
    return completed.stdout.strip()


class Issue512GitProjectCheckpointTests(unittest.TestCase):
    def setUp(self) -> None:
        self.tempdir = tempfile.TemporaryDirectory()
        self.repo = Path(self.tempdir.name)
        _git(self.repo, "init")
        _git(self.repo, "config", "user.email", "fixture@example.invalid")
        _git(self.repo, "config", "user.name", "Fixture")
        (self.repo / "project.txt").write_text("root\n")
        _git(self.repo, "add", "project.txt")
        _git(self.repo, "commit", "-m", "root")
        self.objective = ProjectObjective("project-512", "req-512", "checkpoint a real Git repository")
        self.unit = WorkUnit("work-512", "write repository change")
        self.port = GitRepositoryCheckpointPort(self.repo, "repo-512")

    def tearDown(self) -> None:
        self.tempdir.cleanup()

    def _head(self) -> str:
        return _git(self.repo, "rev-parse", "HEAD")

    def _artifact(self, head: str) -> str:
        return f"git://repo-512/{head}"

    def _commit(self, text: str, message: str) -> str:
        (self.repo / "project.txt").write_text(text)
        _git(self.repo, "add", "project.txt")
        _git(self.repo, "commit", "-m", message)
        return self._head()

    def test_initial_checkpoint_binds_trusted_clean_head(self):
        head = self._head()
        checkpoint = self.port.initial(self.objective)
        self.assertEqual(checkpoint.repository_id, "repo-512")
        self.assertEqual(checkpoint.state_id, head)
        self.assertEqual(checkpoint.artifact_ref, self._artifact(head))

    def test_capture_binds_new_committed_head(self):
        head = self._commit("change\n", "change")
        execution = WorkExecutionResult(
            self.unit.work_unit_id,
            "executor-a",
            "provider-a",
            WorkExecutionStatus.SUCCEEDED,
            head,
            artifact_ref=self._artifact(head),
            evidence_ref="execution://512",
        )
        checkpoint = self.port.capture(self.objective, self.unit, execution)
        self.assertEqual(checkpoint.state_id, head)
        self.assertEqual(checkpoint.artifact_ref, self._artifact(head))

    def test_capture_rejects_executor_reported_wrong_state(self):
        head = self._head()
        execution = WorkExecutionResult(
            self.unit.work_unit_id,
            "executor-a",
            "provider-a",
            WorkExecutionStatus.SUCCEEDED,
            "0" * len(head),
            artifact_ref=self._artifact(head),
        )
        with self.assertRaisesRegex(ValueError, "does not match trusted Git HEAD"):
            self.port.capture(self.objective, self.unit, execution)

    def test_capture_rejects_executor_reported_wrong_artifact(self):
        head = self._head()
        execution = WorkExecutionResult(
            self.unit.work_unit_id,
            "executor-a",
            "provider-a",
            WorkExecutionStatus.SUCCEEDED,
            head,
            artifact_ref="git://repo-512/forged",
        )
        with self.assertRaisesRegex(ValueError, "artifact ref"):
            self.port.capture(self.objective, self.unit, execution)

    def test_dirty_worktree_is_not_a_checkpoint_boundary(self):
        (self.repo / "project.txt").write_text("dirty\n")
        with self.assertRaisesRegex(ValueError, "clean worktree"):
            self.port.initial(self.objective)

    def test_handoff_rejects_head_movement_after_checkpoint(self):
        checkpoint = self.port.initial(self.objective)
        self._commit("moved\n", "move")
        with self.assertRaisesRegex(ValueError, "HEAD moved"):
            self.port.handoff(
                checkpoint,
                from_executor_id="executor-a",
                to_executor_id="executor-b",
            )

    def test_handoff_returns_exact_checkpoint_when_state_is_unchanged(self):
        checkpoint = self.port.initial(self.objective)
        handed = self.port.handoff(
            checkpoint,
            from_executor_id="executor-a",
            to_executor_id="executor-b",
        )
        self.assertIs(handed, checkpoint)
        self.assertEqual(handed, checkpoint)


if __name__ == "__main__":
    unittest.main(verbosity=2)
