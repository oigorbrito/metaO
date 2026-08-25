"""Declarative adversarial acceptance harness for Roadmap 8 A19.

This module defines the attack matrix and expected fail-closed terminal defense.
It does not execute final acceptance itself and does not claim those attacks are
already proven through the composed terminal path.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum


class AttackVector(StrEnum):
    FALSE_DONE = "FALSE_DONE"
    STALE_STATE = "STALE_STATE"
    EVIDENCE_SUBSTITUTION = "EVIDENCE_SUBSTITUTION"
    EVIDENCE_REPLAY = "EVIDENCE_REPLAY"
    EVIDENCE_CONFLICT = "EVIDENCE_CONFLICT"
    UNTRUSTED_VERIFIER = "UNTRUSTED_VERIFIER"
    FABRICATED_AUTHORITY = "FABRICATED_AUTHORITY"
    POLICY_SUBSTITUTION = "POLICY_SUBSTITUTION"
    OMITTED_RETRY_HISTORY = "OMITTED_RETRY_HISTORY"
    BUDGET_RESET = "BUDGET_RESET"
    STALE_APPROVAL = "STALE_APPROVAL"
    PROVENANCE_SUBSTITUTION = "PROVENANCE_SUBSTITUTION"
    HOSTILE_ATTESTATION_FAILURE = "HOSTILE_ATTESTATION_FAILURE"


class ExpectedDecision(StrEnum):
    BLOCK = "BLOCK"
    STALE = "STALE"
    NOT_DONE = "NOT_DONE"
    REQUIRE_HUMAN = "REQUIRE_HUMAN"


@dataclass(frozen=True)
class AdversarialCase:
    vector: AttackVector
    expected_decision: ExpectedDecision
    expected_gate: str
    accepted_terminal_record_allowed: bool = False

    def __post_init__(self) -> None:
        if not self.expected_gate:
            raise ValueError("adversarial case requires expected_gate")
        if self.accepted_terminal_record_allowed:
            raise ValueError("A19 hostile cases must never allow accepted terminal records")


STANDARD_A19_MATRIX: tuple[AdversarialCase, ...] = (
    AdversarialCase(AttackVector.FALSE_DONE, ExpectedDecision.NOT_DONE, "independent_acceptance"),
    AdversarialCase(AttackVector.STALE_STATE, ExpectedDecision.STALE, "authoritative_subject_state"),
    AdversarialCase(AttackVector.EVIDENCE_SUBSTITUTION, ExpectedDecision.BLOCK, "evidence_binding"),
    AdversarialCase(AttackVector.EVIDENCE_REPLAY, ExpectedDecision.BLOCK, "replay_detection"),
    AdversarialCase(AttackVector.EVIDENCE_CONFLICT, ExpectedDecision.BLOCK, "evidence_aggregation"),
    AdversarialCase(AttackVector.UNTRUSTED_VERIFIER, ExpectedDecision.BLOCK, "verifier_authority"),
    AdversarialCase(AttackVector.FABRICATED_AUTHORITY, ExpectedDecision.BLOCK, "authority_registry"),
    AdversarialCase(AttackVector.POLICY_SUBSTITUTION, ExpectedDecision.BLOCK, "policy_registry"),
    AdversarialCase(AttackVector.OMITTED_RETRY_HISTORY, ExpectedDecision.BLOCK, "retry_history_authority"),
    AdversarialCase(AttackVector.BUDGET_RESET, ExpectedDecision.BLOCK, "acceptance_budget"),
    AdversarialCase(AttackVector.STALE_APPROVAL, ExpectedDecision.BLOCK, "approval_authority"),
    AdversarialCase(AttackVector.PROVENANCE_SUBSTITUTION, ExpectedDecision.BLOCK, "provenance_binding"),
    AdversarialCase(AttackVector.HOSTILE_ATTESTATION_FAILURE, ExpectedDecision.BLOCK, "attestation_provider"),
)


def validate_attack_matrix(cases: tuple[AdversarialCase, ...] = STANDARD_A19_MATRIX) -> None:
    vectors = [case.vector for case in cases]
    if len(vectors) != len(set(vectors)):
        raise ValueError("adversarial matrix contains duplicate attack vectors")
    missing = set(AttackVector) - set(vectors)
    if missing:
        raise ValueError(f"adversarial matrix missing vectors: {sorted(item.value for item in missing)}")


__all__ = [
    "AttackVector",
    "ExpectedDecision",
    "AdversarialCase",
    "STANDARD_A19_MATRIX",
    "validate_attack_matrix",
]
