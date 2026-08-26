from __future__ import annotations

import unittest

from metao.approval_authority import (
    ApprovalAuthorityContext,
    ApprovalAuthorityRequest,
    ApproverCapability,
)
from metao.authoritative_snapshot import (
    AuthoritativeSnapshotDecision,
    AuthoritativeTerminalSnapshot,
)
from metao.authoritative_sources import (
    AuthorityResolution,
    AuthorityResolutionRequest,
    PolicyBundle,
    SubjectState,
)
from metao.freshness_authority import FixedClock, FreshnessPolicy, FreshnessRequest
from metao.provenance_attestation import (
    AttestationStatus,
    ProvenanceAttestationRequest,
    ProvenanceAttestationResult,
)
from metao.terminal_preconditions import (
    TerminalPreconditionDecision,
    evaluate_terminal_preconditions,
)


class _Provider:
    provider_id = "provider-1"
    provider_version = "1.0"

    def __init__(self, result: ProvenanceAttestationResult | None = None, *, error: bool = False) -> None:
        self._result = result
        self._error = error

    def verify(self, request: ProvenanceAttestationRequest) -> ProvenanceAttestationResult:
        if self._error:
            raise RuntimeError("boom")
        return self._result or ProvenanceAttestationResult(
            request.request_id,
            self.provider_id,
            self.provider_version,
            AttestationStatus.VERIFIED,
            "attestation-digest",
        )


