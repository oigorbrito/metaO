import threading
import unittest

from metao.governance import AcceptanceBudget, AcceptanceBudgetAuthority, BudgetExhausted


class ChassisL5BudgetAtomicityV1(unittest.TestCase):
    def make_authority(self, money_limit: float = 10.0) -> AcceptanceBudgetAuthority:
        return AcceptanceBudgetAuthority(
            AcceptanceBudget(
                money_limit=money_limit,
                token_limit=10_000,
                wall_time_limit_s=60.0,
                verifier_attempt_limit=10,
            )
        )

    def test_shared_budget_cannot_oversubscribe_under_concurrent_reservations(self):
        authority = self.make_authority()
        barrier = threading.Barrier(2)
        accepted: list[str] = []
        rejected: list[str] = []
        result_lock = threading.Lock()

        def reserve_six(reservation_id: str):
            barrier.wait()
            try:
                authority.reserve(reservation_id, money=6.0)
            except BudgetExhausted:
                with result_lock:
                    rejected.append(reservation_id)
                return
            with result_lock:
                accepted.append(reservation_id)

        threads = [
            threading.Thread(target=reserve_six, args=("r1",)),
            threading.Thread(target=reserve_six, args=("r2",)),
        ]
        for thread in threads:
            thread.start()
        for thread in threads:
            thread.join()

        self.assertEqual(len(accepted), 1)
        self.assertEqual(len(rejected), 1)
        winner = authority.reservation(accepted[0])
        self.assertIsNotNone(winner)
        self.assertEqual(winner.money, 6.0)
        self.assertEqual(authority.snapshot().money_used, 0.0)

    def test_concurrent_reservations_exactly_at_capacity_are_all_admitted(self):
        authority = self.make_authority()
        barrier = threading.Barrier(2)
        failures: list[Exception] = []
        result_lock = threading.Lock()

        def reserve_five(reservation_id: str):
            barrier.wait()
            try:
                authority.reserve(reservation_id, money=5.0)
            except Exception as exc:  # pragma: no cover - assertion captures unexpected concurrency failures
                with result_lock:
                    failures.append(exc)

        threads = [
            threading.Thread(target=reserve_five, args=("r1",)),
            threading.Thread(target=reserve_five, args=("r2",)),
        ]
        for thread in threads:
            thread.start()
        for thread in threads:
            thread.join()

        self.assertEqual(failures, [])
        self.assertEqual(authority.reservation("r1").money, 5.0)
        self.assertEqual(authority.reservation("r2").money, 5.0)

    def test_failed_reservation_does_not_mutate_authoritative_usage(self):
        authority = self.make_authority()
        authority.reserve("winner", money=8.0)

        with self.assertRaises(BudgetExhausted):
            authority.reserve("loser", money=3.0)

        self.assertIsNone(authority.reservation("loser"))
        self.assertEqual(authority.snapshot().money_used, 0.0)
        settled = authority.settle("winner")
        self.assertEqual(settled.money_used, 8.0)

    def test_duplicate_reservation_replay_is_idempotent(self):
        authority = self.make_authority()
        first = authority.reserve("reservation-1", money=4.0, tokens=10)
        retry = authority.reserve("reservation-1", money=4.0, tokens=10)

        self.assertEqual(retry, first)
        self.assertEqual(authority.snapshot().money_used, 0.0)

    def test_conflicting_reservation_replay_fails_closed(self):
        authority = self.make_authority()
        authority.reserve("reservation-1", money=4.0)

        with self.assertRaises(ValueError):
            authority.reserve("reservation-1", money=5.0)

        self.assertEqual(authority.reservation("reservation-1").money, 4.0)

    def test_budget_settlement_retry_is_idempotent(self):
        authority = self.make_authority()
        authority.reserve("reservation-1", money=4.0)

        first = authority.settle("reservation-1")
        retry = authority.settle("reservation-1")

        self.assertEqual(first.money_used, 4.0)
        self.assertEqual(retry.money_used, first.money_used)
        self.assertTrue(authority.reservation("reservation-1").settled)

    def test_concurrent_same_settlement_has_one_accounting_effect(self):
        authority = self.make_authority()
        authority.reserve("reservation-1", money=4.0)
        barrier = threading.Barrier(2)
        results: list[float] = []
        result_lock = threading.Lock()

        def settle_same_reservation():
            barrier.wait()
            snapshot = authority.settle("reservation-1")
            with result_lock:
                results.append(snapshot.money_used)

        threads = [threading.Thread(target=settle_same_reservation) for _ in range(2)]
        for thread in threads:
            thread.start()
        for thread in threads:
            thread.join()

        self.assertEqual(results, [4.0, 4.0])
        self.assertEqual(authority.snapshot().money_used, 4.0)

    def test_unknown_settlement_identity_fails_closed(self):
        authority = self.make_authority()

        with self.assertRaises(KeyError):
            authority.settle("missing-reservation")

        self.assertEqual(authority.snapshot().money_used, 0.0)


if __name__ == "__main__":
    unittest.main(verbosity=2)
