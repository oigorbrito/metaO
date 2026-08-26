"""Normalize a bound independent verifier result into canonical EvidenceEnvelope.

This module creates evidence input only. It never calls final acceptance and it
never fabricates authority or provenance. ERROR verifier results are rejected
instead of being flattened into ordinary failed evidence.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum

from .evidence import EvidenceEnvelope
from .verifier import VerificationRequest, VerificationStatus, VerifierDescriptor, VerifierResult


class VerifierEvidenceDecision(StrEnum):
    READY = "READY"
    BLOCK = "BLOCK"


@dataclass(frozen=True)
class VerifierEvidenceBindings:
    evidence_id: str
    orchestrator_id: str
    adapter_id: str
    adapter_version: str
    attempt_id: str
    provenance_root: str
    authority_id: str
    created_at_epoch: float
    expires_at_epoch: float | None = None
    approval_id: str | None = None

    def __post_init__(self) -> None:
        if not all(
            (
                self.evidence_id,
                self.orchestrator_id,
                self.adapter_id,
                self.adapter_version,
                self.attempt_id,
                self.provenance_root,
                self.authority_id,
            )
        ):
            raise ValueError("verifier evidence bindings require all trust/runtime identities")


@dataclass(frozen=True)
class VerifierEvidenceResult:
    decision: VerifierEvidenceDecision
    evidence: EvidenceEnvelope | None
    reason: str = ""


def normalize_verifier_result(
    *,
    request: VerificationRequest,
    descriptor: VerifierDescriptor,
    result: VerifierResult,
    bindings: VerifierEvidenceBindings,
) -> VerifierEvidenceResult:
    """Create canonical evidence only from an exactly bound PASS/FAIL result."""

    if result.request_id != request.request_id:
        return VerifierEvidenceResult(
            VerifierEvidenceDecision.BLOCK, None, "verifier_result_request_mismatch"
        )
    if result.verifier_id != descriptor.verifier_id:
        return VerifierEvidenceResult(
            VerifierEvidenceDecision.BLOCK, None, "verifier_result_identity_mismatch"
        )
    if result.verifier_version != descriptor.version:
        return VerifierEvidenceResult(
            VerifierEvidenceDecision.BLOCK, None, "verifier_result_version_mismatch"
        )
    if result.status is VerificationStatus.ERROR:
        return VerifierEvidenceResult(
            VerifierEvidenceDecision.BLOCK, None, "verifier_result_error"
        )
    if result.status not in (VerificationStatus.PASS, VerificationStatus.FAIL):
        return VerifierEvidenceResult(
            VerifierEvidenceDecision.BLOCK, None, "unsupported_verifier_status"
        )

    evidence = EvidenceEnvelope(
        evidence_id=bindings.evidence_id,
        obligation_id=request.obligation_id,
        mission_id=request.mission_id,
        execution_id=request.execution_id,
        orchestrator_id=bindings.orchestrator_id,
        adapter_id=bindings.adapter_id,
        adapter_version=bindings.adapter_version,
        attempt_id=bindings.attempt_id,
        subject_id=request.subject_id,
        subject_state_id=request.subject_state_id,
        verification_context_id=request.verification_context_id,
        policy_bundle_id=request.policy_bundle_id,
        verifier_id=descriptor.verifier_id,
        payload_digest=request.payload_digest,
        provenance_root=bindings.provenance_root,
        authority_id=bindings.authority_id,
        passed=result.status is VerificationStatus.PASS,
        created_at_epoch=bindings.created_at_epoch,
        expires_at_epoch=bindings.expires_at_epoch,
        approval_id=bindings.approval_id,
        confidence=result.confidence,
        verification_cost_units=0,
    )
    return VerifierEvidenceResult(VerifierEvidenceDecision.READY, evidence)


__all__ = [
    "VerifierEvidenceDecision",
    "VerifierEvidenceBindings",
    "VerifierEvidenceResult",
    "normalize_verifier_result",
]
