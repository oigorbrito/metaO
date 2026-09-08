from __future__ import annotations

import unittest

from metao.catalog import OrchestratorCatalog
from metao.core import OrchestratorRegistry
from metao.strategy import (
    CostQualityRouter,
    DeterministicScorer,
    OrchestratorPoolState,
    OrchestratorStatus,
)


class RoutingNonFiniteMetricTests(unittest.TestCase):
    def test_catalog_rejects_non_finite_cost_and_latency_before_registry_lookup(self) -> None:
        catalog = OrchestratorCatalog(OrchestratorRegistry())
        normalizer = lambda execution: ()
        for value in (float("nan"), float("inf"), float("-inf")):
            with self.subTest(metric="cost", value=value):
                with self.assertRaisesRegex(ValueError, "catalog cost and latency must be finite"):
                    catalog.register("missing", normalizer=normalizer, cost=value)
            with self.subTest(metric="latency", value=value):
                with self.assertRaisesRegex(ValueError, "catalog cost and latency must be finite"):
                    catalog.register("missing", normalizer=normalizer, latency_ms=value)

    def test_catalog_rejects_non_finite_unit_interval_metrics(self) -> None:
        for metric in ("success_rate", "quality", "reliability"):
            for value in (float("nan"), float("inf"), float("-inf")):
                with self.subTest(metric=metric, value=value):
                    with self.assertRaisesRegex(ValueError, f"{metric} must be finite"):
                        OrchestratorCatalog._validate_unit_interval(metric, value)

    def test_scorer_rejects_non_finite_configuration(self) -> None:
        for value in (float("nan"), float("inf"), float("-inf")):
            with self.subTest(kind="weight", value=value):
                with self.assertRaisesRegex(ValueError, "scorer weights and scales must be finite"):
                    DeterministicScorer(outcome_weight=value)
            with self.subTest(kind="latency_scale", value=value):
                with self.assertRaisesRegex(ValueError, "scorer weights and scales must be finite"):
                    DeterministicScorer(latency_scale_ms=value)
            with self.subTest(kind="cost_scale", value=value):
                with self.assertRaisesRegex(ValueError, "scorer weights and scales must be finite"):
                    DeterministicScorer(cost_scale=value)

    def test_scorer_rejects_non_finite_dynamic_inputs(self) -> None:
        scorer = DeterministicScorer()
        base = {"outcome": 0.8, "quality": 0.7, "latency_ms": 100.0, "cost": 0.2}
        for metric in base:
            for value in (float("nan"), float("inf"), float("-inf")):
                with self.subTest(metric=metric, value=value):
                    values = dict(base)
                    values[metric] = value
                    with self.assertRaisesRegex(ValueError, "scorer inputs must be finite"):
                        scorer.score(**values)

    def test_finite_ranking_and_tie_break_are_preserved(self) -> None:
        pools = (
            OrchestratorPoolState(
                "z-runtime",
                OrchestratorStatus.HEALTHY,
                success_rate=0.8,
                quality=0.8,
                latency_ms=100.0,
                cost=0.1,
            ),
            OrchestratorPoolState(
                "a-runtime",
                OrchestratorStatus.HEALTHY,
                success_rate=0.8,
                quality=0.8,
                latency_ms=100.0,
                cost=0.1,
            ),
            OrchestratorPoolState(
                "lower-runtime",
                OrchestratorStatus.HEALTHY,
                success_rate=0.2,
                quality=0.2,
                latency_ms=1000.0,
                cost=1.0,
            ),
        )
        ranked = CostQualityRouter().rank(pools, now_epoch=0.0)
        self.assertEqual(
            [candidate.orchestrator_id for candidate in ranked],
            ["a-runtime", "z-runtime", "lower-runtime"],
        )
        self.assertEqual(ranked[0].score, ranked[1].score)


if __name__ == "__main__":
    unittest.main(verbosity=2)
