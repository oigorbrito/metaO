"""Durable, non-authoritative audit receipts for executor routing decisions."""

from __future__ import annotations

from contextlib import closing
from dataclasses import asdict, dataclass
from hashlib import sha256
import json
from math import isfinite
from pathlib import Path
import sqlite3
from typing import Protocol, runtime_checkable


@dataclass(frozen=True, slots=True)
class RoutingCandidateReceipt:
    executor_id: str
    rank: int
    total_score: float
    base_score: float
    benchmark_score: float | None
    evidence_id: str | None
    observed_evidence_id: str | None = None
    reason: str = ""

    def __post_init__(self) -> None:
        if not self.executor_id.strip() or self.rank < 1 or not self.reason.strip():
            raise ValueError("routing candidate receipt is invalid")
        numeric = (self.total_score, self.base_score)
        if self.benchmark_score is not None:
            numeric += (self.benchmark_score,)
        if not all(isfinite(value) for value in numeric):
            raise ValueError("routing candidate scores must be finite")


@dataclass(frozen=True, slots=True)
class RoutingDecisionReceipt:
    receipt_id: str
    mission_id: str
    execution_id: str
    attempt_number: int
    now_epoch: float
    policy_digest: str
    selected_executor_id: str
    candidates: tuple[RoutingCandidateReceipt, ...]
    authority_scope: str = "routing-audit-only"

    def __post_init__(self) -> None:
        required = (
            self.receipt_id,
            self.mission_id,
            self.execution_id,
            self.policy_digest,
            self.selected_executor_id,
            self.authority_scope,
        )
        if not all(value.strip() for value in required):
            raise ValueError("routing decision receipt requires stable identity")
        if self.attempt_number < 1:
            raise ValueError("routing decision attempt number must be positive")
        if not isfinite(self.now_epoch) or self.now_epoch < 0:
            raise ValueError("routing decision time must be finite and non-negative")
        if not self.candidates:
            raise ValueError("routing decision receipt requires candidates")
        ids = tuple(candidate.executor_id for candidate in self.candidates)
        if len(ids) != len(set(ids)):
            raise ValueError("routing decision candidates must be unique")
        if self.selected_executor_id not in set(ids):
            raise ValueError("selected executor must be present in candidate receipts")
        if tuple(candidate.rank for candidate in self.candidates) != tuple(
            range(1, len(self.candidates) + 1)
        ):
            raise ValueError("routing decision candidate ranks must be contiguous")


def routing_policy_digest(payload: dict[str, object]) -> str:
    encoded = json.dumps(payload, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return "sha256:" + sha256(encoded).hexdigest()


def routing_receipt_id(
    *,
    mission_id: str,
    execution_id: str,
    attempt_number: int,
    now_epoch: float,
    policy_digest: str,
    selected_executor_id: str,
    candidates: tuple[RoutingCandidateReceipt, ...],
) -> str:
    payload = {
        "mission_id": mission_id,
        "execution_id": execution_id,
        "attempt_number": attempt_number,
        "now_epoch": now_epoch,
        "policy_digest": policy_digest,
        "selected_executor_id": selected_executor_id,
        "candidates": [asdict(candidate) for candidate in candidates],
    }
    return routing_policy_digest(payload)


class RoutingDecisionConflict(RuntimeError):
    pass


class RoutingDecisionCorrupt(RuntimeError):
    pass


@runtime_checkable
class RoutingDecisionStorePort(Protocol):
    def record(self, receipt: RoutingDecisionReceipt) -> RoutingDecisionReceipt: ...
    def get(self, receipt_id: str) -> RoutingDecisionReceipt | None: ...
    def history(self, mission_id: str) -> tuple[RoutingDecisionReceipt, ...]: ...


class SQLiteRoutingDecisionStore:
    def __init__(self, path: str | Path) -> None:
        self._path = str(path)
        if self._path == ":memory:":
            raise ValueError("routing decisions require durable SQLite storage")
        Path(self._path).parent.mkdir(parents=True, exist_ok=True)
        self._initialize()

    def _connect(self) -> sqlite3.Connection:
        return sqlite3.connect(self._path, timeout=5.0)

    def _initialize(self) -> None:
        with closing(self._connect()) as connection, connection:
            connection.execute(
                """
                CREATE TABLE IF NOT EXISTS routing_decision_receipts (
                    receipt_id TEXT PRIMARY KEY,
                    mission_id TEXT NOT NULL,
                    execution_id TEXT NOT NULL,
                    attempt_number INTEGER NOT NULL,
                    payload_json TEXT NOT NULL
                )
                """
            )
            connection.execute(
                """
                CREATE INDEX IF NOT EXISTS idx_routing_decision_mission
                ON routing_decision_receipts(mission_id, attempt_number, execution_id, receipt_id)
                """
            )

    @staticmethod
    def _encode(receipt: RoutingDecisionReceipt) -> str:
        payload = asdict(receipt)
        payload["candidates"] = [asdict(candidate) for candidate in receipt.candidates]
        return json.dumps(payload, sort_keys=True, separators=(",", ":"))

    @staticmethod
    def _decode(payload_json: str) -> RoutingDecisionReceipt:
        try:
            payload = json.loads(payload_json)
            candidates = tuple(
                RoutingCandidateReceipt(**candidate)
                for candidate in payload.pop("candidates")
            )
            return RoutingDecisionReceipt(candidates=candidates, **payload)
        except (TypeError, ValueError, KeyError, json.JSONDecodeError) as exc:
            raise RoutingDecisionCorrupt("invalid routing decision receipt row") from exc

    def record(self, receipt: RoutingDecisionReceipt) -> RoutingDecisionReceipt:
        payload_json = self._encode(receipt)
        with closing(self._connect()) as connection, connection:
            row = connection.execute(
                "SELECT payload_json FROM routing_decision_receipts WHERE receipt_id=?",
                (receipt.receipt_id,),
            ).fetchone()
            if row is not None:
                existing = self._decode(str(row[0]))
                if existing != receipt:
                    raise RoutingDecisionConflict(receipt.receipt_id)
                return existing
            connection.execute(
                """
                INSERT INTO routing_decision_receipts(
                    receipt_id, mission_id, execution_id, attempt_number, payload_json
                ) VALUES(?,?,?,?,?)
                """,
                (
                    receipt.receipt_id,
                    receipt.mission_id,
                    receipt.execution_id,
                    receipt.attempt_number,
                    payload_json,
                ),
            )
        return receipt

    def get(self, receipt_id: str) -> RoutingDecisionReceipt | None:
        with closing(self._connect()) as connection, connection:
            row = connection.execute(
                "SELECT payload_json FROM routing_decision_receipts WHERE receipt_id=?",
                (receipt_id,),
            ).fetchone()
        return None if row is None else self._decode(str(row[0]))

    def history(self, mission_id: str) -> tuple[RoutingDecisionReceipt, ...]:
        with closing(self._connect()) as connection, connection:
            rows = connection.execute(
                """
                SELECT payload_json
                FROM routing_decision_receipts
                WHERE mission_id=?
                ORDER BY attempt_number, execution_id, receipt_id
                """,
                (mission_id,),
            ).fetchall()
        return tuple(self._decode(str(row[0])) for row in rows)


__all__ = [
    "RoutingCandidateReceipt",
    "RoutingDecisionReceipt",
    "RoutingDecisionConflict",
    "RoutingDecisionCorrupt",
    "RoutingDecisionStorePort",
    "SQLiteRoutingDecisionStore",
    "routing_policy_digest",
    "routing_receipt_id",
]