class TerminalPreconditionTests(unittest.TestCase):
    def setUp(self) -> None:
        self.request = AuthorityResolutionRequest(
            "mission-1",
            "execution-1",
            "subject-1",
            "state-1",
            "verify-1",
            "policy-1",
            "verifier-1",
        )
        self.snapshot = AuthoritativeTerminalSnapshot(
            AuthoritativeSnapshotDecision.READY,
            self.request,
            SubjectState("subject-1", "state-1"),
            AuthorityResolution(
                "authority-context-1",
                "authority-1",
                True,
                request=self.request,
            ),
            PolicyBundle("policy-1", "v1", {}),
        )
        self.freshness = FreshnessRequest(
            "evidence-1",
            "subject-1",
            "state-1",
            "verify-1",
            90.0,
            110.0,
        )
        self.provenance = ProvenanceAttestationRequest(
            "prov-1",
            "mission-1",
            "execution-1",
            "subject-1",
            "state-1",
            "verify-1",
            "payload-1",
            "root-1",
        )
        self.approval_context = ApprovalAuthorityContext("authority-context-1", 4, 100.0)
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
        self.approval_request = ApprovalAuthorityRequest(
            "approver-1",
            "approve",
            "mission-1",
            "policy-1",
        )

    def evaluate(self, **overrides: object):
        values: dict[str, object] = {
            "authoritative_snapshot": self.snapshot,
            "freshness_request": self.freshness,
            "clock": FixedClock(100.0),
            "freshness_policy": FreshnessPolicy(max_age_s=20.0),
            "provenance_request": self.provenance,
            "provenance_provider": _Provider(),
            "approval_required": True,
            "approval_context": self.approval_context,
            "approver_capability": self.capability,
            "approval_request": self.approval_request,
        }
        values.update(overrides)
        return evaluate_terminal_preconditions(**values)  # type: ignore[arg-type]

    def test_ready_requires_all_preconditions(self) -> None:
        result = self.evaluate()
        self.assertEqual(result.decision, TerminalPreconditionDecision.READY)
        self.assertEqual(result.attestation_digest, "attestation-digest")
        self.assertEqual(result.approval_capability_id, "cap-1")

    def test_authoritative_stale_short_circuits(self) -> None:
        stale = AuthoritativeTerminalSnapshot(
            AuthoritativeSnapshotDecision.STALE,
            self.request,
            self.snapshot.subject_state,
            self.snapshot.authority,
            self.snapshot.policy_bundle,
            "state_changed",
        )
        result = self.evaluate(authoritative_snapshot=stale)
        self.assertEqual(result.decision, TerminalPreconditionDecision.STALE)

    def test_freshness_binding_mismatch_blocks(self) -> None:
        hostile = FreshnessRequest("e", "other", "state-1", "verify-1", 90.0, 110.0)
        result = self.evaluate(freshness_request=hostile)
        self.assertEqual(result.decision, TerminalPreconditionDecision.BLOCK)
        self.assertEqual(result.reason, "freshness_binding_mismatch")

    def test_stale_freshness_returns_stale(self) -> None:
        result = self.evaluate(clock=FixedClock(200.0))
        self.assertEqual(result.decision, TerminalPreconditionDecision.STALE)

    def test_provenance_request_binding_mismatch_blocks(self) -> None:
        hostile = ProvenanceAttestationRequest(
            "prov-1", "mission-2", "execution-1", "subject-1", "state-1", "verify-1", "payload-1", "root-1"
        )
        result = self.evaluate(provenance_request=hostile)
        self.assertEqual(result.decision, TerminalPreconditionDecision.BLOCK)
        self.assertEqual(result.reason, "provenance_request_binding_mismatch")

    def test_attestation_request_provider_and_version_are_bound(self) -> None:
        cases = (
            ProvenanceAttestationResult("other", "provider-1", "1.0", AttestationStatus.VERIFIED, "d"),
            ProvenanceAttestationResult("prov-1", "other", "1.0", AttestationStatus.VERIFIED, "d"),
            ProvenanceAttestationResult("prov-1", "provider-1", "2.0", AttestationStatus.VERIFIED, "d"),
        )
        for attestation in cases:
            with self.subTest(attestation=attestation):
                result = self.evaluate(provenance_provider=_Provider(attestation))
                self.assertEqual(result.decision, TerminalPreconditionDecision.BLOCK)

    def test_attestation_stale_and_invalid_fail_closed(self) -> None:
        stale = ProvenanceAttestationResult(
            "prov-1", "provider-1", "1.0", AttestationStatus.STALE, "d"
        )
        invalid = ProvenanceAttestationResult(
            "prov-1", "provider-1", "1.0", AttestationStatus.INVALID, "d"
        )
        self.assertEqual(
            self.evaluate(provenance_provider=_Provider(stale)).decision,
            TerminalPreconditionDecision.STALE,
        )
        self.assertEqual(
            self.evaluate(provenance_provider=_Provider(invalid)).decision,
            TerminalPreconditionDecision.BLOCK,
        )

    def test_provider_exception_blocks(self) -> None:
        result = self.evaluate(provenance_provider=_Provider(error=True))
        self.assertEqual(result.decision, TerminalPreconditionDecision.BLOCK)
        self.assertEqual(result.reason, "provenance_provider_error")

    def test_required_approval_inputs_cannot_be_omitted(self) -> None:
        result = self.evaluate(approval_context=None)
        self.assertEqual(result.decision, TerminalPreconditionDecision.BLOCK)
        self.assertEqual(result.reason, "approval_authority_inputs_missing")

    def test_stale_and_wrong_approval_authority_fail_closed(self) -> None:
        stale = ApproverCapability(
            "cap-1", "approver-1", "approve", "mission-1", "policy-1", 3, 90.0, 110.0
        )
        wrong = ApprovalAuthorityRequest("other", "approve", "mission-1", "policy-1")
        self.assertEqual(
            self.evaluate(approver_capability=stale).decision,
            TerminalPreconditionDecision.STALE,
        )
        self.assertEqual(
            self.evaluate(approval_request=wrong).decision,
            TerminalPreconditionDecision.BLOCK,
        )

    def test_approval_can_be_explicitly_not_required(self) -> None:
        result = self.evaluate(
            approval_required=False,
            approval_context=None,
            approver_capability=None,
            approval_request=None,
        )
        self.assertEqual(result.decision, TerminalPreconditionDecision.READY)
        self.assertIsNone(result.approval_capability_id)

    def test_bundle_does_not_expose_terminal_acceptance(self) -> None:
        result = self.evaluate()
        self.assertFalse(hasattr(result, "acceptance_decision"))
        self.assertFalse(hasattr(result, "metao_accepted"))


if __name__ == "__main__":
    unittest.main(verbosity=2)
