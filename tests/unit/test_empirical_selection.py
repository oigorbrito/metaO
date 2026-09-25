from __future__ import annotations

from pathlib import Path
import tempfile
import unittest

from metao.benchmark_evidence import BenchmarkEvidence, BenchmarkEvidenceSource, BenchmarkMetric
from metao.benchmark_routing import BenchmarkRoutingPolicy
from metao.benchmark_store import SQLiteBenchmarkEvidenceStore
from metao.empirical_selection import (
    EmpiricalFamilyRoutingPolicy,
    EmpiricalTaskFamilySelectionPolicy,
    ObservedPerformanceRoutingPolicy,
)
from metao.observed_performance import (
    ObservedPerformanceEvidence,
    ObservedPerformanceMetric,
    ObservedPerformanceSource,
)
from metao.observed_performance_store import SQLiteObservedPerformanceStore
from metao.routing_decision import SQLiteRoutingDecisionStore
from metao.strategy import OrchestratorPoolState, OrchestratorStatus, SelectionContext


def bench(executor_id: str, score: float) -> BenchmarkEvidence:
    return BenchmarkEvidence(
        evidence_id=f"bench-{executor_id}",
        benchmark_id="matrix",
        benchmark_version="v1",
        task_set="coding",
        executor_id=executor_id,
        executor_version="1",
        harness_id="h",
        harness_version="1",
        model_id="m",
        provider_id="p",
        model_version="1",
        runtime_config_digest=f"r-{executor_id}",
        tool_policy_digest="t",
        environment_id="env",
        observed_at_epoch=100.0,
        source=BenchmarkEvidenceSource.METAO_REPRODUCED,
        raw_result_ref="artifact://bench",
        metrics=(BenchmarkMetric("success_rate", score, "ratio"),),
    )


def observed(executor_id: str, score: float, *, at: float = 110.0, samples: int = 5) -> ObservedPerformanceEvidence:
    return ObservedPerformanceEvidence(
        evidence_id=f"obs-{executor_id}-{at}",
        executor_id=executor_id,
        executor_version="1",
        task_family="coding",
        runtime_config_digest=f"r-{executor_id}",
        tool_policy_digest="t",
        environment_id="env",
        observed_at_epoch=at,
        source=ObservedPerformanceSource.METAO_EXECUTION,
        raw_result_ref="artifact://obs",
        sample_count=samples,
        metrics=(
            ObservedPerformanceMetric("success_rate", score, "ratio"),
            ObservedPerformanceMetric("latency_ms", 50.0, "ms"),
            ObservedPerformanceMetric("cost", 0.1, "currency"),
        ),
    )


class EmpiricalSelectionTests(unittest.TestCase):
    def test_routing_candidate_receipt_keeps_legacy_reason_position(self):
        from metao.routing_decision import RoutingCandidateReceipt

        receipt = RoutingCandidateReceipt(
            "alpha",
            1,
            0.9,
            0.8,
            0.7,
            "bench-alpha",
            "legacy-reason",
        )
        self.assertEqual(receipt.reason, "legacy-reason")
        self.assertEqual(receipt.observed_evidence_ids, ())

    def test_observed_performance_can_change_rank_without_reintroducing_candidates(self):
        with tempfile.TemporaryDirectory() as temp:
            db = Path(temp) / "metao.db"
            benchmark_store = SQLiteBenchmarkEvidenceStore(db)
            observed_store = SQLiteObservedPerformanceStore(db)
            decision_store = SQLiteRoutingDecisionStore(db)
            for executor_id, score in (("alpha", 0.9), ("beta", 0.8), ("outside", 1.0)):
                benchmark_store.record(bench(executor_id, score))
            observed_store.record(observed("alpha", 0.1, at=108.0, samples=1))
            observed_store.record(observed("alpha", 0.3, at=109.0, samples=1))
            observed_store.record(observed("beta", 1.0, at=108.0, samples=1))
            observed_store.record(observed("beta", 0.9, at=110.0, samples=1))
            observed_store.record(observed("outside", 1.0, at=110.0, samples=2))

            policy = EmpiricalTaskFamilySelectionPolicy(
                benchmark_store,
                observed_store,
                {
                    "coding": EmpiricalFamilyRoutingPolicy(
                        BenchmarkRoutingPolicy(
                            benchmark_id="matrix",
                            benchmark_version="v1",
                            task_set="coding",
                            metric_name="success_rate",
                            base_weight=0.1,
                            benchmark_weight=0.9,
                            max_age_seconds=60.0,
                        ),
                        ObservedPerformanceRoutingPolicy(
                            metric_name="success_rate",
                            prior_weight=0.2,
                            observed_weight=0.8,
                            max_age_seconds=60.0,
                            min_samples=2,
                        ),
                    )
                },
                decision_store=decision_store,
            )
            candidates = (
                OrchestratorPoolState("alpha", OrchestratorStatus.HEALTHY, frozenset({"workflow"})),
                OrchestratorPoolState("beta", OrchestratorStatus.HEALTHY, frozenset({"workflow"})),
            )
            selected = policy.select_with_context(
                candidates,
                120.0,
                SelectionContext("mission", "exec", 1, "coding"),
            )

            self.assertEqual(selected, "beta")
            receipt = decision_store.history("mission")[0]
            self.assertEqual(tuple(item.executor_id for item in receipt.candidates), ("beta", "alpha"))
            self.assertEqual(receipt.candidates[0].evidence_id, "bench-beta")
            self.assertEqual(
                receipt.candidates[0].observed_evidence_ids,
                ("obs-beta-108.0", "obs-beta-110.0"),
            )
            self.assertNotIn("outside", {item.executor_id for item in receipt.candidates})

    def test_stale_or_low_sample_observation_does_not_gain_advantage(self):
        with tempfile.TemporaryDirectory() as temp:
            db = Path(temp) / "metao.db"
            benchmark_store = SQLiteBenchmarkEvidenceStore(db)
            observed_store = SQLiteObservedPerformanceStore(db)
            benchmark_store.record(bench("alpha", 0.9))
            benchmark_store.record(bench("beta", 0.8))
            observed_store.record(observed("beta", 1.0, at=1.0, samples=1))
            policy = EmpiricalTaskFamilySelectionPolicy(
                benchmark_store,
                observed_store,
                {
                    "coding": EmpiricalFamilyRoutingPolicy(
                        BenchmarkRoutingPolicy(
                            benchmark_id="matrix",
                            benchmark_version="v1",
                            task_set="coding",
                            metric_name="success_rate",
                            max_age_seconds=60.0,
                        ),
                        ObservedPerformanceRoutingPolicy(
                            metric_name="success_rate",
                            max_age_seconds=60.0,
                            min_samples=2,
                        ),
                    )
                },
            )
            selected = policy.select_with_context(
                (
                    OrchestratorPoolState("alpha", OrchestratorStatus.HEALTHY),
                    OrchestratorPoolState("beta", OrchestratorStatus.HEALTHY),
                ),
                120.0,
                SelectionContext("mission", "exec", 1, "coding"),
            )
            self.assertEqual(selected, "alpha")


if __name__ == "__main__":
    unittest.main(verbosity=2)
