from __future__ import annotations

import copy
import json
import unittest
from pathlib import Path

import scripts.repository_convergence_classifier as classifier


ROOT = Path(__file__).resolve().parents[2]
FIXTURE_PATH = (
    ROOT
    / "experiments"
    / "rust-chassis-a"
    / "metao-contracts"
    / "tests"
    / "fixtures"
    / "repository_convergence_cases.v1.json"
)
AUTHORITY_PATH = (
    ROOT
    / "experiments"
    / "rust-chassis-a"
    / "metao-contracts"
    / "tests"
    / "fixtures"
    / "repository_convergence_authority_facts.v1.json"
)


class RepositoryConvergenceClassifierTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.fixture = json.loads(FIXTURE_PATH.read_text(encoding="utf-8"))
        cls.authority = json.loads(AUTHORITY_PATH.read_text(encoding="utf-8"))

    def classify(self, cases=None, authority=None):
        return classifier.classify_cases(
            self.fixture["cases"] if cases is None else cases,
            self.authority if authority is None else authority,
        )

    def test_ground_truth_replay_matches_every_expected_disposition(self) -> None:
        results = self.classify()
        actual = {result["id"]: result for result in results}

        for case in self.fixture["cases"]:
            self.assertEqual(
                actual[case["id"]]["disposition"],
                case["expected_disposition"],
                case["id"],
            )
            self.assertEqual(
                actual[case["id"]]["safe_to_close"],
                case["safe_to_close"],
                case["id"],
            )

        metrics = classifier.summarize_against_ground_truth(
            self.fixture["cases"], results
        )
        self.assertEqual(metrics["mismatched_disposition"], 0)
        self.assertEqual(metrics["false_close"], 0)
        self.assertEqual(metrics["protected_experiment_loss"], 0)
        self.assertEqual(metrics["dependency_break"], 0)
        self.assertEqual(metrics["known_terminal_left_active"], 0)

    def test_input_order_does_not_change_results(self) -> None:
        forward = self.classify()
        reverse = self.classify(list(reversed(self.fixture["cases"])))
        self.assertEqual(forward, reverse)

    def test_similarity_and_inactivity_metadata_have_zero_close_authority(self) -> None:
        cases = copy.deepcopy(self.fixture["cases"])
        target = next(case for case in cases if case["id"] == "active-canonical-discovery")
        target["similarity_score"] = 1.0
        target["inactive_days"] = 10000

        actual = {result["id"]: result for result in self.classify(cases)}
        self.assertEqual(actual[target["id"]]["disposition"], "ACTIVE_CANONICAL")
        self.assertFalse(actual[target["id"]]["safe_to_close"])

    def test_partial_integration_unique_obligation_remains_active(self) -> None:
        actual = {result["id"]: result for result in self.classify()}
        result = actual["partial-integration-with-unique-obligation"]
        self.assertEqual(result["disposition"], "ACTIVE_CANONICAL")
        self.assertFalse(result["safe_to_close"])

    def test_protected_evidence_wins_over_accepted_superseding_decision(self) -> None:
        actual = {result["id"]: result for result in self.classify()}
        for item_id in (
            "protected-chassis-spike-a",
            "protected-chassis-spike-b",
            "protected-chassis-spike-c",
        ):
            self.assertEqual(actual[item_id]["disposition"], "PROTECTED_EVIDENCE")
            self.assertFalse(actual[item_id]["safe_to_close"])

    def test_dependency_predecessor_cannot_be_terminally_disposed(self) -> None:
        actual = {result["id"]: result for result in self.classify()}
        result = actual["stack-parent-runtime-contract"]
        self.assertEqual(result["disposition"], "ACTIVE_CANONICAL")
        self.assertFalse(result["safe_to_close"])

    def test_unknown_blocker_does_not_gain_external_blocker_authority(self) -> None:
        case = {
            "id": "unknown-blocker-case",
            "kind": "ISSUE",
            "obligations": ["still-valid-obligation"],
            "dependencies": [],
            "blocked_by": "caller-declared-blocker",
            "protected": False,
            "canonical_owner": "unknown-blocker-case",
            "superseded_by": None,
        }
        result = self.classify([case])[0]
        self.assertEqual(result["disposition"], "ACTIVE_CANONICAL")
        self.assertFalse(result["safe_to_close"])

    def test_absorption_requires_complete_obligation_containment(self) -> None:
        cases = [
            {
                "id": "old",
                "kind": "PR",
                "obligations": ["x", "unique-y"],
                "dependencies": [],
                "blocked_by": None,
                "protected": False,
                "canonical_owner": "new",
                "superseded_by": "new",
            },
            {
                "id": "new",
                "kind": "PR",
                "obligations": ["x"],
                "dependencies": [],
                "blocked_by": None,
                "protected": False,
                "canonical_owner": "new",
                "superseded_by": None,
            },
        ]
        actual = {result["id"]: result for result in self.classify(cases)}
        self.assertEqual(actual["old"]["disposition"], "ACTIVE_CANONICAL")
        self.assertFalse(actual["old"]["safe_to_close"])

    def test_satisfied_authority_is_docs_only_and_fails_closed_otherwise(self) -> None:
        authority = copy.deepcopy(self.authority)
        authority["satisfied_item_ids"].append("active-canonical-discovery")
        with self.assertRaises(classifier.ClassificationError):
            self.classify(authority=authority)

    def test_duplicate_item_ids_fail_closed(self) -> None:
        cases = copy.deepcopy(self.fixture["cases"])
        cases.append(copy.deepcopy(cases[0]))
        with self.assertRaises(classifier.ClassificationError):
            self.classify(cases)

    def test_module_exposes_no_repository_mutation_actions(self) -> None:
        forbidden = {
            "close_issue",
            "merge_pull_request",
            "delete_branch",
            "update_issue",
            "update_pull_request",
            "push",
        }
        self.assertTrue(forbidden.isdisjoint(classifier.__dict__))


if __name__ == "__main__":
    unittest.main()
