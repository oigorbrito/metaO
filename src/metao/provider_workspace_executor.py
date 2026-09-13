"""Compose provider-backed execution with configured workspace mutation.

Provider execution never becomes repository authority. A successful provider result
may be applied to a configured executor workspace; resulting repository identifiers
remain claims until the project repository checkpoint port re-observes them.
"""

from __future__ import annotations

from dataclasses import dataclass
from hashlib import sha256
import json
from pathlib import Path
import re
import subprocess
from typing import Any, Mapping, Protocol, runtime_checkable

from .core import (
    ExecutionRequest,
    ExecutionResult,
    ExecutionStatus,
    HealthReport,
    OrchestratorContract,
    OrchestratorDescriptor,
)

_RESERVED_WORKSPACE_OUTPUT_KEYS = frozenset(
    {"repository_state_id", "artifact_ref", "evidence_ref"}
)
_WORK_UNIT_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]{0,127}$")
_SHA_RE = re.compile(r"^[0-9a-fA-F]{40,64}$")


@dataclass(frozen=True, slots=True)
class WorkProductUpdate:
    repository_state_id: str
    artifact_ref: str
    evidence_ref: str

    def __post_init__(self) -> None:
        for name, value in (
            ("repository_state_id", self.repository_state_id),
            ("artifact_ref", self.artifact_ref),
            ("evidence_ref", self.evidence_ref),
        ):
            if not value or not value.strip():
                raise ValueError(f"{name} must be non-empty")


@runtime_checkable
class WorkProductApplierPort(Protocol):
    def apply(
        self,
        request: ExecutionRequest,
        *,
        provider_output: Mapping[str, Any],
    ) -> WorkProductUpdate: ...


@dataclass(frozen=True, slots=True)
class LocalGitWorkProductApplier:
    """Reference applier for a configured filesystem-visible executor worktree."""

    repo_path: Path
    repository_id: str

    def __post_init__(self) -> None:
        repo = Path(self.repo_path).expanduser().resolve()
        if not repo.is_dir():
            raise ValueError("configured executor worktree must exist")
        if not self.repository_id or not self.repository_id.strip():
            raise ValueError("repository_id must be non-empty")
        object.__setattr__(self, "repo_path", repo)
        if self._git("rev-parse", "--is-inside-work-tree") != "true":
            raise ValueError("configured executor workspace must be a Git worktree")

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
            raise ValueError("executor workspace Git operation failed") from exc
        return completed.stdout.strip()

    @staticmethod
    def _expected_context(request: ExecutionRequest) -> tuple[str, str]:
        work_unit_id = request.context.get("work_unit_id")
        expected_state = request.context.get("repository_state_id")
        if not isinstance(work_unit_id, str) or not _WORK_UNIT_RE.fullmatch(work_unit_id):
            raise ValueError("execution context requires canonical work_unit_id")
        if not isinstance(expected_state, str) or not _SHA_RE.fullmatch(expected_state):
            raise ValueError("execution context requires canonical repository_state_id")
        return work_unit_id, expected_state

    def apply(
        self,
        request: ExecutionRequest,
        *,
        provider_output: Mapping[str, Any],
    ) -> WorkProductUpdate:
        work_unit_id, expected_state = self._expected_context(request)
        if self._git("status", "--porcelain", "--untracked-files=normal"):
            raise ValueError("executor workspace must be clean before applying work product")
        if self._git("rev-parse", "HEAD") != expected_state:
            raise ValueError("executor workspace HEAD does not match dispatched checkpoint")
        try:
            self._git("cat-file", "-e", f"{expected_state}^{{commit}}")
        except ValueError as exc:
            raise ValueError("dispatched checkpoint commit is unavailable in workspace") from exc

        payload = json.dumps(
            dict(provider_output),
            sort_keys=True,
            default=str,
            separators=(",", ":"),
        ) + "\n"
        relative = Path(".metao") / "work-products" / f"{work_unit_id}.json"
        destination = self.repo_path / relative
        destination.parent.mkdir(parents=True, exist_ok=True)
        destination.write_text(payload, encoding="utf-8")
        self._git("add", "--", relative.as_posix())
        self._git("commit", "-m", f"metaO work product: {work_unit_id}")
        head = self._git("rev-parse", "HEAD")
        if not _SHA_RE.fullmatch(head) or head == expected_state:
            raise ValueError("executor workspace did not produce a new canonical commit")
        if self._git("status", "--porcelain", "--untracked-files=normal"):
            raise ValueError("executor workspace is not clean after applying work product")
        digest = sha256(payload.encode()).hexdigest()
        return WorkProductUpdate(
            repository_state_id=head,
            artifact_ref=f"git://{self.repository_id}/{head}",
            evidence_ref=f"work-product:{work_unit_id}:{digest}",
        )


class ProviderWorkspaceOrchestratorAdapter:
    """Expose one scheduler-visible executor over provider + workspace mutation."""

    def __init__(
        self,
        provider: OrchestratorContract,
        applier: WorkProductApplierPort,
        *,
        executor_id: str,
        version: str = "1",
        capabilities: frozenset[str] | None = None,
    ) -> None:
        if not executor_id or not executor_id.strip():
            raise ValueError("executor_id must be non-empty")
        provider_descriptor = provider.descriptor
        executor_capabilities = capabilities or provider_descriptor.capabilities
        if not executor_capabilities:
            raise ValueError("executor capabilities must be non-empty")
        self._provider = provider
        self._applier = applier
        self._descriptor = OrchestratorDescriptor(
            orchestrator_id=executor_id,
            version=version,
            capabilities=executor_capabilities,
            metadata={
                "adapter": "provider-workspace",
                "provider_adapter_id": provider_descriptor.orchestrator_id,
                "provider_adapter_version": provider_descriptor.version,
            },
        )

    @property
    def descriptor(self) -> OrchestratorDescriptor:
        return self._descriptor

    def health(self) -> HealthReport:
        return self._provider.health()

    def execute(self, request: ExecutionRequest) -> ExecutionResult:
        provider_result = self._provider.execute(request)
        provider_id = self._provider.descriptor.orchestrator_id
        if provider_result.execution_id != request.execution_id:
            raise ValueError("provider result execution binding mismatch")
        if provider_result.orchestrator_id != provider_id:
            raise ValueError("provider result orchestrator binding mismatch")

        if provider_result.status is not ExecutionStatus.SUCCEEDED:
            return ExecutionResult(
                request.execution_id,
                self.descriptor.orchestrator_id,
                provider_result.status,
                output=provider_result.output,
                evidence=provider_result.evidence,
                error=provider_result.error,
                capacity_observation=provider_result.capacity_observation,
            )

        sanitized_provider_output = {
            key: value
            for key, value in provider_result.output.items()
            if key not in _RESERVED_WORKSPACE_OUTPUT_KEYS
        }
        update = self._applier.apply(
            request,
            provider_output=sanitized_provider_output,
        )
        output = dict(sanitized_provider_output)
        output.update(
            {
                "repository_state_id": update.repository_state_id,
                "artifact_ref": update.artifact_ref,
                "evidence_ref": update.evidence_ref,
            }
        )
        return ExecutionResult(
            request.execution_id,
            self.descriptor.orchestrator_id,
            ExecutionStatus.SUCCEEDED,
            output=output,
            evidence=provider_result.evidence,
        )

    def cancel(self, execution_id: str) -> None:
        self._provider.cancel(execution_id)


__all__ = [
    "WorkProductUpdate",
    "WorkProductApplierPort",
    "LocalGitWorkProductApplier",
    "ProviderWorkspaceOrchestratorAdapter",
]
