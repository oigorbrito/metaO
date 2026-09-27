from __future__ import annotations

import subprocess
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from metao.ssh_git_transport import (
    OpenSshCommandExecutor,
    SshGitRepositoryEndpoint,
    SshGitRepositoryTransport,
)


SHA_A = "a" * 40
SHA_B = "b" * 40


class FakeSshExecutor:
    def __init__(self) -> None:
        self.heads = {"source": SHA_A, "destination": SHA_B}
        self.commits = {"source": {SHA_A}, "destination": {SHA_B}}
        self.clean = {"source": True, "destination": True}
        self.fetch_head: dict[str, str] = {}
        self.uploaded: dict[str, bytes] = {}
        self.calls: list[tuple[str, tuple[str, ...]]] = []
        self.copy_calls: list[tuple[str, str]] = []

    def run(self, endpoint: SshGitRepositoryEndpoint, argv: tuple[str, ...]) -> bytes:
        self.calls.append((endpoint.endpoint_id, argv))
        if argv[0] == "mktemp":
            return b"/tmp/metao-checkpoint.ABC123.bundle\n"
        if argv[0] == "rm":
            return b""
        self.assert_git_prefix(endpoint, argv)
        args = argv[3:]
        if args == ("rev-parse", "--is-inside-work-tree"):
            return b"true\n"
        if args == ("status", "--porcelain", "--untracked-files=normal"):
            return b"" if self.clean[endpoint.endpoint_id] else b"dirty\n"
        if args == ("rev-parse", "HEAD"):
            return f"{self.heads[endpoint.endpoint_id]}\n".encode()
        if args == ("rev-parse", "FETCH_HEAD"):
            return f"{self.fetch_head[endpoint.endpoint_id]}\n".encode()
        if args[:2] == ("cat-file", "-e"):
            commit_id = args[2].split("^{commit}")[0]
            if commit_id not in self.commits[endpoint.endpoint_id]:
                raise ValueError("missing commit")
            return b""
        if args == ("bundle", "create", "-", "HEAD"):
            return f"bundle:{self.heads[endpoint.endpoint_id]}".encode()
        if args[:2] == ("fetch", "--no-tags"):
            payload = self.uploaded[endpoint.endpoint_id].decode()
            commit_id = payload.split(":", 1)[1]
            self.commits[endpoint.endpoint_id].add(commit_id)
            self.fetch_head[endpoint.endpoint_id] = commit_id
            return b""
        if args[:2] == ("reset", "--hard"):
            commit_id = args[2]
            if commit_id not in self.commits[endpoint.endpoint_id]:
                raise ValueError("reset missing commit")
            self.heads[endpoint.endpoint_id] = commit_id
            return b""
        raise AssertionError(f"unexpected remote command: {argv!r}")

    @staticmethod
    def assert_git_prefix(endpoint: SshGitRepositoryEndpoint, argv: tuple[str, ...]) -> None:
        if argv[:3] != ("git", "-C", endpoint.repository_locator):
            raise AssertionError(f"unexpected git prefix: {argv!r}")

    def copy_to(
        self,
        endpoint: SshGitRepositoryEndpoint,
        local_path: Path,
        remote_path: str,
    ) -> None:
        self.copy_calls.append((endpoint.endpoint_id, remote_path))
        self.uploaded[endpoint.endpoint_id] = local_path.read_bytes()


def endpoint(endpoint_id: str, *, locator: str = "/srv/metao/repo") -> SshGitRepositoryEndpoint:
    return SshGitRepositoryEndpoint(
        endpoint_id,
        locator,
        host=f"{endpoint_id}.example.internal",
        username="metao",
        known_hosts_file="/etc/metao/known_hosts",
        identity_file="/etc/metao/id_ed25519",
    )


