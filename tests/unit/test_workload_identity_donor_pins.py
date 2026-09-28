import json
from pathlib import Path
import unittest

from scripts.validate_workload_identity_donors import (
    EXPECTED_SPIFFE_PATHS,
    EXPECTED_SPIFFE_REVISION,
    EXPECTED_SPIRE_COMMIT,
    EXPECTED_SPIRE_PATHS,
    validate_manifest,
    validate_product_dependencies,
)

ROOT = Path(__file__).resolve().parents[2]
MANIFEST = ROOT / "docs/workload-identity-spiffe-spire-donors.json"


class WorkloadIdentityDonorPinTests(unittest.TestCase):
    def manifest(self):
        return json.loads(MANIFEST.read_text(encoding="utf-8"))

    def test_exact_spiffe_and_spire_paths_are_pinned(self):
        data = self.manifest()
        self.assertEqual(validate_manifest(data), [])
        self.assertEqual(data["spiffe"]["revision"], EXPECTED_SPIFFE_REVISION)
        self.assertEqual(
            {item["path"]: item["blob_sha"] for item in data["spiffe"]["reference_paths"]},
            EXPECTED_SPIFFE_PATHS,
        )
        self.assertEqual(data["spire"]["release_commit"], EXPECTED_SPIRE_COMMIT)
        self.assertEqual(
            {item["path"]: item["blob_sha"] for item in data["spire"]["reference_paths"]},
            EXPECTED_SPIRE_PATHS,
        )

    def test_identity_reference_donors_are_not_product_dependencies(self):
        pyproject = (ROOT / "pyproject.toml").read_text(encoding="utf-8")
        self.assertEqual(validate_product_dependencies(pyproject), [])

    def test_identity_fact_cannot_become_policy_authority(self):
        authority = self.manifest()["authority_boundary"]
        self.assertFalse(authority["spiffe_identity_is_policy_authority"])
        self.assertTrue(authority["metao_policy_authority_remains_authoritative"])

    def test_caller_trust_root_and_dev_promotion_are_fail_closed(self):
        authority = self.manifest()["authority_boundary"]
        self.assertFalse(authority["caller_supplied_trust_root_allowed"])
        self.assertFalse(authority["dev_identity_can_claim_production_attestation"])
        self.assertFalse(authority["spire_runtime_dependency_in_core"])

    def test_real_spire_execution_is_not_claimed(self):
        data = self.manifest()
        self.assertFalse(data["real_spire_execution"])
        self.assertTrue(data["remaining_external_evidence"])


if __name__ == "__main__":
    unittest.main()
