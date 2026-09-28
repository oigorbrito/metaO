import unittest

from metao.runtime import (
    ConcurrencyGuard,
    FencingToken,
    IdempotencyKey,
    Lease,
    RecoveryState,
    ReplayGuard,
    StaleWorkerError,
    deduplicate_event,
    recover_preserving_success,
    reject_stale_worker,
)


class BlockGRuntimeInvariantAcceptance(unittest.TestCase):
    def test_lease_and_fencing_contract(self):
        old = FencingToken(1, "worker-a")
        current = FencingToken(2, "worker-b")
        lease = Lease("job:1", "worker-b", current, ttl_seconds=10)
        self.assertTrue(lease.is_active(now=lease.last_confirmed_at + 1))
        self.assertFalse(lease.is_active(now=lease.last_confirmed_at + 11))
        with self.assertRaises(StaleWorkerError):
            reject_stale_worker(current, old)

    def test_stale_worker_rejection_accepts_current_holder_only(self):
        current = FencingToken(7, "worker-b")
        self.assertTrue(reject_stale_worker(current, FencingToken(7, "worker-b")))
        with self.assertRaises(StaleWorkerError):
            reject_stale_worker(current, FencingToken(7, "worker-a"))

    def test_event_idempotency(self):
        seen = set()
        key = IdempotencyKey("execution-42:event-1")
        self.assertTrue(deduplicate_event(key, seen))
        self.assertFalse(deduplicate_event(key, seen))

    def test_concurrency_and_replay_guards(self):
        guard = ConcurrencyGuard()
        with guard.hold("mission-1", blocking=False) as first:
            self.assertTrue(first)
            with guard.hold("mission-1", blocking=False) as second:
                self.assertFalse(second)
        replay = ReplayGuard()
        self.assertTrue(replay.accept("event-1"))
        self.assertFalse(replay.accept("event-1"))

    def test_lifecycle_recovery_preserves_successful_progress(self):
        state = RecoveryState(
            successful_steps=frozenset({"discover", "plan"}),
            failed_steps=frozenset({"execute"}),
        )
        reused, pending = recover_preserving_success(
            state, ["discover", "plan", "execute", "verify"]
        )
        self.assertEqual(reused, ("discover", "plan"))
        self.assertEqual(pending, ("execute", "verify"))


if __name__ == "__main__":
    unittest.main()
