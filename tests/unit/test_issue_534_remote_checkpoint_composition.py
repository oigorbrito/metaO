from __future__ import annotations

import unittest
from pathlib import Path

from metao.git_checkpoint_transport import EndpointGitCheckpointPort
from metao.project_supervision import (
    ProjectObjective,
    WorkExecutionResult,
    WorkExecutionStatus,
    WorkUnit,
)
from metao.ssh_git_transport import SshGitRepositoryEndpoint, SshGitRepositoryTransport


SHA_0 = "0" * 40
SHA_1 = "1" * 40


class MemorySshExecutor:
    def __init__(self) -> None:
        self.head = {"host": SHA_0, "executor-a": SHA_1}
        self.commits = {"host": {SHA_0}, "executor-a": {SHA_1}}
        self.fetch_head: dict[str, str] = {}
        self.bundle_upload: dict[str, bytes] = {}

    def run(self, endpoint: SshGitRepositoryEndpoint, argv: tuple[str, ...]) -> bytes:
        endpoint_id = endpoint.endpoint_id
        if argv[0] == "mktemp":
            return b"/tmp/metao-checkpoint.Z9Y8X7.bundle\n"
        if argv[0] == "rm":
            return b""
        args = argv[3:]
        if args == ("rev-parse", "--is-inside-work-tree"):
            return b"true\n"
        if args == ("status", "--porcelain", "--untracked-files=normal"):
            return b""
        if args == ("rev-parse", "HEAD"):
            return f"{self.head[endpoint_id]}\n".encode()
        if args == ("rev-parse", "FETCH_HEAD"):
            return f"{self.fetch_head[endpoint_id]}\n".encode()
        if args[:2] == ("cat-file", "-e"):
            commit_id = args[2].split("^{commit}", 1)[0]
            if commit_id not in self.commits[endpoint_id]:
                raise ValueError("missing commit")
            return b""
        if args == ("bundle", "create", "-", "HEAD"):
            return f"bundle:{self.head[endpoint_id]}".encode()
        if args[:2] == ("fetch", "--no-tags"):
            payload = self.bundle_upload[endpoint_id].decode()
            commit_id = payload.split(":", 1)[1]
            self.commits[endpoint_id].add(commit_id)
            self.fetch_head[endpoint_id] = commit_id
            return b""
        if args[:2] == ("reset", "--hard"):
            self.head[endpoint_id] = args[2]
            return b""
        raise AssertionError(argv)

    def copy_to(
        self,
        endpoint: SshGitRepositoryEndpoint,
        local_path: Path,
        remote_path: str,
    ) -> None:
        del remote_path
        self.bundle_upload[endpoint.endpoint_id] = local_path.read_bytes()


def remote(endpoint_id: str) -> SshGitRepositoryEndpoint:
    return SshGitRepositoryEndpoint(
        endpoint_id,
        f"/srv/metao/{endpoint_id}",
        host=f"{endpoint_id}.example.internal",
        username="metao",
        known_hosts_file="/etc/metao/known_hosts",
    )


class RemoteCheckpointCompositionTests(unittest.TestCase):
    def test_initial_checkpoint_materialization_remains_checkpoint_authority_owned(self):
        executor = MemorySshExecutor()
        port = EndpointGitCheckpointPort(
            initial_endpoint=remote("host"),
            executor_endpoints={"executor-a": remote("executor-a")},
            repository_id="repo-metao",
            transport=SshGitRepositoryTransport(executor),
        )
        objective = ProjectObjective("project-360", "req-360", "deliver")

        checkpoint = port.initial(objective)
        self.assertEqual(checkpoint.state_id, SHA_0)
        self.assertEqual(checkpoint.artifact_ref, f"git://repo-metao/{SHA_0}")
        materialized = port.materialize(checkpoint, to_executor_id="executor-a")

        self.assertEqual(materialized, checkpoint)
        self.assertEqual(executor.head["executor-a"], SHA_0)

    def test_capture_rejects_executor_claim_that_differs_from_remote_observation(self):
        executor = MemorySshExecutor()
        executor.head["executor-a"] = SHA_0
        executor.commits["executor-a"].add(SHA_0)
        port = EndpointGitCheckpointPort(
            initial_endpoint=remote("host"),
            executor_endpoints={"executor-a": remote("executor-a")},
            repository_id="repo-metao",
            transport=SshGitRepositoryTransport(executor),
        )

        execution = WorkExecutionResult(
            work_unit_id="unit-1",
            executor_id="executor-a",
            provider_id="provider-x",
            status=WorkExecutionStatus.SUCCEEDED,
            repository_state_id=SHA_1,
            artifact_ref=f"git://repo-metao/{SHA_1}",
        )
        with self.assertRaisesRegex(ValueError, "trusted Git endpoint HEAD"):
            port.capture(
                ProjectObjective("project-360", "req-360", "deliver"),
                WorkUnit("unit-1", "work"),
                execution,
            )


if __name__ == "__main__":
    unittest.main()
