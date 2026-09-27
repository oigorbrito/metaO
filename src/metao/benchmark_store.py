"""Durable storage and JSON ingestion for canonical benchmark evidence."""

from __future__ import annotations

from contextlib import closing
import json
from pathlib import Path
import sqlite3
from typing import Any, Mapping, Protocol, runtime_checkable

from .benchmark_evidence import (
    BenchmarkEvidence,
    BenchmarkEvidenceSource,
    BenchmarkMetric,
)


class BenchmarkEvidenceConflict(RuntimeError):
    pass


class BenchmarkEvidenceCorrupt(RuntimeError):
    pass


@runtime_checkable
class BenchmarkEvidenceStorePort(Protocol):
    def record(self, evidence: BenchmarkEvidence) -> BenchmarkEvidence: ...
    def get(self, evidence_id: str) -> BenchmarkEvidence | None: ...
    def history(self, executor_id: str) -> tuple[BenchmarkEvidence, ...]: ...


def benchmark_evidence_from_mapping(payload: Mapping[str, Any]) -> BenchmarkEvidence:
    metrics_value = payload.get("metrics")
    if not isinstance(metrics_value, list):
        raise ValueError("benchmark evidence metrics must be a list")

    metrics: list[BenchmarkMetric] = []
    for item in metrics_value:
        if not isinstance(item, dict):
            raise ValueError("benchmark metric must be an object")
        metrics.append(
            BenchmarkMetric(
                name=str(item.get("name", "")),
                value=float(item["value"]),
                unit=str(item.get("unit", "score")),
            )
        )

    try:
        source = BenchmarkEvidenceSource(str(payload["source"]))
    except (KeyError, ValueError) as exc:
        raise ValueError("benchmark evidence source is invalid") from exc

    def required(key: str) -> str:
        value = payload.get(key)
        if not isinstance(value, str) or not value.strip():
            raise ValueError(f"benchmark evidence requires {key}")
        return value

    try:
        observed_at_epoch = float(payload["observed_at_epoch"])
    except (KeyError, TypeError, ValueError) as exc:
        raise ValueError("benchmark evidence requires observed_at_epoch") from exc

    return BenchmarkEvidence(
        evidence_id=required("evidence_id"),
        benchmark_id=required("benchmark_id"),
        benchmark_version=required("benchmark_version"),
        task_set=required("task_set"),
        executor_id=required("executor_id"),
        executor_version=required("executor_version"),
        harness_id=required("harness_id"),
        harness_version=required("harness_version"),
        model_id=required("model_id"),
        provider_id=required("provider_id"),
        model_version=required("model_version"),
        runtime_config_digest=required("runtime_config_digest"),
        tool_policy_digest=required("tool_policy_digest"),
        environment_id=required("environment_id"),
        observed_at_epoch=observed_at_epoch,
        source=source,
        raw_result_ref=required("raw_result_ref"),
        metrics=tuple(metrics),
    )


def load_benchmark_evidence_json(path: str | Path) -> BenchmarkEvidence:
    try:
        payload = json.loads(Path(path).read_text(encoding="utf-8"))
    except OSError as exc:
        raise ValueError(f"cannot read benchmark evidence file: {path}") from exc
    except json.JSONDecodeError as exc:
        raise ValueError(f"invalid benchmark evidence JSON: {path}") from exc
    if not isinstance(payload, dict):
        raise ValueError("benchmark evidence file must contain a JSON object")
    return benchmark_evidence_from_mapping(payload)


