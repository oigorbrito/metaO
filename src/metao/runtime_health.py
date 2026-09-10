"""Framework-neutral factual runtime health for real adapter executions.

This module mirrors the authority boundary of the canonical Rust runtime-health
contract: adapter-verified execution outcomes are factual health evidence;
structural readiness and runtime self-report are not.

Health stores persist execution facts, never derived state. A tracker replays
those append-only facts so restart/failover cannot reset an unhealthy history
to UNKNOWN when the same runtime/version/config binding is reconstructed.
"""

from __future__ import annotations

from collections import deque
from dataclasses import dataclass
from enum import StrEnum
from threading import RLock
from typing import Protocol, runtime_checkable

from .core import ExecutionStatus, HealthReport, HealthStatus


class RuntimeHealthState(StrEnum):
    UNKNOWN = "UNKNOWN"
    HEALTHY = "HEALTHY"
    DEGRADED = "DEGRADED"
    UNHEALTHY = "UNHEALTHY"
    QUARANTINED = "QUARANTINED"
    RECOVERING = "RECOVERING"


class RuntimeHealthConflict(RuntimeError):
    """Raised when one execution identity is rewritten with different facts."""


class RuntimeHealthHistoryCorrupt(RuntimeError):
    """Raised when durable health history violates its factual binding/order."""


@dataclass(frozen=True, slots=True)
class RuntimeHealthPolicy:
    window_size: int = 5
    quarantine_consecutive_failures: int = 3
    unhealthy_failure_percent: int = 60
    recovery_successes_required: int = 2

    def __post_init__(self) -> None:
        if self.window_size < 1:
            raise ValueError("runtime health window_size must be positive")
        if self.quarantine_consecutive_failures < 1:
            raise ValueError("runtime health quarantine threshold must be positive")
        if not 1 <= self.unhealthy_failure_percent <= 100:
            raise ValueError("runtime health unhealthy percentage must be within [1, 100]")
        if self.recovery_successes_required < 1:
            raise ValueError("runtime health recovery threshold must be positive")


@dataclass(frozen=True, slots=True)
class RuntimeHealthExecutionFact:
    runtime_id: str
    runtime_version: str
    config_id: str
    execution_id: str
    status: ExecutionStatus
    sequence: int

    def __post_init__(self) -> None:
        for name, value in (
            ("runtime_id", self.runtime_id),
            ("runtime_version", self.runtime_version),
            ("config_id", self.config_id),
            ("execution_id", self.execution_id),
        ):
            if not value or not value.strip():
                raise ValueError(f"{name} must be non-empty")
        if (
            not isinstance(self.status, ExecutionStatus)
            or self.status not in {ExecutionStatus.SUCCEEDED, ExecutionStatus.FAILED}
        ):
            raise ValueError("runtime health facts only persist SUCCEEDED or FAILED")
        if self.sequence < 1:
            raise ValueError("runtime health fact sequence must be positive")


@runtime_checkable
class RuntimeHealthStorePort(Protocol):
    def record(
        self,
        *,
        runtime_id: str,
        runtime_version: str,
        config_id: str,
        execution_id: str,
        status: ExecutionStatus,
    ) -> RuntimeHealthExecutionFact: ...

    def history(
        self,
        *,
        runtime_id: str,
        runtime_version: str,
        config_id: str,
    ) -> tuple[RuntimeHealthExecutionFact, ...]: ...


class InMemoryRuntimeHealthStore:
    """Process-local append-only execution-fact store."""

    def __init__(self) -> None:
        self._facts: dict[tuple[str, str, str, str], RuntimeHealthExecutionFact] = {}
        self._lock = RLock()

    def record(
        self,
        *,
        runtime_id: str,
        runtime_version: str,
        config_id: str,
        execution_id: str,
        status: ExecutionStatus,
    ) -> RuntimeHealthExecutionFact:
        probe = RuntimeHealthExecutionFact(
            runtime_id,
            runtime_version,
            config_id,
            execution_id,
            status,
            1,
        )
        key = (runtime_id, runtime_version, config_id, execution_id)
        with self._lock:
            existing = self._facts.get(key)
            if existing is not None:
                if existing.status is not status:
                    raise RuntimeHealthConflict(execution_id)
                return existing
            sequence = (
                max(
                    (
                        item.sequence
                        for item in self._facts.values()
                        if (
                            item.runtime_id,
                            item.runtime_version,
                            item.config_id,
                        )
                        == (runtime_id, runtime_version, config_id)
                    ),
                    default=0,
                )
                + 1
            )
            fact = RuntimeHealthExecutionFact(
                probe.runtime_id,
                probe.runtime_version,
                probe.config_id,
                probe.execution_id,
                probe.status,
                sequence,
            )
            self._facts[key] = fact
            return fact

    def history(
        self,
        *,
        runtime_id: str,
        runtime_version: str,
        config_id: str,
    ) -> tuple[RuntimeHealthExecutionFact, ...]:
        with self._lock:
            return tuple(
                sorted(
                    (
                        item
                        for item in self._facts.values()
                        if (
                            item.runtime_id,
                            item.runtime_version,
                            item.config_id,
                        )
                        == (runtime_id, runtime_version, config_id)
                    ),
                    key=lambda item: item.sequence,
                )
            )


