"""Framework-neutral independent verifier contracts for metaO.

A verifier evaluates candidate evidence or execution output. Its result is an
input to metaO acceptance; it is never final acceptance authority by itself.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum
from math import isfinite
from types import MappingProxyType
from typing import Mapping, Protocol, runtime_checkable


class VerificationStatus(StrEnum):
    PASS = "PASS"
    FAIL = "FAIL"
    ERROR = "ERROR"


@dataclass(frozen=True)
class VerifierDescriptor:
    verifier_id: str
    version: str
    capabilities: frozenset[str] = frozenset()

    def __post_init__(self) -> None:
        if not self.verifier_id:
            raise ValueError("verifier descriptor requires verifier_id")
        if not self.version:
            raise ValueError("verifier descriptor requires version")


@dataclass(frozen=True)
class VerificationRequest:
    request_id: str
    mission_id: str
    execution_id: str
    obligation_id: str
    subject_id: str
    subject_state_id: str
    verification_context_id: str
    policy_bundle_id: str
    payload_digest: str
    payload: Mapping[str, object]

    def __post_init__(self) -> None:
        required = (
            self.request_id,
            self.mission_id,
            self.execution_id,
            self.obligation_id,
            self.subject_id,
            self.subject_state_id,
            self.verification_context_id,
            self.policy_bundle_id,
            self.payload_digest,
        )
        if not all(required):
            raise ValueError("verification request requires all identity bindings")
        object.__setattr__(self, "payload", MappingProxyType(dict(self.payload)))


@dataclass(frozen=True)
class VerifierResult:
    request_id: str
    verifier_id: str
    verifier_version: str
    status: VerificationStatus
    result_digest: str
    reason: str = ""
    confidence: float | None = None
    metadata: Mapping[str, object] | None = None

    def __post_init__(self) -> None:
        if not self.request_id or not self.verifier_id or not self.verifier_version:
            raise ValueError("verifier result requires request/verifier identity")
        if not self.result_digest:
            raise ValueError("verifier result requires result_digest")
        if self.confidence is not None:
            if isinstance(self.confidence, bool) or not isinstance(self.confidence, (int, float)):
                raise ValueError("verifier confidence must be numeric and non-boolean")
            if not isfinite(float(self.confidence)) or not 0.0 <= self.confidence <= 1.0:
                raise ValueError("verifier confidence must be finite and in [0, 1]")
        if self.metadata is not None:
            object.__setattr__(self, "metadata", MappingProxyType(dict(self.metadata)))

    @property
    def passed(self) -> bool:
        return self.status is VerificationStatus.PASS


@runtime_checkable
class VerifierPort(Protocol):
    @property
    def descriptor(self) -> VerifierDescriptor: ...

    def verify(self, request: VerificationRequest) -> VerifierResult: ...


class VerifierAlreadyRegistered(RuntimeError):
    pass


class VerifierNotFound(KeyError):
    pass


class VerifierRegistry:
    """Deterministic registry of independently selected verifier ports."""

    def __init__(self) -> None:
        self._verifiers: dict[str, VerifierPort] = {}

    def register(self, verifier: VerifierPort) -> None:
        verifier_id = verifier.descriptor.verifier_id
        if verifier_id in self._verifiers:
            raise VerifierAlreadyRegistered(verifier_id)
        self._verifiers[verifier_id] = verifier

    def get(self, verifier_id: str) -> VerifierPort:
        try:
            return self._verifiers[verifier_id]
        except KeyError as exc:
            raise VerifierNotFound(verifier_id) from exc

    def list(self) -> tuple[VerifierDescriptor, ...]:
        return tuple(self._verifiers[key].descriptor for key in sorted(self._verifiers))

    def select(self, *, required_capability: str | None = None) -> VerifierPort | None:
        for verifier_id in sorted(self._verifiers):
            verifier = self._verifiers[verifier_id]
            if required_capability is None or required_capability in verifier.descriptor.capabilities:
                return verifier
        return None


__all__ = [
    "VerificationStatus",
    "VerifierDescriptor",
    "VerificationRequest",
    "VerifierResult",
    "VerifierPort",
    "VerifierAlreadyRegistered",
    "VerifierNotFound",
    "VerifierRegistry",
]
