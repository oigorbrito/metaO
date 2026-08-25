"""SQLite adapter for append-only runtime conformance certificates."""

from __future__ import annotations

from contextlib import closing
import json
from pathlib import Path
import sqlite3
from typing import Any

from .runtime_certification import (
    RuntimeCertification,
    RuntimeCertificationConflict,
)


class RuntimeCertificationCorrupt(RuntimeError):
    pass


class SQLiteRuntimeCertificationStore:
    def __init__(self, path: str | Path) -> None:
        self._path = str(path)
        if self._path == ":memory:":
            raise ValueError("use InMemoryRuntimeCertificationStore for process-local state")
        Path(self._path).parent.mkdir(parents=True, exist_ok=True)
        self._initialize()

    def _connect(self) -> sqlite3.Connection:
        return sqlite3.connect(self._path, timeout=5.0)

    def _initialize(self) -> None:
        with closing(self._connect()) as connection, connection:
            connection.execute(
                """
                CREATE TABLE IF NOT EXISTS runtime_certifications (
                    certificate_id TEXT PRIMARY KEY,
                    orchestrator_id TEXT NOT NULL,
                    runtime_version TEXT NOT NULL,
                    probe_execution_id TEXT NOT NULL,
                    passed INTEGER NOT NULL CHECK (passed IN (0, 1)),
                    failed_checks_json TEXT NOT NULL,
                    checks_digest TEXT NOT NULL,
                    total_checks INTEGER NOT NULL CHECK (total_checks >= 1),
                    certified_at_epoch REAL NOT NULL DEFAULT 0 CHECK (certified_at_epoch >= 0)
                )
                """
            )
            columns = {
                str(row[1])
                for row in connection.execute("PRAGMA table_info(runtime_certifications)").fetchall()
            }
            if "certified_at_epoch" not in columns:
                # Legacy WU03 databases are migrated without rewriting old evidence.
                # Timestamp zero deliberately means legacy/stale under freshness policy.
                connection.execute(
                    "ALTER TABLE runtime_certifications "
                    "ADD COLUMN certified_at_epoch REAL NOT NULL DEFAULT 0"
                )
            connection.execute(
                "CREATE INDEX IF NOT EXISTS idx_runtime_certifications_orchestrator "
                "ON runtime_certifications(orchestrator_id, certified_at_epoch, certificate_id)"
            )

    @staticmethod
    def _decode(row: tuple[Any, ...]) -> RuntimeCertification:
        try:
            failed = json.loads(str(row[5]))
            if not isinstance(failed, list) or not all(isinstance(item, str) for item in failed):
                raise ValueError("invalid failed checks")
            return RuntimeCertification(
                certificate_id=str(row[0]),
                orchestrator_id=str(row[1]),
                runtime_version=str(row[2]),
                probe_execution_id=str(row[3]),
                passed=bool(int(row[4])),
                failed_checks=tuple(failed),
                checks_digest=str(row[6]),
                total_checks=int(row[7]),
                certified_at_epoch=float(row[8]),
            )
        except (TypeError, ValueError, json.JSONDecodeError) as exc:
            raise RuntimeCertificationCorrupt("invalid runtime certification row") from exc

    def record(self, certificate: RuntimeCertification) -> RuntimeCertification:
        with closing(self._connect()) as connection, connection:
            row = connection.execute(
                """
                SELECT certificate_id,orchestrator_id,runtime_version,probe_execution_id,
                       passed,failed_checks_json,checks_digest,total_checks,certified_at_epoch
                FROM runtime_certifications WHERE certificate_id=?
                """,
                (certificate.certificate_id,),
            ).fetchone()
            if row is not None:
                existing = self._decode(row)
                if existing != certificate:
                    raise RuntimeCertificationConflict(certificate.certificate_id)
                return existing
            connection.execute(
                """
                INSERT INTO runtime_certifications(
                    certificate_id,orchestrator_id,runtime_version,probe_execution_id,
                    passed,failed_checks_json,checks_digest,total_checks,certified_at_epoch
                ) VALUES(?,?,?,?,?,?,?,?,?)
                """,
                (
                    certificate.certificate_id,
                    certificate.orchestrator_id,
                    certificate.runtime_version,
                    certificate.probe_execution_id,
                    1 if certificate.passed else 0,
                    json.dumps(list(certificate.failed_checks), separators=(",", ":")),
                    certificate.checks_digest,
                    certificate.total_checks,
                    certificate.certified_at_epoch,
                ),
            )
        return certificate

    def get(self, certificate_id: str) -> RuntimeCertification | None:
        with closing(self._connect()) as connection, connection:
            row = connection.execute(
                """
                SELECT certificate_id,orchestrator_id,runtime_version,probe_execution_id,
                       passed,failed_checks_json,checks_digest,total_checks,certified_at_epoch
                FROM runtime_certifications WHERE certificate_id=?
                """,
                (certificate_id,),
            ).fetchone()
        return None if row is None else self._decode(row)

    def history(self, orchestrator_id: str) -> tuple[RuntimeCertification, ...]:
        with closing(self._connect()) as connection, connection:
            rows = connection.execute(
                """
                SELECT certificate_id,orchestrator_id,runtime_version,probe_execution_id,
                       passed,failed_checks_json,checks_digest,total_checks,certified_at_epoch
                FROM runtime_certifications
                WHERE orchestrator_id=?
                ORDER BY certified_at_epoch, certificate_id
                """,
                (orchestrator_id,),
            ).fetchall()
        return tuple(self._decode(row) for row in rows)


__all__ = [
    "RuntimeCertificationCorrupt",
    "SQLiteRuntimeCertificationStore",
]
