from __future__ import annotations

import unittest

from metao.adversarial import (
    AdversarialCase,
    AttackVector,
    ExpectedDecision,
    STANDARD_A19_MATRIX,
    validate_attack_matrix,
)


class AdversarialHarnessTests(unittest.TestCase):
    def test_standard_matrix_is_complete_and_unique(self) -> None:
        validate_attack_matrix()
        self.assertEqual({case.vector for case in STANDARD_A19_MATRIX}, set(AttackVector))

    def test_no_hostile_case_allows_accepted_terminal_record(self) -> None:
        self.assertTrue(all(not case.accepted_terminal_record_allowed for case in STANDARD_A19_MATRIX))

    def test_matrix_covers_authority_budget_retry_approval_and_provenance(self) -> None:
        vectors = {case.vector for case in STANDARD_A19_MATRIX}
        for expected in (
            AttackVector.FABRICATED_AUTHORITY,
            AttackVector.BUDGET_RESET,
            AttackVector.OMITTED_RETRY_HISTORY,
            AttackVector.STALE_APPROVAL,
            AttackVector.PROVENANCE_SUBSTITUTION,
            AttackVector.HOSTILE_ATTESTATION_FAILURE,
        ):
            self.assertIn(expected, vectors)

    def test_duplicate_vector_fails_closed(self) -> None:
        case = STANDARD_A19_MATRIX[0]
        with self.assertRaises(ValueError):
            validate_attack_matrix(STANDARD_A19_MATRIX + (case,))

    def test_missing_vector_fails_closed(self) -> None:
        with self.assertRaises(ValueError):
            validate_attack_matrix(STANDARD_A19_MATRIX[:-1])

    def test_hostile_case_cannot_allow_accept_record(self) -> None:
        with self.assertRaises(ValueError):
            AdversarialCase(
                AttackVector.FALSE_DONE,
                ExpectedDecision.NOT_DONE,
                "independent_acceptance",
                accepted_terminal_record_allowed=True,
            )


if __name__ == "__main__":
    unittest.main()
