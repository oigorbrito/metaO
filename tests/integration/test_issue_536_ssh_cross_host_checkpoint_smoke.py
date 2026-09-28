from __future__ import annotations

import os
import re
import tempfile
import unittest
from pathlib import Path

from metao.git_checkpoint_transport import EndpointGitCheckpointPort
from metao.project_supervision import ProjectObjective
from metao.ssh_git_transport import (
    OpenSshCommandExecutor,
    SshGitRepositoryEndpoint,
    SshGitRepositoryTransport,
)


_REMOTE_SMOKE_RE = re.compile(r"^/tmp/metao-ssh-smoke\.[A-Za-z0-9]+$")


def _required_env(name: str) -> str | None:
    value = os.environ.get(name)
    if value is None or not value.strip():
        return None
    return value


class SshCrossHostCheckpointSmokeTests(unittest.TestCase):
    def test_materializes_exact_checkpoint_across_two_credential_backed_hosts(self):
        required_names = (
            "METAO_SSH_SMOKE_SOURCE_HOST",
            "METAO_SSH_SMOKE_DESTINATION_HOST",
            "METAO_SSH_SMOKE_SOURCE_USER",
            "METAO_SSH_SMOKE_DESTINATION_USER",
            "METAO_SSH_SMOKE_KNOWN_HOSTS",
        )
        values = {name: _required_env(name) for name in required_names}
        missing = [name for name, value in values.items() if value is None]
        if missing:
            self.skipTest("credential-backed SSH smoke environment is not configured")

        source_host = values["METAO_SSH_SMOKE_SOURCE_HOST"]
        destination_host = values["METAO_SSH_SMOKE_DESTINATION_HOST"]
        assert source_host is not None
        assert destination_host is not None
        self.assertNotEqual(
            source_host,
            destination_host,
            "cross-host qualification requires distinct source and destination hosts",
        )

        source_user = values["METAO_SSH_SMOKE_SOURCE_USER"]
        destination_user = values["METAO_SSH_SMOKE_DESTINATION_USER"]
        known_hosts_content = values["METAO_SSH_SMOKE_KNOWN_HOSTS"]
        assert source_user is not None
        assert destination_user is not None
        assert known_hosts_content is not None

        source_port = int(os.environ.get("METAO_SSH_SMOKE_SOURCE_PORT", "22"))
        destination_port = int(os.environ.get("METAO_SSH_SMOKE_DESTINATION_PORT", "22"))
        identity_content = os.environ.get("METAO_SSH_SMOKE_IDENTITY")

        with tempfile.TemporaryDirectory() as local_root:
            local_root_path = Path(local_root)
            known_hosts_file = local_root_path / "known_hosts"
            known_hosts_file.write_text(known_hosts_content, encoding="utf-8")
            identity_file: Path | None = None
            if identity_content is not None and identity_content.strip():
                identity_file = local_root_path / "identity"
                identity_file.write_text(identity_content, encoding="utf-8")
                identity_file.chmod(0o600)

            def bootstrap_endpoint(
                endpoint_id: str,
                host: str,
                username: str,
                port: int,
            ) -> SshGitRepositoryEndpoint:
                return SshGitRepositoryEndpoint(
                    endpoint_id,
                    "/tmp",
                    host=host,
                    username=username,
                    known_hosts_file=str(known_hosts_file),
                    port=port,
                    identity_file=str(identity_file) if identity_file is not None else None,
                )

            source_admin = bootstrap_endpoint(
                "smoke-source-admin",
                source_host,
                source_user,
                source_port,
            )
            destination_admin = bootstrap_endpoint(
                "smoke-destination-admin",
                destination_host,
                destination_user,
                destination_port,
            )
            executor = OpenSshCommandExecutor()
            created: list[tuple[SshGitRepositoryEndpoint, str]] = []
            cleanup_errors: list[Exception] = []

            try:
                source_repo = executor.run(
                    source_admin,
                    ("mktemp", "-d", "/tmp/metao-ssh-smoke.XXXXXXXXXX"),
                ).decode().strip()
                destination_repo = executor.run(
                    destination_admin,
                    ("mktemp", "-d", "/tmp/metao-ssh-smoke.XXXXXXXXXX"),
                ).decode().strip()
                for endpoint, path in (
                    (source_admin, source_repo),
                    (destination_admin, destination_repo),
                ):
                    if not _REMOTE_SMOKE_RE.fullmatch(path):
                        self.fail("remote smoke repository path is not canonical")
                    created.append((endpoint, path))
                    executor.run(endpoint, ("git", "-C", path, "init"))

                executor.run(
                    source_admin,
                    (
                        "git",
                        "-C",
                        source_repo,
                        "-c",
                        "user.name=metaO",
                        "-c",
                        "user.email=metao@example.invalid",
                        "commit",
                        "--allow-empty",
                        "-m",
                        "source-smoke",
                    ),
                )
                executor.run(
                    destination_admin,
                    (
                        "git",
                        "-C",
                        destination_repo,
                        "-c",
                        "user.name=metaO",
                        "-c",
                        "user.email=metao@example.invalid",
                        "commit",
                        "--allow-empty",
                        "-m",
                        "destination-smoke",
                    ),
                )

                source_endpoint = SshGitRepositoryEndpoint(
                    "smoke-source",
                    source_repo,
                    host=source_host,
                    username=source_user,
                    known_hosts_file=str(known_hosts_file),
                    port=source_port,
                    identity_file=str(identity_file) if identity_file is not None else None,
                )
                destination_endpoint = SshGitRepositoryEndpoint(
                    "smoke-destination",
                    destination_repo,
                    host=destination_host,
                    username=destination_user,
                    known_hosts_file=str(known_hosts_file),
                    port=destination_port,
                    identity_file=str(identity_file) if identity_file is not None else None,
                )
                transport = SshGitRepositoryTransport(executor)
                source_before = transport.observe_clean_head(source_endpoint)
                destination_before = transport.observe_clean_head(destination_endpoint)
                self.assertNotEqual(source_before, destination_before)

                port = EndpointGitCheckpointPort(
                    initial_endpoint=source_endpoint,
                    executor_endpoints={"executor-remote": destination_endpoint},
                    repository_id="repo-ssh-cross-host-smoke",
                    transport=transport,
                )
                checkpoint = port.initial(
                    ProjectObjective("project-360", "req-360", "cross-host smoke")
                )
                materialized = port.materialize(
                    checkpoint,
                    to_executor_id="executor-remote",
                )

                self.assertEqual(materialized, checkpoint)
                self.assertEqual(
                    transport.observe_clean_head(destination_endpoint),
                    checkpoint.state_id,
                )
            finally:
                for endpoint, path in reversed(created):
                    try:
                        executor.run(endpoint, ("rm", "-rf", "--", path))
                    except Exception as exc:  # cleanup must be attempted on both hosts
                        cleanup_errors.append(exc)
                if cleanup_errors:
                    raise AssertionError("remote SSH smoke cleanup failed") from cleanup_errors[0]


if __name__ == "__main__":
    unittest.main()
