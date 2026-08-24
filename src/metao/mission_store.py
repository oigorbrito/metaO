"""Framework-neutral mission record storage boundary.

The first implementation is intentionally in-memory. The port is the product
boundary; SQLite or another durable backend can replace it without changing the
control-plane or orchestrator contracts.
"""

from __future__ import annotations

from dataclasses import dataclass, replace
from typing import Protocol, runtime_checkable

from .control_plane import MissionOutcome, MissionStatus
from .core import Mission


class MissionAlreadyExists(RuntimeError):
    """Raised when a mission id is created more than once."""


class MissionNotFound(KeyError):
    """Raised when a mission record does not exist."""


@dataclass(frozen=True)
class MissionRecord:
    mission: Mission
    outcome: MissionOutcome
    revision: int = 1

    def __post_init__(self) -> None:
        if self.mission.mission_id != self.outcome.mission_id:
            raise ValueError("mission record ids must match")
        if self.outcome.state is None:
            raise ValueError("mission record requires an auditable mission state")
        if self.revision < 1:
            raise ValueError("mission record revision must be positive")

    @property
    def mission_id(self) -> str:
        return self.mission.mission_id

    @property
    def status(self) -> MissionStatus:
        assert self.outcome.state is not None
        return self.outcome.state.status


@runtime_checkable
class MissionStorePort(Protocol):
    def contains(self, mission_id: str) -> bool: ...
    def create(self, record: MissionRecord) -> None: ...
    def get(self, mission_id: str) -> MissionRecord: ...
    def replace(self, record: MissionRecord) -> MissionRecord: ...
    def list(self) -> tuple[MissionRecord, ...]: ...


class InMemoryMissionStore:
    """Deterministic process-local MissionStorePort implementation."""

    def __init__(self) -> None:
        self._records: dict[str, MissionRecord] = {}

    def contains(self, mission_id: str) -> bool:
        return mission_id in self._records

    def create(self, record: MissionRecord) -> None:
        if record.mission_id in self._records:
            raise MissionAlreadyExists(record.mission_id)
        self._records[record.mission_id] = record

    def get(self, mission_id: str) -> MissionRecord:
        try:
            return self._records[mission_id]
        except KeyError as exc:
            raise MissionNotFound(mission_id) from exc

    def replace(self, record: MissionRecord) -> MissionRecord:
        current = self.get(record.mission_id)
        updated = replace(record, revision=current.revision + 1)
        self._records[record.mission_id] = updated
        return updated

    def list(self) -> tuple[MissionRecord, ...]:
        return tuple(self._records[key] for key in sorted(self._records))


__all__ = [
    "MissionAlreadyExists",
    "MissionNotFound",
    "MissionRecord",
    "MissionStorePort",
    "InMemoryMissionStore",
]
