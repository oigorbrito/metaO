import importlib
import unittest


class BlockKGovernanceBudgetApprovalAcceptance(unittest.TestCase):
    def _governance(self):
        return importlib.import_module("metao.governance")

    def test_policy_decision_model_exists(self):
        governance = self._governance()
        self.assertTrue(hasattr(governance, "PolicyDecision"))
        self.assertTrue(hasattr(governance, "evaluate_policy"))

    def test_acceptance_budget_limits_exist(self):
        governance = self._governance()
        self.assertTrue(hasattr(governance, "AcceptanceBudget"))
        self.assertTrue(hasattr(governance, "BudgetExhausted"))

    def test_durable_approval_request_and_record_exist(self):
        governance = self._governance()
        self.assertTrue(hasattr(governance, "ApprovalRequest"))
        self.assertTrue(hasattr(governance, "ApprovalRecord"))

    def test_human_escalation_wait_resume_contract_exists(self):
        governance = self._governance()
        self.assertTrue(hasattr(governance, "require_human"))
        self.assertTrue(hasattr(governance, "resume_after_approval"))

    def test_confidence_cannot_bypass_hard_gate(self):
        governance = self._governance()
        self.assertTrue(hasattr(governance, "apply_confidence_after_hard_gates"))


if __name__ == "__main__":
    unittest.main()
