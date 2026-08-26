"""Compose authoritative Roadmap 8 terminal preconditions without final acceptance.

This coordinator joins A05/A07/A09 authoritative snapshot truth with A04
freshness, A06 provenance attestation, and A08 approver authority. Its output is
only READY/STALE/BLOCK. It never issues `METAO_ACCEPTED`.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum

from .approval_authority import ApprovalAuthorityDecision, ApprovalAuthorityContext, ApprovalAuthorityRequest, ApproverCapability, evaluate_approval_authority
from .authoritative_snapshot import AuthoritativeSnapshotDecision, AuthoritativeTerminalSnapshot
from .freshness_authority import FreshnessDecision, FreshnessPolicy, FreshnessRequest, TrustedClockPort, evaluate_authoritative_freshness
from .provenance_attestation import AttestationStatus, ProvenanceAttestationPort, ProvenanceAttestationRequest


class TerminalPreconditionDecision(StrEnum):
    READY = "READY"
    STALE = "STALE"
    BLOCK = "BLOCK"


@dataclass(frozen=True)
class TerminalPreconditionResult:
    decision: TerminalPreconditionDecision
    authoritative_snapshot: AuthoritativeTerminalSnapshot
    reason: str = ""
    observed_now_epoch: float | None = None
    attestation_digest: str | None = None
    approval_capability_id: str | None = None


def evaluate_terminal_preconditions(
    *,
    authoritative_snapshot: AuthoritativeTerminalSnapshot,
    freshness_request: FreshnessRequest,
    clock: TrustedClockPort,
    freshness_policy: FreshnessPolicy,
    provenance_request: ProvenanceAttestationRequest,
    provenance_provider: ProvenanceAttestationPort,
    approval_required: bool,
    approval_context: ApprovalAuthorityContext | None = None,
    approver_capability: ApproverCapability | None = None,
    approval_request: ApprovalAuthorityRequest | None = None,
) -> TerminalPreconditionResult:
    if not isinstance(approval_required, bool):
        raise TypeError("approval_required must be bool")

    if authoritative_snapshot.decision is AuthoritativeSnapshotDecision.STALE:
        return TerminalPreconditionResult(TerminalPreconditionDecision.STALE, authoritative_snapshot, authoritative_snapshot.reason or "authoritative_snapshot_stale")
    if authoritative_snapshot.decision is not AuthoritativeSnapshotDecision.READY:
        return TerminalPreconditionResult(TerminalPreconditionDecision.BLOCK, authoritative_snapshot, authoritative_snapshot.reason or "authoritative_snapshot_blocked")

    request = authoritative_snapshot.request
    if freshness_request.subject_id != request.subject_id or freshness_request.subject_state_id != request.subject_state_id or freshness_request.verification_context_id != request.verification_context_id:
        return TerminalPreconditionResult(TerminalPreconditionDecision.BLOCK, authoritative_snapshot, "freshness_binding_mismatch")

    freshness = evaluate_authoritative_freshness(freshness_request, clock=clock, policy=freshness_policy)
    if freshness.decision is FreshnessDecision.STALE:
        return TerminalPreconditionResult(TerminalPreconditionDecision.STALE, authoritative_snapshot, freshness.reason, observed_now_epoch=freshness.observed_now_epoch)
    if freshness.decision is not FreshnessDecision.FRESH:
        return TerminalPreconditionResult(TerminalPreconditionDecision.BLOCK, authoritative_snapshot, freshness.reason or "freshness_blocked", observed_now_epoch=freshness.observed_now_epoch)

    if provenance_request.mission_id != request.mission_id or provenance_request.execution_id != request.execution_id or provenance_request.subject_id != request.subject_id or provenance_request.subject_state_id != request.subject_state_id or provenance_request.verification_context_id != request.verification_context_id:
        return TerminalPreconditionResult(TerminalPreconditionDecision.BLOCK, authoritative_snapshot, "provenance_request_binding_mismatch", observed_now_epoch=freshness.observed_now_epoch)

    try:
        attestation = provenance_provider.verify(provenance_request)
    except Exception:
        return TerminalPreconditionResult(TerminalPreconditionDecision.BLOCK, authoritative_snapshot, "provenance_provider_error", observed_now_epoch=freshness.observed_now_epoch)

    if attestation.request_id != provenance_request.request_id:
        return TerminalPreconditionResult(TerminalPreconditionDecision.BLOCK, authoritative_snapshot, "attestation_request_mismatch", observed_now_epoch=freshness.observed_now_epoch)
    if attestation.provider_id != provenance_provider.provider_id:
        return TerminalPreconditionResult(TerminalPreconditionDecision.BLOCK, authoritative_snapshot, "attestation_provider_identity_mismatch", observed_now_epoch=freshness.observed_now_epoch)
    if attestation.provider_version != provenance_provider.provider_version:
        return TerminalPreconditionResult(TerminalPreconditionDecision.BLOCK, authoritative_snapshot, "attestation_provider_version_mismatch", observed_now_epoch=freshness.observed_now_epoch)
    if attestation.status is AttestationStatus.STALE:
        return TerminalPreconditionResult(TerminalPreconditionDecision.STALE, authoritative_snapshot, attestation.reason or "provenance_attestation_stale", observed_now_epoch=freshness.observed_now_epoch, attestation_digest=attestation.attestation_digest)
    if attestation.status is not AttestationStatus.VERIFIED:
        return TerminalPreconditionResult(TerminalPreconditionDecision.BLOCK, authoritative_snapshot, attestation.reason or "provenance_attestation_not_verified", observed_now_epoch=freshness.observed_now_epoch, attestation_digest=attestation.attestation_digest)

    capability_id: str | None = None
    if approval_required:
        if approval_context is None or approver_capability is None or approval_request is None:
            return TerminalPreconditionResult(TerminalPreconditionDecision.BLOCK, authoritative_snapshot, "approval_authority_inputs_missing", observed_now_epoch=freshness.observed_now_epoch, attestation_digest=attestation.attestation_digest)
        if approval_context.authority_context_id != authoritative_snapshot.authority.authority_context_id:
            return TerminalPreconditionResult(TerminalPreconditionDecision.BLOCK, authoritative_snapshot, "approval_authority_context_mismatch", observed_now_epoch=freshness.observed_now_epoch, attestation_digest=attestation.attestation_digest)
        if approval_request.target != request.mission_id or approval_request.scope != request.policy_bundle_id:
            return TerminalPreconditionResult(TerminalPreconditionDecision.BLOCK, authoritative_snapshot, "approval_request_binding_mismatch", observed_now_epoch=freshness.observed_now_epoch, attestation_digest=attestation.attestation_digest)
        approval = evaluate_approval_authority(context=approval_context, capability=approver_capability, request=approval_request)
        capability_id = approval.capability_id
        if approval.decision is ApprovalAuthorityDecision.STALE:
            return TerminalPreconditionResult(TerminalPreconditionDecision.STALE, authoritative_snapshot, approval.reasons[0] if approval.reasons else "approval_authority_stale", observed_now_epoch=freshness.observed_now_epoch, attestation_digest=attestation.attestation_digest, approval_capability_id=capability_id)
        if approval.decision is not ApprovalAuthorityDecision.ALLOW:
            return TerminalPreconditionResult(TerminalPreconditionDecision.BLOCK, authoritative_snapshot, approval.reasons[0] if approval.reasons else "approval_authority_blocked", observed_now_epoch=freshness.observed_now_epoch, attestation_digest=attestation.attestation_digest, approval_capability_id=capability_id)

    return TerminalPreconditionResult(TerminalPreconditionDecision.READY, authoritative_snapshot, observed_now_epoch=freshness.observed_now_epoch, attestation_digest=attestation.attestation_digest, approval_capability_id=capability_id)


__all__ = ["TerminalPreconditionDecision", "TerminalPreconditionResult", "evaluate_terminal_preconditions"]
