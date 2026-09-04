import unittest

from metao.strategy import (
    CapacityRecovery,
    CapacityStatus,
    CostQualityRouter,
    OrchestratorPoolState,
    OrchestratorStatus,
    RecoveryEvidenceBasis,
    select_orchestrator,
)


class CapacityRecoveryWindowTests(unittest.TestCase):
    def _recovery(self, *, recover_at_epoch=200.0):
        return CapacityRecovery(
            recover_at_epoch=recover_at_epoch,
            evidence_basis=RecoveryEvidenceBasis.PROVIDER_API,
            evidence_ref="provider://rate-limit/reset/primary",
        )

    def _primary(
        self,
        *,
        capacity_status=CapacityStatus.AVAILABLE,
        recover_at_epoch=None,
        recovery=None,
    ):
        return OrchestratorPoolState(
            "primary",
            OrchestratorStatus.HEALTHY,
            success_rate=1.0,
            quality=1.0,
            latency_ms=10,
            cost=0.0,
            capacity_status=capacity_status,
            recover_at_epoch=recover_at_epoch,
            recovery=recovery,
        )

    def _fallback(self):
        return OrchestratorPoolState(
            "fallback",
            OrchestratorStatus.HEALTHY,
            success_rate=0.6,
            quality=0.6,
            latency_ms=500,
            cost=0.2,
        )

    def test_baseline_primary_wins_when_capacity_is_available(self):
        pools = (self._primary(), self._fallback())
        self.assertEqual(select_orchestrator(pools, now_epoch=100.0), "primary")

    def test_rate_limited_primary_is_excluded_before_scoring(self):
        pools = (
            self._primary(
                capacity_status=CapacityStatus.TEMPORARILY_RATE_LIMITED,
                recovery=self._recovery(),
            ),
            self._fallback(),
        )
        ranked = CostQualityRouter().rank(pools, now_epoch=150.0)
        self.assertEqual(tuple(candidate.orchestrator_id for candidate in ranked), ("fallback",))
        self.assertEqual(select_orchestrator(pools, now_epoch=150.0), "fallback")

    def test_rate_limited_primary_reenters_after_evidenced_recovery_window(self):
        pools = (
            self._primary(
                capacity_status=CapacityStatus.TEMPORARILY_RATE_LIMITED,
                recovery=self._recovery(),
            ),
            self._fallback(),
        )
        self.assertEqual(select_orchestrator(pools, now_epoch=199.999), "fallback")
        self.assertEqual(select_orchestrator(pools, now_epoch=200.0), "primary")

    def test_rate_limit_without_recovery_evidence_remains_ineligible(self):
        pools = (
            self._primary(capacity_status=CapacityStatus.TEMPORARILY_RATE_LIMITED),
            self._fallback(),
        )
        self.assertEqual(select_orchestrator(pools, now_epoch=10_000.0), "fallback")

    def test_rate_limit_timestamp_without_evidence_binding_remains_ineligible(self):
        pools = (
            self._primary(
                capacity_status=CapacityStatus.TEMPORARILY_RATE_LIMITED,
                recover_at_epoch=200.0,
            ),
            self._fallback(),
        )
        self.assertEqual(select_orchestrator(pools, now_epoch=1_000.0), "fallback")

    def test_invalid_recovery_evidence_fails_closed(self):
        invalid = CapacityRecovery(
            recover_at_epoch=200.0,
            evidence_basis=RecoveryEvidenceBasis.UNKNOWN,
            evidence_ref="",
        )
        pools = (
            self._primary(
                capacity_status=CapacityStatus.TEMPORARILY_RATE_LIMITED,
                recovery=invalid,
            ),
            self._fallback(),
        )
        self.assertEqual(select_orchestrator(pools, now_epoch=1_000.0), "fallback")

    def test_quota_exhaustion_does_not_auto_recover_by_elapsed_time(self):
        pools = (
            self._primary(
                capacity_status=CapacityStatus.TEMPORARILY_QUOTA_EXHAUSTED,
                recover_at_epoch=200.0,
            ),
            self._fallback(),
        )
        self.assertEqual(select_orchestrator(pools, now_epoch=1_000.0), "fallback")

    def test_health_and_capacity_remain_independent(self):
        rate_limited = self._primary(
            capacity_status=CapacityStatus.TEMPORARILY_RATE_LIMITED,
            recovery=self._recovery(),
        )
        self.assertIs(rate_limited.status, OrchestratorStatus.HEALTHY)
        self.assertFalse(rate_limited.capacity_available(now_epoch=150.0))
        self.assertTrue(rate_limited.capacity_available(now_epoch=200.0))
        self.assertIs(rate_limited.status, OrchestratorStatus.HEALTHY)


if __name__ == "__main__":
    unittest.main()
