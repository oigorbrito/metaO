from __future__ import annotations

import unittest

from metao.confidence import (
    BoundConfidence,
    ConfidenceAction,
    ConfidencePolicy,
    advise_from_confidence,
)


class BoundConfidenceTests(unittest.TestCase):
    def confidence(self, **overrides: object) -> BoundConfidence:
        values = {
            "verifier_id": "verifier-1",
            "verifier_version": "1",
            "verification_request_id": "request-1",
            "mission_id": "mission-1",
            "execution_id": "execution-1",
            "subject_id": "subject-1",
            "subject_state_id": "state-1",
            "verification_context_id": "verify-1",
            "policy_bundle_id": "policy-1",
            "payload_digest": "digest-1",
            "score": 0.9,
        }
        values.update(overrides)
        return BoundConfidence(**values)  # type: ignore[arg-type]

    def test_hard_gate_denial_cannot_be_rescued(self) -> None:
        action = advise_from_confidence(
            self.confidence(score=1.0),
            hard_gates_passed=False,
            policy=ConfidencePolicy(minimum_continue=0.8, minimum_escalate=0.5),
        )
        self.assertEqual(action, ConfidenceAction.REJECT)

    def test_high_bound_confidence_can_continue_only_after_hard_gates(self) -> None:
        action = advise_from_confidence(
            self.confidence(score=0.9),
            hard_gates_passed=True,
            policy=ConfidencePolicy(minimum_continue=0.8, minimum_escalate=0.5),
        )
        self.assertEqual(action, ConfidenceAction.CONTINUE)

    def test_mid_confidence_escalates(self) -> None:
        action = advise_from_confidence(
            self.confidence(score=0.6),
            hard_gates_passed=True,
            policy=ConfidencePolicy(minimum_continue=0.8, minimum_escalate=0.5),
        )
        self.assertEqual(action, ConfidenceAction.ESCALATE)

    def test_low_confidence_rejects(self) -> None:
        action = advise_from_confidence(
            self.confidence(score=0.2),
            hard_gates_passed=True,
            policy=ConfidencePolicy(minimum_continue=0.8, minimum_escalate=0.5),
        )
        self.assertEqual(action, ConfidenceAction.REJECT)

    def test_missing_binding_fails_closed(self) -> None:
        with self.assertRaises(ValueError):
            self.confidence(payload_digest="")

    def test_invalid_scores_fail_closed(self) -> None:
        for score in (-0.1, 1.1, float("nan"), float("inf")):
            with self.subTest(score=score), self.assertRaises(ValueError):
                self.confidence(score=score)

    def test_policy_threshold_order_is_validated(self) -> None:
        with self.assertRaises(ValueError):
            ConfidencePolicy(minimum_continue=0.5, minimum_escalate=0.6)


if __name__ == "__main__":
    unittest.main()
