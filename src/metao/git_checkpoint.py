"""Trusted local-Git repository checkpoints for project supervision.

This adapter observes repository state from the host-side Git worktree. It never
uses executor-provided repository identity as authority and never mutates the
repository during checkpoint capture or handoff.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import re
import subprocess

from .project_supervision import (
    ProjectObjective,
    RepositoryCheckpoint,
    WorkExecutionResult,
    WorkUnit,
)


_SHA_RE = re.compile(r"^[0-9a-fA-F]{40,64}$")


@dataclass(frozen=True, slots=True)
class GitRepositoryCheckpointPort:
    repo_path: Path
    repository_id: str

    def __post_init__(self) -> None:
        path = Path(self.repo_path).expanduser().resolve()
        if not path.is_dir():
            raise ValueError("repository path must be an existing directory")
        if not self.repository_id or not self.repository_id.strip():
            raise ValueError("repository_id must be non-empty")
        object.__setattr__(self, "repo_path", path)
        self._assert_git_worktree()

    def _git(self, *args: str) -> str:
        try:
            completed = subprocess.run(
                ["git", "-C", str(self.repo_path), *args],
                check=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
            )
        except (OSError, subprocess.CalledProcessError) as exc:
            raise ValueError(f"git checkpoint observation failed: {exc}") from exc
        return completed.stdout.strip()

    def _assert_git_worktree(self) -> None:
        if self._git("rev-parse", "--is-inside-work-tree") != "true":
            raise ValueError("repository path must be a Git worktree")

    def _assert_clean(self) -> None:
        if self._git("status", "--porcelain", "--untracked-files=normal"):
            raise ValueError("repository checkpoint requires a clean worktree")

    def _head(self) -> str:
        head = self._git("rev-parse", "HEAD")
        self._assert_commit_id(head)
        self._assert_commit_exists(head)
        return head

    @staticmethod
    def _assert_commit_id(commit_id: str) -> None:
        if not _SHA_RE.fullmatch(commit_id):
            raise ValueError("checkpoint state_id must be a canonical Git commit id")

    def _assert_commit_exists(self, commit_id: str) -> None:
        self._assert_commit_id(commit_id)
        self._git("cat-file", "-e", f"{commit_id}^{{commit}}")

    def _artifact_ref(self, commit_id: str) -> str:
        return f"git://{self.repository_id}/{commit_id}"

    def _checkpoint(self, commit_id: str) -> RepositoryCheckpoint:
        return RepositoryCheckpoint(
            checkpoint_id=f"git-checkpoint:{self.repository_id}:{commit_id}",
            repository_id=self.repository_id,
            state_id=commit_id,
            artifact_ref=self._artifact_ref(commit_id),
        )

    def initial(self, objective: ProjectObjective) -> RepositoryCheckpoint:
        del objective
        self._assert_git_worktree()
        self._assert_clean()
        return self._checkpoint(self._head())

    def capture(
        self,
        objective: ProjectObjective,
        unit: WorkUnit,
        execution: WorkExecutionResult,
    ) -> RepositoryCheckpoint:
        del objective, unit
        self._assert_git_worktree()
        self._assert_clean()
        head = self._head()
        canonical_artifact = self._artifact_ref(head)
        if execution.repository_state_id != head:
            raise ValueError("executor repository state does not match trusted Git HEAD")
        if execution.artifact_ref != canonical_artifact:
            raise ValueError("executor artifact ref does not match trusted Git checkpoint")
        return self._checkpoint(head)

    def handoff(
        self,
        checkpoint: RepositoryCheckpoint,
        *,
        from_executor_id: str,
        to_executor_id: str,
    ) -> RepositoryCheckpoint:
        if not from_executor_id or not from_executor_id.strip():
            raise ValueError("handoff source executor must be non-empty")
        if not to_executor_id or not to_executor_id.strip():
            raise ValueError("handoff target executor must be non-empty")
        if checkpoint.repository_id != self.repository_id:
            raise ValueError("checkpoint repository identity mismatch")
        self._assert_commit_id(checkpoint.state_id)
        if checkpoint.artifact_ref != self._artifact_ref(checkpoint.state_id):
            raise ValueError("checkpoint artifact ref is not canonical for repository state")
        self._assert_git_worktree()
        self._assert_clean()
        self._assert_commit_exists(checkpoint.state_id)
        if self._head() != checkpoint.state_id:
            raise ValueError("repository HEAD moved after checkpoint")
        return checkpoint


__all__ = ["GitRepositoryCheckpointPort"]
