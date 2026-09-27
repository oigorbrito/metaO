from __future__ import annotations

import unittest
from pathlib import Path

from metao.ssh_git_transport import SshGitRepositoryEndpoint, SshGitRepositoryTransport


SHA_A = "a" * 40
SHA_B = "b" * 40
SHA_C = "c" * 40


class FailureInjectingExecutor:
    def __init__(self, mode: str) -> None:
        self.mode = mode
        self.heads = {"source": SHA_A, "destination": SHA_B}
        self.commits = {"source": {SHA_A}, "destination": {SHA_B}}
        self.fetch_head: dict[str, str] = {}
        self.uploaded: dict[str, bytes] = {}
        self.calls: list[tuple[str, tuple[str, ...]]] = []
        self.after_reset = False
        self.injected = False

    def run(self, endpoint: SshGitRepositoryEndpoint, argv: tuple[str, ...]) -> bytes:
        self.calls.append((endpoint.endpoint_id, argv))
        if argv[0] == "mktemp":
            return b"/tmp/metao-checkpoint.ABC123.bundle\n"
        if argv[0] == "rm":
            if self.mode == "cleanup" and not self.injected:
                self.injected = True
                raise ValueError("injected cleanup failure")
            return b""

        if argv[:3] != ("git", "-C", endpoint.repository_locator):
            raise AssertionError(f"unexpected git prefix: {argv!r}")
        args = argv[3:]

        if args == ("rev-parse", "--is-inside-work-tree"):
            if self.after_reset and not self.injected and self.mode in {
                "post-reset-observation",
                "post-reset-drift",
            }:
                self.injected = True
                if self.mode == "post-reset-drift":
                    self.heads[endpoint.endpoint_id] = SHA_C
                    self.commits[endpoint.endpoint_id].add(SHA_C)
                raise ValueError("injected post-reset observation failure")
            return b"true\n"
        if args == ("status", "--porcelain", "--untracked-files=normal"):
            return b""
        if args == ("rev-parse", "HEAD"):
            return f"{self.heads[endpoint.endpoint_id]}\n".encode()
        if args == ("rev-parse", "FETCH_HEAD"):
            if self.mode == "post-fetch" and not self.injected:
                self.injected = True
                raise ValueError("injected post-fetch failure")
            return f"{self.fetch_head[endpoint.endpoint_id]}\n".encode()
        if args[:2] == ("cat-file", "-e"):
            commit_id = args[2].split("^{commit}")[0]
            if commit_id not in self.commits[endpoint.endpoint_id]:
                raise ValueError("missing commit")
            return b""
        if args == ("bundle", "create", "-", "HEAD"):
            return f"bundle:{self.heads[endpoint.endpoint_id]}".encode()
        if args[:2] == ("fetch", "--no-tags"):
            commit_id = self.uploaded[endpoint.endpoint_id].decode().split(":", 1)[1]
            self.commits[endpoint.endpoint_id].add(commit_id)
            self.fetch_head[endpoint.endpoint_id] = commit_id
            return b""
        if args[:2] == ("reset", "--hard"):
            commit_id = args[2]
            if commit_id not in self.commits[endpoint.endpoint_id]:
                raise ValueError("reset missing commit")
            self.heads[endpoint.endpoint_id] = commit_id
            self.after_reset = commit_id == SHA_A
            return b""
        raise AssertionError(f"unexpected remote command: {argv!r}")

    def copy_to(
        self,
        endpoint: SshGitRepositoryEndpoint,
        local_path: Path,
        remote_path: str,
    ) -> None:
        self.uploaded[endpoint.endpoint_id] = local_path.read_bytes()


def endpoint(endpoint_id: str) -> SshGitRepositoryEndpoint:
    return SshGitRepositoryEndpoint(
        endpoint_id,
        "/srv/metao/repo",
        host=f"{endpoint_id}.example.internal",
        username="metao",
        known_hosts_file="/etc/metao/known_hosts",
        identity_file="/etc/metao/id_ed25519",
    )


class Issue567SshCheckpointTransactionTests(unittest.TestCase):
    def test_post_fetch_failure_leaves_destination_head_unchanged(self) -> None:
        executor = FailureInjectingExecutor("post-fetch")
        transport = SshGitRepositoryTransport(executor)

        with self.assertRaisesRegex(ValueError, "post-fetch"):
            transport.transfer_exact(endpoint("source"), endpoint("destination"), SHA_A)

        self.assertEqual(executor.heads["destination"], SHA_B)

    def test_post_reset_observation_failure_rolls_back_previous_head(self) -> None:
        executor = FailureInjectingExecutor("post-reset-observation")
        transport = SshGitRepositoryTransport(executor)

        with self.assertRaisesRegex(ValueError, "post-reset observation"):
            transport.transfer_exact(endpoint("source"), endpoint("destination"), SHA_A)

        self.assertEqual(executor.heads["destination"], SHA_B)
        reset_targets = [
            call[1][-1]
            for call in executor.calls
            if call[1][0:3] == ("git", "-C", "/srv/metao/repo")
            and call[1][3:5] == ("reset", "--hard")
        ]
        self.assertEqual(reset_targets, [SHA_A, SHA_B])

    def test_cleanup_failure_after_reset_rolls_back_and_remains_failure(self) -> None:
        executor = FailureInjectingExecutor("cleanup")
        transport = SshGitRepositoryTransport(executor)

        with self.assertRaisesRegex(ValueError, "remote temp cleanup failed"):
            transport.transfer_exact(endpoint("source"), endpoint("destination"), SHA_A)

        self.assertEqual(executor.heads["destination"], SHA_B)

    def test_concurrent_destination_drift_refuses_unsafe_rollback(self) -> None:
        executor = FailureInjectingExecutor("post-reset-drift")
        transport = SshGitRepositoryTransport(executor)

        with self.assertRaisesRegex(ValueError, "rollback failed"):
            transport.transfer_exact(endpoint("source"), endpoint("destination"), SHA_A)

        self.assertEqual(executor.heads["destination"], SHA_C)
        self.assertNotEqual(executor.heads["destination"], SHA_B)


if __name__ == "__main__":
    unittest.main()
