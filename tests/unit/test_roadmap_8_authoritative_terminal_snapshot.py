from __future__ import annotations

import unittest

from metao.authoritative_snapshot import (
    AuthoritativeSnapshotDecision,
    resolve_authoritative_terminal_snapshot,
)
from metao.authoritative_sources import (
    AuthorityResolutionRequest,
    AuthoritativeSourceNotFound,
    InMemoryAuthorityRegistry,
    InMemoryPolicyRegistry,
    InMemorySubjectStateStore,
    PolicyBundle,
    SubjectState,
)


class AuthoritativeTerminalSnapshotTests(unittest.TestCase):
    def request(self, **overrides: str) -> AuthorityResolutionRequest:
        values = {
            "mission_id": "mission-1",
            "execution_id": "execution-1",
            "subject_id": "subject-1",
            "subject_state_id": "state-1",
            "verification_context_id": "verify-1",
            "policy_bundle_id": "policy-1",
            "verifier_id": "verifier-1",
        }
        values.update(overrides)
        return AuthorityResolutionRequest(**values)

    def sources(self, *, authorized: bool = True):
        request = self.request()
        states = InMemorySubjectStateStore({"subject-1": SubjectState("subject-1", "state-1")})
        authorities = InMemoryAuthorityRegistry()
        authorities.put(
            authority_context_id="authority-context-1",
            request=request,
            authority_id="authority-1",
            authorized=authorized,
            reason="denied" if not authorized else "",
        )
        policies = InMemoryPolicyRegistry({
            "policy-1": PolicyBundle("policy-1", "v1", {"rule": "quality"})
        })
        return request, states, authorities, policies

    def test_ready_snapshot_uses_all_authoritative_sources(self) -> None:
        request, states, authorities, policies = self.sources()
        snapshot = resolve_authoritative_terminal_snapshot(
            authority_context_id="authority-context-1",
            request=request,
            subject_state_port=states,
            authority_registry=authorities,
            policy_registry=policies,
        )
        self.assertEqual(snapshot.decision, AuthoritativeSnapshotDecision.READY)
        self.assertEqual(snapshot.subject_state.subject_state_id, "state-1")
        self.assertEqual(snapshot.authority.request, request)
        self.assertEqual(snapshot.policy_bundle.policy_bundle_id, "policy-1")

    def test_forward_subject_state_change_is_stale(self) -> None:
        request, states, authorities, policies = self.sources()
        states.put(SubjectState("subject-1", "state-2"))
        snapshot = resolve_authoritative_terminal_snapshot(
            authority_context_id="authority-context-1",
            request=request,
            subject_state_port=states,
            authority_registry=authorities,
            policy_registry=policies,
        )
        self.assertEqual(snapshot.decision, AuthoritativeSnapshotDecision.STALE)
        self.assertEqual(snapshot.reason, "authoritative_subject_state_changed")

    def test_denied_authority_blocks(self) -> None:
        request, states, authorities, policies = self.sources(authorized=False)
        snapshot = resolve_authoritative_terminal_snapshot(
            authority_context_id="authority-context-1",
            request=request,
            subject_state_port=states,
            authority_registry=authorities,
            policy_registry=policies,
        )
        self.assertEqual(snapshot.decision, AuthoritativeSnapshotDecision.BLOCK)
        self.assertEqual(snapshot.reason, "denied")

    def test_hostile_request_change_cannot_reuse_authority(self) -> None:
        request, states, authorities, policies = self.sources()
        hostile = self.request(policy_bundle_id="policy-2")
        policies.put(PolicyBundle("policy-2", "v2", {"rule": "hostile"}))
        with self.assertRaises(AuthoritativeSourceNotFound):
            resolve_authoritative_terminal_snapshot(
                authority_context_id="authority-context-1",
                request=hostile,
                subject_state_port=states,
                authority_registry=authorities,
                policy_registry=policies,
            )

    def test_missing_authoritative_source_fails_closed(self) -> None:
        request, _, authorities, policies = self.sources()
        with self.assertRaises(AuthoritativeSourceNotFound):
            resolve_authoritative_terminal_snapshot(
                authority_context_id="authority-context-1",
                request=request,
                subject_state_port=InMemorySubjectStateStore(),
                authority_registry=authorities,
                policy_registry=policies,
            )

    def test_ready_snapshot_is_not_metaO_acceptance(self) -> None:
        request, states, authorities, policies = self.sources()
        snapshot = resolve_authoritative_terminal_snapshot(
            authority_context_id="authority-context-1",
            request=request,
            subject_state_port=states,
            authority_registry=authorities,
            policy_registry=policies,
        )
        self.assertFalse(hasattr(snapshot, "acceptance_decision"))


if __name__ == "__main__":
    unittest.main()
