"""Framework-neutral observability contracts for metaO missions.

The event ledger is intentionally append-only and storage-neutral. Runtime or
orchestrator SDKs must not leak into this boundary. Durable implementations may
persist these events in SQLite or another backend without changing the control
plane contracts.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum
from threading import Lock
from types import MappingProxyType
from typing import Any, Mapping, Protocol, runtime_checkable


class MissionEventKind(StrEnum):
    MISSION_CREATED = "MISSION_CREATED"
    POLICY_EVALUATED = "POLICY_EVALUATED"
    APPROVAL_REQUESTED = "APPROVAL_REQUESTED"
    APPROVAL_RECORDED = "APPROVAL_RECORDED"
    MISSION_RESUMED = "MISSION_RESUMED"
    CANCELLATION_REQUESTED = "CANCELLATION_REQUESTED"
    ORCHESTRATOR_SELECTED = "ORCHESTRATOR_SELECTED"
    RUNTIME_STARTED = "RUNTIME_STARTED"
    RUNTIME_COMPLETED = "RUNTIME_COMPLETED"
    EVIDENCE_RECORDED = "EVIDENCE_RECORDED"
    ACCEPTANCE_EVALUATED = "ACCEPTANCE_EVALUATED"
    REPLAN_REQUESTED = "REPLAN_REQUESTED"
    MISSION_TERMINAL = "MISSION_TERMINAL"


def _freeze(value: Any) -> Any:
    if value is None or isinstance(value, (str, bool, int)):
        return value
    if isinstance(value, float):
        if value != value or value in (float("inf"), float("-inf")):
            raise TypeError("event payload does not support non-finite floats")
        return value
    if isinstance(value, Mapping):
        frozen: dict[str, Any] = {}
        for key, item in value.items():
            if not isinstance(key, str):
                raise TypeError("event payload mappings require string keys")
            frozen[key] = _freeze(item)
        return MappingProxyType(frozen)
    if isinstance(value, (list, tuple)):
        return tuple(_freeze(item) for item in value)
    raise TypeError(f"unsupported event payload value: {type(value).__name__}")


def thaw_event_value(value: Any) -> Any:
    """Return a JSON-compatible mutable representation of a frozen event value."""
    if isinstance(value, Mapping):
        return {str(key): thaw_event_value(item) for key, item in value.items()}
    if isinstance(value, tuple):
        return [thaw_event_value(item) for item in value]
    return value


@dataclass(frozen=True)
class MissionEvent:
    event_id: str
    mission_id: str
    sequence: int
    kind: MissionEventKind
    occurred_at_epoch: float
    payload: Mapping[str, Any]

    def __post_init__(self) -> None:
        if not self.event_id or not self.mission_id:
            raise ValueError("mission event requires event_id and mission_id")
        if self.sequence < 1:
            raise ValueError("mission event sequence must be positive")
        if self.occurred_at_epoch < 0:
            raise ValueError("mission event timestamp must be non-negative")
        object.__setattr__(self, "payload", _freeze(self.payload))


@runtime_checkable
class EventLedgerPort(Protocol):
    def append(
        self,
        mission_id: str,
        kind: MissionEventKind,
        *,
        payload: Mapping[str, Any] | None = None,
        occurred_at_epoch: float = 0.0,
    ) -> MissionEvent: ...

    def list(self, mission_id: str) -> tuple[MissionEvent, ...]: ...
    def all(self) -> tuple[MissionEvent, ...]: ...


class InMemoryEventLedger:
    """Thread-safe process-local append-only event ledger."""

    def __init__(self) -> None:
        self._events: dict[str, list[MissionEvent]] = {}
        self._lock = Lock()

    def append(
        self,
        mission_id: str,
        kind: MissionEventKind,
        *,
        payload: Mapping[str, Any] | None = None,
        occurred_at_epoch: float = 0.0,
    ) -> MissionEvent:
        if not mission_id:
            raise ValueError("mission_id is required")
        with self._lock:
            items = self._events.setdefault(mission_id, [])
            sequence = len(items) + 1
            event = MissionEvent(
                event_id=f"{mission_id}:event:{sequence}",
                mission_id=mission_id,
                sequence=sequence,
                kind=kind,
                occurred_at_epoch=occurred_at_epoch,
                payload=payload or {},
            )
            items.append(event)
            return event

    def list(self, mission_id: str) -> tuple[MissionEvent, ...]:
        with self._lock:
            return tuple(self._events.get(mission_id, ()))

    def all(self) -> tuple[MissionEvent, ...]:
        with self._lock:
            return tuple(
                event
                for mission_id in sorted(self._events)
                for event in self._events[mission_id]
            )


__all__ = [
    "MissionEventKind",
    "MissionEvent",
    "EventLedgerPort",
    "InMemoryEventLedger",
    "thaw_event_value",
]
