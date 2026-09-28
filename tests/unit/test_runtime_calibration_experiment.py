import json
from pathlib import Path
import tempfile
import unittest

from metao.runtime_health import RuntimeHealthPolicy
from scripts.runtime_calibration_experiment import (
    DEFAULT_SUPERVISION_INTERVALS_S,
    build_report,
    measure_health_policy,
    measure_supervision_interval,
)


class RuntimeCalibrationExperimentTests(unittest.TestCase):
    def test_supervision_tradeoff_is_deterministic_and_not_ranked(self):
        report = build_report()
        self.assertEqual(
            [item["interval_s"] for item in report["supervision_intervals"]],
            list(DEFAULT_SUPERVISION_INTERVALS_S),
        )
        self.assertEqual(
            report["supervision_pareto_frontier_s"],
            list(DEFAULT_SUPERVISION_INTERVALS_S),
        )
        self.assertFalse(report["selects_product_defaults"])
        self.assertFalse(report["real_provider_execution"])
        self.assertEqual(report["evidence_classification"], "SYNTHETIC_ONLY")
        self.assertNotIn("recommended_interval_s", report)

    def test_shorter_interval_has_lower_detection_latency_and_higher_observation_pressure(self):
        short = measure_supervision_interval(30)
        long = measure_supervision_interval(300)
        self.assertLess(
            short.mean_detection_latency_s,
            long.mean_detection_latency_s,
        )
        self.assertGreater(short.observations_per_hour, long.observations_per_hour)

    def test_current_health_defaults_are_measured_without_mutating_defaults(self):
        policy = RuntimeHealthPolicy()
        measurement = measure_health_policy(policy)
        self.assertEqual(policy.window_size, 5)
        self.assertEqual(policy.quarantine_consecutive_failures, 3)
        self.assertEqual(policy.unhealthy_failure_percent, 60)
        self.assertEqual(policy.recovery_successes_required, 2)
        self.assertFalse(measurement.transient_quarantined)
        self.assertIsNotNone(
            measurement.burst_first_unhealthy_or_quarantined_observation
        )
        self.assertIsNotNone(measurement.recovery_successes_until_healthy)

    def test_report_contains_full_health_policy_grid(self):
        report = build_report()
        self.assertEqual(len(report["health_policy_candidates"]), 81)
        for item in report["health_policy_candidates"]:
            self.assertIn("transient_quarantined", item)
            self.assertIn(
                "burst_first_unhealthy_or_quarantined_observation",
                item,
            )
            self.assertIn("recovery_successes_until_healthy", item)

    def test_report_is_json_serializable_and_stable_shape(self):
        report = build_report()
        encoded = json.dumps(report, sort_keys=True)
        decoded = json.loads(encoded)
        self.assertEqual(decoded["schema"], "metao-runtime-calibration-synthetic-v1")


if __name__ == "__main__":
    unittest.main()