class SQLiteBenchmarkEvidenceStore:
    def __init__(self, path: str | Path) -> None:
        self._path = str(path)
        if self._path == ":memory:":
            raise ValueError("benchmark evidence requires durable SQLite storage")
        Path(self._path).parent.mkdir(parents=True, exist_ok=True)
        self._initialize()

    def _connect(self) -> sqlite3.Connection:
        return sqlite3.connect(self._path, timeout=5.0)

    def _initialize(self) -> None:
        with closing(self._connect()) as connection, connection:
            connection.execute(
                """
                CREATE TABLE IF NOT EXISTS benchmark_evidence (
                    evidence_id TEXT PRIMARY KEY,
                    executor_id TEXT NOT NULL,
                    observed_at_epoch REAL NOT NULL,
                    payload_json TEXT NOT NULL
                )
                """
            )
            connection.execute(
                """
                CREATE INDEX IF NOT EXISTS idx_benchmark_evidence_executor
                ON benchmark_evidence(executor_id, observed_at_epoch, evidence_id)
                """
            )

    @staticmethod
    def _encode(evidence: BenchmarkEvidence) -> str:
        payload = {
            "evidence_id": evidence.evidence_id,
            "benchmark_id": evidence.benchmark_id,
            "benchmark_version": evidence.benchmark_version,
            "task_set": evidence.task_set,
            "executor_id": evidence.executor_id,
            "executor_version": evidence.executor_version,
            "harness_id": evidence.harness_id,
            "harness_version": evidence.harness_version,
            "model_id": evidence.model_id,
            "provider_id": evidence.provider_id,
            "model_version": evidence.model_version,
            "runtime_config_digest": evidence.runtime_config_digest,
            "tool_policy_digest": evidence.tool_policy_digest,
            "environment_id": evidence.environment_id,
            "observed_at_epoch": evidence.observed_at_epoch,
            "source": evidence.source.value,
            "raw_result_ref": evidence.raw_result_ref,
            "metrics": [
                {"name": metric.name, "value": metric.value, "unit": metric.unit}
                for metric in evidence.metrics
            ],
        }
        return json.dumps(payload, sort_keys=True, separators=(",", ":"))

    @staticmethod
    def _decode(payload_json: str) -> BenchmarkEvidence:
        try:
            payload = json.loads(payload_json)
            if not isinstance(payload, dict):
                raise ValueError("invalid benchmark evidence payload")
            return benchmark_evidence_from_mapping(payload)
        except (TypeError, ValueError, json.JSONDecodeError, KeyError) as exc:
            raise BenchmarkEvidenceCorrupt("invalid benchmark evidence row") from exc

    def record(self, evidence: BenchmarkEvidence) -> BenchmarkEvidence:
        payload_json = self._encode(evidence)
        with closing(self._connect()) as connection, connection:
            row = connection.execute(
                "SELECT payload_json FROM benchmark_evidence WHERE evidence_id=?",
                (evidence.evidence_id,),
            ).fetchone()
            if row is not None:
                existing = self._decode(str(row[0]))
                if existing != evidence:
                    raise BenchmarkEvidenceConflict(evidence.evidence_id)
                return existing
            connection.execute(
                """
                INSERT INTO benchmark_evidence(
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

    def get(self, evidence_id: str) -> BenchmarkEvidence | None:
        with closing(self._connect()) as connection, connection:
            row = connection.execute(
                "SELECT payload_json FROM benchmark_evidence WHERE evidence_id=?",
                (evidence_id,),
            ).fetchone()
        return None if row is None else self._decode(str(row[0]))

    def history(self, executor_id: str) -> tuple[BenchmarkEvidence, ...]:
        with closing(self._connect()) as connection, connection:
            rows = connection.execute(
                """
                SELECT payload_json
                FROM benchmark_evidence
                WHERE executor_id=?
                ORDER BY observed_at_epoch, evidence_id
                """,
                (executor_id,),
            ).fetchall()
        return tuple(self._decode(str(row[0])) for row in rows)


__all__ = [
    "BenchmarkEvidenceConflict",
    "BenchmarkEvidenceCorrupt",
    "BenchmarkEvidenceStorePort",
    "SQLiteBenchmarkEvidenceStore",
    "benchmark_evidence_from_mapping",
    "load_benchmark_evidence_json",
]
