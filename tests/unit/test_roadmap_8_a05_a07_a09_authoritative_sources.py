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
    def test_subject_state_returns_current_authoritative_state(self) -> None:
        store = InMemorySubjectStateStore()
        store.put(SubjectState("subject-1", "state-1"))
        store.put(SubjectState("subject-1", "state-2"))
        self.assertEqual(store.current("subject-1").subject_state_id, "state-2")

    def test_missing_subject_state_fails_closed(self) -> None:
        with self.assertRaises(AuthoritativeSourceNotFound):
            InMemorySubjectStateStore().current("missing")

    def test_authority_resolution_is_bound_to_context_and_verifier(self) -> None:
        registry = InMemoryAuthorityRegistry()
        registry.put(
            authority_context_id="authority-context-1",
            verifier_id="verifier-1",
            authority_id="authority-1",
            authorized=True,
        )
        request = AuthorityResolutionRequest(
            "mission-1",
            "execution-1",
            "subject-1",
            "state-1",
            "verification-context-1",
            "policy-1",
            "verifier-1",
        )
        result = registry.resolve("authority-context-1", request)
        self.assertTrue(result.authorized)
        self.assertEqual(result.authority_id, "authority-1")

    def test_caller_cannot_change_verifier_claim_to_reuse_authority(self) -> None:
        registry = InMemoryAuthorityRegistry()
        registry.put(
            authority_context_id="authority-context-1",
            verifier_id="trusted",
            authority_id="authority-1",
            authorized=True,
        )
        hostile = AuthorityResolutionRequest(
            "mission-1",
            "execution-1",
            "subject-1",
            "state-1",
            "verification-context-1",
            "policy-1",
            "untrusted",
        )
        with self.assertRaises(AuthoritativeSourceNotFound):
            registry.resolve("authority-context-1", hostile)

    def test_policy_registry_returns_registered_bundle(self) -> None:
        registry = InMemoryPolicyRegistry()
        registry.put(PolicyBundle("policy-1", "v1", {"require": "quality"}))
        bundle = registry.get("policy-1")
        self.assertEqual(bundle.version, "v1")
        self.assertEqual(bundle.rules["require"], "quality")

    def test_missing_policy_fails_closed(self) -> None:
        with self.assertRaises(AuthoritativeSourceNotFound):
            InMemoryPolicyRegistry().get("missing")

    def test_authority_request_requires_all_bindings(self) -> None:
        args = [
            "mission-1",
            "execution-1",
            "subject-1",
            "state-1",
            "verification-context-1",
            "policy-1",
            "verifier-1",
        ]
        for index in range(len(args)):
            values = list(args)
            values[index] = ""
            with self.subTest(index=index), self.assertRaises(ValueError):
                AuthorityResolutionRequest(*values)


if __name__ == "__main__":
    unittest.main()
