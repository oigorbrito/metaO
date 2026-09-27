from __future__ import annotations

import subprocess
import tempfile
import unittest
from pathlib import Path

from metao.executor_git_checkpoint import ExecutorGitCheckpointPort
from metao.project_supervision import ProjectObjective


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


class InitialCheckpointMaterializationGitTests(unittest.TestCase):
    def _repos(self):
        root = tempfile.TemporaryDirectory()
        root_path = Path(root.name)
        seed = root_path / "seed"
        executor = root_path / "executor"
        seed.mkdir()
        git(seed, "init")
        git(seed, "config", "user.email", "metao@example.invalid")
        git(seed, "config", "user.name", "metaO")
        commit(seed, "README.md", "seed\n", "seed")
        subprocess.run(
            ["git", "clone", str(seed), str(executor)],
            check=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        )
        git(executor, "config", "user.email", "metao@example.invalid")
        git(executor, "config", "user.name", "metaO")
        return root, seed, executor

    def test_materialize_replaces_clean_divergent_executor_head_with_exact_initial_checkpoint(self):
        root, seed, executor = self._repos()
        with root:
            port = ExecutorGitCheckpointPort(
                initial_repo_path=seed,
                executor_repo_paths={"executor-a": executor},
                repository_id="repo-metao",
            )
            checkpoint = port.initial(ProjectObjective("project-360", "req-360", "deliver"))
            divergent = commit(executor, "local.txt", "diverged\n", "diverge")
            self.assertNotEqual(divergent, checkpoint.state_id)

            materialized = port.materialize(checkpoint, to_executor_id="executor-a")

            self.assertEqual(materialized, checkpoint)
            self.assertEqual(git(executor, "rev-parse", "HEAD"), checkpoint.state_id)
            self.assertEqual(git(executor, "status", "--porcelain"), "")

    def test_dirty_destination_fails_before_materialization(self):
        root, seed, executor = self._repos()
        with root:
            port = ExecutorGitCheckpointPort(
                initial_repo_path=seed,
                executor_repo_paths={"executor-a": executor},
                repository_id="repo-metao",
            )
            checkpoint = port.initial(ProjectObjective("project-360", "req-360", "deliver"))
            original_head = git(executor, "rev-parse", "HEAD")
            (executor / "dirty.txt").write_text("dirty\n", encoding="utf-8")

            with self.assertRaisesRegex(ValueError, "clean worktree"):
                port.materialize(checkpoint, to_executor_id="executor-a")

            self.assertEqual(git(executor, "rev-parse", "HEAD"), original_head)

    def test_initial_source_head_movement_invalidates_materialization(self):
        root, seed, executor = self._repos()
        with root:
            port = ExecutorGitCheckpointPort(
                initial_repo_path=seed,
                executor_repo_paths={"executor-a": executor},
                repository_id="repo-metao",
            )
            checkpoint = port.initial(ProjectObjective("project-360", "req-360", "deliver"))
            commit(seed, "moved.txt", "moved\n", "move source")

            with self.assertRaisesRegex(ValueError, "source Git HEAD does not match checkpoint"):
                port.materialize(checkpoint, to_executor_id="executor-a")


if __name__ == "__main__":
    unittest.main()
