"""Framework-neutral durable runtime control records.

Runtime quarantine is an explicit control-plane decision. It does not mutate a
runtime, its adapter, or its routing score. Instead it overlays an operator
control state on the live catalog so a quarantined runtime is ineligible until
explicitly restored.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum
from threading import RLock
from typing import Protocol, runtime_checkable


class RuntimeDisposition(StrEnum):
    ACTIVE = "ACTIVE"
    QUARANTINED = "QUARANTINED"


@dataclass(frozen=True, slots=True)
class RuntimeControlRecord:
    orchestrator_id: str
    disposition: RuntimeDisposition
    reason: str
    actor_id: str
    updated_at_epoch: float
    revision: int

    def __post_init__(self) -> None:
        if not self.orchestrator_id:
            raise ValueError("orchestrator_id is required")
        if not self.reason:
            raise ValueError("runtime control reason is required")
        if not self.actor_id:
            raise ValueError("runtime control actor_id is required")
        if self.updated_at_epoch < 0:
            raise ValueError("updated_at_epoch must be non-negative")
        if self.revision < 1:
            raise ValueError("runtime control revision must be at least 1")


@runtime_checkable
class RuntimeControlStorePort(Protocol):
    def set(
        self,
        orchestrator_id: str,
        disposition: RuntimeDisposition,
        *,
        reason: str,
        actor_id: str,
        updated_at_epoch: float,
    ) -> RuntimeControlRecord: ...

    def current(self, orchestrator_id: str) -> RuntimeControlRecord | None: ...

    def list_current(self) -> tuple[RuntimeControlRecord, ...]: ...

    def history(self, orchestrator_id: str) -> tuple[RuntimeControlRecord, ...]: ...


class InMemoryRuntimeControlStore:
    """Process-local reference implementation with immutable revision history."""

    def __init__(self) -> None:
        self._history: dict[str, tuple[RuntimeControlRecord, ...]] = {}
        self._lock = RLock()

    def set(
        self,
        orchestrator_id: str,
        disposition: RuntimeDisposition,
        *,
        reason: str,
        actor_id: str,
        updated_at_epoch: float,
    ) -> RuntimeControlRecord:
        if not isinstance(disposition, RuntimeDisposition):
            raise ValueError("invalid runtime disposition")
        with self._lock:
            previous = self._history.get(orchestrator_id, ())
            record = RuntimeControlRecord(
                orchestrator_id=orchestrator_id,
                disposition=disposition,
                reason=reason,
                actor_id=actor_id,
                updated_at_epoch=updated_at_epoch,
                revision=len(previous) + 1,
            )
            self._history[orchestrator_id] = previous + (record,)
            return record

    def current(self, orchestrator_id: str) -> RuntimeControlRecord | None:
        with self._lock:
            items = self._history.get(orchestrator_id, ())
            return items[-1] if items else None

    def list_current(self) -> tuple[RuntimeControlRecord, ...]:
        with self._lock:
            return tuple(
                self._history[key][-1]
                for key in sorted(self._history)
                if self._history[key]
            )

    def history(self, orchestrator_id: str) -> tuple[RuntimeControlRecord, ...]:
        with self._lock:
            return self._history.get(orchestrator_id, ())


def quarantine(
    store: RuntimeControlStorePort,
    orchestrator_id: str,
    *,
    reason: str,
    actor_id: str,
    updated_at_epoch: float,
) -> RuntimeControlRecord:
    return store.set(
        orchestrator_id,
        RuntimeDisposition.QUARANTINED,
        reason=reason,
        actor_id=actor_id,
        updated_at_epoch=updated_at_epoch,
    )


def restore(
    store: RuntimeControlStorePort,
    orchestrator_id: str,
    *,
    reason: str,
    actor_id: str,
    updated_at_epoch: float,
) -> RuntimeControlRecord:
    return store.set(
        orchestrator_id,
        RuntimeDisposition.ACTIVE,
        reason=reason,
        actor_id=actor_id,
        updated_at_epoch=updated_at_epoch,
    )


__all__ = [
    "RuntimeDisposition",
    "RuntimeControlRecord",
    "RuntimeControlStorePort",
    "InMemoryRuntimeControlStore",
    "quarantine",
    "restore",
]
