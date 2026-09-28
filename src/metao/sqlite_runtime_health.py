"""SQLite adapter for append-only factual runtime health execution history."""

from __future__ import annotations

from contextlib import closing
from pathlib import Path
import sqlite3
from typing import Any

from .core import ExecutionStatus
from .failure_origin import FailureOrigin
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
                    failure_origin TEXT,
                    failure_origin_evidence_ref TEXT,
                    PRIMARY KEY (
                        runtime_id, runtime_version, config_id, execution_id
                    ),
                    UNIQUE (
                        runtime_id, runtime_version, config_id, sequence
                    )
                )
                """
            )
            columns = {
                str(row[1])
                for row in connection.execute("PRAGMA table_info(runtime_health_execution_facts)")
            }
            if "failure_origin" not in columns:
                connection.execute(
                    "ALTER TABLE runtime_health_execution_facts ADD COLUMN failure_origin TEXT"
                )
            if "failure_origin_evidence_ref" not in columns:
                connection.execute(
                    "ALTER TABLE runtime_health_execution_facts ADD COLUMN failure_origin_evidence_ref TEXT"
                )
            connection.execute(
                """
                UPDATE runtime_health_execution_facts
                SET failure_origin=?,
                    failure_origin_evidence_ref='legacy-runtime-local://' || execution_id
                WHERE status=? AND failure_origin IS NULL
                """,
                (FailureOrigin.RUNTIME_LOCAL.value, ExecutionStatus.FAILED.value),
            )
            connection.execute(
                "CREATE INDEX IF NOT EXISTS idx_runtime_health_binding_sequence "
                "ON runtime_health_execution_facts("
                "runtime_id,runtime_version,config_id,sequence)"
            )

    @staticmethod
    def _decode(row: tuple[Any, ...]) -> RuntimeHealthExecutionFact:
        try:
            status = ExecutionStatus(str(row[4]))
            origin = FailureOrigin(str(row[6])) if row[6] is not None else None
            evidence_ref = str(row[7]) if row[7] is not None else None
            return RuntimeHealthExecutionFact(
                runtime_id=str(row[0]),
                runtime_version=str(row[1]),
                config_id=str(row[2]),
                execution_id=str(row[3]),
                status=status,
                sequence=int(row[5]),
                failure_origin=origin,
                failure_origin_evidence_ref=evidence_ref,
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
        failure_origin: FailureOrigin | None = None,
        failure_origin_evidence_ref: str | None = None,
    ) -> RuntimeHealthExecutionFact:
        if status is ExecutionStatus.FAILED and failure_origin is None:
            failure_origin = FailureOrigin.RUNTIME_LOCAL
            failure_origin_evidence_ref = failure_origin_evidence_ref or f"legacy-runtime-local://{execution_id}"
        probe = RuntimeHealthExecutionFact(
            runtime_id,
            runtime_version,
            config_id,
            execution_id,
            status,
            1,
            failure_origin,
            failure_origin_evidence_ref,
        )
        binding = (runtime_id, runtime_version, config_id)
        with closing(self._connect()) as connection, connection:
            connection.execute("BEGIN IMMEDIATE")
            row = connection.execute(
                """
                SELECT runtime_id,runtime_version,config_id,execution_id,status,sequence,
                       failure_origin,failure_origin_evidence_ref
                FROM runtime_health_execution_facts
                WHERE runtime_id=? AND runtime_version=? AND config_id=? AND execution_id=?
                """,
                (*binding, execution_id),
            ).fetchone()
            if row is not None:
                existing = self._decode(row)
                if (
                    existing.status is not probe.status
                    or existing.failure_origin is not probe.failure_origin
                    or existing.failure_origin_evidence_ref != probe.failure_origin_evidence_ref
                ):
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
                    runtime_id,runtime_version,config_id,execution_id,status,sequence,
                    failure_origin,failure_origin_evidence_ref
                ) VALUES(?,?,?,?,?,?,?,?)
                """,
                (
                    *binding,
                    execution_id,
                    status.value,
                    sequence,
                    failure_origin.value if failure_origin is not None else None,
                    failure_origin_evidence_ref,
                ),
            )

        return RuntimeHealthExecutionFact(
            runtime_id,
            runtime_version,
            config_id,
            execution_id,
            status,
            sequence,
            failure_origin,
            failure_origin_evidence_ref,
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
                SELECT runtime_id,runtime_version,config_id,execution_id,status,sequence,
                       failure_origin,failure_origin_evidence_ref
                FROM runtime_health_execution_facts
                WHERE runtime_id=? AND runtime_version=? AND config_id=?
                ORDER BY sequence
                """,
                (runtime_id, runtime_version, config_id),
            ).fetchall()
        return tuple(self._decode(row) for row in rows)


__all__ = ["RuntimeHealthStoreCorrupt", "SQLiteRuntimeHealthStore"]
