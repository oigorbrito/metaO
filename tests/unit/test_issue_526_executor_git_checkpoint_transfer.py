from __future__ import annotations

from pathlib import Path
import subprocess
import tempfile
import unittest

from metao.executor_git_checkpoint import ExecutorGitCheckpointPort
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


def commit_file(repo: Path, name: str, content: str, message: str) -> str:
    (repo / name).write_text(content, encoding="utf-8")
    git(repo, "add", name)
    git(
        repo,
        "-c",
        "user.name=metaO test",
        "-c",
        "user.email=metao@example.invalid",
        "commit",
        "-m",
        message,
    )
    return git(repo, "rev-parse", "HEAD")


class Issue526ExecutorGitCheckpointTransferTests(unittest.TestCase):
    def _repos(self, root: Path) -> tuple[Path, Path, Path]:
        seed = root / "seed"
        executor_a = root / "executor-a"
        executor_c = root / "executor-c"
        seed.mkdir()
        git(seed, "init")
        commit_file(seed, "README.md", "initial\n", "initial")
        subprocess.run(
            ["git", "clone", str(seed), str(executor_a)],
            check=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
        )
        subprocess.run(
            ["git", "clone", str(seed), str(executor_c)],
            check=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
        )
        return seed, executor_a, executor_c

    def test_handoff_transfers_exact_checkpoint_to_distinct_executor_worktree(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            seed, executor_a, executor_c = self._repos(Path(temp_dir))
            port = ExecutorGitCheckpointPort(
                seed,
                {"executor-a": executor_a, "executor-c": executor_c},
                "repo-metao",
            )
            objective = ProjectObjective("project", "req", "deliver")
            initial = port.initial(objective)
            self.assertEqual(initial.state_id, git(seed, "rev-parse", "HEAD"))

            new_head = commit_file(executor_a, "prepare.txt", "prepared\n", "prepare")
            execution = WorkExecutionResult(
                "prepare",
                "executor-a",
                "provider-x",
                WorkExecutionStatus.SUCCEEDED,
                new_head,
                f"git://repo-metao/{new_head}",
            )
            checkpoint = port.capture(
                objective,
                WorkUnit("prepare", "prepare"),
                execution,
            )
            self.assertNotEqual(git(executor_c, "rev-parse", "HEAD"), checkpoint.state_id)

            handed = port.handoff(
                checkpoint,
                from_executor_id="executor-a",
                to_executor_id="executor-c",
            )

            self.assertEqual(handed, checkpoint)
            self.assertEqual(git(executor_c, "rev-parse", "HEAD"), checkpoint.state_id)
            self.assertEqual(git(executor_c, "status", "--porcelain"), "")

    def test_dirty_destination_fails_before_transfer(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            seed, executor_a, executor_c = self._repos(Path(temp_dir))
            port = ExecutorGitCheckpointPort(
                seed,
                {"executor-a": executor_a, "executor-c": executor_c},
                "repo-metao",
            )
            objective = ProjectObjective("project", "req", "deliver")
            new_head = commit_file(executor_a, "prepare.txt", "prepared\n", "prepare")
            checkpoint = port.capture(
                objective,
                WorkUnit("prepare", "prepare"),
                WorkExecutionResult(
                    "prepare",
                    "executor-a",
                    "provider-x",
                    WorkExecutionStatus.SUCCEEDED,
                    new_head,
                    f"git://repo-metao/{new_head}",
                ),
            )
            before = git(executor_c, "rev-parse", "HEAD")
            (executor_c / "dirty.txt").write_text("dirty\n", encoding="utf-8")

            with self.assertRaisesRegex(ValueError, "clean worktree"):
                port.handoff(
                    checkpoint,
                    from_executor_id="executor-a",
                    to_executor_id="executor-c",
                )

            self.assertEqual(git(executor_c, "rev-parse", "HEAD"), before)

    def test_source_head_must_match_checkpoint(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            seed, executor_a, executor_c = self._repos(Path(temp_dir))
            port = ExecutorGitCheckpointPort(
                seed,
                {"executor-a": executor_a, "executor-c": executor_c},
                "repo-metao",
            )
            objective = ProjectObjective("project", "req", "deliver")
            first_head = commit_file(executor_a, "prepare.txt", "prepared\n", "prepare")
            checkpoint = port.capture(
                objective,
                WorkUnit("prepare", "prepare"),
                WorkExecutionResult(
                    "prepare",
                    "executor-a",
                    "provider-x",
                    WorkExecutionStatus.SUCCEEDED,
                    first_head,
                    f"git://repo-metao/{first_head}",
                ),
            )
            commit_file(executor_a, "drift.txt", "drift\n", "drift")

            with self.assertRaisesRegex(ValueError, "source executor Git HEAD"):
                port.handoff(
                    checkpoint,
                    from_executor_id="executor-a",
                    to_executor_id="executor-c",
                )

    def test_unknown_executor_mapping_fails_closed(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            seed, executor_a, executor_c = self._repos(Path(temp_dir))
            port = ExecutorGitCheckpointPort(
                seed,
                {"executor-a": executor_a, "executor-c": executor_c},
                "repo-metao",
            )
            checkpoint = port.initial(ProjectObjective("project", "req", "deliver"))

            with self.assertRaisesRegex(ValueError, "unknown executor repository mapping"):
                port.handoff(
                    checkpoint,
                    from_executor_id="executor-missing",
                    to_executor_id="executor-c",
                )


if __name__ == "__main__":
    unittest.main()
