"""SQLite adapter for the framework-neutral metaO event ledger."""

from __future__ import annotations

import json
from pathlib import Path
import sqlite3
from typing import Any, Mapping

from .observability import MissionEvent, MissionEventKind, thaw_event_value


class EventLedgerCorrupt(RuntimeError):
    """Raised when persisted event data violates the ledger contract."""


class SQLiteEventLedger:
    """File-backed append-only EventLedgerPort implementation."""

    def __init__(self, path: str | Path) -> None:
        self._path = str(path)
        if self._path == ":memory:":
            raise ValueError("use InMemoryEventLedger for process-local event storage")
        Path(self._path).parent.mkdir(parents=True, exist_ok=True)
        self._initialize()

    def _connect(self) -> sqlite3.Connection:
        connection = sqlite3.connect(self._path, timeout=5.0)
        connection.execute("PRAGMA foreign_keys = ON")
        return connection

    def _initialize(self) -> None:
        with self._connect() as connection:
            connection.execute(
                """
                CREATE TABLE IF NOT EXISTS mission_events (
                    event_id TEXT PRIMARY KEY,
                    mission_id TEXT NOT NULL,
                    sequence INTEGER NOT NULL CHECK (sequence >= 1),
                    kind TEXT NOT NULL,
                    occurred_at_epoch REAL NOT NULL CHECK (occurred_at_epoch >= 0),
                    payload_json TEXT NOT NULL,
                    UNIQUE(mission_id, sequence)
                )
                """
            )
            connection.execute(
                "CREATE INDEX IF NOT EXISTS idx_mission_events_mission ON mission_events(mission_id, sequence)"
            )

    @staticmethod
    def _payload_json(payload: Mapping[str, Any]) -> str:
        value = thaw_event_value(payload)
        try:
            return json.dumps(value, sort_keys=True, separators=(",", ":"), allow_nan=False)
        except (TypeError, ValueError) as exc:
            raise TypeError("event payload must be JSON-compatible") from exc

    @staticmethod
    def _decode(row: tuple[Any, ...]) -> MissionEvent:
        event_id, mission_id, sequence, kind, occurred_at_epoch, payload_json = row
        try:
            payload = json.loads(str(payload_json))
            if not isinstance(payload, dict):
                raise EventLedgerCorrupt("event payload root must be an object")
            event = MissionEvent(
                event_id=str(event_id),
                mission_id=str(mission_id),
                sequence=int(sequence),
                kind=MissionEventKind(str(kind)),
                occurred_at_epoch=float(occurred_at_epoch),
                payload=payload,
            )
        except EventLedgerCorrupt:
            raise
        except (TypeError, ValueError, json.JSONDecodeError) as exc:
            raise EventLedgerCorrupt("invalid mission event row") from exc
        expected = f"{event.mission_id}:event:{event.sequence}"
        if event.event_id != expected:
            raise EventLedgerCorrupt("event id does not match mission/sequence binding")
        return event

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
        if occurred_at_epoch < 0:
            raise ValueError("event timestamp must be non-negative")
        with self._connect() as connection:
            connection.execute("BEGIN IMMEDIATE")
            row = connection.execute(
                "SELECT COALESCE(MAX(sequence), 0) FROM mission_events WHERE mission_id = ?",
                (mission_id,),
            ).fetchone()
            sequence = int(row[0]) + 1
            event = MissionEvent(
                event_id=f"{mission_id}:event:{sequence}",
                mission_id=mission_id,
                sequence=sequence,
                kind=kind,
                occurred_at_epoch=occurred_at_epoch,
                payload=payload or {},
            )
            payload_json = self._payload_json(event.payload)
            connection.execute(
                "INSERT INTO mission_events(event_id,mission_id,sequence,kind,occurred_at_epoch,payload_json) VALUES(?,?,?,?,?,?)",
                (
                    event.event_id,
                    event.mission_id,
                    event.sequence,
                    event.kind.value,
                    event.occurred_at_epoch,
                    payload_json,
                ),
            )
        return event

    def list(self, mission_id: str) -> tuple[MissionEvent, ...]:
        with self._connect() as connection:
            rows = connection.execute(
                "SELECT event_id,mission_id,sequence,kind,occurred_at_epoch,payload_json FROM mission_events WHERE mission_id = ? ORDER BY sequence",
                (mission_id,),
            ).fetchall()
        return tuple(self._decode(row) for row in rows)

    def all(self) -> tuple[MissionEvent, ...]:
        with self._connect() as connection:
            rows = connection.execute(
                "SELECT event_id,mission_id,sequence,kind,occurred_at_epoch,payload_json FROM mission_events ORDER BY mission_id, sequence"
            ).fetchall()
        return tuple(self._decode(row) for row in rows)


__all__ = ["EventLedgerCorrupt", "SQLiteEventLedger"]
