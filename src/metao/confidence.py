"""Bound confidence advisory primitives for Roadmap 8 A14.

Confidence is advisory metadata produced by an identified verifier for an exact
request/result binding. It never grants authorization and cannot override a
hard-gate denial.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum
from math import isfinite


class ConfidenceAction(StrEnum):
    CONTINUE = "CONTINUE"
    ESCALATE = "ESCALATE"
    REJECT = "REJECT"


@dataclass(frozen=True)
class BoundConfidence:
    verifier_id: str
    verifier_version: str
    verification_request_id: str
    mission_id: str
    execution_id: str
    subject_id: str
    subject_state_id: str
    verification_context_id: str
    policy_bundle_id: str
    payload_digest: str
    score: float

    def __post_init__(self) -> None:
        bindings = (
            self.verifier_id,
            self.verifier_version,
            self.verification_request_id,
            self.mission_id,
            self.execution_id,
            self.subject_id,
            self.subject_state_id,
            self.verification_context_id,
            self.policy_bundle_id,
            self.payload_digest,
        )
        if not all(bindings):
            raise ValueError("bound confidence requires all identity bindings")
        if isinstance(self.score, bool) or not isinstance(self.score, (int, float)):
            raise TypeError("confidence score must be numeric")
        if not isfinite(float(self.score)) or not 0.0 <= self.score <= 1.0:
            raise ValueError("confidence score must be finite and within [0, 1]")


@dataclass(frozen=True)
class ConfidencePolicy:
    minimum_continue: float = 0.0
    minimum_escalate: float = 0.0

    def __post_init__(self) -> None:
        for name, value in (
            ("minimum_continue", self.minimum_continue),
            ("minimum_escalate", self.minimum_escalate),
        ):
            if isinstance(value, bool) or not isinstance(value, (int, float)):
                raise TypeError(f"{name} must be numeric")
            if not isfinite(float(value)) or not 0.0 <= value <= 1.0:
                raise ValueError(f"{name} must be finite and within [0, 1]")
        if self.minimum_escalate > self.minimum_continue:
            raise ValueError("minimum_escalate cannot exceed minimum_continue")


def advise_from_confidence(
    confidence: BoundConfidence,
    *,
    hard_gates_passed: bool,
    policy: ConfidencePolicy,
) -> ConfidenceAction:
    """Return an advisory action without creating terminal acceptance authority."""

    if not isinstance(hard_gates_passed, bool):
        raise TypeError("hard_gates_passed must be bool")
    if not hard_gates_passed:
        return ConfidenceAction.REJECT
    if confidence.score >= policy.minimum_continue:
        return ConfidenceAction.CONTINUE
    if confidence.score >= policy.minimum_escalate:
        return ConfidenceAction.ESCALATE
    return ConfidenceAction.REJECT


__all__ = [
    "ConfidenceAction",
    "BoundConfidence",
    "ConfidencePolicy",
    "advise_from_confidence",
]
