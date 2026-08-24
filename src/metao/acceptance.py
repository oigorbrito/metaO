"""Framework-neutral final acceptance authority for metaO.

Core acceptance semantics are adapted from OMA at the frozen Block-C pin:
- executor completion is never final acceptance;
- evidence is bound to subject/state/context/policy/obligation;
- duplicate, conflicting, unknown, or mis-bound evidence fails closed;
- incomplete/failed required evidence is NOT_DONE;
- stale evidence is STALE;
- ACCEPT requires the exact required, correctly bound, passing evidence set.

The final decision is deterministic over recorded evidence.
"""

from __future__ import annotations

from dataclasses import dataclass, field, replace
from enum import Enum
from hashlib import sha256
import json
from typing import Iterable, Optional, Sequence, Tuple


class AcceptanceDecision(str, Enum):
    ACCEPT = "ACCEPT"
    NOT_DONE = "NOT_DONE"
    STALE = "STALE"
    BLOCK = "BLOCK"
    REQUIRE_HUMAN = "REQUIRE_HUMAN"


class ConflictDecision(str, Enum):
    NONE = "NONE"
    DUPLICATE = "DUPLICATE"
    CONFLICT = "CONFLICT"
    UNEXPECTED = "UNEXPECTED"


@dataclass(frozen=True)
class EvidenceEnvelope:
    evidence_id: str
    obligation_id: str
    mission_id: str
    execution_id: str
    orchestrator_id: str
    adapter_version: str
    attempt_id: str
    subject_id: str
    subject_state_id: str
    verification_context_id: str
    policy_bundle_id: str
    verifier_id: str
    payload_digest: str
    provenance_root: str
    authority_id: str
    passed: bool
    created_at_epoch: float = 0.0
    expires_at_epoch: Optional[float] = None
    approval_id: Optional[str] = None
    confidence: Optional[float] = None


@dataclass(frozen=True)
class AcceptanceContext:
    subject_id: str
    subject_state_id: str
    verification_context_id: str
    policy_bundle_id: str
    required_obligations: frozenset[str]
    trusted_verifiers: frozenset[str] = frozenset()
    trusted_provenance_roots: frozenset[str] = frozenset()
    authorized_authorities: frozenset[str] = frozenset()


@dataclass(frozen=True)
class RequiredEvidenceSet:
    obligations: frozenset[str]


@dataclass(frozen=True)
class GateResult:
    passed: bool
    decision: AcceptanceDecision = AcceptanceDecision.BLOCK
    reason: str = ""


@dataclass(frozen=True)
class AggregationResult:
    decision: AcceptanceDecision
    reasons: Tuple[str, ...] = ()
    conflict: ConflictDecision = ConflictDecision.NONE


@dataclass(frozen=True)
class AcceptanceProof:
    decision: AcceptanceDecision
    reasons: Tuple[str, ...]
    evidence_ids: Tuple[str, ...]
    digest: str


@dataclass(frozen=True)
class AcceptanceResult:
    decision: AcceptanceDecision
    reasons: Tuple[str, ...] = ()
    proof: Optional[AcceptanceProof] = None


def _digest_payload(payload: object) -> str:
    encoded = json.dumps(payload, sort_keys=True, separators=(",", ":"), default=str).encode()
    return sha256(encoded).hexdigest()


def check_freshness(evidence: EvidenceEnvelope, *, now_epoch: float) -> GateResult:
    if evidence.expires_at_epoch is not None and now_epoch > evidence.expires_at_epoch:
        return GateResult(False, AcceptanceDecision.STALE, "evidence_expired")
    if evidence.created_at_epoch and evidence.created_at_epoch > now_epoch:
        return GateResult(False, AcceptanceDecision.BLOCK, "evidence_from_future")
    return GateResult(True, AcceptanceDecision.ACCEPT)


def check_provenance(evidence: EvidenceEnvelope, context: AcceptanceContext) -> GateResult:
    if not evidence.payload_digest or not evidence.provenance_root:
        return GateResult(False, AcceptanceDecision.BLOCK, "missing_provenance")
    if context.trusted_verifiers and evidence.verifier_id not in context.trusted_verifiers:
        return GateResult(False, AcceptanceDecision.BLOCK, "untrusted_verifier")
    if (
        context.trusted_provenance_roots
        and evidence.provenance_root not in context.trusted_provenance_roots
    ):
        return GateResult(False, AcceptanceDecision.BLOCK, "untrusted_provenance_root")
    return GateResult(True, AcceptanceDecision.ACCEPT)


def check_authority(evidence: EvidenceEnvelope, context: AcceptanceContext) -> GateResult:
    if not evidence.authority_id:
        return GateResult(False, AcceptanceDecision.BLOCK, "missing_authority")
    if (
        context.authorized_authorities
        and evidence.authority_id not in context.authorized_authorities
    ):
        return GateResult(False, AcceptanceDecision.BLOCK, "unauthorized_authority")
    return GateResult(True, AcceptanceDecision.ACCEPT)


def check_policy(evidence: EvidenceEnvelope, context: AcceptanceContext) -> GateResult:
    if evidence.policy_bundle_id != context.policy_bundle_id:
        return GateResult(False, AcceptanceDecision.BLOCK, "policy_bundle_mismatch")
    return GateResult(True, AcceptanceDecision.ACCEPT)


