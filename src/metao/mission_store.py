"""Framework-neutral mission record storage boundary.

The port is the product boundary; in-memory, SQLite or another durable backend
can replace one another without changing control-plane or orchestrator contracts.
Mission records may also carry the framework-neutral run/approval context needed
for a truthful approval resume after process restart.
"""

from __future__ import annotations

from dataclasses import dataclass, replace
from typing import Protocol, runtime_checkable

from .acceptance import AcceptanceContext
from .control_plane import MissionOutcome, MissionStatus
from .core import Mission
from .governance import AcceptanceBudget, ApprovalRecord, ApprovalRequest, PolicyDecision


class MissionAlreadyExists(RuntimeError):
    """Raised when a mission id is created more than once."""


class MissionNotFound(KeyError):
    """Raised when a mission record does not exist."""


@dataclass(frozen=True)
class MissionRunContext:
    policy: PolicyDecision
    budget: AcceptanceBudget
    acceptance_context: AcceptanceContext
    execution_id_prefix: str
    max_attempts: int = 2

    def __post_init__(self) -> None:
        if not self.execution_id_prefix:
            raise ValueError("mission run context requires execution_id_prefix")
        if self.max_attempts < 1:
            raise ValueError("mission run context max_attempts must be at least 1")


@dataclass(frozen=True)
class MissionRecord:
    mission: Mission
    outcome: MissionOutcome
    revision: int = 1
    run_context: MissionRunContext | None = None
    approval_request: ApprovalRequest | None = None
    approval_record: ApprovalRecord | None = None

    def __post_init__(self) -> None:
        if self.mission.mission_id != self.outcome.mission_id:
            raise ValueError("mission record ids must match")
        if self.outcome.state is None:
            raise ValueError("mission record requires an auditable mission state")
        if self.revision < 1:
            raise ValueError("mission record revision must be positive")
        if self.approval_request is not None and self.approval_request.mission_id != self.mission.mission_id:
            raise ValueError("approval request mission id mismatch")
        if self.approval_record is not None:
            if self.approval_request is None:
                raise ValueError("approval record requires approval request")
            request = self.approval_request
            record = self.approval_record
            bindings = (
                request.approval_id == record.approval_id,
                request.mission_id == record.mission_id,
                request.execution_id == record.execution_id,
                request.subject_state_id == record.subject_state_id,
                request.policy_bundle_id == record.policy_bundle_id,
            )
            if not all(bindings):
                raise ValueError("approval record bindings do not match request")

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
    "MissionRunContext",
    "MissionRecord",
    "MissionStorePort",
    "InMemoryMissionStore",
]
