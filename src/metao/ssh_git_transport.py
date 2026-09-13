"""Authenticated SSH transport for trusted Git checkpoint endpoints.

This module is deliberately transport-only. Executor/provider selection, checkpoint
identity and project acceptance remain owned by their existing authorities.
Credentials and host verification configuration stay on typed endpoints and never
enter execution context or trace evidence.
"""

from __future__ import annotations

from dataclasses import dataclass
from ipaddress import IPv4Address, IPv6Address, ip_address
from pathlib import Path, PurePosixPath
import re
import shlex
import subprocess
import tempfile
from typing import Protocol, runtime_checkable

from .git_checkpoint_transport import GitRepositoryEndpoint


_SHA_RE = re.compile(r"^[0-9a-fA-F]{40,64}$")
_HOSTNAME_RE = re.compile(r"^[A-Za-z0-9](?:[A-Za-z0-9.-]{0,251}[A-Za-z0-9])?$")
_USER_RE = re.compile(r"^[A-Za-z0-9._-]+$")
_REMOTE_TMP_RE = re.compile(r"^/tmp/metao-checkpoint\.[A-Za-z0-9]+\.bundle$")


def _canonical_host(value: str) -> str:
    if not value or value != value.strip() or any(character in value for character in ("\r", "\n", "\x00")):
        raise ValueError("SSH Git endpoint requires a canonical host name or address")
    if value.startswith("[") or value.endswith("]"):
        raise ValueError("SSH Git endpoint host must not include IPv6 brackets")
    try:
        address = ip_address(value)
    except ValueError:
        if not _HOSTNAME_RE.fullmatch(value):
            raise ValueError("SSH Git endpoint requires a canonical host name or address") from None
        return value
    if not isinstance(address, (IPv4Address, IPv6Address)):
        raise ValueError("SSH Git endpoint requires an IPv4 or IPv6 address")
    return str(address)


@dataclass(frozen=True, slots=True)
class SshGitRepositoryEndpoint(GitRepositoryEndpoint):
    host: str
    username: str
    known_hosts_file: str
    port: int = 22
    identity_file: str | None = None

    def __post_init__(self) -> None:
        GitRepositoryEndpoint.__post_init__(self)
        object.__setattr__(self, "host", _canonical_host(self.host))
        if not _USER_RE.fullmatch(self.username):
            raise ValueError("SSH Git endpoint requires a canonical username")
        if not 1 <= self.port <= 65535:
            raise ValueError("SSH Git endpoint port must be between 1 and 65535")
        locator = PurePosixPath(self.repository_locator)
        if not locator.is_absolute() or "\x00" in self.repository_locator or "\n" in self.repository_locator:
            raise ValueError("SSH Git repository locator must be an absolute remote path")
        if not self.known_hosts_file or not self.known_hosts_file.strip():
            raise ValueError("SSH Git endpoint requires known_hosts_file")
        if self.identity_file is not None and not self.identity_file.strip():
            raise ValueError("SSH identity_file must be non-empty when configured")

    @property
    def is_ipv6_literal(self) -> bool:
        try:
            return isinstance(ip_address(self.host), IPv6Address)
        except ValueError:
            return False


@runtime_checkable
class SshCommandExecutorPort(Protocol):
    def run(
        self,
        endpoint: SshGitRepositoryEndpoint,
        argv: tuple[str, ...],
    ) -> bytes: ...

    def copy_to(
        self,
        endpoint: SshGitRepositoryEndpoint,
        local_path: Path,
        remote_path: str,
    ) -> None: ...


