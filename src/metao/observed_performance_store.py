"""Durable storage for canonical observed-performance evidence."""

from __future__ import annotations

from contextlib import closing
import json
from pathlib import Path
import sqlite3
from typing import Any, Mapping, Protocol, runtime_checkable

from .observed_performance import (
    ObservedPerformanceEvidence,
    ObservedPerformanceMetric,
    ObservedPerformanceSource,
)


class ObservedPerformanceConflict(RuntimeError):
    pass


class ObservedPerformanceCorrupt(RuntimeError):
    pass


@runtime_checkable
class ObservedPerformanceStorePort(Protocol):
    def record(self, evidence: ObservedPerformanceEvidence) -> ObservedPerformanceEvidence: ...
    def get(self, evidence_id: str) -> ObservedPerformanceEvidence | None: ...
    def history(self, executor_id: str) -> tuple[ObservedPerformanceEvidence, ...]: ...


def observed_performance_from_mapping(payload: Mapping[str, Any]) -> ObservedPerformanceEvidence:
    metrics_raw = payload.get("metrics")
    if not isinstance(metrics_raw, list):
        raise ValueError("observed performance metrics must be a list")
    metrics = tuple(
        ObservedPerformanceMetric(
            name=str(item.get("name", "")),
            value=float(item["value"]),
            unit=str(item.get("unit", "")),
        )
        for item in metrics_raw
        if isinstance(item, dict)
    )
    if len(metrics) != len(metrics_raw):
        raise ValueError("observed performance metric must be an object")
    try:
        source = ObservedPerformanceSource(str(payload["source"]))
    except (KeyError, ValueError) as exc:
        raise ValueError("observed performance source is invalid") from exc

    def required(key: str) -> str:
        value = payload.get(key)
        if not isinstance(value, str) or not value.strip():
            raise ValueError(f"observed performance evidence requires {key}")
        return value

    try:
        observed_at_epoch = float(payload["observed_at_epoch"])
        sample_count = int(payload["sample_count"])
    except (KeyError, TypeError, ValueError) as exc:
        raise ValueError("observed performance evidence requires time/sample_count") from exc

    return ObservedPerformanceEvidence(
        evidence_id=required("evidence_id"),
        executor_id=required("executor_id"),
        executor_version=required("executor_version"),
        task_family=required("task_family"),
        runtime_config_digest=required("runtime_config_digest"),
        tool_policy_digest=required("tool_policy_digest"),
        environment_id=required("environment_id"),
        observed_at_epoch=observed_at_epoch,
        source=source,
        raw_result_ref=required("raw_result_ref"),
        sample_count=sample_count,
        metrics=metrics,
    )


class SQLiteObservedPerformanceStore:
    def __init__(self, path: str | Path) -> None:
        self._path = str(path)
        if self._path == ":memory:":
            raise ValueError("observed performance requires durable SQLite storage")
        Path(self._path).parent.mkdir(parents=True, exist_ok=True)
        self._initialize()

    def _connect(self) -> sqlite3.Connection:
        return sqlite3.connect(self._path, timeout=5.0)

    def _initialize(self) -> None:
        with closing(self._connect()) as connection, connection:
            connection.execute(
                """
                CREATE TABLE IF NOT EXISTS observed_performance_evidence (
                    evidence_id TEXT PRIMARY KEY,
                    executor_id TEXT NOT NULL,
                    observed_at_epoch REAL NOT NULL,
                    payload_json TEXT NOT NULL
                )
                """
            )
            connection.execute(
                """
                CREATE INDEX IF NOT EXISTS idx_observed_performance_executor
                ON observed_performance_evidence(executor_id, observed_at_epoch, evidence_id)
                """
            )

    @staticmethod
    def _encode(evidence: ObservedPerformanceEvidence) -> str:
        payload = {
            "evidence_id": evidence.evidence_id,
            "executor_id": evidence.executor_id,
            "executor_version": evidence.executor_version,
            "task_family": evidence.task_family,
            "runtime_config_digest": evidence.runtime_config_digest,
            "tool_policy_digest": evidence.tool_policy_digest,
            "environment_id": evidence.environment_id,
            "observed_at_epoch": evidence.observed_at_epoch,
            "source": evidence.source.value,
            "raw_result_ref": evidence.raw_result_ref,
            "sample_count": evidence.sample_count,
            "metrics": [
                {"name": metric.name, "value": metric.value, "unit": metric.unit}
                for metric in evidence.metrics
            ],
        }
        return json.dumps(payload, sort_keys=True, separators=(",", ":"))

    @staticmethod
    def _decode(raw: str) -> ObservedPerformanceEvidence:
        try:
            payload = json.loads(raw)
            if not isinstance(payload, dict):
                raise ValueError("invalid observed performance payload")
            return observed_performance_from_mapping(payload)
        except (TypeError, ValueError, KeyError, json.JSONDecodeError) as exc:
            raise ObservedPerformanceCorrupt("invalid observed performance evidence row") from exc

    def record(self, evidence: ObservedPerformanceEvidence) -> ObservedPerformanceEvidence:
        payload_json = self._encode(evidence)
        with closing(self._connect()) as connection, connection:
            row = connection.execute(
                "SELECT payload_json FROM observed_performance_evidence WHERE evidence_id=?",
                (evidence.evidence_id,),
            ).fetchone()
            if row is not None:
                existing = self._decode(str(row[0]))
                if existing != evidence:
                    raise ObservedPerformanceConflict(evidence.evidence_id)
                return existing
            connection.execute(
                """
                INSERT INTO observed_performance_evidence(
                    evidence_id, executor_id, observed_at_epoch, payload_json
                ) VALUES(?,?,?,?)
                """,
                (
                    evidence.evidence_id,
                    evidence.executor_id,
                    evidence.observed_at_epoch,
                    payload_json,
                ),
            )
        return evidence

    def get(self, evidence_id: str) -> ObservedPerformanceEvidence | None:
        with closing(self._connect()) as connection, connection:
            row = connection.execute(
                "SELECT payload_json FROM observed_performance_evidence WHERE evidence_id=?",
                (evidence_id,),
            ).fetchone()
        return None if row is None else self._decode(str(row[0]))

    def history(self, executor_id: str) -> tuple[ObservedPerformanceEvidence, ...]:
        with closing(self._connect()) as connection, connection:
            rows = connection.execute(
                """
                SELECT payload_json
                FROM observed_performance_evidence
                WHERE executor_id=?
                ORDER BY observed_at_epoch, evidence_id
                """,
                (executor_id,),
            ).fetchall()
        return tuple(self._decode(str(row[0])) for row in rows)


__all__ = [
    "ObservedPerformanceConflict",
    "ObservedPerformanceCorrupt",
    "ObservedPerformanceStorePort",
    "SQLiteObservedPerformanceStore",
    "observed_performance_from_mapping",
]
