import json
from pathlib import Path
import unittest

from scripts.validate_scientific_validation_matrix import (
    validate_matrix,
    validate_receipt,
)

ROOT = Path(__file__).resolve().parents[2]
MATRIX = json.loads(
    (ROOT / "docs/scientific-validation-matrix.json").read_text(encoding="utf-8")
)


def receipt(**overrides):
    value = {
        "schema": "metao-scientific-gate-receipt-v1",
        "repository": "oigorbrito/metaO",
        "commit": "a" * 40,
        "gate_id": "T7",
        "gate_level": "L4",
        "runtime_identities": ["runtime-a:v1", "runtime-b:v1"],
        "runtime_substrate": {"mode": "SIMULATED", "runtimes": ["runtime-a", "runtime-b"]},
        "mission_lineage": ["mission-1", "execution-1"],
        "commands": ["python -m unittest tests.unit.test_example"],
        "environment": {"os": "linux", "python": "3.13"},
        "started_at": "2026-09-28T00:00:00Z",
        "ended_at": "2026-09-28T00:00:01Z",
        "duration_seconds": 1.0,
        "result": "PASS",
        "failure_reason": None,
        "evidence_ids": ["artifact:test-log"],
        "external_systems": {"mode": "SIMULATED", "systems": ["local-fence-service"]},
    }
    value.update(overrides)
    return value


class ScientificValidationMatrixTests(unittest.TestCase):
    def test_matrix_contains_exact_t1_to_t15_registry(self):
        self.assertEqual(validate_matrix(MATRIX), [])

    def test_valid_receipt_preserves_simulated_substrate(self):
        self.assertEqual(validate_receipt(receipt(), MATRIX), [])

    def test_blocked_is_not_pass_and_requires_reason(self):
        errors = validate_receipt(
            receipt(result="BLOCKED", failure_reason="runner unavailable"),
            MATRIX,
        )
        self.assertEqual(errors, [])

        errors = validate_receipt(
            receipt(result="BLOCKED", failure_reason=""),
            MATRIX,
        )
        self.assertIn("BLOCKED receipt requires failure_reason", errors)

    def test_real_runtime_substrate_requires_named_runtime(self):
        errors = validate_receipt(
            receipt(runtime_substrate={"mode": "REAL", "runtimes": []}),
            MATRIX,
        )
        self.assertIn("REAL runtime substrate requires named runtimes", errors)

    def test_real_runtime_can_coexist_with_no_external_system(self):
        self.assertEqual(
            validate_receipt(
                receipt(
                    runtime_substrate={
                        "mode": "REAL",
                        "runtimes": ["langgraph-real:1.2.11", "crewai-real:1.15.16"],
                    },
                    external_systems={"mode": "NONE", "systems": []},
                ),
                MATRIX,
            ),
            [],
        )

    def test_real_mode_requires_named_external_system(self):
        errors = validate_receipt(
            receipt(external_systems={"mode": "REAL", "systems": []}),
            MATRIX,
        )
        self.assertIn("REAL external mode requires named systems", errors)

    def test_unknown_family_or_level_fails_closed(self):
        errors = validate_receipt(receipt(gate_id="T99", gate_level="L8"), MATRIX)
        self.assertIn("receipt gate_id is not registered in T1..T15", errors)
        self.assertIn("invalid gate_level", errors)


if __name__ == "__main__":
    unittest.main()
