from __future__ import annotations

import unittest
from dataclasses import replace

from metao.benchmark_evidence import (
    BenchmarkEvidence,
    BenchmarkEvidenceSource,
    BenchmarkMetric,
)
from metao.benchmark_routing import (
    BenchmarkRoutingPolicy,
    EvidenceWeightedRouter,
)
from metao.strategy import OrchestratorPoolState, OrchestratorStatus


def evidence(
    executor_id: str,
    *,
    evidence_id: str,
    value: float,
    observed_at_epoch: float = 100.0,
    benchmark_version: str = "v1",
    task_set: str = "verified",
) -> BenchmarkEvidence:
    return BenchmarkEvidence(
        evidence_id=evidence_id,
        benchmark_id="software-engineering",
        benchmark_version=benchmark_version,
        task_set=task_set,
        executor_id=executor_id,
        executor_version="1.0",
        harness_id="harness",
        harness_version="1.0",
        model_id="model",
        provider_id="provider",
        model_version="2026-09",
        runtime_config_digest=f"runtime-{executor_id}",
        tool_policy_digest="tool-policy",
        environment_id="linux",
        observed_at_epoch=observed_at_epoch,
        source=BenchmarkEvidenceSource.METAO_REPRODUCED,
        raw_result_ref=f"artifact://{evidence_id}",
        metrics=(BenchmarkMetric("resolved_rate", value, "ratio"),),
    )


def pool(
    orchestrator_id: str,
    *,
    status: OrchestratorStatus = OrchestratorStatus.HEALTHY,
    success_rate: float = 0.8,
    quality: float = 0.8,
    latency_ms: float = 100.0,
    cost: float = 0.1,
) -> OrchestratorPoolState:
    return OrchestratorPoolState(
        orchestrator_id=orchestrator_id,
        status=status,
        capabilities=frozenset({"code"}),
        success_rate=success_rate,
        quality=quality,
        latency_ms=latency_ms,
        cost=cost,
    )


class EvidenceWeightedRoutingTests(unittest.TestCase):
    def policy(self, **overrides) -> BenchmarkRoutingPolicy:
        values = {
            "benchmark_id": "software-engineering",
            "benchmark_version": "v1",
            "task_set": "verified",
            "metric_name": "resolved_rate",
            "base_weight": 1.0,
            "benchmark_weight": 1.0,
            "max_age_seconds": 60.0,
        }
        values.update(overrides)
        return BenchmarkRoutingPolicy(**values)

    def test_exact_fresh_evidence_can_change_ranking(self):
        first = pool("first")
        second = pool("second")
        router = EvidenceWeightedRouter(self.policy(base_weight=0.1, benchmark_weight=0.9))

        ranked = router.rank(
            (first, second),
            {
                "first": (evidence("first", evidence_id="first-e", value=0.2),),
                "second": (evidence("second", evidence_id="second-e", value=0.95),),
            },
            now_epoch=120.0,
        )

        self.assertEqual(ranked[0].orchestrator_id, "second")
        self.assertEqual(ranked[0].evidence_id, "second-e")

    def test_hard_ineligible_candidate_never_reenters_from_benchmark_score(self):
        healthy = pool("healthy", success_rate=0.1, quality=0.1, latency_ms=5000, cost=5)
        quarantined = pool(
            "quarantined",
            status=OrchestratorStatus.QUARANTINED,
            success_rate=1.0,
            quality=1.0,
            latency_ms=1,
            cost=0,
        )
        router = EvidenceWeightedRouter(self.policy(base_weight=0.1, benchmark_weight=0.9))

        ranked = router.rank(
            (healthy, quarantined),
            {
                "healthy": (evidence("healthy", evidence_id="h", value=0.1),),
                "quarantined": (evidence("quarantined", evidence_id="q", value=1.0),),
            },
            now_epoch=120.0,
        )

        self.assertEqual([item.orchestrator_id for item in ranked], ["healthy"])

    def test_stale_or_incompatible_evidence_is_not_applied(self):
        candidate = pool("runtime-a")
        router = EvidenceWeightedRouter(self.policy(max_age_seconds=10.0))

        ranked = router.rank(
            (candidate,),
            {
                "runtime-a": (
                    evidence(
                        "runtime-a",
                        evidence_id="stale",
                        value=1.0,
                        observed_at_epoch=100.0,
                    ),
                    evidence(
                        "runtime-a",
                        evidence_id="wrong-version",
                        value=1.0,
                        observed_at_epoch=119.0,
                        benchmark_version="v2",
                    ),
                )
            },
            now_epoch=120.0,
        )

        self.assertIsNone(ranked[0].benchmark_score)
        self.assertEqual(ranked[0].reason, "no_applicable_benchmark_evidence")

    def test_latest_exact_applicable_evidence_is_used_deterministically(self):
        candidate = pool("runtime-a")
        router = EvidenceWeightedRouter(self.policy())

        ranked = router.rank(
            (candidate,),
            {
                "runtime-a": (
                    evidence("runtime-a", evidence_id="older", value=0.2, observed_at_epoch=100.0),
                    evidence("runtime-a", evidence_id="newer", value=0.9, observed_at_epoch=110.0),
                )
            },
            now_epoch=120.0,
        )

        self.assertEqual(ranked[0].benchmark_score, 0.9)
        self.assertEqual(ranked[0].evidence_id, "newer")

    def test_missing_evidence_keeps_base_score_and_is_explicit(self):
        first = pool("a")
        second = pool("b")
        router = EvidenceWeightedRouter(self.policy())

        ranked = router.rank((first, second), {}, now_epoch=120.0)

        self.assertTrue(all(item.benchmark_score is None for item in ranked))
        self.assertTrue(all(item.total_score == item.base_score for item in ranked))
        self.assertTrue(
            all(item.reason == "no_applicable_benchmark_evidence" for item in ranked)
        )

    def test_non_ratio_metric_does_not_enter_routing_score(self):
        candidate = pool("runtime-a")
        item = evidence("runtime-a", evidence_id="absolute", value=0.9)
        item = replace(
            item,
            metrics=(BenchmarkMetric("resolved_rate", 0.9, "count"),),
        )
        router = EvidenceWeightedRouter(self.policy())

        ranked = router.rank(
            (candidate,),
            {"runtime-a": (item,)},
            now_epoch=120.0,
        )

        self.assertIsNone(ranked[0].benchmark_score)

    def test_policy_rejects_nonfinite_or_degenerate_weights(self):
        with self.assertRaises(ValueError):
            self.policy(base_weight=float("nan"))
        with self.assertRaises(ValueError):
            self.policy(base_weight=0.0, benchmark_weight=0.0)


if __name__ == "__main__":
    unittest.main(verbosity=2)
