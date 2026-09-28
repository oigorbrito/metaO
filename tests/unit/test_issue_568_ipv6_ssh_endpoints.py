from __future__ import annotations

import subprocess
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from metao.ssh_git_transport import OpenSshCommandExecutor, SshGitRepositoryEndpoint


def endpoint(host: str, known_hosts_file: str) -> SshGitRepositoryEndpoint:
    return SshGitRepositoryEndpoint(
        "remote",
        "/srv/metao/repo",
        host=host,
        username="metao",
        known_hosts_file=known_hosts_file,
    )


class Issue568Ipv6SshEndpointTests(unittest.TestCase):
    def test_hostname_ipv4_and_ipv6_are_accepted_and_ips_are_canonicalized(self) -> None:
        with tempfile.TemporaryDirectory() as root:
            known_hosts = Path(root) / "known_hosts"
            known_hosts.write_text("placeholder\n", encoding="utf-8")
            self.assertEqual(endpoint("host.example", str(known_hosts)).host, "host.example")
            self.assertEqual(endpoint("192.0.2.10", str(known_hosts)).host, "192.0.2.10")
            self.assertEqual(
                endpoint("2001:0db8:0000:0000:0000:0000:0000:0001", str(known_hosts)).host,
                "2001:db8::1",
            )

    def test_user_supplied_ipv6_brackets_and_control_characters_are_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as root:
            known_hosts = Path(root) / "known_hosts"
            known_hosts.write_text("placeholder\n", encoding="utf-8")
            for host in ("[2001:db8::1]", "2001:db8::1\nmalicious", "host.example\x00x"):
                with self.subTest(host=host), self.assertRaises(ValueError):
                    endpoint(host, str(known_hosts))

    def test_ssh_uses_unbracketed_ipv6_destination(self) -> None:
        with tempfile.TemporaryDirectory() as root:
            known_hosts = Path(root) / "known_hosts"
            known_hosts.write_text("placeholder\n", encoding="utf-8")
            remote = endpoint("2001:db8::1", str(known_hosts))
            completed = subprocess.CompletedProcess([], 0, stdout=b"ok", stderr=b"")
            with patch("metao.ssh_git_transport.subprocess.run", return_value=completed) as run:
                OpenSshCommandExecutor().run(remote, ("true",))
            command = run.call_args.args[0]
            self.assertEqual(command[-2], "metao@2001:db8::1")

    def test_scp_brackets_ipv6_to_disambiguate_remote_path_separator(self) -> None:
        with tempfile.TemporaryDirectory() as root:
            root_path = Path(root)
            known_hosts = root_path / "known_hosts"
            known_hosts.write_text("placeholder\n", encoding="utf-8")
            payload = root_path / "checkpoint.bundle"
            payload.write_bytes(b"bundle")
            remote = endpoint("2001:db8::1", str(known_hosts))
            completed = subprocess.CompletedProcess([], 0, stdout=b"", stderr=b"")
            with patch("metao.ssh_git_transport.subprocess.run", return_value=completed) as run:
                OpenSshCommandExecutor().copy_to(
                    remote,
                    payload,
                    "/tmp/metao-checkpoint.ABC123.bundle",
                )
            command = run.call_args.args[0]
            self.assertEqual(
                command[-1],
                "metao@[2001:db8::1]:/tmp/metao-checkpoint.ABC123.bundle",
            )


if __name__ == "__main__":
    unittest.main()
