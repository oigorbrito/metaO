from __future__ import annotations

import unittest

from metao.benchmark_evidence import BenchmarkEvidenceSource
from metao.benchmark_ingestion import (
    BENCHMARK_FAMILY_PROFILES,
    ingest_benchmark_family_result,
)


def identity(**overrides):
    values = {
        "evidence_id": "evidence-1",
        "task_set": None,
        "executor_id": "executor",
        "executor_version": "1.0",
        "harness_id": "harness",
        "harness_version": "1.0",
        "model_id": "model",
        "provider_id": "provider",
        "model_version": "2026-09",
        "runtime_config_digest": "runtime-sha256",
        "tool_policy_digest": "policy-sha256",
        "environment_id": "isolated-linux",
        "observed_at_epoch": 100.0,
        "source": BenchmarkEvidenceSource.EXTERNAL_REPORTED,
        "raw_result_ref": "artifact://official-result",
    }
    values.update(overrides)
    return values


class BenchmarkFamilyIngestionTests(unittest.TestCase):
    def test_official_family_profiles_have_immutable_subject_pins(self):
        self.assertEqual(len(BENCHMARK_FAMILY_PROFILES), 3)
        for profile in BENCHMARK_FAMILY_PROFILES.values():
            self.assertRegex(profile.upstream_revision, r"^[0-9a-f]{40}$")

    def test_normalizes_swe_bench_and_terminal_results(self):
        swe = ingest_benchmark_family_result(
            "swe-bench", {"resolved": 8, "total": 10}, **identity()
        )
        terminal = ingest_benchmark_family_result(
            "terminal-bench-core", {"pass_rate": 3 / 4}, **identity(evidence_id="terminal")
        )
        self.assertEqual(swe.task_set, "verified")
        self.assertEqual(swe.metrics[0].value, 0.8)
        self.assertEqual(terminal.metrics[0].value, 0.75)

    def test_normalizes_agentgovbench_aggregate(self):
        evidence = ingest_benchmark_family_result(
            "agentgovbench",
            {"aggregate": {"total_passed": 13, "total_scenarios": 48}},
            **identity(evidence_id="agentgov")
        )
        self.assertEqual(evidence.benchmark_version, "0.2")
        self.assertAlmostEqual(evidence.metrics[0].value, 13 / 48)

    def test_unknown_or_malformed_results_fail_closed(self):
        with self.assertRaisesRegex(ValueError, "unsupported benchmark family"):
            ingest_benchmark_family_result("unknown", {"pass_rate": 1 / 1}, **identity())
        with self.assertRaisesRegex(ValueError, "supported aggregate metric"):
            ingest_benchmark_family_result(
                "swe-bench", {"not_a_metric": 1}, **identity()
            )
        with self.assertRaisesRegex(ValueError, "finite ratio"):
            ingest_benchmark_family_result(
                "terminal-bench-core", {"pass_rate": 2 / 1}, **identity()
            )


if __name__ == "__main__":
    unittest.main(verbosity=2)