class OpenSshCommandExecutor:
    """OpenSSH command/copy adapter with strict host-key verification."""

    @staticmethod
    def _known_hosts(endpoint: SshGitRepositoryEndpoint) -> str:
        path = Path(endpoint.known_hosts_file).expanduser().resolve()
        if not path.is_file():
            raise ValueError("configured SSH known_hosts file must exist")
        return str(path)

    @staticmethod
    def _identity(endpoint: SshGitRepositoryEndpoint) -> str | None:
        if endpoint.identity_file is None:
            return None
        path = Path(endpoint.identity_file).expanduser().resolve()
        if not path.is_file():
            raise ValueError("configured SSH identity file must exist")
        return str(path)

    def _ssh_options(self, endpoint: SshGitRepositoryEndpoint, *, scp: bool) -> list[str]:
        port_flag = "-P" if scp else "-p"
        options = [
            "-o",
            "BatchMode=yes",
            "-o",
            "StrictHostKeyChecking=yes",
            "-o",
            f"UserKnownHostsFile={self._known_hosts(endpoint)}",
            port_flag,
            str(endpoint.port),
        ]
        identity = self._identity(endpoint)
        if identity is not None:
            options.extend(["-i", identity])
        return options

    @staticmethod
    def _ssh_destination(endpoint: SshGitRepositoryEndpoint) -> str:
        return f"{endpoint.username}@{endpoint.host}"

    @staticmethod
    def _scp_destination(endpoint: SshGitRepositoryEndpoint, remote_path: str) -> str:
        host = f"[{endpoint.host}]" if endpoint.is_ipv6_literal else endpoint.host
        return f"{endpoint.username}@{host}:{remote_path}"

    def run(
        self,
        endpoint: SshGitRepositoryEndpoint,
        argv: tuple[str, ...],
    ) -> bytes:
        if not argv or any("\x00" in arg or "\n" in arg for arg in argv):
            raise ValueError("remote command arguments must be non-empty and single-line")
        remote_command = " ".join(shlex.quote(arg) for arg in argv)
        command = [
            "ssh",
            *self._ssh_options(endpoint, scp=False),
            self._ssh_destination(endpoint),
            remote_command,
        ]
        try:
            completed = subprocess.run(
                command,
                check=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
            )
        except (OSError, subprocess.CalledProcessError) as exc:
            raise ValueError(f"authenticated SSH command failed: {endpoint.endpoint_id}") from exc
        return completed.stdout

    def copy_to(
        self,
        endpoint: SshGitRepositoryEndpoint,
        local_path: Path,
        remote_path: str,
    ) -> None:
        local = Path(local_path).resolve()
        if not local.is_file():
            raise ValueError("SSH copy source must be an existing file")
        if not _REMOTE_TMP_RE.fullmatch(remote_path):
            raise ValueError("SSH copy destination is not an approved checkpoint temp path")
        command = [
            "scp",
            *self._ssh_options(endpoint, scp=True),
            str(local),
            self._scp_destination(endpoint, remote_path),
        ]
        try:
            subprocess.run(
                command,
                check=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
            )
        except (OSError, subprocess.CalledProcessError) as exc:
            raise ValueError(f"authenticated SSH copy failed: {endpoint.endpoint_id}") from exc


