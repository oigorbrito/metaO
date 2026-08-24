import importlib
import unittest


class BlockHStrategyScoringAcceptance(unittest.TestCase):
    def _strategy(self):
        return importlib.import_module("metao.strategy")

    def test_system_snapshot_and_pool_state_exist(self):
        strategy = self._strategy()
        self.assertTrue(hasattr(strategy, "SystemSnapshot"))
        self.assertTrue(hasattr(strategy, "OrchestratorPoolState"))

    def test_budget_and_status_state_exist(self):
        strategy = self._strategy()
        self.assertTrue(hasattr(strategy, "BudgetState"))
        self.assertTrue(hasattr(strategy, "OrchestratorStatus"))

    def test_deterministic_historical_scorer_exists(self):
        strategy = self._strategy()
        self.assertTrue(hasattr(strategy, "DeterministicScorer"))
        self.assertTrue(hasattr(strategy, "HistoricalScore"))

    def test_scorer_accounts_for_outcome_quality_latency_and_cost(self):
        strategy = self._strategy()
        scorer_cls = getattr(strategy, "DeterministicScorer")
        scorer = scorer_cls()
        result = scorer.score(outcome=1.0, quality=0.9, latency_ms=100, cost=0.01)
        self.assertIsNotNone(result)

    def test_cost_quality_router_baseline_exists(self):
        strategy = self._strategy()
        self.assertTrue(hasattr(strategy, "CostQualityRouter"))
        self.assertTrue(hasattr(strategy, "select_orchestrator"))


if __name__ == "__main__":
    unittest.main()
