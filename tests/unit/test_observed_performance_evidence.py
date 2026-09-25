from __future__ import annotations

from pathlib import Path
import sqlite3
import tempfile
import unittest

from metao.observed_performance import (
    ObservedPerformanceEvidence,
    ObservedPerformanceMetric,
    ObservedPerformanceSource,
    aggregate_compatible_observations,
)
from metao.observed_performance_store import (
    ObservedPerformanceConflict,
    ObservedPerformanceCorrupt,
    SQLiteObservedPerformanceStore,
)


def evidence(
    evidence_id: str,
    *,
    executor_id: str = "runtime-a",
    value: float = 0.8,
    at: float = 100.0,
    samples: int = 1,
    runtime_digest: str = "runtime-a-config",
) -> ObservedPerformanceEvidence:
    return ObservedPerformanceEvidence(
        evidence_id=evidence_id,
        executor_id=executor_id,
        executor_version="1.0",
        task_family="coding",
        runtime_config_digest=runtime_digest,
        tool_policy_digest="tool-policy",
        environment_id="test",
        observed_at_epoch=at,
        source=ObservedPerformanceSource.METAO_EXECUTION,
        raw_result_ref=f"artifact://{evidence_id}",
        sample_count=samples,
        metrics=(ObservedPerformanceMetric("success_rate", value, "ratio"),),
    )


class ObservedPerformanceEvidenceTests(unittest.TestCase):
    def test_sqlite_store_is_idempotent_and_conflicts_fail_closed(self):
        with tempfile.TemporaryDirectory() as temp:
            store = SQLiteObservedPerformanceStore(Path(temp) / "observed.db")
            item = evidence("e1")
            self.assertEqual(store.record(item), item)
            self.assertEqual(store.record(item), item)
            self.assertEqual(store.get("e1"), item)
            self.assertEqual(store.history("runtime-a"), (item,))
            with self.assertRaises(ObservedPerformanceConflict):
                store.record(evidence("e1", value=0.1))

    def test_corrupt_persisted_row_is_detected(self):
        with tempfile.TemporaryDirectory() as temp:
            path = Path(temp) / "observed.db"
            store = SQLiteObservedPerformanceStore(path)
            store.record(evidence("e1"))
            with sqlite3.connect(path) as connection:
                connection.execute(
                    "UPDATE observed_performance_evidence SET payload_json=? WHERE evidence_id=?",
                    ("{}", "e1"),
                )
                connection.commit()
            with self.assertRaises(ObservedPerformanceCorrupt):
                store.get("e1")

    def test_multiple_fresh_records_aggregate_by_sample_count(self):
        result = aggregate_compatible_observations(
            (
                evidence("e1", value=0.2, at=100.0, samples=1),
                evidence("e2", value=0.8, at=110.0, samples=3),
            ),
            task_family="coding",
            metric_name="success_rate",
            now_epoch=120.0,
            max_age_seconds=60.0,
            min_samples=4,
        )
        self.assertIsNotNone(result)
        assert result is not None
        self.assertAlmostEqual(result.value, 0.65)
        self.assertEqual(result.sample_count, 4)
        self.assertEqual(result.evidence_ids, ("e1", "e2"))

    def test_mixed_runtime_identity_is_not_aggregated(self):
        result = aggregate_compatible_observations(
            (
                evidence("e1", runtime_digest="config-a"),
                evidence("e2", runtime_digest="config-b"),
            ),
            task_family="coding",
            metric_name="success_rate",
            now_epoch=120.0,
            max_age_seconds=60.0,
            min_samples=1,
        )
        self.assertIsNone(result)

    def test_stale_records_do_not_satisfy_min_samples(self):
        result = aggregate_compatible_observations(
            (
                evidence("fresh", at=115.0, samples=1),
                evidence("stale", at=1.0, samples=10),
            ),
            task_family="coding",
            metric_name="success_rate",
            now_epoch=120.0,
            max_age_seconds=10.0,
            min_samples=2,
        )
        self.assertIsNone(result)

    def test_mapping_rejects_fractional_or_boolean_sample_count(self):
        from metao.observed_performance_store import observed_performance_from_mapping

        payload = {
            "evidence_id": "e1",
            "executor_id": "runtime-a",
            "executor_version": "1.0",
            "task_family": "coding",
            "runtime_config_digest": "runtime-a-config",
            "tool_policy_digest": "tool-policy",
            "environment_id": "test",
            "observed_at_epoch": 100.0,
            "source": "metao_execution",
            "raw_result_ref": "artifact://e1",
            "sample_count": 1.5,
            "metrics": [{"name": "success_rate", "value": 0.8, "unit": "ratio"}],
        }
        with self.assertRaisesRegex(ValueError, "sample_count"):
            observed_performance_from_mapping(payload)

        payload["sample_count"] = True
        with self.assertRaisesRegex(ValueError, "sample_count"):
            observed_performance_from_mapping(payload)

    def test_mapping_rejects_boolean_metric_value(self):
        from metao.observed_performance_store import observed_performance_from_mapping

        payload = {
            "evidence_id": "e1",
            "executor_id": "runtime-a",
            "executor_version": "1.0",
            "task_family": "coding",
            "runtime_config_digest": "runtime-a-config",
            "tool_policy_digest": "tool-policy",
            "environment_id": "test",
            "observed_at_epoch": 100.0,
            "source": "metao_execution",
            "raw_result_ref": "artifact://e1",
            "sample_count": 1,
            "metrics": [{"name": "success_rate", "value": True, "unit": "ratio"}],
        }
        with self.assertRaisesRegex(ValueError, "metric value"):
            observed_performance_from_mapping(payload)


if __name__ == "__main__":
    unittest.main(verbosity=2)
