from __future__ import annotations

import unittest

from metao.core import ExecutionRequest, Mission
from metao.ssh_git_transport import SshGitRepositoryEndpoint
from metao.ssh_work_product import SshGitWorkProductApplier


class FakeSshExecutor:
    def __init__(self, head: str) -> None:
        self.head = head
        self.commands: list[tuple[str, ...]] = []
        self.copy_calls = []
        self.writes = 0

    def run(self, endpoint, argv):
        self.commands.append(argv)
        if argv[:4] == ("git", "-C", endpoint.repository_locator, "rev-parse"):
            if argv[4:] == ("--is-inside-work-tree",):
                return b"true\n"
            if argv[4:] == ("HEAD",):
                return (self.head + "\n").encode()
        if argv[:4] == ("git", "-C", endpoint.repository_locator, "status"):
            return b""
        if argv[:4] == ("git", "-C", endpoint.repository_locator, "cat-file"):
            return b""
        if argv[:4] == ("git", "-C", endpoint.repository_locator, "add"):
            return b""
        if argv[:4] == ("git", "-C", endpoint.repository_locator, "commit"):
            self.head = "b" * 40
            return b"committed\n"
        if argv and argv[0] == "python3":
            self.writes += 1
            return b""
        raise AssertionError(f"unexpected argv: {argv!r}")

    def copy_to(self, endpoint, local_path, remote_path):
        self.copy_calls.append((endpoint, local_path, remote_path))


class SshWorkProductApplierTests(unittest.TestCase):
    def endpoint(self):
        return SshGitRepositoryEndpoint(
            endpoint_id="executor-a",
            repository_locator="/srv/metao/workspace",
            host="executor-a.example.test",
            username="metao",
            known_hosts_file="/tmp/known-hosts",
        )

    def request(self, state: str, work_unit_id: str = "prepare"):
        return ExecutionRequest(
            "execution-1",
            Mission("mission-1", "produce artifact"),
            {"work_unit_id": work_unit_id, "repository_state_id": state},
        )

    def test_exact_checkpoint_is_written_to_controlled_path_and_committed(self):
        initial = "a" * 40
        executor = FakeSshExecutor(initial)
        applier = SshGitWorkProductApplier(
            self.endpoint(),
            "repo-metao",
            executor,
        )
        update = applier.apply(
            self.request(initial),
            provider_output={"result": "provider output", "path": "/evil/provider/path"},
        )
        self.assertEqual(update.repository_state_id, "b" * 40)
        self.assertEqual(update.artifact_ref, "git://repo-metao/" + "b" * 40)
        self.assertEqual(executor.writes, 1)
        write = next(command for command in executor.commands if command[0] == "python3")
        self.assertEqual(write[1], "-c")
        self.assertEqual(write[4], ".metao/work-products/prepare.json")
        self.assertNotIn("/evil/provider/path", write)
        self.assertFalse(any(command[:2] == ("sh", "-c") for command in executor.commands))
        self.assertEqual(executor.copy_calls, [])

    def test_checkpoint_drift_fails_before_remote_write(self):
        executor = FakeSshExecutor("a" * 40)
        applier = SshGitWorkProductApplier(self.endpoint(), "repo-metao", executor)
        with self.assertRaisesRegex(ValueError, "HEAD does not match"):
            applier.apply(
                self.request("f" * 40),
                provider_output={"result": "must not be written"},
            )
        self.assertEqual(executor.writes, 0)
        self.assertFalse(any("commit" in command for command in executor.commands))

    def test_noncanonical_work_unit_id_is_rejected_before_ssh(self):
        executor = FakeSshExecutor("a" * 40)
        applier = SshGitWorkProductApplier(self.endpoint(), "repo-metao", executor)
        with self.assertRaisesRegex(ValueError, "work_unit_id"):
            applier.apply(
                self.request("a" * 40, "../../escape"),
                provider_output={"result": "x"},
            )
        self.assertEqual(executor.commands, [])


if __name__ == "__main__":
    unittest.main()
