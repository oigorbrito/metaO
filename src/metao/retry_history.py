"""Append-only factual execution/retry history for metaO.

MissionStorePort remains the current operational snapshot. RetryHistoryPort is
the factual authority for started execution attempts and their terminal facts.
A11 intentionally does not account verification money/tokens/time; that belongs
to A18 acceptance usage accounting.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum
from math import isfinite
from typing import Protocol, runtime_checkable


class RetryOutcome(StrEnum):
    SUCCEEDED = "SUCCEEDED"
    FAILED = "FAILED"
    CANCELLED = "CANCELLED"
    BLOCKED = "BLOCKED"


@dataclass(frozen=True)
class RetryHistoryEntry:
    history_id: str
    mission_id: str
    attempt_number: int
    execution_id: str
    orchestrator_id: str
    started_at_epoch: float
    ended_at_epoch: float
    outcome: RetryOutcome
    execution_cost: float = 0.0
    failure_class: str = ""

    def __post_init__(self) -> None:
        if not all((self.history_id, self.mission_id, self.execution_id, self.orchestrator_id)):
            raise ValueError("retry history entry requires identity bindings")
        if isinstance(self.attempt_number, bool) or not isinstance(self.attempt_number, int) or self.attempt_number < 1:
            raise ValueError("retry history attempt number must be a positive integer")
        if not all(isfinite(value) for value in (self.started_at_epoch, self.ended_at_epoch, self.execution_cost)):
            raise ValueError("retry history numeric values must be finite")
        if self.started_at_epoch < 0 or self.ended_at_epoch < 0:
            raise ValueError("retry history timestamps must be non-negative")
        if self.ended_at_epoch < self.started_at_epoch:
            raise ValueError("retry history end cannot precede start")
        if self.execution_cost < 0:
            raise ValueError("retry history execution cost must be non-negative")


@runtime_checkable
class RetryHistoryPort(Protocol):
    def append(self, entry: RetryHistoryEntry) -> None: ...
    def for_mission(self, mission_id: str) -> tuple[RetryHistoryEntry, ...]: ...
    def all(self) -> tuple[RetryHistoryEntry, ...]: ...


class RetryHistoryDuplicate(RuntimeError):
    pass


class InMemoryRetryHistoryStore:
    def __init__(self) -> None:
        self._entries: list[RetryHistoryEntry] = []
        self._ids: set[str] = set()
        self._attempt_keys: set[tuple[str, int, str]] = set()

    def append(self, entry: RetryHistoryEntry) -> None:
        if entry.history_id in self._ids:
            raise RetryHistoryDuplicate(entry.history_id)
        attempt_key = (entry.mission_id, entry.attempt_number, entry.execution_id)
        if attempt_key in self._attempt_keys:
            raise RetryHistoryDuplicate(
                f"{entry.mission_id}:{entry.attempt_number}:{entry.execution_id}"
            )
        self._ids.add(entry.history_id)
        self._attempt_keys.add(attempt_key)
        self._entries.append(entry)

    def for_mission(self, mission_id: str) -> tuple[RetryHistoryEntry, ...]:
        return tuple(
            sorted(
                (entry for entry in self._entries if entry.mission_id == mission_id),
                key=lambda entry: (entry.attempt_number, entry.started_at_epoch, entry.history_id),
            )
        )

    def all(self) -> tuple[RetryHistoryEntry, ...]:
        return tuple(self._entries)


__all__ = [
    "RetryOutcome",
    "RetryHistoryEntry",
    "RetryHistoryPort",
    "RetryHistoryDuplicate",
    "InMemoryRetryHistoryStore",
]
