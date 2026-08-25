"""Framework-neutral hostile provenance attestation boundary.

The port accepts bound provenance claims and returns provider-bound verification
observations. Provider verification is evidence only; it is never final metaO
acceptance authority.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum
from typing import Protocol, runtime_checkable


class AttestationStatus(StrEnum):
    VERIFIED = "VERIFIED"
    INVALID = "INVALID"
    STALE = "STALE"
    ERROR = "ERROR"


@dataclass(frozen=True)
class ProvenanceAttestationRequest:
    request_id: str
    mission_id: str
    execution_id: str
    subject_id: str
    subject_state_id: str
    verification_context_id: str
    payload_digest: str
    provenance_root: str

    def __post_init__(self) -> None:
        if not all(
            (
                self.request_id,
                self.mission_id,
                self.execution_id,
                self.subject_id,
                self.subject_state_id,
                self.verification_context_id,
                self.payload_digest,
                self.provenance_root,
            )
        ):
            raise ValueError("provenance attestation request requires all bindings")


@dataclass(frozen=True)
class ProvenanceAttestationResult:
    request_id: str
    provider_id: str
    provider_version: str
    status: AttestationStatus
    attestation_digest: str
    reason: str = ""

    def __post_init__(self) -> None:
        if not all(
            (
                self.request_id,
                self.provider_id,
                self.provider_version,
                self.attestation_digest,
            )
        ):
            raise ValueError("provenance attestation result requires bound provider identity")

    @property
    def verified(self) -> bool:
        return self.status is AttestationStatus.VERIFIED


@runtime_checkable
class ProvenanceAttestationPort(Protocol):
    @property
    def provider_id(self) -> str: ...

    @property
    def provider_version(self) -> str: ...

    def verify(
        self,
        request: ProvenanceAttestationRequest,
    ) -> ProvenanceAttestationResult: ...


__all__ = [
    "AttestationStatus",
    "ProvenanceAttestationRequest",
    "ProvenanceAttestationResult",
    "ProvenanceAttestationPort",
]
