from __future__ import annotations

import unittest

from metao.benchmark_evidence import (
    BenchmarkEvidence,
    BenchmarkEvidenceSource,
    BenchmarkMetric,
    benchmark_evidence_comparable,
    is_benchmark_evidence_fresh,
)


def evidence(**overrides):
    values = {
        "evidence_id": "bench-evidence-1",
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
        "source": BenchmarkEvidenceSource.METAO_REPRODUCED,
        "raw_result_ref": "artifact://run-1/results.json",
        "metrics": (BenchmarkMetric("resolved_rate", 0.72, "ratio"),),
    }
    values.update(overrides)
    return BenchmarkEvidence(**values)


class BenchmarkEvidenceTests(unittest.TestCase):
    def test_same_model_under_different_harnesses_has_distinct_executor_identity(self):
        left = evidence()
        right = evidence(
            evidence_id="bench-evidence-2",
            harness_id="harness-b",
            harness_version="3.0",
        )

        self.assertNotEqual(
            left.executor_configuration_identity,
            right.executor_configuration_identity,
        )
        self.assertTrue(benchmark_evidence_comparable(left, right))

    def test_runtime_or_policy_mutation_changes_evidence_applicability_identity(self):
        left = evidence()
        right = evidence(
            evidence_id="bench-evidence-2",
            runtime_config_digest="different-runtime-config",
        )
        third = evidence(
            evidence_id="bench-evidence-3",
            tool_policy_digest="different-tool-policy",
        )

        self.assertNotEqual(
            left.executor_configuration_identity,
            right.executor_configuration_identity,
        )
        self.assertNotEqual(
            left.executor_configuration_identity,
            third.executor_configuration_identity,
        )

    def test_incompatible_benchmark_versions_are_not_comparable(self):
        left = evidence()
        right = evidence(
            evidence_id="bench-evidence-2",
            benchmark_version="v2",
        )
        self.assertFalse(benchmark_evidence_comparable(left, right))

    def test_freshness_fails_closed_on_clock_reversal_and_stale_evidence(self):
        item = evidence(observed_at_epoch=100.0)
        self.assertFalse(
            is_benchmark_evidence_fresh(
                item,
                now_epoch=90.0,
                max_age_seconds=60.0,
            )
        )
        self.assertTrue(
            is_benchmark_evidence_fresh(
                item,
                now_epoch=150.0,
                max_age_seconds=60.0,
            )
        )
        self.assertFalse(
            is_benchmark_evidence_fresh(
                item,
                now_epoch=161.0,
                max_age_seconds=60.0,
            )
        )

    def test_requires_complete_identity_and_at_least_one_metric(self):
        with self.assertRaisesRegex(ValueError, "complete stable identity"):
            evidence(raw_result_ref="")
        with self.assertRaisesRegex(ValueError, "at least one metric"):
            evidence(metrics=())

    def test_metric_names_are_unique_and_values_finite(self):
        with self.assertRaisesRegex(ValueError, "metric names must be unique"):
            evidence(
                metrics=(
                    BenchmarkMetric("score", 0.5),
                    BenchmarkMetric("score", 0.6),
                )
            )
        with self.assertRaisesRegex(ValueError, "must be finite"):
            BenchmarkMetric("score", float("nan"))


if __name__ == "__main__":
    unittest.main(verbosity=2)
