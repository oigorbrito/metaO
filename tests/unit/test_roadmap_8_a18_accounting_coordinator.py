from __future__ import annotations

import unittest

from metao.acceptance_accounting import (
    AcceptanceAccountingDecision,
    record_verification_usage,
)
from metao.acceptance_usage import (
    DuplicateUsage,
    InMemoryAcceptanceUsageStore,
    VerificationOutcome,
    VerificationUsage,
)
from metao.governance import AcceptanceBudget


class AcceptanceAccountingCoordinatorTests(unittest.TestCase):
    def budget(self, **overrides: object) -> AcceptanceBudget:
        values: dict[str, object] = {
            "money_limit": 1.0,
            "token_limit": 100,
            "wall_time_limit_s": 10.0,
            "verifier_attempt_limit": 2,
        }
        values.update(overrides)
        return AcceptanceBudget(**values)  # type: ignore[arg-type]

    def usage(self, **overrides: object) -> VerificationUsage:
        values: dict[str, object] = {
            "usage_id": "usage-1",
            "mission_id": "mission-1",
            "execution_id": "execution-1",
            "attempt_id": "attempt-1",
            "verifier_id": "verifier-1",
            "verification_request_id": "request-1",
            "subject_id": "subject-1",
            "subject_state_id": "state-1",
            "verification_context_id": "context-1",
            "policy_bundle_id": "policy-1",
            "started_at_epoch": 10.0,
            "ended_at_epoch": 12.0,
            "money": 0.25,
            "tokens": 20,
            "wall_time_s": 2.0,
            "verifier_attempts": 1,
            "outcome": VerificationOutcome.PASS,
        }
        values.update(overrides)
        return VerificationUsage(**values)  # type: ignore[arg-type]

    def test_within_budget_persists_then_returns_updated_budget(self) -> None:
        store = InMemoryAcceptanceUsageStore()
        item = self.usage()
        result = record_verification_usage(
            budget=self.budget(),
            usage=item,
            usage_port=store,
        )
        self.assertEqual(result.decision, AcceptanceAccountingDecision.CONTINUE)
        self.assertEqual(store.for_mission("mission-1"), (item,))
        self.assertEqual(result.budget.money_used, 0.25)
        self.assertEqual(result.budget.tokens_used, 20)
        self.assertEqual(result.budget.wall_time_used_s, 2.0)
        self.assertEqual(result.budget.verifier_attempts_used, 1)

    def test_over_budget_usage_remains_persisted_and_blocks(self) -> None:
        store = InMemoryAcceptanceUsageStore()
        item = self.usage(money=1.25)
        result = record_verification_usage(
            budget=self.budget(),
            usage=item,
            usage_port=store,
        )
        self.assertEqual(result.decision, AcceptanceAccountingDecision.BLOCK)
        self.assertEqual(store.for_mission("mission-1"), (item,))
        self.assertEqual(result.budget.money_used, 1.25)
        self.assertGreater(result.budget.money_used, result.budget.money_limit)
        self.assertIn("money", result.reason)

    def test_each_budget_dimension_fails_closed_after_factual_append(self) -> None:
        cases = (
            ({"tokens": 101}, "token"),
            ({"wall_time_s": 11.0}, "wall-time"),
            ({"verifier_attempts_used": 2}, "verifier-attempt"),
        )
        for index, (overrides, reason_fragment) in enumerate(cases, start=1):
            with self.subTest(reason_fragment=reason_fragment):
                store = InMemoryAcceptanceUsageStore()
                item = self.usage(usage_id=f"usage-{index}", attempt_id=f"attempt-{index}")
                budget = self.budget(**overrides) if "verifier_attempts_used" in overrides else self.budget()
                if "tokens" in overrides:
                    item = self.usage(usage_id=f"usage-{index}", attempt_id=f"attempt-{index}", tokens=101)
                elif "wall_time_s" in overrides:
                    item = self.usage(usage_id=f"usage-{index}", attempt_id=f"attempt-{index}", wall_time_s=11.0)
                result = record_verification_usage(budget=budget, usage=item, usage_port=store)
                self.assertEqual(result.decision, AcceptanceAccountingDecision.BLOCK)
                self.assertEqual(len(store.for_mission("mission-1")), 1)
                self.assertIn(reason_fragment, result.reason)

    def test_failed_verifier_attempt_is_still_accounted(self) -> None:
        store = InMemoryAcceptanceUsageStore()
        item = self.usage(outcome=VerificationOutcome.ERROR)
        result = record_verification_usage(
            budget=self.budget(),
            usage=item,
            usage_port=store,
        )
        self.assertEqual(result.decision, AcceptanceAccountingDecision.CONTINUE)
        self.assertEqual(result.budget.verifier_attempts_used, 1)
        self.assertEqual(store.for_mission("mission-1")[0].outcome, VerificationOutcome.ERROR)

    def test_duplicate_factual_attempt_cannot_double_charge_budget(self) -> None:
        store = InMemoryAcceptanceUsageStore()
        item = self.usage()
        first = record_verification_usage(budget=self.budget(), usage=item, usage_port=store)
        with self.assertRaises(DuplicateUsage):
            record_verification_usage(budget=first.budget, usage=item, usage_port=store)
        self.assertEqual(len(store.for_mission("mission-1")), 1)


if __name__ == "__main__":
    unittest.main()
