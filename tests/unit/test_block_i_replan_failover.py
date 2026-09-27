import unittest

from metao.replan import (
    ControlAction,
    FailureClass,
    ReplanLimit,
    classify_failure,
    escalate,
    evaluate,
    halt,
    preserve_successful_progress,
    replan,
    replan_allowed,
    reselect_orchestrator,
)
from metao.strategy import OrchestratorPoolState, OrchestratorStatus


class BlockIReplanFailoverAcceptance(unittest.TestCase):
    def test_evaluate_halt_replan_escalate_primitives(self):
        self.assertEqual(evaluate(None).action, ControlAction.CONTINUE)
        self.assertEqual(halt("stop").action, ControlAction.HALT)
        self.assertEqual(replan("retry elsewhere").action, ControlAction.REPLAN)
        self.assertEqual(escalate("human").action, ControlAction.ESCALATE)

    def test_runtime_failure_classification(self):
        self.assertEqual(classify_failure("worker runtime crashed"), FailureClass.RUNTIME)
        self.assertEqual(classify_failure("request timed out"), FailureClass.TIMEOUT)
        self.assertEqual(classify_failure("policy denied"), FailureClass.POLICY)
        self.assertEqual(classify_failure("budget exhausted"), FailureClass.BUDGET)

    def test_alternate_orchestrator_reselection(self):
        pools = (
            OrchestratorPoolState("a", OrchestratorStatus.HEALTHY, success_rate=1.0, quality=1.0, latency_ms=10, cost=0.0),
            OrchestratorPoolState("b", OrchestratorStatus.HEALTHY, success_rate=0.9, quality=0.9, latency_ms=20, cost=0.1),
        )
        self.assertEqual(reselect_orchestrator(pools, current_orchestrator_id="a"), "b")

    def test_replan_preserves_successful_steps(self):
        reused, pending = preserve_successful_progress({"discover", "plan"}, ["discover", "plan", "execute", "verify"])
        self.assertEqual(reused, ("discover", "plan"))
        self.assertEqual(pending, ("execute", "verify"))

    def test_infinite_replan_loop_guard(self):
        limit = ReplanLimit(max_attempts=2)
        self.assertTrue(replan_allowed(0, limit))
        self.assertTrue(replan_allowed(1, limit))
        self.assertFalse(replan_allowed(2, limit))
        self.assertEqual(evaluate(FailureClass.RUNTIME, attempts=2, limit=limit).action, ControlAction.ESCALATE)
        self.assertEqual(evaluate(FailureClass.POLICY, attempts=0, limit=limit).action, ControlAction.HALT)


if __name__ == "__main__":
    unittest.main()
