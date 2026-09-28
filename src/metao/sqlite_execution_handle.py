"""SQLite adapter for durable active mission execution handles."""

from __future__ import annotations

from contextlib import closing
from pathlib import Path
import sqlite3
from typing import Any

from .core import ExecutionStatus
from .execution_handle import (
    ActiveExecutionHandle,
    ActiveExecutionNotFound,
    ExecutionHandleStatus,
)


class ExecutionHandleCorrupt(RuntimeError):
    pass


class SQLiteExecutionHandleStore:
    """Cross-process execution handle/cancellation coordination in SQLite."""

    def __init__(self, path: str | Path) -> None:
        self._path = str(path)
        if self._path == ":memory:":
            raise ValueError("use InMemoryExecutionHandleStore for process-local coordination")
        Path(self._path).parent.mkdir(parents=True, exist_ok=True)
        self._initialize()

    def _connect(self) -> sqlite3.Connection:
        return sqlite3.connect(self._path, timeout=5.0)

    def _initialize(self) -> None:
        with closing(self._connect()) as connection, connection:
            connection.execute(
                """
                CREATE TABLE IF NOT EXISTS active_mission_executions (
                    mission_id TEXT PRIMARY KEY,
                    execution_id TEXT NOT NULL,
                    orchestrator_id TEXT NOT NULL,
                    attempt_number INTEGER NOT NULL CHECK (attempt_number >= 1),
                    started_at_epoch REAL NOT NULL CHECK (started_at_epoch >= 0),
                    cost REAL NOT NULL CHECK (cost >= 0),
                    status TEXT NOT NULL,
                    cancel_requested INTEGER NOT NULL CHECK (cancel_requested IN (0,1)),
                    cancel_delegated INTEGER NOT NULL CHECK (cancel_delegated IN (0,1)),
                    ended_at_epoch REAL,
                    execution_status TEXT
                )
                """
            )

    @staticmethod
    def _decode(row: tuple[Any, ...]) -> ActiveExecutionHandle:
        try:
            (
                mission_id,
                execution_id,
                orchestrator_id,
                attempt_number,
                started_at_epoch,
                cost,
                status,
                cancel_requested,
                cancel_delegated,
                ended_at_epoch,
                execution_status,
            ) = row
            return ActiveExecutionHandle(
                mission_id=str(mission_id),
                execution_id=str(execution_id),
                orchestrator_id=str(orchestrator_id),
                attempt_number=int(attempt_number),
                started_at_epoch=float(started_at_epoch),
                cost=float(cost),
                status=ExecutionHandleStatus(str(status)),
                cancel_requested=bool(cancel_requested),
                cancel_delegated=bool(cancel_delegated),
                ended_at_epoch=None if ended_at_epoch is None else float(ended_at_epoch),
                execution_status=None if execution_status is None else ExecutionStatus(str(execution_status)),
            )
        except (TypeError, ValueError) as exc:
            raise ExecutionHandleCorrupt("invalid active execution handle row") from exc

    def get(self, mission_id: str) -> ActiveExecutionHandle:
        with closing(self._connect()) as connection, connection:
            row = connection.execute(
                """SELECT mission_id,execution_id,orchestrator_id,attempt_number,
                          started_at_epoch,cost,status,cancel_requested,cancel_delegated,
                          ended_at_epoch,execution_status
                   FROM active_mission_executions WHERE mission_id=?""",
                (mission_id,),
            ).fetchone()
        if row is None:
            raise ActiveExecutionNotFound(mission_id)
        return self._decode(row)

    def activate(self, handle: ActiveExecutionHandle) -> ActiveExecutionHandle:
        with closing(self._connect()) as connection, connection:
            connection.execute("BEGIN IMMEDIATE")
            previous = connection.execute(
                "SELECT cancel_requested,cancel_delegated FROM active_mission_executions WHERE mission_id=?",
                (handle.mission_id,),
            ).fetchone()
            requested = bool(previous[0]) if previous is not None else handle.cancel_requested
            delegated = bool(previous[1]) if previous is not None else handle.cancel_delegated
            connection.execute(
                """
                INSERT INTO active_mission_executions(
                    mission_id,execution_id,orchestrator_id,attempt_number,started_at_epoch,
                    cost,status,cancel_requested,cancel_delegated,ended_at_epoch,execution_status
                ) VALUES(?,?,?,?,?,?,?,?,?,?,?)
                ON CONFLICT(mission_id) DO UPDATE SET
                    execution_id=excluded.execution_id,
                    orchestrator_id=excluded.orchestrator_id,
                    attempt_number=excluded.attempt_number,
                    started_at_epoch=excluded.started_at_epoch,
                    cost=excluded.cost,
                    status=excluded.status,
                    cancel_requested=excluded.cancel_requested,
                    cancel_delegated=excluded.cancel_delegated,
                    ended_at_epoch=NULL,
                    execution_status=NULL
                """,
                (
                    handle.mission_id,
                    handle.execution_id,
                    handle.orchestrator_id,
                    handle.attempt_number,
                    handle.started_at_epoch,
                    handle.cost,
                    ExecutionHandleStatus.ACTIVE.value,
                    int(requested),
                    int(delegated),
                    None,
                    None,
                ),
            )
        return self.get(handle.mission_id)

    def request_cancel(self, mission_id: str) -> ActiveExecutionHandle:
        with closing(self._connect()) as connection, connection:
            connection.execute("BEGIN IMMEDIATE")
            cursor = connection.execute(
                "UPDATE active_mission_executions SET cancel_requested=1 WHERE mission_id=?",
                (mission_id,),
            )
            if cursor.rowcount != 1:
                raise ActiveExecutionNotFound(mission_id)
        return self.get(mission_id)

    def mark_cancel_delegated(self, mission_id: str) -> ActiveExecutionHandle:
        with closing(self._connect()) as connection, connection:
            connection.execute("BEGIN IMMEDIATE")
            cursor = connection.execute(
                "UPDATE active_mission_executions SET cancel_requested=1,cancel_delegated=1 WHERE mission_id=?",
                (mission_id,),
            )
            if cursor.rowcount != 1:
                raise ActiveExecutionNotFound(mission_id)
        return self.get(mission_id)

    def complete(
        self,
        mission_id: str,
        *,
        ended_at_epoch: float,
        execution_status: ExecutionStatus,
    ) -> ActiveExecutionHandle:
        with closing(self._connect()) as connection, connection:
            connection.execute("BEGIN IMMEDIATE")
            cursor = connection.execute(
                """UPDATE active_mission_executions
                   SET status=?,ended_at_epoch=?,execution_status=?
                   WHERE mission_id=?""",
                (
                    ExecutionHandleStatus.COMPLETED.value,
                    ended_at_epoch,
                    execution_status.value,
                    mission_id,
                ),
            )
            if cursor.rowcount != 1:
                raise ActiveExecutionNotFound(mission_id)
        return self.get(mission_id)


__all__ = ["ExecutionHandleCorrupt", "SQLiteExecutionHandleStore"]