class SshGitRepositoryTransportTests(unittest.TestCase):
    def test_transfer_exact_moves_only_authoritative_head_and_reobserves_destination(self):
        executor = FakeSshExecutor()
        transport = SshGitRepositoryTransport(executor)
        source = endpoint("source")
        destination = endpoint("destination")

        transport.transfer_exact(source, destination, SHA_A)

        self.assertEqual(executor.heads["destination"], SHA_A)
        self.assertIn(SHA_A, executor.commits["destination"])
        self.assertEqual(
            executor.copy_calls,
            [("destination", "/tmp/metao-checkpoint.ABC123.bundle")],
        )
        destination_head_observations = [
            call
            for call in executor.calls
            if call == (
                "destination",
                ("git", "-C", destination.repository_locator, "rev-parse", "HEAD"),
            )
        ]
        self.assertGreaterEqual(len(destination_head_observations), 2)
        self.assertIn(
            ("destination", ("rm", "-f", "--", "/tmp/metao-checkpoint.ABC123.bundle")),
            executor.calls,
        )

    def test_source_drift_fails_before_bundle_or_copy(self):
        executor = FakeSshExecutor()
        executor.heads["source"] = SHA_B
        executor.commits["source"].add(SHA_B)
        transport = SshGitRepositoryTransport(executor)

        with self.assertRaisesRegex(ValueError, "source SSH Git endpoint HEAD"):
            transport.transfer_exact(endpoint("source"), endpoint("destination"), SHA_A)

        self.assertEqual(executor.copy_calls, [])
        self.assertFalse(any(call[1][0] == "mktemp" for call in executor.calls))

    def test_dirty_destination_fails_before_transfer(self):
        executor = FakeSshExecutor()
        executor.clean["destination"] = False
        transport = SshGitRepositoryTransport(executor)

        with self.assertRaisesRegex(ValueError, "worktree must be clean"):
            transport.transfer_exact(endpoint("source"), endpoint("destination"), SHA_A)

        self.assertEqual(executor.copy_calls, [])

    def test_non_ssh_endpoint_and_noncanonical_commit_fail_closed(self):
        executor = FakeSshExecutor()
        transport = SshGitRepositoryTransport(executor)
        with self.assertRaisesRegex(ValueError, "SshGitRepositoryEndpoint"):
            from metao.git_checkpoint_transport import GitRepositoryEndpoint

            transport.observe_clean_head(GitRepositoryEndpoint("local", "/tmp/repo"))
        with self.assertRaisesRegex(ValueError, "canonical commit"):
            transport.require_commit(endpoint("source"), "HEAD; rm -rf /")

    def test_endpoint_rejects_command_shaped_identity_fields(self):
        with self.assertRaises(ValueError):
            SshGitRepositoryEndpoint(
                "remote",
                "/srv/repo",
                host="host;touch-pwn",
                username="metao",
                known_hosts_file="/known_hosts",
            )
        with self.assertRaises(ValueError):
            SshGitRepositoryEndpoint(
                "remote",
                "relative/repo",
                host="host.example",
                username="metao",
                known_hosts_file="/known_hosts",
            )


class OpenSshCommandExecutorTests(unittest.TestCase):
    def test_command_uses_strict_host_verification_batch_mode_and_shell_quotes_each_remote_arg(self):
        with tempfile.TemporaryDirectory() as root:
            known_hosts = Path(root) / "known_hosts"
            known_hosts.write_text("host.example ssh-ed25519 AAAA\n", encoding="utf-8")
            remote = SshGitRepositoryEndpoint(
                "remote",
                "/srv/repo with space",
                host="host.example",
                username="metao",
                known_hosts_file=str(known_hosts),
            )
            completed = subprocess.CompletedProcess([], 0, stdout=b"ok", stderr=b"")
            with patch("metao.ssh_git_transport.subprocess.run", return_value=completed) as run:
                output = OpenSshCommandExecutor().run(
                    remote,
                    ("git", "-C", remote.repository_locator, "status", "x; touch /tmp/pwn"),
                )

            self.assertEqual(output, b"ok")
            command = run.call_args.args[0]
            self.assertEqual(command[0], "ssh")
            self.assertIn("BatchMode=yes", command)
            self.assertIn("StrictHostKeyChecking=yes", command)
            self.assertTrue(any(item.startswith("UserKnownHostsFile=") for item in command))
            self.assertEqual(command[-2], "metao@host.example")
            self.assertIn("'/srv/repo with space'", command[-1])
            self.assertIn("'x; touch /tmp/pwn'", command[-1])

    def test_missing_known_hosts_fails_before_network_call(self):
        remote = SshGitRepositoryEndpoint(
            "remote",
            "/srv/repo",
            host="host.example",
            username="metao",
            known_hosts_file="/definitely/missing/metao-known-hosts",
        )
        with patch("metao.ssh_git_transport.subprocess.run") as run:
            with self.assertRaisesRegex(ValueError, "known_hosts"):
                OpenSshCommandExecutor().run(remote, ("true",))
        run.assert_not_called()


if __name__ == "__main__":
    unittest.main()
