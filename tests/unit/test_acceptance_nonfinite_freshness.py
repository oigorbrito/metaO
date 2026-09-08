from __future__ import annotations

import unittest

from metao.acceptance import (
    AcceptanceContext,
    AcceptanceDecision,
    EvidenceEnvelope,
    check_freshness,
    evaluate_acceptance,
)


def envelope(*, created_at_epoch: float = 10.0, expires_at_epoch: float | None = 20.0) -> EvidenceEnvelope:
    return EvidenceEnvelope(
        evidence_id="evidence-1",
        obligation_id="obligation",
        mission_id="mission",
        execution_id="execution",
        orchestrator_id="runtime",
        adapter_version="v1",
        attempt_id="attempt-1",
        subject_id="subject",
        subject_state_id="state",
        verification_context_id="verification",
        policy_bundle_id="policy",
        verifier_id="verifier",
        payload_digest="digest",
        provenance_root="root",
        authority_id="authority",
        passed=True,
        created_at_epoch=created_at_epoch,
        expires_at_epoch=expires_at_epoch,
    )


def context() -> AcceptanceContext:
    return AcceptanceContext(
        subject_id="subject",
        subject_state_id="state",
        verification_context_id="verification",
        policy_bundle_id="policy",
        required_obligations=frozenset({"obligation"}),
        trusted_verifiers=frozenset({"verifier"}),
        trusted_provenance_roots=frozenset({"root"}),
        authorized_authorities=frozenset({"authority"}),
    )


class AcceptanceNonFiniteFreshnessTests(unittest.TestCase):
    def test_non_finite_creation_time_is_rejected(self) -> None:
        for value in (float("nan"), float("inf"), float("-inf")):
            with self.subTest(value=value):
                with self.assertRaisesRegex(ValueError, "evidence creation time must be finite"):
                    envelope(created_at_epoch=value, expires_at_epoch=None)

    def test_non_finite_expiry_time_is_rejected(self) -> None:
        for value in (float("nan"), float("inf"), float("-inf")):
            with self.subTest(value=value):
                with self.assertRaisesRegex(ValueError, "evidence expiry time must be finite"):
                    envelope(expires_at_epoch=value)

    def test_reversed_evidence_window_is_rejected(self) -> None:
        with self.assertRaisesRegex(ValueError, "evidence expiry time cannot precede creation"):
            envelope(created_at_epoch=20.0, expires_at_epoch=19.0)

    def test_non_finite_acceptance_now_is_rejected_by_public_gates(self) -> None:
        item = envelope()
        for value in (float("nan"), float("inf"), float("-inf")):
            with self.subTest(value=value):
                with self.assertRaisesRegex(ValueError, "acceptance current time must be finite"):
                    check_freshness(item, now_epoch=value)
                with self.assertRaisesRegex(ValueError, "acceptance current time must be finite"):
                    evaluate_acceptance(context(), (), now_epoch=value)

    def test_negative_acceptance_now_is_rejected(self) -> None:
        with self.assertRaisesRegex(ValueError, "acceptance current time must be non-negative"):
            evaluate_acceptance(context(), (), now_epoch=-1.0)

    def test_finite_freshness_decisions_are_preserved(self) -> None:
        item = envelope(created_at_epoch=10.0, expires_at_epoch=20.0)
        self.assertEqual(check_freshness(item, now_epoch=15.0).decision, AcceptanceDecision.ACCEPT)
        self.assertEqual(check_freshness(item, now_epoch=5.0).decision, AcceptanceDecision.BLOCK)
        self.assertEqual(check_freshness(item, now_epoch=21.0).decision, AcceptanceDecision.STALE)

    def test_current_valid_evidence_can_still_accept(self) -> None:
        result = evaluate_acceptance(context(), (envelope(),), now_epoch=15.0, executor_done=True)
        self.assertEqual(result.decision, AcceptanceDecision.ACCEPT)
        self.assertIsNotNone(result.proof)


if __name__ == "__main__":
    unittest.main(verbosity=2)
