from __future__ import annotations

import unittest

from metao.provenance_attestation import (
    AttestationStatus,
    ProvenanceAttestationPort,
    ProvenanceAttestationRequest,
    ProvenanceAttestationResult,
)


class FakeProvider:
    provider_id = "provider-1"
    provider_version = "v1"

    def verify(self, request: ProvenanceAttestationRequest) -> ProvenanceAttestationResult:
        return ProvenanceAttestationResult(
            request_id=request.request_id,
            provider_id=self.provider_id,
            provider_version=self.provider_version,
            status=AttestationStatus.VERIFIED,
            attestation_digest="attestation-digest-1",
        )


class Roadmap8A06ProvenanceAttestationTests(unittest.TestCase):
    def request(self, **overrides: str) -> ProvenanceAttestationRequest:
        values = {
            "request_id": "request-1",
            "mission_id": "mission-1",
            "execution_id": "execution-1",
            "subject_id": "subject-1",
            "subject_state_id": "state-1",
            "verification_context_id": "context-1",
            "payload_digest": "payload-1",
            "provenance_root": "root-1",
        }
        values.update(overrides)
        return ProvenanceAttestationRequest(**values)

    def test_provider_satisfies_framework_neutral_port(self) -> None:
        self.assertIsInstance(FakeProvider(), ProvenanceAttestationPort)

    def test_result_is_bound_to_request_and_provider(self) -> None:
        result = FakeProvider().verify(self.request())
        self.assertEqual(result.request_id, "request-1")
        self.assertEqual(result.provider_id, "provider-1")
        self.assertEqual(result.provider_version, "v1")
        self.assertTrue(result.verified)

    def test_missing_request_binding_fails_closed(self) -> None:
        for field in ProvenanceAttestationRequest.__dataclass_fields__:
            with self.subTest(field=field):
                with self.assertRaises(ValueError):
                    self.request(**{field: ""})

    def test_verified_result_does_not_encode_metao_acceptance(self) -> None:
        result = FakeProvider().verify(self.request())
        self.assertFalse(hasattr(result, "acceptance_decision"))
        self.assertFalse(hasattr(result, "metao_accepted"))

    def test_invalid_stale_and_error_are_first_class_fail_closed_observations(self) -> None:
        for status in (
            AttestationStatus.INVALID,
            AttestationStatus.STALE,
            AttestationStatus.ERROR,
        ):
            with self.subTest(status=status):
                result = ProvenanceAttestationResult(
                    "request-1", "provider-1", "v1", status, "digest-1", "reason"
                )
                self.assertFalse(result.verified)


if __name__ == "__main__":
    unittest.main(verbosity=2)
