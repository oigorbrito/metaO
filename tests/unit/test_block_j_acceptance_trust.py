import unittest

from metao.acceptance import (
    AcceptanceContext,
    AcceptanceDecision,
    ConflictDecision,
    EvidenceEnvelope,
    RequiredEvidenceSet,
    aggregate_evidence,
    check_authority,
    check_freshness,
    check_policy,
    check_provenance,
    evaluate_acceptance,
    replay_acceptance_decision,
)


def evidence(**overrides):
    data = dict(
        evidence_id="e1",
        obligation_id="verify",
        mission_id="m1",
        execution_id="x1",
        orchestrator_id="orch-a",
        adapter_version="1",
        attempt_id="a1",
        subject_id="s1",
        subject_state_id="state-1",
        verification_context_id="ctx-1",
        policy_bundle_id="policy-1",
        verifier_id="verifier-1",
        payload_digest="abc",
        provenance_root="root-1",
        authority_id="authority-1",
        passed=True,
        created_at_epoch=10,
        expires_at_epoch=20,
    )
    data.update(overrides)
    return EvidenceEnvelope(**data)


def context(required=frozenset({"verify"})):
    return AcceptanceContext(
        subject_id="s1",
        subject_state_id="state-1",
        verification_context_id="ctx-1",
        policy_bundle_id="policy-1",
        required_obligations=required,
        trusted_verifiers=frozenset({"verifier-1"}),
        trusted_provenance_roots=frozenset({"root-1"}),
        authorized_authorities=frozenset({"authority-1"}),
    )


class BlockJAcceptanceTrustAcceptance(unittest.TestCase):
    def test_orchestrator_done_is_not_final_acceptance(self):
        result = evaluate_acceptance(context(), [], now_epoch=15, executor_done=True)
        self.assertEqual(result.decision, AcceptanceDecision.NOT_DONE)

    def test_framework_neutral_evidence_envelope_accepts_bound_evidence(self):
        result = evaluate_acceptance(context(), [evidence()], now_epoch=15)
        self.assertEqual(result.decision, AcceptanceDecision.ACCEPT)

    def test_hard_gates_cover_freshness_provenance_authority_policy(self):
        ctx = context()
        item = evidence()
        self.assertTrue(check_freshness(item, now_epoch=15).passed)
        self.assertTrue(check_provenance(item, ctx).passed)
        self.assertTrue(check_authority(item, ctx).passed)
        self.assertTrue(check_policy(item, ctx).passed)
        self.assertEqual(evaluate_acceptance(ctx, [item], now_epoch=21).decision, AcceptanceDecision.STALE)
        self.assertEqual(evaluate_acceptance(ctx, [evidence(verifier_id="evil")], now_epoch=15).decision, AcceptanceDecision.BLOCK)

    def test_partial_conflicting_and_duplicate_evidence_are_governed(self):
        required = RequiredEvidenceSet(frozenset({"verify", "audit"}))
        self.assertEqual(aggregate_evidence(required, [evidence()]).decision, AcceptanceDecision.NOT_DONE)
        duplicate = evidence(evidence_id="e2", passed=False)
        result = aggregate_evidence(RequiredEvidenceSet(frozenset({"verify"})), [evidence(), duplicate])
        self.assertEqual(result.decision, AcceptanceDecision.BLOCK)
        self.assertIn(result.conflict, {ConflictDecision.CONFLICT, ConflictDecision.DUPLICATE})

    def test_final_acceptance_is_deterministic_and_auditable(self):
        first = evaluate_acceptance(context(), [evidence()], now_epoch=15)
        second = evaluate_acceptance(context(), [evidence()], now_epoch=15)
        self.assertEqual(first.proof, second.proof)
        self.assertEqual(replay_acceptance_decision(first.proof), AcceptanceDecision.ACCEPT)


if __name__ == "__main__":
    unittest.main()
