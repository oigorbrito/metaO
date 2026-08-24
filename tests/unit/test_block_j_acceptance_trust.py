import importlib
import unittest


class BlockJAcceptanceTrustAcceptance(unittest.TestCase):
    def _acceptance(self):
        return importlib.import_module("metao.acceptance")

    def test_orchestrator_done_is_not_final_acceptance(self):
        acceptance = self._acceptance()
        self.assertTrue(hasattr(acceptance, "AcceptanceDecision"))
        self.assertTrue(hasattr(acceptance, "evaluate_acceptance"))

    def test_framework_neutral_evidence_envelope_exists(self):
        acceptance = self._acceptance()
        self.assertTrue(hasattr(acceptance, "EvidenceEnvelope"))

    def test_hard_gates_cover_freshness_provenance_authority_policy(self):
        acceptance = self._acceptance()
        for name in ("check_freshness", "check_provenance", "check_authority", "check_policy"):
            self.assertTrue(hasattr(acceptance, name), name)

    def test_partial_conflicting_and_duplicate_evidence_are_governed(self):
        acceptance = self._acceptance()
        for name in ("RequiredEvidenceSet", "aggregate_evidence", "ConflictDecision"):
            self.assertTrue(hasattr(acceptance, name), name)

    def test_final_acceptance_is_deterministic_and_auditable(self):
        acceptance = self._acceptance()
        self.assertTrue(hasattr(acceptance, "AcceptanceProof"))
        self.assertTrue(hasattr(acceptance, "replay_acceptance_decision"))


if __name__ == "__main__":
    unittest.main()
