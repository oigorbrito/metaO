import threading
import unittest

from metao.governance import AcceptanceBudget


class ChassisL5BudgetAtomicityV1(unittest.TestCase):
    def test_shared_budget_cannot_oversubscribe_under_concurrent_reservations(self):
        """Qualification gate: two concurrent reservations must share one authority.

        The current immutable AcceptanceBudget exposes only pure `consume()` transitions,
        not an atomic shared reserve/settle authority. This test intentionally fails if
        two workers can independently derive locally valid states whose combined spend
        exceeds the shared limit.
        """

        initial = AcceptanceBudget(
            money_limit=10.0,
            token_limit=10_000,
            wall_time_limit_s=60.0,
            verifier_attempt_limit=10,
        )
        barrier = threading.Barrier(2)
        accepted = []
        lock = threading.Lock()

        def reserve_six():
            barrier.wait()
            try:
                local = initial.consume(money=6.0)
            except ValueError:
                return
            with lock:
                accepted.append(local.money_used)

        threads = [threading.Thread(target=reserve_six) for _ in range(2)]
        for thread in threads:
            thread.start()
        for thread in threads:
            thread.join()

        total_reserved = sum(accepted)
        self.assertLessEqual(
            total_reserved,
            initial.money_limit,
            "P1 violated: independent concurrent reservations oversubscribed one shared budget",
        )

    def test_budget_settlement_retry_must_be_idempotent(self):
        """P2 cannot pass until budget exposes reservation/settlement identity.

        Pure `consume()` has no reservation id/idempotency key, so repeated settlement
        cannot be distinguished from a second legitimate charge. Keep this gate red
        rather than silently treating immutability as settlement idempotency.
        """

        budget = AcceptanceBudget(10.0, 10_000, 60.0, 10)
        first = budget.consume(money=4.0)
        retry = first.consume(money=4.0)
        self.assertEqual(
            retry.money_used,
            first.money_used,
            "P2 violated: settlement retry charged the same logical reservation twice",
        )


if __name__ == "__main__":
    unittest.main(verbosity=2)
