import unittest

from metao.strategy import (
    CapacityRecovery,
    CapacityStatus,
    OrchestratorPoolState,
    OrchestratorStatus,
    RecoveryEvidenceBasis,
)


class CapacityTemporaryQuotaRecoveryRedTests(unittest.TestCase):
    def test_evidenced_temporary_quota_recovery_reenters_at_boundary(self):
        pool = OrchestratorPoolState(
            "primary",
            OrchestratorStatus.HEALTHY,
            success_rate=1.0,
            quality=1.0,
            latency_ms=10,
            cost=0.0,
            capacity_status=CapacityStatus.TEMPORARILY_QUOTA_EXHAUSTED,
            recovery=CapacityRecovery(
                recover_at_epoch=200.0,
                evidence_basis=RecoveryEvidenceBasis.PROVIDER_API,
                evidence_ref="provider://quota/reset/primary",
            ),
        )

        self.assertFalse(pool.capacity_available(now_epoch=199.999))
        self.assertTrue(
            pool.capacity_available(now_epoch=200.0),
            "validated temporary quota recovery should re-enter eligibility at its boundary",
        )


if __name__ == "__main__":
    unittest.main()
