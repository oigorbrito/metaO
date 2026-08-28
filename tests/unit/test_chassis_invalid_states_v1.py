import unittest

from metao.core import ExecutionRequest, Mission, OrchestratorDescriptor
from metao.governance import AcceptanceBudget


class ChassisInvalidStateV1(unittest.TestCase):
    def test_empty_mission_id_is_rejected(self):
        with self.assertRaises(ValueError):
            Mission("", "objective")

    def test_empty_execution_id_is_rejected(self):
        with self.assertRaises(ValueError):
            ExecutionRequest("", Mission("m", "objective"))

    def test_empty_orchestrator_identity_is_rejected(self):
        with self.assertRaises(ValueError):
            OrchestratorDescriptor("", "1", frozenset({"workflow"}))

    def test_negative_budget_limit_is_rejected_at_construction(self):
        with self.assertRaises(ValueError):
            AcceptanceBudget(-1.0, 100, 10.0, 1)

    def test_negative_initial_budget_usage_is_rejected_at_construction(self):
        with self.assertRaises(ValueError):
            AcceptanceBudget(10.0, 100, 10.0, 1, money_used=-1.0)

    def test_initial_usage_cannot_exceed_limit(self):
        with self.assertRaises(ValueError):
            AcceptanceBudget(10.0, 100, 10.0, 1, money_used=11.0)


if __name__ == "__main__":
    unittest.main(verbosity=2)
