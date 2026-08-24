"""Framework-neutral active mission execution handles.

Handles bridge a synchronous orchestrator call with an external operator that
needs to request cancellation while the call is still in flight. The durable
record contains only control-plane identifiers; runtime SDK types stay outside
this boundary.
"""

from __future__ import annotations

from dataclasses import dataclass, replace
from enum import StrEnum
from threading import Lock
from typing import Protocol, runtime_checkable

from .core import ExecutionStatus


class ExecutionHandleStatus(StrEnum):
    ACTIVE = "ACTIVE"
    COMPLETED = "COMPLETED"


class ActiveExecutionNotFound(KeyError):
    pass


@dataclass(frozen=True)
class ActiveExecutionHandle:
    mission_id: str
    execution_id: str
    orchestrator_id: str
    attempt_number: int
    started_at_epoch: float
    cost: float = 0.0
    status: ExecutionHandleStatus = ExecutionHandleStatus.ACTIVE
    cancel_requested: bool = False
    cancel_delegated: bool = False
    ended_at_epoch: float | None = None
    execution_status: ExecutionStatus | None = None

    def __post_init__(self) -> None:
        if not self.mission_id or not self.execution_id or not self.orchestrator_id:
            raise ValueError("active execution handle requires mission/execution/orchestrator ids")
        if self.attempt_number < 1:
            raise ValueError("active execution attempt number must be positive")
        if self.started_at_epoch < 0:
            raise ValueError("active execution start timestamp must be non-negative")
        if self.ended_at_epoch is not None and self.ended_at_epoch < self.started_at_epoch:
            raise ValueError("active execution end timestamp cannot precede start")
        if self.cost < 0:
            raise ValueError("active execution cost must be non-negative")
        if self.status is ExecutionHandleStatus.COMPLETED and self.ended_at_epoch is None:
            raise ValueError("completed execution handle requires end timestamp")


@runtime_checkable
class ExecutionHandleStorePort(Protocol):
    def activate(self, handle: ActiveExecutionHandle) -> ActiveExecutionHandle: ...
    def get(self, mission_id: str) -> ActiveExecutionHandle: ...
    def request_cancel(self, mission_id: str) -> ActiveExecutionHandle: ...
    def mark_cancel_delegated(self, mission_id: str) -> ActiveExecutionHandle: ...
    def complete(
        self,
        mission_id: str,
        *,
        ended_at_epoch: float,
        execution_status: ExecutionStatus,
    ) -> ActiveExecutionHandle: ...


class InMemoryExecutionHandleStore:
    """Thread-safe process-local handle store used by tests and embeddings."""

    def __init__(self) -> None:
        self._items: dict[str, ActiveExecutionHandle] = {}
        self._lock = Lock()

    def activate(self, handle: ActiveExecutionHandle) -> ActiveExecutionHandle:
        with self._lock:
            previous = self._items.get(handle.mission_id)
            if previous is not None and previous.cancel_requested:
                handle = replace(
                    handle,
                    cancel_requested=True,
                    cancel_delegated=previous.cancel_delegated,
                )
            self._items[handle.mission_id] = handle
            return handle

    def get(self, mission_id: str) -> ActiveExecutionHandle:
        with self._lock:
            try:
                return self._items[mission_id]
            except KeyError as exc:
                raise ActiveExecutionNotFound(mission_id) from exc

    def request_cancel(self, mission_id: str) -> ActiveExecutionHandle:
        with self._lock:
            try:
                current = self._items[mission_id]
            except KeyError as exc:
                raise ActiveExecutionNotFound(mission_id) from exc
            updated = replace(current, cancel_requested=True)
            self._items[mission_id] = updated
            return updated

    def mark_cancel_delegated(self, mission_id: str) -> ActiveExecutionHandle:
        with self._lock:
            try:
                current = self._items[mission_id]
            except KeyError as exc:
                raise ActiveExecutionNotFound(mission_id) from exc
            updated = replace(current, cancel_requested=True, cancel_delegated=True)
            self._items[mission_id] = updated
            return updated

    def complete(
        self,
        mission_id: str,
        *,
        ended_at_epoch: float,
        execution_status: ExecutionStatus,
    ) -> ActiveExecutionHandle:
        with self._lock:
            try:
                current = self._items[mission_id]
            except KeyError as exc:
                raise ActiveExecutionNotFound(mission_id) from exc
            updated = replace(
                current,
                status=ExecutionHandleStatus.COMPLETED,
                ended_at_epoch=ended_at_epoch,
                execution_status=execution_status,
            )
            self._items[mission_id] = updated
            return updated


__all__ = [
    "ExecutionHandleStatus",
    "ActiveExecutionNotFound",
    "ActiveExecutionHandle",
    "ExecutionHandleStorePort",
    "InMemoryExecutionHandleStore",
]