@dataclass(frozen=True, slots=True)
class SshGitRepositoryTransport:
    executor: SshCommandExecutorPort

    @staticmethod
    def _endpoint(endpoint: GitRepositoryEndpoint) -> SshGitRepositoryEndpoint:
        if not isinstance(endpoint, SshGitRepositoryEndpoint):
            raise ValueError("SSH Git transport requires SshGitRepositoryEndpoint")
        return endpoint

    @staticmethod
    def _assert_commit_id(commit_id: str) -> None:
        if not _SHA_RE.fullmatch(commit_id):
            raise ValueError("SSH Git transport requires a canonical commit id")

    def _git(self, endpoint: SshGitRepositoryEndpoint, *args: str) -> bytes:
        return self.executor.run(
            endpoint,
            ("git", "-C", endpoint.repository_locator, *args),
        )

    def _observe_clean_head_without_commit_probe(
        self,
        remote: SshGitRepositoryEndpoint,
    ) -> str:
        if self._git(remote, "rev-parse", "--is-inside-work-tree").decode().strip() != "true":
            raise ValueError("SSH Git endpoint must be a worktree")
        if self._git(remote, "status", "--porcelain", "--untracked-files=normal").decode().strip():
            raise ValueError("SSH Git endpoint worktree must be clean")
        head = self._git(remote, "rev-parse", "HEAD").decode().strip()
        self._assert_commit_id(head)
        return head

    def observe_clean_head(self, endpoint: GitRepositoryEndpoint) -> str:
        remote = self._endpoint(endpoint)
        head = self._observe_clean_head_without_commit_probe(remote)
        self.require_commit(remote, head)
        return head

    def require_commit(
        self,
        endpoint: GitRepositoryEndpoint,
        commit_id: str,
    ) -> None:
        remote = self._endpoint(endpoint)
        self._assert_commit_id(commit_id)
        try:
            self._git(remote, "cat-file", "-e", f"{commit_id}^{{commit}}")
        except ValueError as exc:
            raise ValueError(f"SSH Git endpoint missing checkpoint commit: {remote.endpoint_id}") from exc

    def _rollback_destination_if_safe(
        self,
        destination: SshGitRepositoryEndpoint,
        *,
        applied_commit: str,
        previous_head: str,
    ) -> None:
        current_head = self._observe_clean_head_without_commit_probe(destination)
        if current_head != applied_commit:
            raise ValueError(
                "destination changed after checkpoint mutation; refusing unsafe rollback"
            )
        self.require_commit(destination, previous_head)
        self._git(destination, "reset", "--hard", previous_head)
        if self.observe_clean_head(destination) != previous_head:
            raise ValueError("destination rollback did not restore previous checkpoint")

    def transfer_exact(
        self,
        source: GitRepositoryEndpoint,
        destination: GitRepositoryEndpoint,
        commit_id: str,
    ) -> None:
        source_remote = self._endpoint(source)
        destination_remote = self._endpoint(destination)
        self._assert_commit_id(commit_id)
        if self.observe_clean_head(source_remote) != commit_id:
            raise ValueError("source SSH Git endpoint HEAD does not match checkpoint")
        previous_destination_head = self.observe_clean_head(destination_remote)

        if source_remote.endpoint_id == destination_remote.endpoint_id:
            if previous_destination_head != commit_id:
                raise ValueError("destination SSH Git endpoint HEAD does not match checkpoint")
            return

        bundle = self._git(source_remote, "bundle", "create", "-", "HEAD")
        if not bundle:
            raise ValueError("source SSH Git endpoint produced an empty checkpoint bundle")

        remote_temp: str | None = None
        reset_applied = False
        operation_error: Exception | None = None
        cleanup_error: Exception | None = None
        try:
            remote_temp = self.executor.run(
                destination_remote,
                ("mktemp", "/tmp/metao-checkpoint.XXXXXXXXXX.bundle"),
            ).decode().strip()
            if not _REMOTE_TMP_RE.fullmatch(remote_temp):
                raise ValueError("remote checkpoint temp path is not canonical")

            with tempfile.TemporaryDirectory() as temp_dir:
                local_bundle = Path(temp_dir) / "checkpoint.bundle"
                local_bundle.write_bytes(bundle)
                self.executor.copy_to(destination_remote, local_bundle, remote_temp)

            self._git(destination_remote, "fetch", "--no-tags", remote_temp, "HEAD")
            fetched = self._git(destination_remote, "rev-parse", "FETCH_HEAD").decode().strip()
            if fetched != commit_id:
                raise ValueError("transported SSH Git checkpoint does not match authoritative state")
            self._git(destination_remote, "reset", "--hard", commit_id)
            reset_applied = True
            if self.observe_clean_head(destination_remote) != commit_id:
                raise ValueError("destination SSH Git endpoint did not reach checkpoint")
        except Exception as exc:
            operation_error = exc
        finally:
            if remote_temp is not None and _REMOTE_TMP_RE.fullmatch(remote_temp):
                try:
                    self.executor.run(destination_remote, ("rm", "-f", "--", remote_temp))
                except Exception as exc:
                    cleanup_error = exc

        if operation_error is None and cleanup_error is None:
            return

        if reset_applied:
            try:
                self._rollback_destination_if_safe(
                    destination_remote,
                    applied_commit=commit_id,
                    previous_head=previous_destination_head,
                )
            except Exception as rollback_error:
                raise ValueError(
                    "SSH Git checkpoint transfer failed and destination rollback failed"
                ) from rollback_error

        if operation_error is not None and cleanup_error is not None:
            raise ValueError(
                "SSH Git checkpoint transfer failed and remote temp cleanup also failed"
            ) from cleanup_error
        if cleanup_error is not None:
            raise ValueError("SSH Git checkpoint remote temp cleanup failed") from cleanup_error
        assert operation_error is not None
        raise operation_error


__all__ = [
    "SshGitRepositoryEndpoint",
    "SshCommandExecutorPort",
    "OpenSshCommandExecutor",
    "SshGitRepositoryTransport",
]
