from __future__ import annotations

import unittest

from metao.approval_authority import (
    ApprovalAuthorityContext,
    ApprovalAuthorityDecision,
    ApprovalAuthorityRequest,
    ApproverCapability,
    evaluate_approval_authority,
)


class Roadmap8A08ApproverAuthorityTests(unittest.TestCase):
    def setUp(self) -> None:
        self.context = ApprovalAuthorityContext("authority-context-1", 4, 100.0)
        self.capability = ApproverCapability(
            "cap-1",
            "approver-1",
            "approve",
            "mission-1",
            "policy-1",
            4,
            90.0,
            110.0,
        )
        self.request = ApprovalAuthorityRequest(
            "approver-1",
            "approve",
            "mission-1",
            "policy-1",
        )

    def test_exact_current_capability_allows(self) -> None:
        result = evaluate_approval_authority(
            context=self.context,
            capability=self.capability,
            request=self.request,
        )
        self.assertEqual(result.decision, ApprovalAuthorityDecision.ALLOW)

    def test_stale_authority_epoch_fails_closed_as_stale(self) -> None:
        stale = ApproverCapability(
            "cap-1", "approver-1", "approve", "mission-1", "policy-1", 3, 90.0, 110.0
        )
        result = evaluate_approval_authority(
            context=self.context,
            capability=stale,
            request=self.request,
        )
        self.assertEqual(result.decision, ApprovalAuthorityDecision.STALE)

    def test_expired_capability_fails_closed_as_stale(self) -> None:
        expired = ApproverCapability(
            "cap-1", "approver-1", "approve", "mission-1", "policy-1", 4, 80.0, 99.0
        )
        result = evaluate_approval_authority(
            context=self.context,
            capability=expired,
            request=self.request,
        )
        self.assertEqual(result.decision, ApprovalAuthorityDecision.STALE)

    def test_future_epoch_and_not_yet_valid_are_blocked(self) -> None:
        future_epoch = ApproverCapability(
            "cap-1", "approver-1", "approve", "mission-1", "policy-1", 5, 90.0, 110.0
        )
        not_yet = ApproverCapability(
            "cap-2", "approver-1", "approve", "mission-1", "policy-1", 4, 101.0, 110.0
        )
        self.assertEqual(
            evaluate_approval_authority(
                context=self.context, capability=future_epoch, request=self.request
            ).decision,
            ApprovalAuthorityDecision.BLOCK,
        )
        self.assertEqual(
            evaluate_approval_authority(
                context=self.context, capability=not_yet, request=self.request
            ).decision,
            ApprovalAuthorityDecision.BLOCK,
        )

    def test_holder_action_target_and_scope_are_all_bound(self) -> None:
        replacements = (
            ApprovalAuthorityRequest("other", "approve", "mission-1", "policy-1"),
            ApprovalAuthorityRequest("approver-1", "deny", "mission-1", "policy-1"),
            ApprovalAuthorityRequest("approver-1", "approve", "mission-2", "policy-1"),
            ApprovalAuthorityRequest("approver-1", "approve", "mission-1", "policy-2"),
        )
        for request in replacements:
            with self.subTest(request=request):
                result = evaluate_approval_authority(
                    context=self.context,
                    capability=self.capability,
                    request=request,
                )
                self.assertEqual(result.decision, ApprovalAuthorityDecision.BLOCK)

    def test_invalid_capability_window_is_rejected(self) -> None:
        with self.assertRaises(ValueError):
            ApproverCapability(
                "cap", "approver", "approve", "mission", "policy", 1, 10.0, 9.0
            )


if __name__ == "__main__":
    unittest.main(verbosity=2)
