import unittest

from metao.strategy import CapacityStatus, OrchestratorPoolState, OrchestratorStatus


class CapacityRecoveryEvidenceRedTests(unittest.TestCase):
    def test_rate_limit_timestamp_without_evidence_binding_remains_ineligible(self):
        pool = OrchestratorPoolState(
            "primary",
            OrchestratorStatus.HEALTHY,
            success_rate=1.0,
            quality=1.0,
            latency_ms=10,
            cost=0.0,
            capacity_status=CapacityStatus.TEMPORARILY_RATE_LIMITED,
            recover_at_epoch=200.0,
        )

        self.assertFalse(
            pool.capacity_available(now_epoch=200.0),
            "elapsed time alone must not manufacture evidenced recovery",
        )


if __name__ == "__main__":
    unittest.main()
