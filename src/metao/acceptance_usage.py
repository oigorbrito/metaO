"""Framework-neutral acceptance/verification usage accounting boundary.

A18 owns factual resource usage for independent verification and acceptance work.
It is intentionally separate from runtime retry history and from the policy limit
object in :mod:`metao.governance`.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum
from typing import Protocol, runtime_checkable


class VerificationOutcome(StrEnum):
    """Terminal observation for one verification attempt.

    This is factual execution state only. It is not metaO final acceptance.
    """

    PASS = "PASS"
    FAIL = "FAIL"
    ERROR = "ERROR"
    TIMEOUT = "TIMEOUT"
    CANCELLED = "CANCELLED"
    INVALID_RESULT = "INVALID_RESULT"


class DuplicateUsage(RuntimeError):
    """Raised when an append-only usage id is written more than once."""


@dataclass(frozen=True)
class VerificationUsage:
    """Append-only factual usage for one bound verification attempt."""

    usage_id: str
    mission_id: str
    execution_id: str
    attempt_id: str
    verifier_id: str
    verification_request_id: str
    subject_id: str
    subject_state_id: str
    verification_context_id: str
    policy_bundle_id: str
    started_at_epoch: float
    ended_at_epoch: float
    money: float
    tokens: int
    wall_time_s: float
    verifier_attempts: int
    outcome: VerificationOutcome

    def __post_init__(self) -> None:
        required_ids = (
            self.usage_id,
            self.mission_id,
            self.execution_id,
            self.attempt_id,
            self.verifier_id,
            self.verification_request_id,
            self.subject_id,
            self.subject_state_id,
            self.verification_context_id,
            self.policy_bundle_id,
        )
        if not all(required_ids):
            raise ValueError("verification usage requires all identity bindings")
        if self.started_at_epoch < 0 or self.ended_at_epoch < 0:
            raise ValueError("verification usage timestamps must be non-negative")
        if self.ended_at_epoch < self.started_at_epoch:
            raise ValueError("verification usage end timestamp cannot precede start")
        if self.money < 0 or self.tokens < 0 or self.wall_time_s < 0:
            raise ValueError("verification resource usage cannot be negative")
        if self.verifier_attempts != 1:
            raise ValueError("one VerificationUsage record must represent exactly one attempt")


@runtime_checkable
class AcceptanceUsagePort(Protocol):
    """Append-only authority for factual acceptance usage."""

    def append(self, usage: VerificationUsage) -> None: ...

    def for_mission(self, mission_id: str) -> tuple[VerificationUsage, ...]: ...

    def for_verification_request(
        self, verification_request_id: str
    ) -> tuple[VerificationUsage, ...]: ...


class InMemoryAcceptanceUsageStore:
    """Deterministic process-local AcceptanceUsagePort implementation."""

    def __init__(self) -> None:
        self._by_id: dict[str, VerificationUsage] = {}

    def append(self, usage: VerificationUsage) -> None:
        if usage.usage_id in self._by_id:
            raise DuplicateUsage(usage.usage_id)
        self._by_id[usage.usage_id] = usage

    def for_mission(self, mission_id: str) -> tuple[VerificationUsage, ...]:
        return tuple(
            item
            for item in self._ordered()
            if item.mission_id == mission_id
        )

    def for_verification_request(
        self, verification_request_id: str
    ) -> tuple[VerificationUsage, ...]:
        return tuple(
            item
            for item in self._ordered()
            if item.verification_request_id == verification_request_id
        )

    def _ordered(self) -> tuple[VerificationUsage, ...]:
        return tuple(
            sorted(
                self._by_id.values(),
                key=lambda item: (item.started_at_epoch, item.usage_id),
            )
        )


__all__ = [
    "VerificationOutcome",
    "DuplicateUsage",
    "VerificationUsage",
    "AcceptanceUsagePort",
    "InMemoryAcceptanceUsageStore",
]
