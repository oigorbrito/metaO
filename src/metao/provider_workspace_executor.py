"""Compose provider-backed execution with configured workspace mutation.

The provider remains an execution dependency, not repository authority. A successful
provider result may be applied to a configured executor workspace; the resulting
repository identifiers are still claims until the project repository checkpoint
port re-observes them.
"""

from __future__ import annotations

from dataclasses import dataclass
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


class ProviderWorkspaceOrchestratorAdapter:
    """Expose one scheduler-visible executor over provider + workspace mutation.

    Provider identity is intentionally not inferred here. The scheduler's explicit
    executor -> provider registration remains authoritative. This adapter only
    gives the selected executor an execution surface that can produce repository
    state claims after provider success.
    """

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
    "ProviderWorkspaceOrchestratorAdapter",
]
