"""Framework-neutral failure-origin evidence for Python runtime adapters.

Adapters consume a configured authority port; they do not infer runtime-local
origin from a generic framework/provider exception. Execution outcome remains
separate from failure-origin evidence.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum
from threading import RLock
from typing import Protocol, runtime_checkable

from .core import ExecutionRequest


class FailureOrigin(StrEnum):
    RUNTIME_LOCAL = "RuntimeLocal"
    PROVIDER_SERVICE = "ProviderService"
    NETWORK_TRANSPORT = "NetworkTransport"
    CAPACITY = "Capacity"
    POLICY = "Policy"


class FactualFailureOutcome(StrEnum):
    FAILED = "Failed"
    TIMEOUT = "Timeout"


class FailureOriginConflict(RuntimeError):
    """Raised when one execution is reclassified with different origin evidence."""


@dataclass(frozen=True, slots=True)
class BoundFailureOriginEvidence:
    producer_id: str
    mission_id: str
    execution_id: str
    origin: FailureOrigin
    outcome: FactualFailureOutcome
    evidence_ref: str

    def __post_init__(self) -> None:
        for name, value in (
            ("producer_id", self.producer_id),
            ("mission_id", self.mission_id),
            ("execution_id", self.execution_id),
            ("evidence_ref", self.evidence_ref),
        ):
            if not value or not value.strip():
                raise ValueError(f"{name} must be non-empty")
        if not isinstance(self.origin, FailureOrigin):
            raise ValueError("origin must be a FailureOrigin")
        if not isinstance(self.outcome, FactualFailureOutcome):
            raise ValueError("outcome must be a FactualFailureOutcome")


@runtime_checkable
class FailureOriginAuthorityPort(Protocol):
    def resolve_failure_origin(
        self,
        *,
        request: ExecutionRequest,
        runtime_id: str,
        runtime_version: str,
        config_id: str,
        error: Exception,
    ) -> BoundFailureOriginEvidence: ...


class FailureOriginEvidenceLedger:
    """Process-local idempotent evidence ledger; not a durability authority."""

    def __init__(self) -> None:
        self._by_execution: dict[str, BoundFailureOriginEvidence] = {}
        self._lock = RLock()

    def record(self, evidence: BoundFailureOriginEvidence) -> BoundFailureOriginEvidence:
        with self._lock:
            existing = self._by_execution.get(evidence.execution_id)
            if existing is not None:
                if existing != evidence:
                    raise FailureOriginConflict(evidence.execution_id)
                return existing
            self._by_execution[evidence.execution_id] = evidence
            return evidence

    def get(self, execution_id: str) -> BoundFailureOriginEvidence | None:
        with self._lock:
            return self._by_execution.get(execution_id)


def validate_failure_origin_binding(
    evidence: BoundFailureOriginEvidence,
    *,
    request: ExecutionRequest,
) -> None:
    if evidence.mission_id != request.mission.mission_id:
        raise ValueError("failure-origin mission binding mismatch")
    if evidence.execution_id != request.execution_id:
        raise ValueError("failure-origin execution binding mismatch")


__all__ = [
    "FailureOrigin",
    "FactualFailureOutcome",
    "FailureOriginConflict",
    "BoundFailureOriginEvidence",
    "FailureOriginAuthorityPort",
    "FailureOriginEvidenceLedger",
    "validate_failure_origin_binding",
]
