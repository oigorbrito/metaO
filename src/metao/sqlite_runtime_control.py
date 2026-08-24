"""SQLite adapter for durable runtime quarantine and restore history."""

from __future__ import annotations

from pathlib import Path
import sqlite3
from typing import Any

from .runtime_control import RuntimeControlRecord, RuntimeDisposition


class RuntimeControlCorrupt(RuntimeError):
    pass


class SQLiteRuntimeControlStore:
    """Cross-process runtime control history stored as append-only revisions."""

    def __init__(self, path: str | Path) -> None:
        self._path = str(path)
        if self._path == ":memory:":
            raise ValueError("use InMemoryRuntimeControlStore for process-local control")
        Path(self._path).parent.mkdir(parents=True, exist_ok=True)
        self._initialize()

    def _connect(self) -> sqlite3.Connection:
        return sqlite3.connect(self._path, timeout=5.0)

    def _initialize(self) -> None:
        with self._connect() as connection:
            connection.execute(
                """
                CREATE TABLE IF NOT EXISTS runtime_control_history (
                    orchestrator_id TEXT NOT NULL,
                    revision INTEGER NOT NULL CHECK (revision >= 1),
                    disposition TEXT NOT NULL,
                    reason TEXT NOT NULL,
                    actor_id TEXT NOT NULL,
                    updated_at_epoch REAL NOT NULL CHECK (updated_at_epoch >= 0),
                    PRIMARY KEY (orchestrator_id, revision)
                )
                """
            )

    @staticmethod
    def _decode(row: tuple[Any, ...]) -> RuntimeControlRecord:
        try:
            orchestrator_id, revision, disposition, reason, actor_id, updated_at_epoch = row
            return RuntimeControlRecord(
                orchestrator_id=str(orchestrator_id),
                disposition=RuntimeDisposition(str(disposition)),
                reason=str(reason),
                actor_id=str(actor_id),
                updated_at_epoch=float(updated_at_epoch),
                revision=int(revision),
            )
        except (TypeError, ValueError) as exc:
            raise RuntimeControlCorrupt("invalid runtime control row") from exc

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
        # Validate all fields before acquiring the write lock.
        probe = RuntimeControlRecord(
            orchestrator_id,
            disposition,
            reason,
            actor_id,
            updated_at_epoch,
            1,
        )
        with self._connect() as connection:
            connection.execute("BEGIN IMMEDIATE")
            row = connection.execute(
                "SELECT MAX(revision) FROM runtime_control_history WHERE orchestrator_id=?",
                (orchestrator_id,),
            ).fetchone()
            revision = int(row[0] or 0) + 1
            connection.execute(
                """
                INSERT INTO runtime_control_history(
                    orchestrator_id,revision,disposition,reason,actor_id,updated_at_epoch
                ) VALUES(?,?,?,?,?,?)
                """,
                (
                    probe.orchestrator_id,
                    revision,
                    probe.disposition.value,
                    probe.reason,
                    probe.actor_id,
                    probe.updated_at_epoch,
                ),
            )
        current = self.current(orchestrator_id)
        assert current is not None
        return current

    def current(self, orchestrator_id: str) -> RuntimeControlRecord | None:
        with self._connect() as connection:
            row = connection.execute(
                """
                SELECT orchestrator_id,revision,disposition,reason,actor_id,updated_at_epoch
                FROM runtime_control_history
                WHERE orchestrator_id=?
                ORDER BY revision DESC
                LIMIT 1
                """,
                (orchestrator_id,),
            ).fetchone()
        return None if row is None else self._decode(row)

    def list_current(self) -> tuple[RuntimeControlRecord, ...]:
        with self._connect() as connection:
            rows = connection.execute(
                """
                SELECT h.orchestrator_id,h.revision,h.disposition,h.reason,h.actor_id,h.updated_at_epoch
                FROM runtime_control_history h
                JOIN (
                    SELECT orchestrator_id,MAX(revision) AS revision
                    FROM runtime_control_history
                    GROUP BY orchestrator_id
                ) latest
                  ON latest.orchestrator_id=h.orchestrator_id
                 AND latest.revision=h.revision
                ORDER BY h.orchestrator_id
                """
            ).fetchall()
        return tuple(self._decode(row) for row in rows)

    def history(self, orchestrator_id: str) -> tuple[RuntimeControlRecord, ...]:
        with self._connect() as connection:
            rows = connection.execute(
                """
                SELECT orchestrator_id,revision,disposition,reason,actor_id,updated_at_epoch
                FROM runtime_control_history
                WHERE orchestrator_id=?
                ORDER BY revision
                """,
                (orchestrator_id,),
            ).fetchall()
        return tuple(self._decode(row) for row in rows)


__all__ = ["RuntimeControlCorrupt", "SQLiteRuntimeControlStore"]