@dataclass(frozen=True, slots=True)
class RuntimeHealthFacts:
    runtime_id: str
    runtime_version: str
    config_id: str
    state: RuntimeHealthState
    evidence_basis: str
    evidence_ref: str
    window_start_sequence: int
    window_end_sequence: int
    attempts: int
    successes: int
    failures: int
    consecutive_failures: int
    fresh_successes_since_unhealthy: int


@dataclass(frozen=True, slots=True)
class _ExecutionObservation:
    sequence: int
    execution_id: str
    succeeded: bool


class RuntimeHealthTracker:
    """Thread-safe factual projection for one runtime/version/config binding."""

    _RECOVERY_STATES = frozenset(
        {
            RuntimeHealthState.UNHEALTHY,
            RuntimeHealthState.QUARANTINED,
            RuntimeHealthState.RECOVERING,
        }
    )

    def __init__(
        self,
        *,
        runtime_id: str,
        runtime_version: str,
        config_id: str,
        policy: RuntimeHealthPolicy | None = None,
        store: RuntimeHealthStorePort | None = None,
    ) -> None:
        for name, value in (
            ("runtime_id", runtime_id),
            ("runtime_version", runtime_version),
            ("config_id", config_id),
        ):
            if not value or not value.strip():
                raise ValueError(f"{name} must be non-empty")
        self._runtime_id = runtime_id
        self._runtime_version = runtime_version
        self._config_id = config_id
        self._policy = policy or RuntimeHealthPolicy()
        self._store: RuntimeHealthStorePort = store or InMemoryRuntimeHealthStore()
        self._lock = RLock()

    @property
    def policy(self) -> RuntimeHealthPolicy:
        return self._policy

    def configure_store(self, store: RuntimeHealthStorePort) -> None:
        if not isinstance(store, RuntimeHealthStorePort):
            raise TypeError("runtime health store does not implement RuntimeHealthStorePort")
        with self._lock:
            if self._history_unlocked():
                raise RuntimeError(
                    "cannot replace runtime health store after factual observations exist"
                )
            self._store = store
            self._facts_from_history(self._history_unlocked())

    def record_execution(
        self,
        status: ExecutionStatus,
        *,
        execution_id: str,
    ) -> RuntimeHealthFacts:
        if not execution_id:
            raise ValueError("execution_id must be non-empty")
        if not isinstance(status, ExecutionStatus):
            raise ValueError(f"unsupported execution status for runtime health: {status}")
        if status is ExecutionStatus.CANCELLED:
            return self.facts()
        if status not in {ExecutionStatus.SUCCEEDED, ExecutionStatus.FAILED}:
            raise ValueError(f"unsupported execution status for runtime health: {status}")

        with self._lock:
            self._store.record(
                runtime_id=self._runtime_id,
                runtime_version=self._runtime_version,
                config_id=self._config_id,
                execution_id=execution_id,
                status=status,
            )
            return self._facts_from_history(self._history_unlocked())

    def facts(self) -> RuntimeHealthFacts:
        with self._lock:
            return self._facts_from_history(self._history_unlocked())

    def report(self) -> HealthReport:
        facts = self.facts()
        if facts.state is RuntimeHealthState.HEALTHY:
            status = HealthStatus.HEALTHY
        elif facts.state in {
            RuntimeHealthState.UNKNOWN,
            RuntimeHealthState.DEGRADED,
            RuntimeHealthState.RECOVERING,
        }:
            status = HealthStatus.DEGRADED
        else:
            status = HealthStatus.UNHEALTHY

        return HealthReport(
            status,
            (
                f"factual runtime health={facts.state.value}; "
                f"adapter-verified window={facts.successes}/{facts.attempts} successes; "
                f"consecutive_failures={facts.consecutive_failures}; "
                f"config={facts.config_id}"
            ),
        )

    def _history_unlocked(self) -> tuple[RuntimeHealthExecutionFact, ...]:
        return self._store.history(
            runtime_id=self._runtime_id,
            runtime_version=self._runtime_version,
            config_id=self._config_id,
        )

    def _facts_from_history(
        self,
        history: tuple[RuntimeHealthExecutionFact, ...],
    ) -> RuntimeHealthFacts:
        window: deque[_ExecutionObservation] = deque(maxlen=self._policy.window_size)
        state = RuntimeHealthState.UNKNOWN
        fresh_successes_since_unhealthy = 0
        prior_sequence = 0

        for fact in history:
            if (
                fact.runtime_id,
                fact.runtime_version,
                fact.config_id,
            ) != (self._runtime_id, self._runtime_version, self._config_id):
                raise RuntimeHealthHistoryCorrupt("runtime health fact binding mismatch")
            if fact.sequence != prior_sequence + 1:
                raise RuntimeHealthHistoryCorrupt(
                    "runtime health fact sequence is not contiguous"
                )
            prior_sequence = fact.sequence
            previous_state = state
            succeeded = fact.status is ExecutionStatus.SUCCEEDED
            window.append(
                _ExecutionObservation(fact.sequence, fact.execution_id, succeeded)
            )
            if succeeded:
                if previous_state in self._RECOVERY_STATES:
                    fresh_successes_since_unhealthy += 1
            else:
                fresh_successes_since_unhealthy = 0
            state = self._derive_state(
                window,
                previous_state,
                fresh_successes_since_unhealthy,
            )

        attempts = len(window)
        successes = sum(1 for item in window if item.succeeded)
        failures = attempts - successes
        start_sequence = window[0].sequence if window else prior_sequence
        end_sequence = window[-1].sequence if window else prior_sequence
        evidence_ref = (
            window[-1].execution_id if window else "no-execution-observation"
        )
        return RuntimeHealthFacts(
            runtime_id=self._runtime_id,
            runtime_version=self._runtime_version,
            config_id=self._config_id,
            state=state,
            evidence_basis="ADAPTER_VERIFIED",
            evidence_ref=evidence_ref,
            window_start_sequence=start_sequence,
            window_end_sequence=end_sequence,
            attempts=attempts,
            successes=successes,
            failures=failures,
            consecutive_failures=self._consecutive_failures(window),
            fresh_successes_since_unhealthy=fresh_successes_since_unhealthy,
        )

    def _derive_state(
        self,
        window: deque[_ExecutionObservation],
        previous_state: RuntimeHealthState,
        fresh_successes_since_unhealthy: int,
    ) -> RuntimeHealthState:
        attempts = len(window)
        if attempts == 0:
            return RuntimeHealthState.UNKNOWN

        failures = sum(1 for item in window if not item.succeeded)
        consecutive_failures = self._consecutive_failures(window)

        if consecutive_failures >= self._policy.quarantine_consecutive_failures:
            return RuntimeHealthState.QUARANTINED

        if failures * 100 >= attempts * self._policy.unhealthy_failure_percent:
            return RuntimeHealthState.UNHEALTHY

        if previous_state in self._RECOVERY_STATES:
            if (
                failures == 0
                and fresh_successes_since_unhealthy
                >= self._policy.recovery_successes_required
            ):
                return RuntimeHealthState.HEALTHY
            return RuntimeHealthState.RECOVERING

        if failures > 0:
            return RuntimeHealthState.DEGRADED

        return RuntimeHealthState.HEALTHY

    @staticmethod
    def _consecutive_failures(window: deque[_ExecutionObservation]) -> int:
        count = 0
        for item in reversed(window):
            if item.succeeded:
                break
            count += 1
        return count


__all__ = [
    "RuntimeHealthState",
    "RuntimeHealthConflict",
    "RuntimeHealthHistoryCorrupt",
    "RuntimeHealthPolicy",
    "RuntimeHealthExecutionFact",
    "RuntimeHealthStorePort",
    "InMemoryRuntimeHealthStore",
    "RuntimeHealthFacts",
    "RuntimeHealthTracker",
]
