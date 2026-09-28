"""SQLite adapter for append-only deterministic runtime feedback."""

from __future__ import annotations

from contextlib import closing
from pathlib import Path
import sqlite3
from typing import Any

from .runtime_feedback import (
    DEFAULT_FEEDBACK_ALPHA,
    RuntimeFeedbackConflict,
    RuntimeObservation,
)
from .strategy import HistoricalScore


class RuntimeFeedbackCorrupt(RuntimeError):
    pass


class SQLiteRuntimeFeedbackStore:
    def __init__(self, path: str | Path) -> None:
        self._path = str(path)
        if self._path == ":memory:":
            raise ValueError("use InMemoryRuntimeFeedbackStore for process-local feedback")
        Path(self._path).parent.mkdir(parents=True, exist_ok=True)
        self._initialize()

    def _connect(self) -> sqlite3.Connection:
        return sqlite3.connect(self._path, timeout=5.0)

    def _initialize(self) -> None:
        with closing(self._connect()) as connection, connection:
            connection.execute(
                """
                CREATE TABLE IF NOT EXISTS runtime_feedback_observations (
                    observation_id TEXT PRIMARY KEY,
                    mission_id TEXT NOT NULL,
                    execution_id TEXT NOT NULL,
                    orchestrator_id TEXT NOT NULL,
                    outcome REAL NOT NULL CHECK (outcome >= 0 AND outcome <= 1),
                    quality REAL NOT NULL CHECK (quality >= 0 AND quality <= 1),
                    latency_ms REAL NOT NULL CHECK (latency_ms >= 0),
                    cost REAL NOT NULL CHECK (cost >= 0),
                    observed_at_epoch REAL NOT NULL CHECK (observed_at_epoch >= 0)
                )
                """
            )
            connection.execute(
                "CREATE INDEX IF NOT EXISTS idx_runtime_feedback_orchestrator_time "
                "ON runtime_feedback_observations(orchestrator_id, observed_at_epoch, observation_id)"
            )

    @staticmethod
    def _decode(row: tuple[Any, ...]) -> RuntimeObservation:
        try:
            return RuntimeObservation(
                observation_id=str(row[0]),
                mission_id=str(row[1]),
                execution_id=str(row[2]),
                orchestrator_id=str(row[3]),
                outcome=float(row[4]),
                quality=float(row[5]),
                latency_ms=float(row[6]),
                cost=float(row[7]),
                observed_at_epoch=float(row[8]),
            )
        except (TypeError, ValueError) as exc:
            raise RuntimeFeedbackCorrupt("invalid runtime feedback row") from exc

    def record(self, observation: RuntimeObservation) -> RuntimeObservation:
        # Dataclass validation occurs before touching durable state.
        with closing(self._connect()) as connection, connection:
            existing_row = connection.execute(
                """
                SELECT observation_id,mission_id,execution_id,orchestrator_id,
                       outcome,quality,latency_ms,cost,observed_at_epoch
                FROM runtime_feedback_observations WHERE observation_id=?
                """,
                (observation.observation_id,),
            ).fetchone()
            if existing_row is not None:
                existing = self._decode(existing_row)
                if existing != observation:
                    raise RuntimeFeedbackConflict(observation.observation_id)
                return existing
            connection.execute(
                """
                INSERT INTO runtime_feedback_observations(
                    observation_id,mission_id,execution_id,orchestrator_id,
                    outcome,quality,latency_ms,cost,observed_at_epoch
                ) VALUES(?,?,?,?,?,?,?,?,?)
                """,
                (
                    observation.observation_id,
                    observation.mission_id,
                    observation.execution_id,
                    observation.orchestrator_id,
                    observation.outcome,
                    observation.quality,
                    observation.latency_ms,
                    observation.cost,
                    observation.observed_at_epoch,
                ),
            )
        return observation

    def history(self, orchestrator_id: str) -> tuple[RuntimeObservation, ...]:
        with closing(self._connect()) as connection, connection:
            rows = connection.execute(
                """
                SELECT observation_id,mission_id,execution_id,orchestrator_id,
                       outcome,quality,latency_ms,cost,observed_at_epoch
                FROM runtime_feedback_observations
                WHERE orchestrator_id=?
                ORDER BY observed_at_epoch, observation_id
                """,
                (orchestrator_id,),
            ).fetchall()
        return tuple(self._decode(row) for row in rows)

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


__all__ = ["RuntimeFeedbackCorrupt", "SQLiteRuntimeFeedbackStore"]
