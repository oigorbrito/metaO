from __future__ import annotations

import unittest

from metao.freshness_authority import (
    FixedClock,
    FreshnessDecision,
    FreshnessPolicy,
    FreshnessRequest,
    evaluate_authoritative_freshness,
)


class FreshnessAuthorityTests(unittest.TestCase):
    def request(self, **overrides: object) -> FreshnessRequest:
        values = {
            "evidence_id": "e-1",
            "subject_id": "subject-1",
            "subject_state_id": "state-1",
            "verification_context_id": "verify-1",
            "created_at_epoch": 100.0,
            "expires_at_epoch": 200.0,
        }
        values.update(overrides)
        return FreshnessRequest(**values)  # type: ignore[arg-type]

    def test_fresh_evidence_uses_trusted_clock(self) -> None:
        result = evaluate_authoritative_freshness(
            self.request(), clock=FixedClock(150.0)
        )
        self.assertEqual(result.decision, FreshnessDecision.FRESH)
        self.assertEqual(result.observed_now_epoch, 150.0)

    def test_future_evidence_blocks(self) -> None:
        result = evaluate_authoritative_freshness(
            self.request(created_at_epoch=200.0, expires_at_epoch=300.0),
            clock=FixedClock(100.0),
        )
        self.assertEqual(result.decision, FreshnessDecision.BLOCK)

    def test_expired_evidence_is_stale(self) -> None:
        result = evaluate_authoritative_freshness(
            self.request(expires_at_epoch=120.0), clock=FixedClock(150.0)
        )
        self.assertEqual(result.decision, FreshnessDecision.STALE)

    def test_max_age_policy_is_authoritative(self) -> None:
        result = evaluate_authoritative_freshness(
            self.request(expires_at_epoch=None),
            clock=FixedClock(151.0),
            policy=FreshnessPolicy(max_age_s=50.0),
        )
        self.assertEqual(result.decision, FreshnessDecision.STALE)
        self.assertEqual(result.reason, "evidence_too_old")

    def test_clock_skew_can_cover_small_future_offset(self) -> None:
        result = evaluate_authoritative_freshness(
            self.request(created_at_epoch=101.0, expires_at_epoch=120.0),
            clock=FixedClock(100.0),
            policy=FreshnessPolicy(allowed_clock_skew_s=2.0),
        )
        self.assertEqual(result.decision, FreshnessDecision.FRESH)

    def test_invalid_numeric_values_fail_closed(self) -> None:
        for value in (float("nan"), float("inf"), -1.0):
            with self.subTest(value=value), self.assertRaises((TypeError, ValueError)):
                FreshnessPolicy(max_age_s=value)

    def test_missing_binding_fails_closed(self) -> None:
        with self.assertRaises(ValueError):
            self.request(evidence_id="")

    def test_expiry_cannot_precede_creation(self) -> None:
        with self.assertRaises(ValueError):
            self.request(created_at_epoch=100.0, expires_at_epoch=99.0)


if __name__ == "__main__":
    unittest.main()
