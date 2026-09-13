"""Trusted Git checkpoints and transfer across configured executor worktrees."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import re
import subprocess
from types import MappingProxyType
from typing import Mapping

from .project_supervision import (
    ProjectObjective,
    RepositoryCheckpoint,
    WorkExecutionResult,
    WorkUnit,
)


_SHA_RE = re.compile(r"^[0-9a-fA-F]{40,64}$")


@dataclass(frozen=True, slots=True)
class ExecutorGitCheckpointPort:
    initial_repo_path: Path
    executor_repo_paths: Mapping[str, Path]
    repository_id: str

    def __post_init__(self) -> None:
        if not self.repository_id or not self.repository_id.strip():
            raise ValueError("repository_id must be non-empty")
        initial = Path(self.initial_repo_path).expanduser().resolve()
        if not initial.is_dir():
            raise ValueError("initial repository path must be an existing directory")
        configured: dict[str, Path] = {}
        for executor_id, value in self.executor_repo_paths.items():
            if not executor_id or not executor_id.strip():
                raise ValueError("executor repository mapping requires non-empty executor id")
            path = Path(value).expanduser().resolve()
            if not path.is_dir():
                raise ValueError(f"executor repository path must exist: {executor_id}")
            configured[executor_id] = path
        if not configured:
            raise ValueError("executor repository mapping must be non-empty")
        object.__setattr__(self, "initial_repo_path", initial)
        object.__setattr__(self, "executor_repo_paths", MappingProxyType(configured))
        self._assert_git_worktree(initial)
        for path in configured.values():
            self._assert_git_worktree(path)

    @staticmethod
    def _assert_commit_id(commit_id: str) -> None:
        if not _SHA_RE.fullmatch(commit_id):
            raise ValueError("checkpoint state_id must be a canonical Git commit id")

    def _git(self, repo: Path, *args: str) -> str:
        try:
            completed = subprocess.run(
                ["git", "-C", str(repo), *args],
                check=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
            )
        except (OSError, subprocess.CalledProcessError) as exc:
            raise ValueError(f"git checkpoint transfer failed: {exc}") from exc
        return completed.stdout.strip()

    def _assert_git_worktree(self, repo: Path) -> None:
        if self._git(repo, "rev-parse", "--is-inside-work-tree") != "true":
            raise ValueError("configured repository path must be a Git worktree")

    def _assert_clean(self, repo: Path) -> None:
        if self._git(repo, "status", "--porcelain", "--untracked-files=normal"):
            raise ValueError("repository checkpoint transfer requires a clean worktree")

    def _assert_commit_exists(self, repo: Path, commit_id: str) -> None:
        self._assert_commit_id(commit_id)
        self._git(repo, "cat-file", "-e", f"{commit_id}^{{commit}}")

    def _head(self, repo: Path) -> str:
        head = self._git(repo, "rev-parse", "HEAD")
        self._assert_commit_id(head)
        self._assert_commit_exists(repo, head)
        return head

    def _artifact_ref(self, commit_id: str) -> str:
        return f"git://{self.repository_id}/{commit_id}"

    def _checkpoint(self, commit_id: str) -> RepositoryCheckpoint:
        return RepositoryCheckpoint(
            checkpoint_id=f"git-checkpoint:{self.repository_id}:{commit_id}",
            repository_id=self.repository_id,
            state_id=commit_id,
            artifact_ref=self._artifact_ref(commit_id),
        )

    def _repo_for_executor(self, executor_id: str) -> Path:
        repo = self.executor_repo_paths.get(executor_id)
        if repo is None:
            raise ValueError(f"unknown executor repository mapping: {executor_id}")
        return repo

    def initial(self, objective: ProjectObjective) -> RepositoryCheckpoint:
        del objective
        self._assert_git_worktree(self.initial_repo_path)
        self._assert_clean(self.initial_repo_path)
        return self._checkpoint(self._head(self.initial_repo_path))

    def capture(
        self,
        objective: ProjectObjective,
        unit: WorkUnit,
        execution: WorkExecutionResult,
    ) -> RepositoryCheckpoint:
        del objective, unit
        repo = self._repo_for_executor(execution.executor_id)
        self._assert_git_worktree(repo)
        self._assert_clean(repo)
        head = self._head(repo)
        if execution.repository_state_id != head:
            raise ValueError("executor repository state does not match trusted executor Git HEAD")
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
        if checkpoint.repository_id != self.repository_id:
            raise ValueError("checkpoint repository identity mismatch")
        self._assert_commit_id(checkpoint.state_id)
        if checkpoint.artifact_ref != self._artifact_ref(checkpoint.state_id):
            raise ValueError("checkpoint artifact ref is not canonical for repository state")

        source = self._repo_for_executor(from_executor_id)
        destination = self._repo_for_executor(to_executor_id)
        self._assert_git_worktree(source)
        self._assert_git_worktree(destination)
        self._assert_clean(source)
        self._assert_clean(destination)
        self._assert_commit_exists(source, checkpoint.state_id)
        if self._head(source) != checkpoint.state_id:
            raise ValueError("source executor Git HEAD does not match checkpoint")

        if source == destination:
            if self._head(destination) != checkpoint.state_id:
                raise ValueError("destination executor Git HEAD does not match checkpoint")
            return checkpoint

        self._git(destination, "fetch", "--no-tags", str(source), "HEAD")
        fetched = self._git(destination, "rev-parse", "FETCH_HEAD")
        if fetched != checkpoint.state_id:
            raise ValueError("fetched executor checkpoint does not match authoritative state")
        self._git(destination, "reset", "--hard", checkpoint.state_id)
        if self._head(destination) != checkpoint.state_id:
            raise ValueError("destination executor Git HEAD does not match checkpoint after transfer")
        self._assert_clean(destination)
        return checkpoint


__all__ = ["ExecutorGitCheckpointPort"]
