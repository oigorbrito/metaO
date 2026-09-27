from __future__ import annotations

import json
import subprocess
import sys
import unittest
from pathlib import Path

from metao.cutover import CapabilityAuthority, default_phase8_cutover_state


ROOT = Path(__file__).resolve().parents[1]
CORPUS = ROOT / "golden" / "phase6_shadow_v1.json"
ORACLE = ROOT / "phase6_shadow_oracle.py"


def _run_shadow_oracle() -> list[dict]:
    completed = subprocess.run(
        [sys.executable, str(ORACLE), str(CORPUS)],
        check=True,
        capture_output=True,
        text=True,
    )
    return json.loads(completed.stdout)


class Phase8RuntimeQualificationTests(unittest.TestCase):
    def test_runtime_is_rust_active_after_phase8_cutover(self) -> None:
        state = default_phase8_cutover_state()
        self.assertEqual(state.authority_for("runtime"), CapabilityAuthority.RUST_ACTIVE)
        self.assertEqual(state.authority_for("acceptance"), CapabilityAuthority.RUST_ACTIVE)
        self.assertEqual(state.authority_for("unknown_capability"), CapabilityAuthority.PYTHON)

    def test_runtime_rollback_is_idempotent_and_restores_python(self) -> None:
        state = default_phase8_cutover_state()
        rolled_back = state.rollback("runtime")
        self.assertEqual(rolled_back.authority_for("runtime"), CapabilityAuthority.PYTHON)
        self.assertEqual(rolled_back.rollback("runtime"), rolled_back)

    def test_sustained_parity_gate_uses_the_frozen_shadow_corpus(self) -> None:
        corpus = json.loads(CORPUS.read_text(encoding="utf-8"))
        results = _run_shadow_oracle()
        runtime_results = [case for case in results if case["category"] == "runtime"]
        comparable_results = [case for case in results if case["category"] != "runtime"]

        self.assertEqual(corpus["fixture_version"], 1)
        self.assertEqual(corpus["contract_version"], 1)
        self.assertEqual(len(corpus["cases"]), 44)
        self.assertEqual(len(comparable_results), 38)
        self.assertEqual(len(runtime_results), 6)
        self.assertTrue(all(case["case_id"].startswith("runtime.") for case in runtime_results))
        self.assertTrue(all(case["comparison_kind"] == "NOT_COMPARABLE" for case in runtime_results))


if __name__ == "__main__":
    unittest.main(verbosity=2)
