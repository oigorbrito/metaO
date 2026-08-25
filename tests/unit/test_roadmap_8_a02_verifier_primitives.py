from __future__ import annotations

import unittest

from metao.verifier import (
    VerificationRequest,
    VerificationStatus,
    VerifierAlreadyRegistered,
    VerifierDescriptor,
    VerifierNotFound,
    VerifierRegistry,
    VerifierResult,
)


class _Verifier:
    def __init__(self, verifier_id: str, *capabilities: str) -> None:
        self._descriptor = VerifierDescriptor(verifier_id, "1.0", frozenset(capabilities))

    @property
    def descriptor(self) -> VerifierDescriptor:
        return self._descriptor

    def verify(self, request: VerificationRequest) -> VerifierResult:
        return VerifierResult(
            request_id=request.request_id,
            verifier_id=self.descriptor.verifier_id,
            verifier_version=self.descriptor.version,
            status=VerificationStatus.PASS,
            result_digest=f"verified:{request.payload_digest}",
        )


class VerifierPrimitiveTests(unittest.TestCase):
    def _request(self) -> VerificationRequest:
        return VerificationRequest(
            request_id="vr-1",
            mission_id="m-1",
            execution_id="e-1",
            obligation_id="o-1",
            subject_id="s-1",
            subject_state_id="ss-1",
            verification_context_id="vc-1",
            policy_bundle_id="p-1",
            payload_digest="digest-1",
            payload={"value": 1},
        )

    def test_request_requires_all_bindings(self) -> None:
        values = self._request().__dict__
        for name in (
            "request_id", "mission_id", "execution_id", "obligation_id",
            "subject_id", "subject_state_id", "verification_context_id",
            "policy_bundle_id", "payload_digest",
        ):
            kwargs = dict(values)
            kwargs[name] = ""
            with self.subTest(name=name), self.assertRaises(ValueError):
                VerificationRequest(**kwargs)

    def test_payload_is_snapshot_not_caller_mutable(self) -> None:
        payload = {"value": 1}
        request = VerificationRequest(
            "vr-1", "m-1", "e-1", "o-1", "s-1", "ss-1", "vc-1", "p-1", "d-1", payload
        )
        payload["value"] = 2
        self.assertEqual(request.payload["value"], 1)
        with self.assertRaises(TypeError):
            request.payload["value"] = 3

    def test_confidence_is_bounded(self) -> None:
        with self.assertRaises(ValueError):
            VerifierResult("r", "v", "1", VerificationStatus.PASS, "d", confidence=1.01)

    def test_pass_is_not_acceptance_decision(self) -> None:
        result = VerifierResult("r", "v", "1", VerificationStatus.PASS, "d")
        self.assertTrue(result.passed)
        self.assertFalse(hasattr(result, "acceptance_decision"))

    def test_registry_rejects_duplicate_identity(self) -> None:
        registry = VerifierRegistry()
        registry.register(_Verifier("v1"))
        with self.assertRaises(VerifierAlreadyRegistered):
            registry.register(_Verifier("v1"))

    def test_registry_missing_fails_explicitly(self) -> None:
        with self.assertRaises(VerifierNotFound):
            VerifierRegistry().get("missing")

    def test_registry_list_and_selection_are_deterministic(self) -> None:
        registry = VerifierRegistry()
        registry.register(_Verifier("zeta", "security"))
        registry.register(_Verifier("alpha", "quality"))
        registry.register(_Verifier("beta", "quality"))
        self.assertEqual([d.verifier_id for d in registry.list()], ["alpha", "beta", "zeta"])
        self.assertEqual(registry.select().descriptor.verifier_id, "alpha")
        self.assertEqual(registry.select(required_capability="quality").descriptor.verifier_id, "alpha")
        self.assertEqual(registry.select(required_capability="security").descriptor.verifier_id, "zeta")
        self.assertIsNone(registry.select(required_capability="missing"))

    def test_invocation_preserves_request_binding(self) -> None:
        verifier = _Verifier("v1")
        request = self._request()
        result = verifier.verify(request)
        self.assertEqual(result.request_id, request.request_id)
        self.assertEqual(result.verifier_id, verifier.descriptor.verifier_id)
        self.assertEqual(result.verifier_version, verifier.descriptor.version)


if __name__ == "__main__":
    unittest.main()
