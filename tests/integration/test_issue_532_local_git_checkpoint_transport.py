from __future__ import annotations

import subprocess
import tempfile
import unittest
from pathlib import Path

from metao.git_checkpoint_transport import (
    EndpointGitCheckpointPort,
    GitRepositoryEndpoint,
    LocalGitRepositoryTransport,
)
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


class LocalGitCheckpointTransportIntegrationTests(unittest.TestCase):
    def test_materialize_and_handoff_preserve_exact_checkpoint_across_endpoints(self):
        with tempfile.TemporaryDirectory() as root:
            root_path = Path(root)
            seed = root_path / "seed"
            executor_a = root_path / "executor-a"
            executor_c = root_path / "executor-c"
            seed.mkdir()
            git(seed, "init")
            git(seed, "config", "user.email", "metao@example.invalid")
            git(seed, "config", "user.name", "metaO")
            initial_sha = commit(seed, "README.md", "seed\n", "seed")
            for destination in (executor_a, executor_c):
                subprocess.run(
                    ["git", "clone", str(seed), str(destination)],
                    check=True,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                )
                git(destination, "config", "user.email", "metao@example.invalid")
                git(destination, "config", "user.name", "metaO")

            divergent = commit(executor_a, "a.txt", "divergent\n", "divergent")
            self.assertNotEqual(divergent, initial_sha)

            port = EndpointGitCheckpointPort(
                initial_endpoint=GitRepositoryEndpoint("host", str(seed)),
                executor_endpoints={
                    "executor-a": GitRepositoryEndpoint("executor-a", str(executor_a)),
                    "executor-c": GitRepositoryEndpoint("executor-c", str(executor_c)),
                },
                repository_id="repo-metao",
                transport=LocalGitRepositoryTransport(),
            )
            checkpoint = port.initial(ProjectObjective("project-360", "req-360", "deliver"))
            self.assertEqual(checkpoint.state_id, initial_sha)

            port.materialize(checkpoint, to_executor_id="executor-a")
            self.assertEqual(git(executor_a, "rev-parse", "HEAD"), initial_sha)

            produced = commit(executor_a, "work.txt", "work\n", "work")
            produced_checkpoint = port._checkpoint(produced)
            port.handoff(
                produced_checkpoint,
                from_executor_id="executor-a",
                to_executor_id="executor-c",
            )
            self.assertEqual(git(executor_c, "rev-parse", "HEAD"), produced)
            self.assertEqual(git(executor_c, "status", "--porcelain"), "")


if __name__ == "__main__":
    unittest.main()
