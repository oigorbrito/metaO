"""Framework-neutral deterministic runtime performance feedback.

Feedback is deliberately simple and auditable: accepted attempts contribute 1.0
for outcome/quality, every other acceptance decision contributes 0.0, and the
existing attempt telemetry supplies latency and cost. Aggregation reuses the
existing ``HistoricalScore`` EMA primitive; no learned routing is introduced.
"""

from __future__ import annotations

from dataclasses import dataclass
from threading import RLock
from typing import Protocol, runtime_checkable

from .acceptance import AcceptanceDecision
from .control_plane import MissionOutcome
from .strategy import HistoricalScore


DEFAULT_FEEDBACK_ALPHA = 0.2


class RuntimeFeedbackConflict(RuntimeError):
    pass


@dataclass(frozen=True, slots=True)
class RuntimeObservation:
    observation_id: str
    mission_id: str
    execution_id: str
    orchestrator_id: str
    outcome: float
    quality: float
    latency_ms: float
    cost: float
    observed_at_epoch: float

    def __post_init__(self) -> None:
        if not all((self.observation_id, self.mission_id, self.execution_id, self.orchestrator_id)):
            raise ValueError("runtime observation requires stable identities")
        for name, value in (("outcome", self.outcome), ("quality", self.quality)):
            if not 0.0 <= value <= 1.0:
                raise ValueError(f"{name} must be within [0, 1]")
        if self.latency_ms < 0 or self.cost < 0 or self.observed_at_epoch < 0:
            raise ValueError("runtime observation latency/cost/time must be non-negative")


@runtime_checkable
class RuntimeFeedbackStorePort(Protocol):
    def record(self, observation: RuntimeObservation) -> RuntimeObservation: ...
    def history(self, orchestrator_id: str) -> tuple[RuntimeObservation, ...]: ...
    def score(self, orchestrator_id: str, *, alpha: float = DEFAULT_FEEDBACK_ALPHA) -> HistoricalScore: ...


class InMemoryRuntimeFeedbackStore:
    def __init__(self) -> None:
        self._by_id: dict[str, RuntimeObservation] = {}
        self._lock = RLock()

    def record(self, observation: RuntimeObservation) -> RuntimeObservation:
        with self._lock:
            existing = self._by_id.get(observation.observation_id)
            if existing is not None:
                if existing != observation:
                    raise RuntimeFeedbackConflict(observation.observation_id)
                return existing
            self._by_id[observation.observation_id] = observation
            return observation

    def history(self, orchestrator_id: str) -> tuple[RuntimeObservation, ...]:
        with self._lock:
            return tuple(
                sorted(
                    (item for item in self._by_id.values() if item.orchestrator_id == orchestrator_id),
                    key=lambda item: (item.observed_at_epoch, item.observation_id),
                )
            )

    def score(self, orchestrator_id: str, *, alpha: float = DEFAULT_FEEDBACK_ALPHA) -> HistoricalScore:
        score = HistoricalScore()
        for item in self.history(orchestrator_id):
            score = score.update(
                outcome=item.outcome,
                quality=item.quality,
                latency_ms=item.latency_ms,
                cost=item.cost,
                alpha=alpha,
            )
        return score


def observations_from_outcome(outcome: MissionOutcome) -> tuple[RuntimeObservation, ...]:
    if outcome.state is None:
        return ()
    result: list[RuntimeObservation] = []
    for attempt in outcome.state.attempts:
        if attempt.execution_status is None:
            continue
        start = attempt.started_at_epoch
        end = attempt.ended_at_epoch
        latency_ms = 0.0 if start is None or end is None else max(0.0, (end - start) * 1000.0)
        accepted = attempt.acceptance_decision is AcceptanceDecision.ACCEPT
        observed_at = end if end is not None else (start if start is not None else 0.0)
        result.append(
            RuntimeObservation(
                observation_id=f"{outcome.mission_id}:{attempt.execution_id}",
                mission_id=outcome.mission_id,
                execution_id=attempt.execution_id,
                orchestrator_id=attempt.orchestrator_id,
                outcome=1.0 if accepted else 0.0,
                quality=1.0 if accepted else 0.0,
                latency_ms=latency_ms,
                cost=attempt.cost,
                observed_at_epoch=observed_at,
            )
        )
    return tuple(result)


def record_outcome(store: RuntimeFeedbackStorePort, outcome: MissionOutcome) -> tuple[RuntimeObservation, ...]:
    return tuple(store.record(item) for item in observations_from_outcome(outcome))


__all__ = [
    "DEFAULT_FEEDBACK_ALPHA",
    "RuntimeFeedbackConflict",
    "RuntimeObservation",
    "RuntimeFeedbackStorePort",
    "InMemoryRuntimeFeedbackStore",
    "observations_from_outcome",
    "record_outcome",
]
