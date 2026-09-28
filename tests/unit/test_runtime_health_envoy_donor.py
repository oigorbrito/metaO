import json
from pathlib import Path
import unittest

from scripts.validate_runtime_health_envoy_donor import (
    EXPECTED_COMMIT,
    EXPECTED_PATHS,
    validate_manifest,
    validate_product_dependencies,
)

ROOT = Path(__file__).resolve().parents[2]
MANIFEST = ROOT / "docs/runtime-health-envoy-donor.json"


class RuntimeHealthEnvoyDonorTests(unittest.TestCase):
    def manifest(self):
        return json.loads(MANIFEST.read_text(encoding="utf-8"))

    def test_exact_release_and_source_paths_are_pinned(self):
        data = self.manifest()
        self.assertEqual(validate_manifest(data), [])
        self.assertEqual(data["donor"]["release_commit"], EXPECTED_COMMIT)
        self.assertEqual(
            {item["path"]: item["blob_sha"] for item in data["donor"]["paths"]},
            EXPECTED_PATHS,
        )

    def test_envoy_does_not_become_product_dependency(self):
        pyproject = (ROOT / "pyproject.toml").read_text(encoding="utf-8")
        self.assertEqual(validate_product_dependencies(pyproject), [])

    def test_outlier_detection_is_reference_not_health_authority(self):
        fit = self.manifest()["metao_fit"]
        self.assertEqual(fit["outlier_detection"], "ADAPT_SEMANTICS")
        self.assertEqual(fit["health_as_acceptance_authority"], "REJECT")
        self.assertEqual(fit["envoy_specific_types_in_core"], "REJECT")

    def test_failure_origin_separation_is_explicit(self):
        paths = self.manifest()["donor"]["paths"]
        semantics = {
            value
            for item in paths
            for value in item["consumed_semantics"]
        }
        self.assertIn(
            "local-origin and externally-originated failure separation",
            semantics,
        )


if __name__ == "__main__":
    unittest.main()
