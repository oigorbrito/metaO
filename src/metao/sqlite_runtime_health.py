"""SQLite adapter for append-only factual runtime health execution history."""

from __future__ import annotations

from contextlib import closing
from pathlib import Path
import sqlite3
from typing import Any

from .core import ExecutionStatus
from .runtime_health import RuntimeHealthConflict, RuntimeHealthExecutionFact


class RuntimeHealthStoreCorrupt(RuntimeError):
    pass


class SQLiteRuntimeHealthStore:
    """Cross-process health facts scoped by runtime/version/config."""

    def __init__(self, path: str | Path) -> None:
        self._path = str(path)
        if self._path == ":memory:":
            raise ValueError("use InMemoryRuntimeHealthStore for process-local health")
        Path(self._path).parent.mkdir(parents=True, exist_ok=True)
        self._initialize()

    def _connect(self) -> sqlite3.Connection:
        return sqlite3.connect(self._path, timeout=5.0)

    def _initialize(self) -> None:
        with closing(self._connect()) as connection, connection:
            connection.execute(
                """
                CREATE TABLE IF NOT EXISTS runtime_health_execution_facts (
                    runtime_id TEXT NOT NULL,
                    runtime_version TEXT NOT NULL,
                    config_id TEXT NOT NULL,
                    execution_id TEXT NOT NULL,
                    status TEXT NOT NULL,
                    sequence INTEGER NOT NULL CHECK (sequence >= 1),
                    PRIMARY KEY (
                        runtime_id, runtime_version, config_id, execution_id
                    ),
                    UNIQUE (
                        runtime_id, runtime_version, config_id, sequence
                    )
                )
                """
            )
            connection.execute(
                "CREATE INDEX IF NOT EXISTS idx_runtime_health_binding_sequence "
                "ON runtime_health_execution_facts("
                "runtime_id,runtime_version,config_id,sequence)"
            )

    @staticmethod
    def _decode(row: tuple[Any, ...]) -> RuntimeHealthExecutionFact:
        try:
            return RuntimeHealthExecutionFact(
                runtime_id=str(row[0]),
                runtime_version=str(row[1]),
                config_id=str(row[2]),
                execution_id=str(row[3]),
                status=ExecutionStatus(str(row[4])),
                sequence=int(row[5]),
            )
        except (TypeError, ValueError) as exc:
            raise RuntimeHealthStoreCorrupt("invalid runtime health fact row") from exc

    def record(
        self,
        *,
        runtime_id: str,
        runtime_version: str,
        config_id: str,
        execution_id: str,
        status: ExecutionStatus,
    ) -> RuntimeHealthExecutionFact:
        RuntimeHealthExecutionFact(
            runtime_id,
            runtime_version,
            config_id,
            execution_id,
            status,
            1,
        )
        binding = (runtime_id, runtime_version, config_id)
        with closing(self._connect()) as connection, connection:
            connection.execute("BEGIN IMMEDIATE")
            row = connection.execute(
                """
                SELECT runtime_id,runtime_version,config_id,execution_id,status,sequence
                FROM runtime_health_execution_facts
                WHERE runtime_id=? AND runtime_version=? AND config_id=? AND execution_id=?
                """,
                (*binding, execution_id),
            ).fetchone()
            if row is not None:
                existing = self._decode(row)
                if existing.status is not status:
                    raise RuntimeHealthConflict(execution_id)
                return existing

            sequence_row = connection.execute(
                """
                SELECT MAX(sequence)
                FROM runtime_health_execution_facts
                WHERE runtime_id=? AND runtime_version=? AND config_id=?
                """,
                binding,
            ).fetchone()
            sequence = int(sequence_row[0] or 0) + 1
            connection.execute(
                """
                INSERT INTO runtime_health_execution_facts(
                    runtime_id,runtime_version,config_id,execution_id,status,sequence
                ) VALUES(?,?,?,?,?,?)
                """,
                (*binding, execution_id, status.value, sequence),
            )

        return RuntimeHealthExecutionFact(
            runtime_id,
            runtime_version,
            config_id,
            execution_id,
            status,
            sequence,
        )

    def history(
        self,
        *,
        runtime_id: str,
        runtime_version: str,
        config_id: str,
    ) -> tuple[RuntimeHealthExecutionFact, ...]:
        with closing(self._connect()) as connection, connection:
            rows = connection.execute(
                """
                SELECT runtime_id,runtime_version,config_id,execution_id,status,sequence
                FROM runtime_health_execution_facts
                WHERE runtime_id=? AND runtime_version=? AND config_id=?
                ORDER BY sequence
                """,
                (runtime_id, runtime_version, config_id),
            ).fetchall()
        return tuple(self._decode(row) for row in rows)


__all__ = ["RuntimeHealthStoreCorrupt", "SQLiteRuntimeHealthStore"]
