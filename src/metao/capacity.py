from __future__ import annotations

from dataclasses import dataclass
from enum import Enum


class CapacityStatus(str, Enum):
    AVAILABLE = "available"
    TEMPORARILY_RATE_LIMITED = "temporarily_rate_limited"
    TEMPORARILY_QUOTA_EXHAUSTED = "temporarily_quota_exhausted"
    PROVIDER_UNAVAILABLE = "provider_unavailable"
    AUTHENTICATION_FAILURE = "authentication_failure"
    UNKNOWN = "unknown"


class RecoveryEvidenceBasis(str, Enum):
    PROVIDER_API = "provider_api"
    PROVIDER_DOCUMENTATION = "provider_documentation"
    ADAPTER_VERIFIED = "adapter_verified"
    INDEPENDENT_OBSERVATION = "independent_observation"
    CONFIGURED_POLICY = "configured_policy"
    UNKNOWN = "unknown"


@dataclass(frozen=True)
class CapacityRecovery:
    recover_at_epoch: float
    evidence_basis: RecoveryEvidenceBasis
    evidence_ref: str

    def valid(self) -> bool:
        return (
            self.recover_at_epoch >= 0
            and isinstance(self.evidence_basis, RecoveryEvidenceBasis)
            and self.evidence_basis is not RecoveryEvidenceBasis.UNKNOWN
            and bool(self.evidence_ref.strip())
        )


@dataclass(frozen=True)
class CapacityObservation:
    capacity_status: CapacityStatus
    recovery: CapacityRecovery | None = None


__all__ = [
    "CapacityStatus",
    "RecoveryEvidenceBasis",
    "CapacityRecovery",
    "CapacityObservation",
]
