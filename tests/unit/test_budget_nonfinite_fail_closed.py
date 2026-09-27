from __future__ import annotations

import math
import unittest

from metao.governance import AcceptanceBudget, AcceptanceBudgetAuthority


class BudgetNonFiniteFailClosedTests(unittest.TestCase):
    @staticmethod
    def valid_budget(**overrides):
        values = {
            "money_limit": 10.0,
            "token_limit": 100,
            "wall_time_limit_s": 30.0,
            "verifier_attempt_limit": 3,
        }
        values.update(overrides)
        return AcceptanceBudget(**values)

    def test_non_finite_limits_fail_closed(self) -> None:
        for value in (float("nan"), float("inf"), float("-inf")):
            with self.subTest(value=value):
                with self.assertRaisesRegex(ValueError, "budget values must be finite"):
                    self.valid_budget(money_limit=value)
                with self.assertRaisesRegex(ValueError, "budget values must be finite"):
                    self.valid_budget(wall_time_limit_s=value)

    def test_non_finite_initial_usage_fails_closed(self) -> None:
        for value in (float("nan"), float("inf"), float("-inf")):
            with self.subTest(value=value):
                with self.assertRaisesRegex(ValueError, "budget values must be finite"):
                    self.valid_budget(money_used=value)
                with self.assertRaisesRegex(ValueError, "budget values must be finite"):
                    self.valid_budget(wall_time_used_s=value)

    def test_non_finite_consumption_fails_before_arithmetic(self) -> None:
        budget = self.valid_budget()
        for value in (float("nan"), float("inf"), float("-inf")):
            with self.subTest(value=value):
                with self.assertRaisesRegex(ValueError, "budget consumption must be finite"):
                    budget.consume(money=value)
                with self.assertRaisesRegex(ValueError, "budget consumption must be finite"):
                    budget.consume(wall_time_s=value)
        self.assertEqual(budget.money_used, 0.0)
        self.assertEqual(budget.wall_time_used_s, 0.0)

    def test_non_finite_reservation_fails_before_ledger_mutation(self) -> None:
        authority = AcceptanceBudgetAuthority(self.valid_budget())
        for index, value in enumerate((float("nan"), float("inf"), float("-inf"))):
            reservation_id = f"nonfinite-{index}"
            with self.subTest(value=value):
                with self.assertRaisesRegex(ValueError, "budget reservation must be finite"):
                    authority.reserve(reservation_id, money=value)
                self.assertIsNone(authority.reservation(reservation_id))

    def test_large_integer_budget_values_remain_supported(self) -> None:
        huge = 10**1000
        budget = AcceptanceBudget(
            money_limit=10.0,
            token_limit=huge,
            wall_time_limit_s=30.0,
            verifier_attempt_limit=huge,
        )
        consumed = budget.consume(tokens=huge, verifier_attempts=huge)
        self.assertEqual(consumed.tokens_used, huge)
        self.assertEqual(consumed.verifier_attempts_used, huge)

        authority = AcceptanceBudgetAuthority(
            AcceptanceBudget(
                money_limit=10.0,
                token_limit=huge,
                wall_time_limit_s=30.0,
                verifier_attempt_limit=huge,
            )
        )
        authority.reserve("large-int", tokens=huge, verifier_attempts=huge)
        settled = authority.settle("large-int")
        self.assertEqual(settled.tokens_used, huge)
        self.assertEqual(settled.verifier_attempts_used, huge)

    def test_finite_budget_semantics_are_preserved(self) -> None:
        budget = self.valid_budget()
        updated = budget.consume(money=2.5, tokens=10, wall_time_s=4.0, verifier_attempts=1)
        self.assertTrue(math.isfinite(updated.money_used))
        self.assertEqual(updated.money_used, 2.5)
        self.assertEqual(updated.tokens_used, 10)
        self.assertEqual(updated.wall_time_used_s, 4.0)
        self.assertEqual(updated.verifier_attempts_used, 1)

        authority = AcceptanceBudgetAuthority(updated)
        reservation = authority.reserve(
            "finite",
            money=1.0,
            tokens=5,
            wall_time_s=2.0,
            verifier_attempts=1,
        )
        self.assertEqual(reservation.reservation_id, "finite")
        settled = authority.settle("finite")
        self.assertEqual(settled.money_used, 3.5)
        self.assertEqual(settled.tokens_used, 15)
        self.assertEqual(settled.wall_time_used_s, 6.0)
        self.assertEqual(settled.verifier_attempts_used, 2)


if __name__ == "__main__":
    unittest.main(verbosity=2)
