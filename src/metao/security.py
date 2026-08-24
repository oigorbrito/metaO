"""Trust-boundary primitives for metaO.

Security policy distinguishes a local trusted control plane from hostile or
cross-boundary execution. Cryptographic verification is never implemented here:
`StandardCryptoProvider` delegates to an injected standards-based verifier
(e.g. Sigstore/Cosign or an equivalent vetted implementation).
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Callable, MutableSet, Protocol, runtime_checkable


class TrustProfile(str, Enum):
    LOCAL_TRUSTED_CONTROL_PLANE = "LOCAL_TRUSTED_CONTROL_PLANE"
    HOSTILE_OR_DISTRIBUTED_BOUNDARY = "HOSTILE_OR_DISTRIBUTED_BOUNDARY"


LOCAL_TRUSTED_CONTROL_PLANE = TrustProfile.LOCAL_TRUSTED_CONTROL_PLANE
HOSTILE_OR_DISTRIBUTED_BOUNDARY = TrustProfile.HOSTILE_OR_DISTRIBUTED_BOUNDARY


class SecurityError(RuntimeError):
    pass


class StaleAttestation(SecurityError):
    pass


class FutureAttestation(SecurityError):
    pass


class ReplayDetected(SecurityError):
    pass


class RevokedVerifier(SecurityError):
    pass


class UntrustedVerifier(SecurityError):
    pass


class AttestationRejected(SecurityError):
    pass


@runtime_checkable
class CryptoProviderPort(Protocol):
    """Port implemented by a vetted standards-based crypto/attestation provider."""

    def verify(self, *, artifact: bytes, attestation: bytes, identity: str) -> bool: ...


class StandardCryptoProvider:
    """Adapter around an existing standards implementation.

    The callable is expected to invoke a vetted library/tool. metaO only owns
    boundary normalization and fail-closed behavior; no signature algorithm,
    key handling, certificate validation, or transparency-log logic lives here.
    """

    def __init__(self, verifier: Callable[..., bool]) -> None:
        if not callable(verifier):
            raise TypeError("verifier must be callable")
        self._verifier = verifier

    def verify(self, *, artifact: bytes, attestation: bytes, identity: str) -> bool:
        return bool(
            self._verifier(
                artifact=artifact,
                attestation=attestation,
                identity=identity,
            )
        )


@dataclass(frozen=True)
class AttestationVerifier:
    provider: CryptoProviderPort
    trusted_identity: str

    def verify(self, *, artifact: bytes, attestation: bytes) -> bool:
        return verify_attestation(
            self.provider,
            artifact=artifact,
            attestation=attestation,
            identity=self.trusted_identity,
        )


def verify_freshness(
    *,
    issued_at_epoch: float,
    expires_at_epoch: float,
    now_epoch: float,
    allowed_clock_skew_s: float = 0.0,
) -> bool:
    if allowed_clock_skew_s < 0:
        raise ValueError("allowed_clock_skew_s must be non-negative")
    if issued_at_epoch > now_epoch + allowed_clock_skew_s:
        raise FutureAttestation("attestation issue time is in the future")
    if now_epoch - allowed_clock_skew_s > expires_at_epoch:
        raise StaleAttestation("attestation expired")
    return True


def reject_replay(attestation_id: str, seen: MutableSet[str]) -> bool:
    if not attestation_id:
        raise ValueError("attestation_id must be non-empty")
    if attestation_id in seen:
        raise ReplayDetected(f"replayed attestation: {attestation_id}")
    seen.add(attestation_id)
    return True


def verify_trust_root(
    verifier_id: str,
    *,
    trusted_verifiers: set[str] | frozenset[str],
    revoked_verifiers: set[str] | frozenset[str] = frozenset(),
) -> bool:
    if verifier_id in revoked_verifiers:
        raise RevokedVerifier(f"revoked verifier: {verifier_id}")
    if verifier_id not in trusted_verifiers:
        raise UntrustedVerifier(f"untrusted verifier: {verifier_id}")
    return True


def verify_attestation(
    provider: CryptoProviderPort,
    *,
    artifact: bytes,
    attestation: bytes,
    identity: str,
) -> bool:
    if not isinstance(artifact, bytes) or not isinstance(attestation, bytes):
        raise TypeError("artifact and attestation must be bytes")
    if not identity:
        raise ValueError("identity must be non-empty")
    if not provider.verify(artifact=artifact, attestation=attestation, identity=identity):
        raise AttestationRejected("standards provider rejected attestation")
    return True


__all__ = [
    "TrustProfile",
    "LOCAL_TRUSTED_CONTROL_PLANE",
    "HOSTILE_OR_DISTRIBUTED_BOUNDARY",
    "SecurityError",
    "StaleAttestation",
    "FutureAttestation",
    "ReplayDetected",
    "RevokedVerifier",
    "UntrustedVerifier",
    "AttestationRejected",
    "CryptoProviderPort",
    "StandardCryptoProvider",
    "AttestationVerifier",
    "verify_freshness",
    "reject_replay",
    "verify_trust_root",
    "verify_attestation",
]
