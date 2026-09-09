"""Framework-neutral factual runtime health for real adapter executions.

This module mirrors the authority boundary of the canonical Rust runtime-health
contract: adapter-verified execution outcomes are factual health evidence;
structural readiness and runtime self-report are not.
"""

from __future__ import annotations

from collections import deque
from dataclasses import dataclass
from enum import StrEnum
from threading import Lock

from .core import ExecutionStatus, HealthReport, HealthStatus


class RuntimeHealthState(StrEnum):
    UNKNOWN = "UNKNOWN"
    HEALTHY = "HEALTHY"
    DEGRADED = "DEGRADED"
    UNHEALTHY = "UNHEALTHY"
    QUARANTINED = "QUARANTINED"
    RECOVERING = "RECOVERING"


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
    """Thread-safe rolling factual health projection for one runtime identity."""

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
        self._window: deque[_ExecutionObservation] = deque(maxlen=self._policy.window_size)
        self._sequence = 0
        self._state = RuntimeHealthState.UNKNOWN
        self._fresh_successes_since_unhealthy = 0
        self._lock = Lock()

    @property
    def policy(self) -> RuntimeHealthPolicy:
        return self._policy

    def record_execution(self, status: ExecutionStatus, *, execution_id: str) -> RuntimeHealthFacts:
        if not execution_id:
            raise ValueError("execution_id must be non-empty")
        if status is ExecutionStatus.CANCELLED:
            return self.facts()
        if status not in {ExecutionStatus.SUCCEEDED, ExecutionStatus.FAILED}:
            raise ValueError(f"unsupported execution status for runtime health: {status}")

        with self._lock:
            previous_state = self._state
            self._sequence += 1
            succeeded = status is ExecutionStatus.SUCCEEDED
            self._window.append(_ExecutionObservation(self._sequence, execution_id, succeeded))

            if succeeded:
                if previous_state in self._RECOVERY_STATES:
                    self._fresh_successes_since_unhealthy += 1
            else:
                self._fresh_successes_since_unhealthy = 0

            self._state = self._derive_state(previous_state)
            return self._facts_unlocked()

    def facts(self) -> RuntimeHealthFacts:
        with self._lock:
            return self._facts_unlocked()

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

    def _derive_state(self, previous_state: RuntimeHealthState) -> RuntimeHealthState:
        attempts = len(self._window)
        if attempts == 0:
            return RuntimeHealthState.UNKNOWN

        failures = sum(1 for item in self._window if not item.succeeded)
        consecutive_failures = self._consecutive_failures_unlocked()

        if consecutive_failures >= self._policy.quarantine_consecutive_failures:
            return RuntimeHealthState.QUARANTINED

        if failures * 100 >= attempts * self._policy.unhealthy_failure_percent:
            return RuntimeHealthState.UNHEALTHY

        if previous_state in self._RECOVERY_STATES:
            if (
                failures == 0
                and self._fresh_successes_since_unhealthy
                >= self._policy.recovery_successes_required
            ):
                return RuntimeHealthState.HEALTHY
            return RuntimeHealthState.RECOVERING

        if failures > 0:
            return RuntimeHealthState.DEGRADED

        return RuntimeHealthState.HEALTHY

    def _consecutive_failures_unlocked(self) -> int:
        count = 0
        for item in reversed(self._window):
            if item.succeeded:
                break
            count += 1
        return count

    def _facts_unlocked(self) -> RuntimeHealthFacts:
        attempts = len(self._window)
        successes = sum(1 for item in self._window if item.succeeded)
        failures = attempts - successes
        start_sequence = self._window[0].sequence if self._window else self._sequence
        end_sequence = self._window[-1].sequence if self._window else self._sequence
        evidence_ref = self._window[-1].execution_id if self._window else "no-execution-observation"
        return RuntimeHealthFacts(
            runtime_id=self._runtime_id,
            runtime_version=self._runtime_version,
            config_id=self._config_id,
            state=self._state,
            evidence_basis="ADAPTER_VERIFIED",
            evidence_ref=evidence_ref,
            window_start_sequence=start_sequence,
            window_end_sequence=end_sequence,
            attempts=attempts,
            successes=successes,
            failures=failures,
            consecutive_failures=self._consecutive_failures_unlocked(),
            fresh_successes_since_unhealthy=self._fresh_successes_since_unhealthy,
        )


__all__ = [
    "RuntimeHealthState",
    "RuntimeHealthPolicy",
    "RuntimeHealthFacts",
    "RuntimeHealthTracker",
]
