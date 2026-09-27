"""Host-neutral trusted Git checkpoint transport boundary.

Checkpoint identity remains metaO-owned. A transport only observes and moves exact
Git states between configured repository endpoints; it grants no scheduling,
provider, policy, retry, budget or acceptance authority.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import re
import subprocess
from types import MappingProxyType
from typing import Mapping, Protocol, runtime_checkable

from .project_supervision import (
    ProjectObjective,
    RepositoryCheckpoint,
    WorkExecutionResult,
    WorkUnit,
)


_SHA_RE = re.compile(r"^[0-9a-fA-F]{40,64}$")


@dataclass(frozen=True, slots=True)
class GitRepositoryEndpoint:
    endpoint_id: str
    repository_locator: str

    def __post_init__(self) -> None:
        if not self.endpoint_id or not self.endpoint_id.strip():
            raise ValueError("Git repository endpoint requires endpoint_id")
        if not self.repository_locator or not self.repository_locator.strip():
            raise ValueError("Git repository endpoint requires repository_locator")


@runtime_checkable
class GitRepositoryTransportPort(Protocol):
    def observe_clean_head(self, endpoint: GitRepositoryEndpoint) -> str: ...

    def require_commit(
        self,
        endpoint: GitRepositoryEndpoint,
        commit_id: str,
    ) -> None: ...

    def transfer_exact(
        self,
        source: GitRepositoryEndpoint,
        destination: GitRepositoryEndpoint,
        commit_id: str,
    ) -> None: ...


class LocalGitRepositoryTransport:
    """Reference transport for filesystem-visible Git worktrees."""

    @staticmethod
    def _path(endpoint: GitRepositoryEndpoint) -> Path:
        path = Path(endpoint.repository_locator).expanduser().resolve()
        if not path.is_dir():
            raise ValueError(f"Git endpoint path must exist: {endpoint.endpoint_id}")
        return path

    @staticmethod
    def _git(repo: Path, *args: str) -> str:
        try:
            completed = subprocess.run(
                ["git", "-C", str(repo), *args],
                check=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
            )
        except (OSError, subprocess.CalledProcessError) as exc:
            raise ValueError(f"Git repository transport failed: {exc}") from exc
        return completed.stdout.strip()

    @classmethod
    def _assert_worktree(cls, repo: Path) -> None:
        if cls._git(repo, "rev-parse", "--is-inside-work-tree") != "true":
            raise ValueError("Git endpoint must be a worktree")

    @classmethod
    def _assert_clean(cls, repo: Path) -> None:
        if cls._git(repo, "status", "--porcelain", "--untracked-files=normal"):
            raise ValueError("Git endpoint worktree must be clean")

    @staticmethod
    def _assert_commit_id(commit_id: str) -> None:
        if not _SHA_RE.fullmatch(commit_id):
            raise ValueError("Git checkpoint state must be a canonical commit id")

    def observe_clean_head(self, endpoint: GitRepositoryEndpoint) -> str:
        repo = self._path(endpoint)
        self._assert_worktree(repo)
        self._assert_clean(repo)
        head = self._git(repo, "rev-parse", "HEAD")
        self._assert_commit_id(head)
        self.require_commit(endpoint, head)
        return head

    def require_commit(
        self,
        endpoint: GitRepositoryEndpoint,
        commit_id: str,
    ) -> None:
        self._assert_commit_id(commit_id)
        repo = self._path(endpoint)
        self._assert_worktree(repo)
        try:
            self._git(repo, "cat-file", "-e", f"{commit_id}^{{commit}}")
        except ValueError as exc:
            raise ValueError(
                f"Git endpoint missing checkpoint commit: {endpoint.endpoint_id}"
            ) from exc

    def transfer_exact(
        self,
        source: GitRepositoryEndpoint,
        destination: GitRepositoryEndpoint,
        commit_id: str,
    ) -> None:
        self._assert_commit_id(commit_id)
        source_repo = self._path(source)
        destination_repo = self._path(destination)
        self._assert_worktree(source_repo)
        self._assert_worktree(destination_repo)
        self._assert_clean(source_repo)
        self._assert_clean(destination_repo)
        self.require_commit(source, commit_id)
        if self._git(source_repo, "rev-parse", "HEAD") != commit_id:
            raise ValueError("source Git endpoint HEAD does not match checkpoint")

        if source_repo == destination_repo:
            if self._git(destination_repo, "rev-parse", "HEAD") != commit_id:
                raise ValueError("destination Git endpoint HEAD does not match checkpoint")
            return

        self._git(destination_repo, "fetch", "--no-tags", str(source_repo), "HEAD")
        if self._git(destination_repo, "rev-parse", "FETCH_HEAD") != commit_id:
            raise ValueError("transported Git checkpoint does not match authoritative state")
        self._git(destination_repo, "reset", "--hard", commit_id)
        self._assert_clean(destination_repo)
        if self._git(destination_repo, "rev-parse", "HEAD") != commit_id:
            raise ValueError("destination Git endpoint did not reach checkpoint")


@dataclass(frozen=True, slots=True)
class EndpointGitCheckpointPort:
    initial_endpoint: GitRepositoryEndpoint
    executor_endpoints: Mapping[str, GitRepositoryEndpoint]
    repository_id: str
    transport: GitRepositoryTransportPort

    def __post_init__(self) -> None:
        if not self.repository_id or not self.repository_id.strip():
            raise ValueError("repository_id must be non-empty")
        configured: dict[str, GitRepositoryEndpoint] = {}
        endpoint_ids: set[str] = {self.initial_endpoint.endpoint_id}
        for executor_id, endpoint in self.executor_endpoints.items():
            if not executor_id or not executor_id.strip():
                raise ValueError("executor endpoint mapping requires executor id")
            if endpoint.endpoint_id in endpoint_ids:
                raise ValueError("Git repository endpoint ids must be unique")
            endpoint_ids.add(endpoint.endpoint_id)
            configured[executor_id] = endpoint
        if not configured:
            raise ValueError("executor endpoint mapping must be non-empty")
        object.__setattr__(self, "executor_endpoints", MappingProxyType(configured))

    @staticmethod
    def _assert_commit_id(commit_id: str) -> None:
        if not _SHA_RE.fullmatch(commit_id):
            raise ValueError("checkpoint state_id must be a canonical Git commit id")

    def _artifact_ref(self, commit_id: str) -> str:
        return f"git://{self.repository_id}/{commit_id}"

    def _checkpoint(self, commit_id: str) -> RepositoryCheckpoint:
        return RepositoryCheckpoint(
            checkpoint_id=f"git-checkpoint:{self.repository_id}:{commit_id}",
            repository_id=self.repository_id,
            state_id=commit_id,
            artifact_ref=self._artifact_ref(commit_id),
        )

    def _endpoint_for_executor(self, executor_id: str) -> GitRepositoryEndpoint:
        endpoint = self.executor_endpoints.get(executor_id)
        if endpoint is None:
            raise ValueError(f"unknown executor Git endpoint: {executor_id}")
        return endpoint

    def _validate_checkpoint(self, checkpoint: RepositoryCheckpoint) -> None:
        if checkpoint.repository_id != self.repository_id:
            raise ValueError("checkpoint repository identity mismatch")
        self._assert_commit_id(checkpoint.state_id)
        if checkpoint.artifact_ref != self._artifact_ref(checkpoint.state_id):
            raise ValueError("checkpoint artifact ref is not canonical")

    def _require_endpoint_at_checkpoint(
        self,
        endpoint: GitRepositoryEndpoint,
        checkpoint: RepositoryCheckpoint,
    ) -> None:
        self.transport.require_commit(endpoint, checkpoint.state_id)
        if self.transport.observe_clean_head(endpoint) != checkpoint.state_id:
            raise ValueError("Git endpoint HEAD does not match authoritative checkpoint")

    def initial(self, objective: ProjectObjective) -> RepositoryCheckpoint:
        del objective
        head = self.transport.observe_clean_head(self.initial_endpoint)
        self._assert_commit_id(head)
        return self._checkpoint(head)

    def materialize(
        self,
        checkpoint: RepositoryCheckpoint,
        *,
        to_executor_id: str,
    ) -> RepositoryCheckpoint:
        self._validate_checkpoint(checkpoint)
        destination = self._endpoint_for_executor(to_executor_id)
        self._require_endpoint_at_checkpoint(self.initial_endpoint, checkpoint)
        self.transport.transfer_exact(
            self.initial_endpoint,
            destination,
            checkpoint.state_id,
        )
        self._require_endpoint_at_checkpoint(destination, checkpoint)
        return checkpoint

    def capture(
        self,
        objective: ProjectObjective,
        unit: WorkUnit,
        execution: WorkExecutionResult,
    ) -> RepositoryCheckpoint:
        del objective, unit
        endpoint = self._endpoint_for_executor(execution.executor_id)
        head = self.transport.observe_clean_head(endpoint)
        self._assert_commit_id(head)
        if execution.repository_state_id != head:
            raise ValueError("executor repository state does not match trusted Git endpoint HEAD")
        if execution.artifact_ref != self._artifact_ref(head):
            raise ValueError("executor artifact ref does not match trusted Git checkpoint")
        return self._checkpoint(head)

    def handoff(
        self,
        checkpoint: RepositoryCheckpoint,
        *,
        from_executor_id: str,
        to_executor_id: str,
    ) -> RepositoryCheckpoint:
        self._validate_checkpoint(checkpoint)
        source = self._endpoint_for_executor(from_executor_id)
        destination = self._endpoint_for_executor(to_executor_id)
        self._require_endpoint_at_checkpoint(source, checkpoint)
        self.transport.transfer_exact(source, destination, checkpoint.state_id)
        self._require_endpoint_at_checkpoint(destination, checkpoint)
        return checkpoint


__all__ = [
    "GitRepositoryEndpoint",
    "GitRepositoryTransportPort",
    "LocalGitRepositoryTransport",
    "EndpointGitCheckpointPort",
]
