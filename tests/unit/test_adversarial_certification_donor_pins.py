import json
from pathlib import Path
import unittest

from scripts.validate_adversarial_certification_donors import (
    validate_manifest,
    validate_product_dependencies,
)

ROOT = Path(__file__).resolve().parents[2]
MANIFEST = ROOT / "docs/adversarial-certification-donors.json"


class AdversarialCertificationDonorPinsTests(unittest.TestCase):
    def manifest(self):
        return json.loads(MANIFEST.read_text(encoding="utf-8"))

    def test_pinned_manifest_is_complete(self):
        self.assertEqual(validate_manifest(self.manifest()), [])

    def test_evaluation_donors_are_not_product_runtime_dependencies(self):
        pyproject = (ROOT / "pyproject.toml").read_text(encoding="utf-8")
        self.assertEqual(validate_product_dependencies(pyproject), [])

    def test_missing_or_ambiguous_evidence_never_maps_to_pass(self):
        data = self.manifest()
        agentdojo = data["donors"]["agentdojo"]["normalization"]
        pyrit = data["donors"]["pyrit"]["normalization"]

        self.assertEqual(agentdojo["evaluator_or_api_error"], "EvaluatorError")
        self.assertEqual(agentdojo["omitted_category"], "NotRequested")
        self.assertEqual(agentdojo["unavailable_or_ambiguous_result"], "Unknown")
        self.assertEqual(pyrit["undetermined_score_or_outcome"], "Unknown")
        self.assertEqual(pyrit["evaluator_or_scorer_error"], "EvaluatorError")
        self.assertEqual(pyrit["omitted_category"], "NotRequested")

    def test_forbidden_objective_attack_success_maps_to_security_failure(self):
        pyrit = self.manifest()["donors"]["pyrit"]["normalization"]
        self.assertEqual(
            pyrit["attack_success_against_forbidden_objective"],
            "Fail",
        )

    def test_agentdojo_pin_is_bound_to_published_release_commit_and_hash(self):
        donor = self.manifest()["donors"]["agentdojo"]
        self.assertEqual(
            donor["release_commit"],
            "a75aba7631d3ca5fb7ab938965c97ead2f9ff84b",
        )
        self.assertEqual(donor["version"], "0.1.35")
        self.assertEqual(len(donor["artifacts"]["wheel_sha256"]), 64)


if __name__ == "__main__":
    unittest.main()
