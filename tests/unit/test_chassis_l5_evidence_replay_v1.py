import unittest
from dataclasses import replace

from metao.acceptance import (
    AcceptanceContext,
    AcceptanceDecision,
    EvidenceEnvelope,
    evaluate_acceptance,
    replay_acceptance_decision,
)


def context():
    return AcceptanceContext(
        subject_id="subject-l5",
        subject_state_id="state-l5",
        verification_context_id="verify-l5",
        policy_bundle_id="policy-l5",
        required_obligations=frozenset({"a", "b"}),
        trusted_verifiers=frozenset({"verifier-l5"}),
        trusted_provenance_roots=frozenset({"root-l5"}),
        authorized_authorities=frozenset({"authority-l5"}),
    )


def evidence(obligation: str, evidence_id: str, *, created_at: float):
    return EvidenceEnvelope(
        evidence_id=evidence_id,
        obligation_id=obligation,
        mission_id="mission-l5",
        execution_id="exec-l5",
        orchestrator_id="runtime-l5",
        adapter_version="1",
        attempt_id="attempt-l5",
        subject_id="subject-l5",
        subject_state_id="state-l5",
        verification_context_id="verify-l5",
        policy_bundle_id="policy-l5",
        verifier_id="verifier-l5",
        payload_digest=f"digest-{evidence_id}",
        provenance_root="root-l5",
        authority_id="authority-l5",
        passed=True,
        created_at_epoch=created_at,
        expires_at_epoch=100.0,
    )


class ChassisL5EvidenceReplayV1(unittest.TestCase):
    def test_valid_evidence_arrival_order_does_not_change_acceptance_or_proof(self):
        a = evidence("a", "e-a", created_at=20.0)
        b = evidence("b", "e-b", created_at=10.0)

        chronological = evaluate_acceptance(
            context(),
            (b, a),
            now_epoch=30.0,
            executor_done=True,
        )
        out_of_order = evaluate_acceptance(
            context(),
            (a, b),
            now_epoch=30.0,
            executor_done=True,
        )

        self.assertEqual(chronological.decision, AcceptanceDecision.ACCEPT)
        self.assertEqual(out_of_order.decision, AcceptanceDecision.ACCEPT)
        self.assertEqual(chronological.proof, out_of_order.proof)

    def test_duplicate_evidence_replay_fails_closed(self):
        a = evidence("a", "same-id", created_at=10.0)
        b = evidence("b", "same-id", created_at=11.0)
        result = evaluate_acceptance(context(), (a, b), now_epoch=20.0, executor_done=True)
        self.assertEqual(result.decision, AcceptanceDecision.BLOCK)
        self.assertIn("duplicate_evidence_id", result.reasons)

    def test_conflicting_obligation_replay_fails_closed(self):
        first = evidence("a", "e-1", created_at=10.0)
        conflicting = replace(first, evidence_id="e-2", payload_digest="different")
        result = evaluate_acceptance(
            context(),
            (first, conflicting),
            now_epoch=20.0,
            executor_done=True,
        )
        self.assertEqual(result.decision, AcceptanceDecision.BLOCK)

    def test_tampered_acceptance_proof_cannot_be_replayed(self):
        result = evaluate_acceptance(
            context(),
            (
                evidence("a", "e-a", created_at=10.0),
                evidence("b", "e-b", created_at=11.0),
            ),
            now_epoch=20.0,
            executor_done=True,
        )
        self.assertEqual(result.decision, AcceptanceDecision.ACCEPT)
        self.assertEqual(replay_acceptance_decision(result.proof), AcceptanceDecision.ACCEPT)

        tampered = replace(result.proof, evidence_ids=("forged",))
        with self.assertRaises(ValueError):
            replay_acceptance_decision(tampered)

    def test_future_evidence_is_blocked_even_when_executor_claims_done(self):
        future = evidence("a", "future", created_at=50.0)
        other = evidence("b", "normal", created_at=10.0)
        result = evaluate_acceptance(
            context(),
            (future, other),
            now_epoch=20.0,
            executor_done=True,
        )
        self.assertEqual(result.decision, AcceptanceDecision.BLOCK)
        self.assertIn("evidence_from_future", result.reasons)


if __name__ == "__main__":
    unittest.main(verbosity=2)
