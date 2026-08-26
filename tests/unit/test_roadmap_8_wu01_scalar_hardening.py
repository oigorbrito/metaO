from __future__ import annotations

from dataclasses import replace
import math
import unittest

from metao.evidence import EvidenceEnvelope


class CanonicalEvidenceScalarHardeningTests(unittest.TestCase):
    def item(self) -> EvidenceEnvelope:
        return EvidenceEnvelope(
            evidence_id="e-1",
            obligation_id="o-1",
            mission_id="m-1",
            execution_id="x-1",
            orchestrator_id="orch-1",
            adapter_id="adapter-1",
            adapter_version="1",
            attempt_id="a-1",
            subject_id="s-1",
            subject_state_id="state-1",
            verification_context_id="ctx-1",
            policy_bundle_id="policy-1",
            verifier_id="verifier-1",
            payload_digest="payload-1",
            provenance_root="root-1",
            authority_id="authority-1",
            passed=True,
            created_at_epoch=10.0,
            expires_at_epoch=20.0,
            confidence=0.5,
            verification_cost_units=1,
        )

    def test_passed_requires_exact_boolean(self) -> None:
        for value in (1, 0, "true"):
            with self.subTest(value=value), self.assertRaises(TypeError):
                replace(self.item(), passed=value)  # type: ignore[arg-type]

    def test_confidence_rejects_boolean_and_non_finite(self) -> None:
        for value in (True, math.nan, math.inf, -math.inf):
            with self.subTest(value=value), self.assertRaises((TypeError, ValueError)):
                replace(self.item(), confidence=value)  # type: ignore[arg-type]

    def test_verification_cost_requires_non_boolean_integer(self) -> None:
        for value in (True, 1.5):
            with self.subTest(value=value), self.assertRaises(TypeError):
                replace(self.item(), verification_cost_units=value)  # type: ignore[arg-type]

    def test_evidence_times_reject_boolean_non_finite_and_reverse_expiry(self) -> None:
        for field in ("created_at_epoch", "expires_at_epoch"):
            for value in (True, math.nan, math.inf, -math.inf, -1.0):
                with self.subTest(field=field, value=value), self.assertRaises((TypeError, ValueError)):
                    replace(self.item(), **{field: value})
        with self.assertRaises(ValueError):
            replace(self.item(), created_at_epoch=10.0, expires_at_epoch=9.0)


if __name__ == "__main__":
    unittest.main()
