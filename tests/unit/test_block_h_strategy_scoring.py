import unittest

from metao.strategy import (
    BudgetState,
    CostQualityRouter,
    DeterministicScorer,
    HistoricalScore,
    OrchestratorPoolState,
    OrchestratorStatus,
    SystemSnapshot,
    select_orchestrator,
)


class BlockHStrategyScoringAcceptance(unittest.TestCase):
    def test_system_snapshot_and_pool_state(self):
        pool = OrchestratorPoolState(
            orchestrator_id="orch-a",
            status=OrchestratorStatus.HEALTHY,
            capabilities=frozenset({"code"}),
        )
        snapshot = SystemSnapshot(
            mission_id="mission-1",
            pools=(pool,),
            budget=BudgetState(10.0, 1000, 60.0),
        )
        self.assertEqual(snapshot.by_id()["orch-a"], pool)

    def test_budget_and_status_state(self):
        self.assertFalse(BudgetState(1.0, 10, 1.0).exhausted())
        self.assertTrue(BudgetState(0.0, 10, 1.0).exhausted())
        self.assertEqual(OrchestratorStatus.QUARANTINED.value, "quarantined")
        self.assertEqual(OrchestratorStatus.UNKNOWN.value, "unknown")
        self.assertEqual(OrchestratorStatus.RECOVERING.value, "recovering")

    def test_historical_score_uses_ema_deterministically(self):
        history = HistoricalScore().update(
            outcome=1.0, quality=0.8, latency_ms=100, cost=0.1, alpha=0.2
        )
        updated = history.update(
            outcome=0.0, quality=0.4, latency_ms=300, cost=0.3, alpha=0.2
        )
        self.assertAlmostEqual(updated.outcome_ema, 0.8)
        self.assertAlmostEqual(updated.quality_ema, 0.72)
        self.assertAlmostEqual(updated.latency_ema_ms, 140.0)
        self.assertAlmostEqual(updated.cost_ema, 0.14)

    def test_scorer_rewards_quality_and_penalizes_latency_and_cost(self):
        scorer = DeterministicScorer()
        strong = scorer.score(outcome=1.0, quality=0.9, latency_ms=100, cost=0.01)
        weak = scorer.score(outcome=0.5, quality=0.5, latency_ms=5000, cost=5.0)
        self.assertGreater(strong.total, weak.total)
        self.assertEqual(
            strong,
            scorer.score(outcome=1.0, quality=0.9, latency_ms=100, cost=0.01),
        )

    def test_cost_quality_router_selects_best_eligible_candidate(self):
        pools = (
            OrchestratorPoolState(
                "slow-expensive",
                OrchestratorStatus.HEALTHY,
                success_rate=0.9,
                quality=0.9,
                latency_ms=5000,
                cost=4.0,
            ),
            OrchestratorPoolState(
                "balanced",
                OrchestratorStatus.HEALTHY,
                success_rate=0.9,
                quality=0.9,
                latency_ms=100,
                cost=0.1,
            ),
            OrchestratorPoolState(
                "quarantined",
                OrchestratorStatus.QUARANTINED,
                success_rate=1.0,
                quality=1.0,
                latency_ms=1,
                cost=0.0,
            ),
        )
        self.assertEqual(select_orchestrator(pools), "balanced")
        self.assertEqual(CostQualityRouter().select(pools), "balanced")

    def test_unknown_runtime_is_bootstrap_only_behind_factually_known_candidate(self):
        known = OrchestratorPoolState(
            "known",
            OrchestratorStatus.HEALTHY,
            success_rate=0.1,
            quality=0.1,
            latency_ms=10_000,
            cost=10.0,
        )
        unknown = OrchestratorPoolState(
            "unknown",
            OrchestratorStatus.UNKNOWN,
            success_rate=1.0,
            quality=1.0,
            latency_ms=1,
            cost=0.0,
        )

        self.assertEqual(select_orchestrator((unknown, known)), "known")
        self.assertEqual(select_orchestrator((unknown,)), "unknown")

    def test_recovering_runtime_is_controlled_fallback_between_normal_and_unknown(self):
        healthy = OrchestratorPoolState(
            "healthy",
            OrchestratorStatus.HEALTHY,
            success_rate=0.1,
            quality=0.1,
            latency_ms=10_000,
            cost=10.0,
        )
        recovering = OrchestratorPoolState(
            "recovering",
            OrchestratorStatus.RECOVERING,
            success_rate=1.0,
            quality=1.0,
            latency_ms=1,
            cost=0.0,
        )
        unknown = OrchestratorPoolState(
            "unknown",
            OrchestratorStatus.UNKNOWN,
            success_rate=1.0,
            quality=1.0,
            latency_ms=1,
            cost=0.0,
        )

        self.assertEqual(
            select_orchestrator((unknown, recovering, healthy)),
            "healthy",
        )
        self.assertEqual(select_orchestrator((unknown, recovering)), "recovering")
        self.assertEqual(select_orchestrator((unknown,)), "unknown")


if __name__ == "__main__":
    unittest.main()
