from __future__ import annotations

import importlib.util
import json
from pathlib import Path
import tempfile
import unittest


MODULE_PATH = Path(__file__).resolve().parents[2] / "scripts" / "validate_release_evidence.py"
SPEC = importlib.util.spec_from_file_location("validate_release_evidence", MODULE_PATH)
if SPEC is None or SPEC.loader is None:  # pragma: no cover
    raise RuntimeError(f"unable to load validator from {MODULE_PATH}")
validator = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(validator)

EXPECTED_COMMIT = "aa9e4e9a2aae73c693eb43a31c71f0801d80d7ea"
EXPECTED_BRANCH = "roadmap7/integration-candidate-v1"


def valid_evidence() -> dict:
    return {
        "schema_version": 1,
        "generated_at_utc": "2026-08-25T13:35:27+00:00",
        "branch": EXPECTED_BRANCH,
        "commit": EXPECTED_COMMIT,
        "clean_worktree": True,
        "python_version": "3.12.10",
        "runtime_pins": dict(validator.EXPECTED_RUNTIME_PINS),
        "hosted_runner_blocker": "external_pre_step_all_standard_hosted_os",
        "phase": "complete",
        "fatal_error": None,
        "results": [
            {
                "name": name,
                "status": "PASS",
                "exit_code": 0,
                "duration_seconds": 0.01,
                "detail": "",
            }
            for name in validator.EXPECTED_GATE_NAMES
        ],
        "failure_count": 0,
        "overall": "PASS",
    }


class ReleaseEvidenceValidatorTests(unittest.TestCase):
    def validate(self, evidence: object) -> list[str]:
        return validator.validate_evidence(
            evidence,
            expected_commit=EXPECTED_COMMIT,
            expected_branch=EXPECTED_BRANCH,
        )

    def test_valid_complete_pass_is_accepted(self):
        self.assertEqual(self.validate(valid_evidence()), [])

    def test_wrong_commit_fails_closed(self):
        evidence = valid_evidence()
        evidence["commit"] = "0" * 40
        errors = self.validate(evidence)
        self.assertTrue(any("commit mismatch" in error for error in errors))

    def test_missing_and_duplicate_gate_are_rejected(self):
        evidence = valid_evidence()
        evidence["results"][-1] = dict(evidence["results"][0])
        errors = self.validate(evidence)
        self.assertTrue(any("gate names must be unique" in error for error in errors))
        self.assertTrue(any("missing gates" in error for error in errors))

    def test_top_level_pass_cannot_hide_failed_gate(self):
        evidence = valid_evidence()
        evidence["results"][5]["status"] = "FAIL"
        evidence["results"][5]["exit_code"] = 1
        errors = self.validate(evidence)
        self.assertTrue(any("status must be 'PASS'" in error for error in errors))
        self.assertTrue(any("exit_code must be integer 0" in error for error in errors))

    def test_dirty_worktree_or_fatal_error_is_rejected(self):
        evidence = valid_evidence()
        evidence["clean_worktree"] = False
        evidence["fatal_error"] = "unexpected abort"
        errors = self.validate(evidence)
        self.assertIn("clean_worktree must be true", errors)
        self.assertTrue(any("fatal_error must be null" in error for error in errors))

    def test_boolean_failure_count_is_not_accepted_as_integer_zero(self):
        evidence = valid_evidence()
        evidence["failure_count"] = False
        errors = self.validate(evidence)
        self.assertTrue(any("failure_count must be integer 0" in error for error in errors))

    def test_utf8_bom_from_windows_powershell_is_supported(self):
        evidence = valid_evidence()
        with tempfile.TemporaryDirectory() as temp_dir:
            path = Path(temp_dir) / "gate.json"
            path.write_text(json.dumps(evidence), encoding="utf-8-sig")
            loaded = validator._load_json(path)
        self.assertEqual(loaded, evidence)


if __name__ == "__main__":
    unittest.main(verbosity=2)
