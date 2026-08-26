from __future__ import annotations

import unittest

from metao.authoritative_sources import (
    AuthorityResolutionRequest,
    AuthoritativeSourceNotFound,
    InMemoryAuthorityRegistry,
    InMemoryPolicyRegistry,
    InMemorySubjectStateStore,
    PolicyBundle,
    SubjectState,
)


class AuthoritativeSourcePrimitiveTests(unittest.TestCase):
    def request(self, **overrides: str) -> AuthorityResolutionRequest:
        values = {
            "mission_id": "mission-1",
            "execution_id": "execution-1",
            "subject_id": "subject-1",
            "subject_state_id": "state-1",
            "verification_context_id": "verification-context-1",
            "policy_bundle_id": "policy-1",
            "verifier_id": "verifier-1",
        }
        values.update(overrides)
        return AuthorityResolutionRequest(**values)

    def test_subject_state_returns_current_authoritative_state(self) -> None:
        store = InMemorySubjectStateStore()
        store.put(SubjectState("subject-1", "state-1"))
        store.put(SubjectState("subject-1", "state-2"))
        self.assertEqual(store.current("subject-1").subject_state_id, "state-2")

    def test_missing_subject_state_fails_closed(self) -> None:
        with self.assertRaises(AuthoritativeSourceNotFound):
            InMemorySubjectStateStore().current("missing")

    def test_authority_resolution_is_bound_to_exact_request(self) -> None:
        registry = InMemoryAuthorityRegistry()
        request = self.request()
        registry.put(
            authority_context_id="authority-context-1",
            request=request,
            authority_id="authority-1",
            authorized=True,
        )
        result = registry.resolve("authority-context-1", request)
        self.assertTrue(result.authorized)
        self.assertEqual(result.authority_id, "authority-1")
        self.assertEqual(result.request, request)

    def test_caller_cannot_change_any_bound_claim_to_reuse_authority(self) -> None:
        variants = {
            "mission_id": "mission-2",
            "execution_id": "execution-2",
            "subject_id": "subject-2",
            "subject_state_id": "state-2",
            "verification_context_id": "verification-context-2",
            "policy_bundle_id": "policy-2",
            "verifier_id": "untrusted",
        }
        for field, hostile_value in variants.items():
            with self.subTest(field=field):
                registry = InMemoryAuthorityRegistry()
                trusted = self.request()
                registry.put(
                    authority_context_id="authority-context-1",
                    request=trusted,
                    authority_id="authority-1",
                    authorized=True,
                )
                hostile = self.request(**{field: hostile_value})
                with self.assertRaises(AuthoritativeSourceNotFound):
                    registry.resolve("authority-context-1", hostile)

    def test_policy_registry_returns_registered_bundle(self) -> None:
        registry = InMemoryPolicyRegistry()
        registry.put(PolicyBundle("policy-1", "v1", {"require": "quality"}))
        bundle = registry.get("policy-1")
        self.assertEqual(bundle.version, "v1")
        self.assertEqual(bundle.rules["require"], "quality")

    def test_policy_bundle_is_snapshot_not_caller_mutable(self) -> None:
        rules = {"require": "quality"}
        bundle = PolicyBundle("policy-1", "v1", rules)
        rules["require"] = "hostile-change"
        self.assertEqual(bundle.rules["require"], "quality")
        with self.assertRaises(TypeError):
            bundle.rules["require"] = "mutation"

    def test_missing_policy_fails_closed(self) -> None:
        with self.assertRaises(AuthoritativeSourceNotFound):
            InMemoryPolicyRegistry().get("missing")

    def test_authority_request_requires_all_bindings(self) -> None:
        values = {
            "mission_id": "mission-1",
            "execution_id": "execution-1",
            "subject_id": "subject-1",
            "subject_state_id": "state-1",
            "verification_context_id": "verification-context-1",
            "policy_bundle_id": "policy-1",
            "verifier_id": "verifier-1",
        }
        for field in tuple(values):
            hostile = dict(values)
            hostile[field] = ""
            with self.subTest(field=field), self.assertRaises(ValueError):
                AuthorityResolutionRequest(**hostile)


if __name__ == "__main__":
    unittest.main()
