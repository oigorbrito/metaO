"""Immutable operator revocation for individual runtime certificates.

Revocation is deliberately different from runtime quarantine. It invalidates one
certificate generation for reuse but does not directly change live runtime health
or catalog eligibility of an already admitted runtime.
"""

from __future__ import annotations

from dataclasses import dataclass
from threading import RLock
from typing import Protocol, runtime_checkable

from .runtime_certification import RuntimeCertificationStorePort


class RuntimeCertificationRevocationConflict(RuntimeError):
    pass


class UnknownRuntimeCertification(KeyError):
    pass


@dataclass(frozen=True, slots=True)
class RuntimeCertificationRevocation:
    certificate_id: str
    orchestrator_id: str
    reason: str
    actor_id: str
    revoked_at_epoch: float

    def __post_init__(self) -> None:
        if not self.certificate_id:
            raise ValueError("certificate_id is required")
        if not self.orchestrator_id:
            raise ValueError("orchestrator_id is required")
        if not self.reason:
            raise ValueError("certificate revocation reason is required")
        if not self.actor_id:
            raise ValueError("certificate revocation actor_id is required")
        if self.revoked_at_epoch < 0:
            raise ValueError("certificate revocation time must be non-negative")


@runtime_checkable
class RuntimeCertificationRevocationStorePort(Protocol):
    def record(
        self, revocation: RuntimeCertificationRevocation
    ) -> RuntimeCertificationRevocation: ...

    def get(self, certificate_id: str) -> RuntimeCertificationRevocation | None: ...

    def history(self, orchestrator_id: str) -> tuple[RuntimeCertificationRevocation, ...]: ...


class InMemoryRuntimeCertificationRevocationStore:
    def __init__(self) -> None:
        self._by_certificate: dict[str, RuntimeCertificationRevocation] = {}
        self._lock = RLock()

    def record(
        self, revocation: RuntimeCertificationRevocation
    ) -> RuntimeCertificationRevocation:
        with self._lock:
            existing = self._by_certificate.get(revocation.certificate_id)
            if existing is not None:
                if existing != revocation:
                    raise RuntimeCertificationRevocationConflict(revocation.certificate_id)
                return existing
            self._by_certificate[revocation.certificate_id] = revocation
            return revocation

    def get(self, certificate_id: str) -> RuntimeCertificationRevocation | None:
        with self._lock:
            return self._by_certificate.get(certificate_id)

    def history(self, orchestrator_id: str) -> tuple[RuntimeCertificationRevocation, ...]:
        with self._lock:
            return tuple(
                sorted(
                    (
                        item
                        for item in self._by_certificate.values()
                        if item.orchestrator_id == orchestrator_id
                    ),
                    key=lambda item: (item.revoked_at_epoch, item.certificate_id),
                )
            )


def revoke_certificate(
    certifications: RuntimeCertificationStorePort,
    revocations: RuntimeCertificationRevocationStorePort,
    certificate_id: str,
    *,
    reason: str,
    actor_id: str,
    revoked_at_epoch: float,
) -> RuntimeCertificationRevocation:
    certificate = certifications.get(certificate_id)
    if certificate is None:
        raise UnknownRuntimeCertification(certificate_id)
    return revocations.record(
        RuntimeCertificationRevocation(
            certificate_id=certificate.certificate_id,
            orchestrator_id=certificate.orchestrator_id,
            reason=reason,
            actor_id=actor_id,
            revoked_at_epoch=revoked_at_epoch,
        )
    )


def is_certificate_revoked(
    revocations: RuntimeCertificationRevocationStorePort | None,
    certificate_id: str,
) -> bool:
    return revocations is not None and revocations.get(certificate_id) is not None


__all__ = [
    "RuntimeCertificationRevocationConflict",
    "UnknownRuntimeCertification",
    "RuntimeCertificationRevocation",
    "RuntimeCertificationRevocationStorePort",
    "InMemoryRuntimeCertificationRevocationStore",
    "revoke_certificate",
    "is_certificate_revoked",
]
