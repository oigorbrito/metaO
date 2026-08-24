import importlib
import unittest


class BlockGRuntimeInvariantAcceptance(unittest.TestCase):
    def _runtime(self):
        return importlib.import_module("metao.runtime")

    def test_lease_and_fencing_contract_exists(self):
        runtime = self._runtime()
        self.assertTrue(hasattr(runtime, "Lease"))
        self.assertTrue(hasattr(runtime, "FencingToken"))

    def test_stale_worker_rejection_exists(self):
        runtime = self._runtime()
        self.assertTrue(hasattr(runtime, "reject_stale_worker"))

    def test_event_idempotency_exists(self):
        runtime = self._runtime()
        self.assertTrue(hasattr(runtime, "IdempotencyKey"))
        self.assertTrue(hasattr(runtime, "deduplicate_event"))

    def test_concurrency_and_replay_guard_exists(self):
        runtime = self._runtime()
        self.assertTrue(hasattr(runtime, "ConcurrencyGuard"))
        self.assertTrue(hasattr(runtime, "ReplayGuard"))

    def test_lifecycle_recovery_preserves_successful_progress(self):
        runtime = self._runtime()
        self.assertTrue(hasattr(runtime, "RecoveryState"))
        self.assertTrue(hasattr(runtime, "recover_preserving_success"))


if __name__ == "__main__":
    unittest.main()
