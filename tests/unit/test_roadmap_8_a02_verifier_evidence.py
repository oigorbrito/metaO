from __future__ import annotations

import unittest

from metao.evidence import EvidenceEnvelope
from metao.verifier import (
    VerificationRequest,
    VerificationStatus,
    VerifierDescriptor,
    VerifierResult,
)
from metao.verifier_evidence import (
    VerifierEvidenceBindings,
    VerifierEvidenceDecision,
    normalize_verifier_result,
)


class VerifierEvidenceNormalizationTests(unittest.TestCase):
    def request(self) -> VerificationRequest:
        return VerificationRequest(
            "request-1",
            "mission-1",
            "execution-1",
            "obligation-1",
            "subject-1",
            "state-1",
            "context-1",
            "policy-1",
            "payload-1",
            {"answer": "candidate"},
        )

    def descriptor(self) -> VerifierDescriptor:
        return VerifierDescriptor("verifier-1", "1.0")

    def bindings(self, **overrides: object) -> VerifierEvidenceBindings:
        values: dict[str, object] = {
            "evidence_id": "evidence-1",
            "orchestrator_id": "langgraph",
            "adapter_id": "langgraph-adapter",
            "adapter_version": "1.2.11",
            "attempt_id": "attempt-1",
            "provenance_root": "verified-provenance-root",
            "authority_id": "authority-1",
            "created_at_epoch": 10.0,
        }
        values.update(overrides)
        return VerifierEvidenceBindings(**values)  # type: ignore[arg-type]

    def result(self, status: VerificationStatus = VerificationStatus.PASS, **overrides: object) -> VerifierResult:
        values: dict[str, object] = {
            "request_id": "request-1",
            "verifier_id": "verifier-1",
            "verifier_version": "1.0",
            "status": status,
            "result_digest": "result-1",
            "confidence": 0.9,
        }
        values.update(overrides)
        return VerifierResult(**values)  # type: ignore[arg-type]

    def test_pass_normalizes_to_canonical_evidence_without_acceptance_authority(self) -> None:
        normalized = normalize_verifier_result(
            request=self.request(),
            descriptor=self.descriptor(),
            result=self.result(),
            bindings=self.bindings(),
        )
        self.assertEqual(normalized.decision, VerifierEvidenceDecision.READY)
        self.assertIsInstance(normalized.evidence, EvidenceEnvelope)
        assert normalized.evidence is not None
        self.assertTrue(normalized.evidence.passed)
        self.assertEqual(normalized.evidence.mission_id, "mission-1")
        self.assertEqual(normalized.evidence.verifier_id, "verifier-1")
        self.assertEqual(normalized.evidence.provenance_root, "verified-provenance-root")
        self.assertEqual(normalized.evidence.authority_id, "authority-1")
        self.assertFalse(hasattr(normalized.evidence, "acceptance_decision"))
        self.assertFalse(hasattr(normalized.evidence, "metao_accepted"))

    def test_fail_normalizes_as_failed_evidence(self) -> None:
        normalized = normalize_verifier_result(
            request=self.request(),
            descriptor=self.descriptor(),
            result=self.result(VerificationStatus.FAIL),
            bindings=self.bindings(),
        )
        self.assertEqual(normalized.decision, VerifierEvidenceDecision.READY)
        assert normalized.evidence is not None
        self.assertFalse(normalized.evidence.passed)

    def test_error_does_not_flatten_into_ordinary_failed_evidence(self) -> None:
        normalized = normalize_verifier_result(
            request=self.request(),
            descriptor=self.descriptor(),
            result=self.result(VerificationStatus.ERROR),
            bindings=self.bindings(),
        )
        self.assertEqual(normalized.decision, VerifierEvidenceDecision.BLOCK)
        self.assertIsNone(normalized.evidence)
        self.assertEqual(normalized.reason, "verifier_result_error")

    def test_request_verifier_and_version_mismatch_fail_closed(self) -> None:
        cases = (
            (self.result(request_id="other"), "verifier_result_request_mismatch"),
            (self.result(verifier_id="other"), "verifier_result_identity_mismatch"),
            (self.result(verifier_version="2.0"), "verifier_result_version_mismatch"),
        )
        for result, reason in cases:
            with self.subTest(reason=reason):
                normalized = normalize_verifier_result(
                    request=self.request(),
                    descriptor=self.descriptor(),
                    result=result,
                    bindings=self.bindings(),
                )
                self.assertEqual(normalized.decision, VerifierEvidenceDecision.BLOCK)
                self.assertIsNone(normalized.evidence)
                self.assertEqual(normalized.reason, reason)

    def test_missing_trust_or_runtime_binding_fails_before_normalization(self) -> None:
        for field in (
            "evidence_id",
            "orchestrator_id",
            "adapter_id",
            "adapter_version",
            "attempt_id",
            "provenance_root",
            "authority_id",
        ):
            with self.subTest(field=field), self.assertRaises(ValueError):
                self.bindings(**{field: ""})

    def test_request_bindings_are_source_of_evidence_identity(self) -> None:
        request = self.request()
        normalized = normalize_verifier_result(
            request=request,
            descriptor=self.descriptor(),
            result=self.result(),
            bindings=self.bindings(),
        )
        assert normalized.evidence is not None
        self.assertEqual(normalized.evidence.execution_id, request.execution_id)
        self.assertEqual(normalized.evidence.obligation_id, request.obligation_id)
        self.assertEqual(normalized.evidence.subject_id, request.subject_id)
        self.assertEqual(normalized.evidence.subject_state_id, request.subject_state_id)
        self.assertEqual(normalized.evidence.verification_context_id, request.verification_context_id)
        self.assertEqual(normalized.evidence.policy_bundle_id, request.policy_bundle_id)
        self.assertEqual(normalized.evidence.payload_digest, request.payload_digest)


if __name__ == "__main__":
    unittest.main()
