"""SQLite adapter for immutable runtime certificate revocations."""

from __future__ import annotations

from pathlib import Path
import sqlite3
from typing import Any

from .runtime_certification_revocation import (
    RuntimeCertificationRevocation,
    RuntimeCertificationRevocationConflict,
)


class RuntimeCertificationRevocationCorrupt(RuntimeError):
    pass


class SQLiteRuntimeCertificationRevocationStore:
    def __init__(self, path: str | Path) -> None:
        self._path = str(path)
        if self._path == ":memory:":
            raise ValueError(
                "use InMemoryRuntimeCertificationRevocationStore for process-local state"
            )
        Path(self._path).parent.mkdir(parents=True, exist_ok=True)
        self._initialize()

    def _connect(self) -> sqlite3.Connection:
        return sqlite3.connect(self._path, timeout=5.0)

    def _initialize(self) -> None:
        with self._connect() as connection:
            connection.execute(
                """
                CREATE TABLE IF NOT EXISTS runtime_certification_revocations (
                    certificate_id TEXT PRIMARY KEY,
                    orchestrator_id TEXT NOT NULL,
                    reason TEXT NOT NULL,
                    actor_id TEXT NOT NULL,
                    revoked_at_epoch REAL NOT NULL CHECK (revoked_at_epoch >= 0)
                )
                """
            )
            connection.execute(
                "CREATE INDEX IF NOT EXISTS idx_runtime_certification_revocations_orchestrator "
                "ON runtime_certification_revocations(orchestrator_id, revoked_at_epoch, certificate_id)"
            )

    @staticmethod
    def _decode(row: tuple[Any, ...]) -> RuntimeCertificationRevocation:
        try:
            return RuntimeCertificationRevocation(
                certificate_id=str(row[0]),
                orchestrator_id=str(row[1]),
                reason=str(row[2]),
                actor_id=str(row[3]),
                revoked_at_epoch=float(row[4]),
            )
        except (TypeError, ValueError) as exc:
            raise RuntimeCertificationRevocationCorrupt(
                "invalid runtime certification revocation row"
            ) from exc

    def record(
        self, revocation: RuntimeCertificationRevocation
    ) -> RuntimeCertificationRevocation:
        with self._connect() as connection:
            row = connection.execute(
                """
                SELECT certificate_id,orchestrator_id,reason,actor_id,revoked_at_epoch
                FROM runtime_certification_revocations WHERE certificate_id=?
                """,
                (revocation.certificate_id,),
            ).fetchone()
            if row is not None:
                existing = self._decode(row)
                if existing != revocation:
                    raise RuntimeCertificationRevocationConflict(revocation.certificate_id)
                return existing
            connection.execute(
                """
                INSERT INTO runtime_certification_revocations(
                    certificate_id,orchestrator_id,reason,actor_id,revoked_at_epoch
                ) VALUES(?,?,?,?,?)
                """,
                (
                    revocation.certificate_id,
                    revocation.orchestrator_id,
                    revocation.reason,
                    revocation.actor_id,
                    revocation.revoked_at_epoch,
                ),
            )
        return revocation

    def get(self, certificate_id: str) -> RuntimeCertificationRevocation | None:
        with self._connect() as connection:
            row = connection.execute(
                """
                SELECT certificate_id,orchestrator_id,reason,actor_id,revoked_at_epoch
                FROM runtime_certification_revocations WHERE certificate_id=?
                """,
                (certificate_id,),
            ).fetchone()
        return None if row is None else self._decode(row)

    def history(self, orchestrator_id: str) -> tuple[RuntimeCertificationRevocation, ...]:
        with self._connect() as connection:
            rows = connection.execute(
                """
                SELECT certificate_id,orchestrator_id,reason,actor_id,revoked_at_epoch
                FROM runtime_certification_revocations
                WHERE orchestrator_id=?
                ORDER BY revoked_at_epoch, certificate_id
                """,
                (orchestrator_id,),
            ).fetchall()
        return tuple(self._decode(row) for row in rows)


__all__ = [
    "RuntimeCertificationRevocationCorrupt",
    "SQLiteRuntimeCertificationRevocationStore",
]
