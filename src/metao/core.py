from __future__ import annotations

from dataclasses import dataclass, field
from enum import StrEnum
from types import MappingProxyType
from typing import Any, Mapping, Protocol, runtime_checkable

from .capacity import CapacityObservation


class HealthStatus(StrEnum):
    HEALTHY = "HEALTHY"
    DEGRADED = "DEGRADED"
    UNHEALTHY = "UNHEALTHY"


class ExecutionStatus(StrEnum):
    SUCCEEDED = "SUCCEEDED"
    FAILED = "FAILED"
    CANCELLED = "CANCELLED"


@dataclass(frozen=True, slots=True)
class OrchestratorDescriptor:
    orchestrator_id: str
    version: str
    capabilities: frozenset[str]
    metadata: Mapping[str, str] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if not self.orchestrator_id or not self.version or not self.capabilities:
            raise ValueError("orchestrator descriptor requires id, version and capabilities")
        object.__setattr__(self, "metadata", MappingProxyType(dict(self.metadata)))


@dataclass(frozen=True, slots=True)
class HealthReport:
    status: HealthStatus
    reason: str = ""


@dataclass(frozen=True, slots=True)
class Mission:
    mission_id: str
    objective: str
    required_capabilities: frozenset[str] = frozenset()

    def __post_init__(self) -> None:
        if not self.mission_id or not self.objective:
            raise ValueError("mission requires mission_id and objective")


@dataclass(frozen=True, slots=True)
class ExecutionRequest:
    execution_id: str
    mission: Mission
    context: Mapping[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if not self.execution_id:
            raise ValueError("execution_id is required")
        object.__setattr__(self, "context", MappingProxyType(dict(self.context)))


@dataclass(frozen=True, slots=True)
class EvidenceEnvelope:
    mission_id: str
    execution_id: str
    orchestrator_id: str
    adapter_id: str
    adapter_version: str
    attempt_id: str
    subject_id: str
    subject_state_id: str
    verification_context_id: str
    policy_bundle_id: str
    obligation_ids: frozenset[str]
    evidence_payload_digest: str
    provenance: str
    verifier_id: str
    approval_evidence: str = ""
    confidence: float | None = None
    verification_cost_units: int = 0

    def __post_init__(self) -> None:
        required = (
            self.mission_id, self.execution_id, self.orchestrator_id,
            self.adapter_id, self.adapter_version, self.attempt_id,
            self.subject_id, self.subject_state_id, self.verification_context_id,
            self.policy_bundle_id, self.evidence_payload_digest,
            self.provenance, self.verifier_id,
        )
        if not all(required):
            raise ValueError("evidence envelope contains an empty required binding")
        if self.confidence is not None and not 0.0 <= self.confidence <= 1.0:
            raise ValueError("confidence must be within [0, 1]")
        if self.verification_cost_units < 0:
            raise ValueError("verification_cost_units must be non-negative")


@dataclass(frozen=True, slots=True)
class ExecutionResult:
    execution_id: str
    orchestrator_id: str
    status: ExecutionStatus
    output: Mapping[str, Any] = field(default_factory=dict)
    evidence: tuple[EvidenceEnvelope, ...] = ()
    error: str = ""
    capacity_observation: CapacityObservation | None = None

    def __post_init__(self) -> None:
        if not self.execution_id or not self.orchestrator_id:
            raise ValueError("execution result requires identities")
        object.__setattr__(self, "output", MappingProxyType(dict(self.output)))


@runtime_checkable
class OrchestratorContract(Protocol):
    @property
    def descriptor(self) -> OrchestratorDescriptor: ...
    def health(self) -> HealthReport: ...
    def execute(self, request: ExecutionRequest) -> ExecutionResult: ...
    def cancel(self, execution_id: str) -> None: ...


class OrchestratorRegistry:
    def __init__(self) -> None:
        self._items: dict[str, OrchestratorContract] = {}

    def register(self, orchestrator: OrchestratorContract) -> None:
        key = orchestrator.descriptor.orchestrator_id
        if key in self._items:
            raise ValueError(f"orchestrator already registered: {key}")
        self._items[key] = orchestrator

    def unregister(self, orchestrator_id: str) -> None:
        self._items.pop(orchestrator_id, None)

    def get(self, orchestrator_id: str) -> OrchestratorContract:
        if orchestrator_id not in self._items:
            raise KeyError(f"unknown orchestrator: {orchestrator_id}")
        return self._items[orchestrator_id]

    def descriptors(self) -> tuple[OrchestratorDescriptor, ...]:
        return tuple(item.descriptor for _, item in sorted(self._items.items()))

    def eligible(self, mission: Mission) -> tuple[OrchestratorContract, ...]:
        result: list[OrchestratorContract] = []
        for _, item in sorted(self._items.items()):
            if item.health().status not in {HealthStatus.HEALTHY, HealthStatus.DEGRADED}:
                continue
            if not mission.required_capabilities <= item.descriptor.capabilities:
                continue
            result.append(item)
        return tuple(result)
