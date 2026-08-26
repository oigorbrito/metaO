"""Append-only factual verification attempt-start ledger for Roadmap 8 A18.

A verification attempt becomes a fact when metaO invokes the selected verifier.
This ledger records that fact before verifier execution so later verifier or
resource-meter failure cannot erase the attempt. It does not fabricate unknown
money/tokens and it has no terminal acceptance authority.
"""

from __future__ import annotations

from dataclasses import dataclass
from math import isfinite
from typing import Protocol, runtime_checkable


class VerificationAttemptDuplicate(RuntimeError):
    pass


@dataclass(frozen=True)
class VerificationAttemptStarted:
    attempt_record_id: str
    mission_id: str
    execution_id: str
    verification_request_id: str
    attempt_id: str
    verifier_id: str
    verifier_version: str
    started_at_epoch: float

    def __post_init__(self) -> None:
        if not all(
            (
                self.attempt_record_id,
                self.mission_id,
                self.execution_id,
                self.verification_request_id,
                self.attempt_id,
                self.verifier_id,
                self.verifier_version,
            )
        ):
            raise ValueError("verification attempt start requires all identity bindings")
        if isinstance(self.started_at_epoch, bool) or not isinstance(
            self.started_at_epoch, (int, float)
        ):
            raise TypeError("started_at_epoch must be numeric and non-boolean")
        if not isfinite(float(self.started_at_epoch)) or self.started_at_epoch < 0:
            raise ValueError("started_at_epoch must be finite and non-negative")


@runtime_checkable
class VerificationAttemptPort(Protocol):
    def append_started(self, event: VerificationAttemptStarted) -> None: ...

    def for_mission(self, mission_id: str) -> tuple[VerificationAttemptStarted, ...]: ...

    def for_verification_request(
        self, verification_request_id: str
    ) -> tuple[VerificationAttemptStarted, ...]: ...


class InMemoryVerificationAttemptStore:
    def __init__(self) -> None:
        self._by_id: dict[str, VerificationAttemptStarted] = {}
        self._attempt_keys: set[tuple[str, str, str, str, str]] = set()

    def append_started(self, event: VerificationAttemptStarted) -> None:
        if event.attempt_record_id in self._by_id:
            raise VerificationAttemptDuplicate(event.attempt_record_id)
        factual_key = (
            event.mission_id,
            event.execution_id,
            event.verification_request_id,
            event.attempt_id,
            event.verifier_id,
        )
        if factual_key in self._attempt_keys:
            raise VerificationAttemptDuplicate(":".join(factual_key))
        self._by_id[event.attempt_record_id] = event
        self._attempt_keys.add(factual_key)

    def for_mission(self, mission_id: str) -> tuple[VerificationAttemptStarted, ...]:
        return tuple(
            item for item in self._ordered() if item.mission_id == mission_id
        )

    def for_verification_request(
        self, verification_request_id: str
    ) -> tuple[VerificationAttemptStarted, ...]:
        return tuple(
            item
            for item in self._ordered()
            if item.verification_request_id == verification_request_id
        )

    def _ordered(self) -> tuple[VerificationAttemptStarted, ...]:
        return tuple(
            sorted(
                self._by_id.values(),
                key=lambda item: (item.started_at_epoch, item.attempt_record_id),
            )
        )


__all__ = [
    "VerificationAttemptDuplicate",
    "VerificationAttemptStarted",
    "VerificationAttemptPort",
    "InMemoryVerificationAttemptStore",
]