def _binding_gate(evidence: EvidenceEnvelope, context: AcceptanceContext) -> GateResult:
    if evidence.subject_id != context.subject_id:
        return GateResult(False, AcceptanceDecision.BLOCK, "subject_mismatch")
    if evidence.subject_state_id != context.subject_state_id:
        return GateResult(False, AcceptanceDecision.STALE, "subject_state_mismatch")
    if evidence.verification_context_id != context.verification_context_id:
        return GateResult(False, AcceptanceDecision.BLOCK, "verification_context_mismatch")
    if evidence.policy_bundle_id != context.policy_bundle_id:
        return GateResult(False, AcceptanceDecision.BLOCK, "policy_bundle_mismatch")
    return GateResult(True, AcceptanceDecision.ACCEPT)


def aggregate_evidence(
    required: RequiredEvidenceSet,
    evidence: Iterable[EvidenceEnvelope],
) -> AggregationResult:
    items = tuple(evidence)
    ids = [item.evidence_id for item in items]
    if len(ids) != len(set(ids)):
        return AggregationResult(
            AcceptanceDecision.BLOCK,
            ("duplicate_evidence_id",),
            ConflictDecision.DUPLICATE,
        )

    by_obligation: dict[str, EvidenceEnvelope] = {}
    for item in items:
        if item.obligation_id not in required.obligations:
            return AggregationResult(
                AcceptanceDecision.BLOCK,
                (f"unexpected_obligation:{item.obligation_id}",),
                ConflictDecision.UNEXPECTED,
            )
        existing = by_obligation.get(item.obligation_id)
        if existing is not None:
            reason = "conflicting_obligation_evidence" if existing != item else "duplicate_obligation_evidence"
            conflict = ConflictDecision.CONFLICT if existing != item else ConflictDecision.DUPLICATE
            return AggregationResult(AcceptanceDecision.BLOCK, (reason,), conflict)
        by_obligation[item.obligation_id] = item

    missing = sorted(required.obligations - by_obligation.keys())
    if missing:
        return AggregationResult(
            AcceptanceDecision.NOT_DONE,
            tuple(f"missing_obligation:{name}" for name in missing),
        )

    failed = sorted(name for name, item in by_obligation.items() if not item.passed)
    if failed:
        return AggregationResult(
            AcceptanceDecision.NOT_DONE,
            tuple(f"failed_obligation:{name}" for name in failed),
        )

    return AggregationResult(AcceptanceDecision.ACCEPT)


def _make_proof(
    decision: AcceptanceDecision,
    reasons: Sequence[str],
    evidence: Iterable[EvidenceEnvelope],
) -> AcceptanceProof:
    evidence_ids = tuple(sorted(item.evidence_id for item in evidence))
    reasons_tuple = tuple(reasons)
    digest = _digest_payload(
        {
            "decision": decision.value,
            "reasons": reasons_tuple,
            "evidence_ids": evidence_ids,
        }
    )
    return AcceptanceProof(decision, reasons_tuple, evidence_ids, digest)


def replay_acceptance_decision(proof: AcceptanceProof) -> AcceptanceDecision:
    expected = _digest_payload(
        {
            "decision": proof.decision.value,
            "reasons": proof.reasons,
            "evidence_ids": proof.evidence_ids,
        }
    )
    if expected != proof.digest:
        raise ValueError("acceptance proof digest mismatch")
    return proof.decision


def evaluate_acceptance(
    context: AcceptanceContext,
    evidence: Iterable[EvidenceEnvelope],
    *,
    now_epoch: float = 0.0,
    executor_done: bool = False,
) -> AcceptanceResult:
    """Return metaO's final decision; executor_done is intentionally non-authoritative."""

    items = tuple(evidence)

    ids = [item.evidence_id for item in items]
    if len(ids) != len(set(ids)):
        reasons = ("duplicate_evidence_id",)
        return AcceptanceResult(
            AcceptanceDecision.BLOCK,
            reasons,
            _make_proof(AcceptanceDecision.BLOCK, reasons, items),
        )

    seen_obligations: dict[str, EvidenceEnvelope] = {}
    for item in items:
        if item.obligation_id not in context.required_obligations:
            reasons = ("unknown_obligation",)
            return AcceptanceResult(
                AcceptanceDecision.BLOCK,
                reasons,
                _make_proof(AcceptanceDecision.BLOCK, reasons, items),
            )
        if item.obligation_id in seen_obligations:
            reasons = ("duplicate_or_conflicting_obligation_evidence",)
            return AcceptanceResult(
                AcceptanceDecision.BLOCK,
                reasons,
                _make_proof(AcceptanceDecision.BLOCK, reasons, items),
            )
        seen_obligations[item.obligation_id] = item

        for gate in (
            _binding_gate(item, context),
            check_freshness(item, now_epoch=now_epoch),
            check_provenance(item, context),
            check_authority(item, context),
            check_policy(item, context),
        ):
            if not gate.passed:
                reasons = (gate.reason,)
                return AcceptanceResult(
                    gate.decision,
                    reasons,
                    _make_proof(gate.decision, reasons, items),
                )

    aggregation = aggregate_evidence(
        RequiredEvidenceSet(context.required_obligations), items
    )
    proof = _make_proof(aggregation.decision, aggregation.reasons, items)
    return AcceptanceResult(aggregation.decision, aggregation.reasons, proof)


__all__ = [
    "AcceptanceDecision",
    "ConflictDecision",
    "EvidenceEnvelope",
    "AcceptanceContext",
    "RequiredEvidenceSet",
    "GateResult",
    "AggregationResult",
    "AcceptanceProof",
    "AcceptanceResult",
    "check_freshness",
    "check_provenance",
    "check_authority",
    "check_policy",
    "aggregate_evidence",
    "evaluate_acceptance",
    "replay_acceptance_decision",
]
