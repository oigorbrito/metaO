"""Runtime invariants for metaO.

Adapted from proven donor semantics:
- OpenLinker singleton lease / lock ownership: lease expiry, holder loss,
  non-overlapping ownership, and stale-holder protection.
- AgentField restart semantics: preserve successful progress and replay only
  work that still needs execution.

This module stays framework-neutral and contains no orchestrator SDK imports.
"""

from __future__ import annotations

from contextlib import contextmanager
from dataclasses import dataclass, field
from threading import Lock, RLock
from time import monotonic
from typing import Dict, Hashable, Iterable, Iterator, MutableSet, Optional, Sequence, Set, Tuple


class StaleWorkerError(RuntimeError):
    """Raised when a worker presents an obsolete fencing token."""


@dataclass(frozen=True, order=True)
class FencingToken:
    """Monotonic ownership token.

    A newer lease always receives a greater generation. Operations carrying an
    older generation are rejected, preventing a previously valid worker from
    acting after failover.
    """

    generation: int
    holder_id: str = field(compare=False)


@dataclass
class Lease:
    """Time-bounded ownership lease with a fencing token."""

    key: str
    holder_id: str
    token: FencingToken
    ttl_seconds: float
    acquired_at: float = field(default_factory=monotonic)
    last_confirmed_at: float = field(default_factory=monotonic)
    released: bool = False

    def is_active(self, now: Optional[float] = None) -> bool:
        if self.released:
            return False
        current = monotonic() if now is None else now
        return current - self.last_confirmed_at < self.ttl_seconds

    def confirm(self, now: Optional[float] = None) -> None:
        if self.released:
            raise RuntimeError("cannot confirm a released lease")
        self.last_confirmed_at = monotonic() if now is None else now

    def release(self) -> None:
        self.released = True


def reject_stale_worker(current: FencingToken, presented: FencingToken) -> bool:
    """Reject a worker whose fencing generation is older than current."""

    if presented.generation < current.generation:
        raise StaleWorkerError(
            f"stale worker token {presented.generation}; current is {current.generation}"
        )
    if presented.generation == current.generation and presented.holder_id != current.holder_id:
        raise StaleWorkerError("fencing generation belongs to a different holder")
    return True


@dataclass(frozen=True)
class IdempotencyKey:
    value: str

    def __post_init__(self) -> None:
        if not self.value or not self.value.strip():
            raise ValueError("idempotency key must be non-empty")


def deduplicate_event(key: IdempotencyKey, seen: MutableSet[str]) -> bool:
    """Return True exactly once for a key; later deliveries are replays."""

    if key.value in seen:
        return False
    seen.add(key.value)
    return True


class ConcurrencyGuard:
    """Per-resource in-process exclusion guard.

    The API mirrors the donor invariant that overlapping work for one ownership
    domain is absorbed/serialized rather than stacked concurrently.
    """

    def __init__(self) -> None:
        self._locks: Dict[Hashable, Lock] = {}
        self._meta_lock = RLock()

    def _lock_for(self, key: Hashable) -> Lock:
        with self._meta_lock:
            return self._locks.setdefault(key, Lock())

    @contextmanager
    def hold(self, key: Hashable, *, blocking: bool = True) -> Iterator[bool]:
        lock = self._lock_for(key)
        acquired = lock.acquire(blocking=blocking)
        try:
            yield acquired
        finally:
            if acquired:
                lock.release()


class ReplayGuard:
    """Reject duplicate execution/event identifiers deterministically."""

    def __init__(self, previously_seen: Optional[Iterable[str]] = None) -> None:
        self._seen: Set[str] = set(previously_seen or ())
        self._lock = Lock()

    def accept(self, event_id: str) -> bool:
        if not event_id:
            raise ValueError("event_id must be non-empty")
        with self._lock:
            if event_id in self._seen:
                return False
            self._seen.add(event_id)
            return True

    def has_seen(self, event_id: str) -> bool:
        with self._lock:
            return event_id in self._seen


@dataclass(frozen=True)
class RecoveryState:
    """Authoritative progress snapshot used to build a restart plan."""

    successful_steps: frozenset[str] = frozenset()
    failed_steps: frozenset[str] = frozenset()


def recover_preserving_success(
    state: RecoveryState, planned_steps: Sequence[str]
) -> Tuple[Tuple[str, ...], Tuple[str, ...]]:
    """Return (reused_successes, steps_to_execute).

    Successful upstream work is preserved; every non-successful planned step is
    scheduled again. Ordering follows the supplied workflow plan.
    """

    reused = tuple(step for step in planned_steps if step in state.successful_steps)
    pending = tuple(step for step in planned_steps if step not in state.successful_steps)
    return reused, pending


__all__ = [
    "Lease",
    "FencingToken",
    "StaleWorkerError",
    "reject_stale_worker",
    "IdempotencyKey",
    "deduplicate_event",
    "ConcurrencyGuard",
    "ReplayGuard",
    "RecoveryState",
    "recover_preserving_success",
]
