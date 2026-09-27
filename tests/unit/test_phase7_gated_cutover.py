from __future__ import annotations

import json
from pathlib import Path
import unittest

from metao.cutover import (
    CapabilityAuthority,
    CapabilityCutoverState,
    PHASE7_QUALIFIED_CAPABILITIES,
    PHASE7_SHADOW_CAPABILITIES,
    default_phase7_cutover_state,
)


ROOT = Path(__file__).resolve().parents[1]
CORPUS = ROOT / "golden" / "phase6_shadow_v1.json"


class Phase7GatedCutoverTests(unittest.TestCase):
    def test_audited_capabilities_follow_the_expected_authority_plan(self) -> None:
        state = default_phase7_cutover_state()

        promoted = state.promote_qualified()
        for capability in sorted(PHASE7_QUALIFIED_CAPABILITIES):
            self.assertEqual(promoted.authority_for(capability), CapabilityAuthority.RUST_ACTIVE)

        for capability in sorted(PHASE7_SHADOW_CAPABILITIES):
            self.assertEqual(promoted.authority_for(capability), CapabilityAuthority.RUST_SHADOW)

        self.assertEqual(
            promoted.authority_for("unqualified_capability"),
            CapabilityAuthority.PYTHON,
        )

    def test_unknown_capability_stays_python_authoritative(self) -> None:
        state = default_phase7_cutover_state()
        after_promote = state.promote("unqualified_capability")
        self.assertIs(after_promote, state)
        self.assertEqual(after_promote.authority_for("unqualified_capability"), CapabilityAuthority.PYTHON)

    def test_rollback_is_idempotent_and_restores_python(self) -> None:
        state = default_phase7_cutover_state().promote("acceptance")
        self.assertEqual(state.authority_for("acceptance"), CapabilityAuthority.RUST_ACTIVE)

        rolled_back = state.rollback("acceptance")
        self.assertEqual(rolled_back.authority_for("acceptance"), CapabilityAuthority.PYTHON)
        self.assertEqual(rolled_back.rollback("acceptance"), rolled_back)

    def test_corpus_case_ids_remain_stable(self) -> None:
        corpus = json.loads(CORPUS.read_text(encoding="utf-8"))
        case_ids = [case["case_id"] for case in corpus["cases"]]
        self.assertEqual(len(case_ids), len(set(case_ids)))
        self.assertEqual(len(case_ids), 44)


if __name__ == "__main__":
    unittest.main(verbosity=2)
