import importlib
import unittest


class BlockIReplanFailoverAcceptance(unittest.TestCase):
    def _replan(self):
        return importlib.import_module("metao.replan")

    def test_evaluate_halt_replan_escalate_primitives_exist(self):
        replan = self._replan()
        for name in ("evaluate", "halt", "replan", "escalate"):
            self.assertTrue(hasattr(replan, name), name)

    def test_runtime_failure_classification_exists(self):
        replan = self._replan()
        self.assertTrue(hasattr(replan, "FailureClass"))
        self.assertTrue(hasattr(replan, "classify_failure"))

    def test_alternate_orchestrator_reselection_exists(self):
        replan = self._replan()
        self.assertTrue(hasattr(replan, "reselect_orchestrator"))

    def test_replan_preserves_successful_steps(self):
        replan = self._replan()
        self.assertTrue(hasattr(replan, "preserve_successful_progress"))

    def test_infinite_replan_loop_guard_exists(self):
        replan = self._replan()
        self.assertTrue(hasattr(replan, "ReplanLimit"))
        self.assertTrue(hasattr(replan, "replan_allowed"))


if __name__ == "__main__":
    unittest.main()
