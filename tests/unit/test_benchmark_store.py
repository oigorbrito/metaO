from __future__ import annotations

import json
from pathlib import Path
import sqlite3
import tempfile
import unittest

from metao.benchmark_evidence import BenchmarkEvidenceSource
from metao.benchmark_store import (
    BenchmarkEvidenceConflict,
    BenchmarkEvidenceCorrupt,
    SQLiteBenchmarkEvidenceStore,
    load_benchmark_evidence_json,
)


def payload(evidence_id: str = "evidence-1", *, value: float = 0.72) -> dict:
    return {
        "evidence_id": evidence_id,
        "benchmark_id": "software-engineering",
        "benchmark_version": "v1",
        "task_set": "verified",
        "executor_id": "executor-a",
        "executor_version": "1.0",
        "harness_id": "harness-a",
        "harness_version": "2.0",
        "model_id": "model-a",
        "provider_id": "provider-a",
        "model_version": "2026-09",
        "runtime_config_digest": "runtime-config-sha256",
        "tool_policy_digest": "tool-policy-sha256",
        "environment_id": "linux-container-v1",
        "observed_at_epoch": 100.0,
        "source": "METAO_REPRODUCED",
        "raw_result_ref": "artifact://run-1/results.json",
        "metrics": [{"name": "resolved_rate", "value": value, "unit": "ratio"}],
    }


class BenchmarkEvidenceStoreTests(unittest.TestCase):
    def test_load_json_and_round_trip_durable_store(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            evidence_path = root / "evidence.json"
            db = root / "metao.db"
            evidence_path.write_text(json.dumps(payload()), encoding="utf-8")

            evidence = load_benchmark_evidence_json(evidence_path)
            self.assertEqual(evidence.source, BenchmarkEvidenceSource.METAO_REPRODUCED)

            store = SQLiteBenchmarkEvidenceStore(db)
            self.assertEqual(store.record(evidence), evidence)

            reopened = SQLiteBenchmarkEvidenceStore(db)
            self.assertEqual(reopened.get("evidence-1"), evidence)
            self.assertEqual(reopened.history("executor-a"), (evidence,))

    def test_duplicate_same_payload_is_idempotent_but_conflict_fails_closed(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            first_path = root / "first.json"
            second_path = root / "second.json"
            first_path.write_text(json.dumps(payload()), encoding="utf-8")
            second_path.write_text(json.dumps(payload(value=0.91)), encoding="utf-8")

            first = load_benchmark_evidence_json(first_path)
            second = load_benchmark_evidence_json(second_path)
            store = SQLiteBenchmarkEvidenceStore(root / "metao.db")

            self.assertEqual(store.record(first), first)
            self.assertEqual(store.record(first), first)
            with self.assertRaises(BenchmarkEvidenceConflict):
                store.record(second)

    def test_history_is_executor_scoped_and_deterministic(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            store = SQLiteBenchmarkEvidenceStore(root / "metao.db")

            items = []
            for evidence_id, epoch in (("b", 200.0), ("a", 100.0)):
                item_payload = payload(evidence_id)
                item_payload["observed_at_epoch"] = epoch
                path = root / f"{evidence_id}.json"
                path.write_text(json.dumps(item_payload), encoding="utf-8")
                item = load_benchmark_evidence_json(path)
                store.record(item)
                items.append(item)

            other_payload = payload("other")
            other_payload["executor_id"] = "executor-b"
            other_path = root / "other.json"
            other_path.write_text(json.dumps(other_payload), encoding="utf-8")
            store.record(load_benchmark_evidence_json(other_path))

            history = store.history("executor-a")
            self.assertEqual([item.evidence_id for item in history], ["a", "b"])

    def test_corrupt_durable_payload_is_detected(self):
        with tempfile.TemporaryDirectory() as temp:
            db = Path(temp) / "metao.db"
            store = SQLiteBenchmarkEvidenceStore(db)
            with sqlite3.connect(db) as connection:
                connection.execute(
                    """
                    INSERT INTO benchmark_evidence(
                        evidence_id, executor_id, observed_at_epoch, payload_json
                    ) VALUES(?,?,?,?)
                    """,
                    ("broken", "executor-a", 100.0, "{not-json"),
                )
                connection.commit()

            with self.assertRaises(BenchmarkEvidenceCorrupt):
                store.get("broken")

    def test_invalid_ingestion_is_rejected_before_persistence(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            path = root / "evidence.json"
            broken = payload()
            broken["metrics"] = "not-a-list"
            path.write_text(json.dumps(broken), encoding="utf-8")
            db = root / "metao.db"

            with self.assertRaises(ValueError):
                load_benchmark_evidence_json(path)
            self.assertFalse(db.exists())


if __name__ == "__main__":
    unittest.main(verbosity=2)
