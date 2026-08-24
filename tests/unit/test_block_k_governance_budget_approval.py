import unittest

from metao.acceptance import AcceptanceDecision
from metao.governance import (
    AcceptanceBudget,
    ApprovalRecord,
    BudgetExhausted,
    PolicyEffect,
    apply_confidence_after_hard_gates,
    evaluate_policy,
    require_human,
    resume_after_approval,
)


class BlockKGovernanceBudgetApprovalAcceptance(unittest.TestCase):
    def test_policy_decision_model(self):
        self.assertEqual(evaluate_policy(policy_bundle_id="p1", allowed=True).effect, PolicyEffect.ALLOW)
        self.assertEqual(evaluate_policy(policy_bundle_id="p1", allowed=False).effect, PolicyEffect.DENY)
        self.assertEqual(
            evaluate_policy(policy_bundle_id="p1", allowed=True, require_human=True).effect,
            PolicyEffect.REQUIRE_HUMAN,
        )

    def test_acceptance_budget_limits(self):
        budget = AcceptanceBudget(1.0, 100, 10.0, 2)
        budget = budget.consume(money=0.2, tokens=10, wall_time_s=1.0, verifier_attempts=1)
        self.assertAlmostEqual(budget.remaining_money(), 0.8)
        with self.assertRaises(BudgetExhausted):
            budget.consume(tokens=100)

    def test_durable_approval_request_and_record_are_bound(self):
        request = require_human(
            approval_id="ap-1",
            mission_id="m1",
            execution_id="x1",
            subject_state_id="s1",
            policy_bundle_id="p1",
            reason="high risk",
        )
        record = ApprovalRecord("ap-1", "m1", "x1", "s1", "p1", "human-1", True)
        self.assertEqual(resume_after_approval(request, record), AcceptanceDecision.ACCEPT)
        wrong = ApprovalRecord("ap-1", "m1", "x2", "s1", "p1", "human-1", True)
        self.assertEqual(resume_after_approval(request, wrong), AcceptanceDecision.BLOCK)

    def test_human_escalation_wait_resume_contract(self):
        request = require_human(
            approval_id="ap-2",
            mission_id="m1",
            execution_id="x1",
            subject_state_id="s1",
            policy_bundle_id="p1",
            reason="low confidence",
        )
        denied = ApprovalRecord("ap-2", "m1", "x1", "s1", "p1", "human-2", False)
        self.assertEqual(resume_after_approval(request, denied), AcceptanceDecision.BLOCK)

    def test_confidence_cannot_bypass_hard_gate(self):
        self.assertEqual(
            apply_confidence_after_hard_gates(AcceptanceDecision.BLOCK, confidence=1.0),
            AcceptanceDecision.BLOCK,
        )
        self.assertEqual(
            apply_confidence_after_hard_gates(AcceptanceDecision.STALE, confidence=1.0),
            AcceptanceDecision.STALE,
        )
        self.assertEqual(
            apply_confidence_after_hard_gates(AcceptanceDecision.ACCEPT, confidence=0.4),
            AcceptanceDecision.REQUIRE_HUMAN,
        )
        self.assertEqual(
            apply_confidence_after_hard_gates(AcceptanceDecision.ACCEPT, confidence=0.95),
            AcceptanceDecision.ACCEPT,
        )


if __name__ == "__main__":
    unittest.main()
