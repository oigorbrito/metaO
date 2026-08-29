from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[1]
CORPUS = ROOT / "golden" / "phase6_shadow_v1.json"
ORACLE = ROOT / "phase6_shadow_oracle.py"


def _run_oracle() -> list[dict]:
    completed = subprocess.run(
        [sys.executable, str(ORACLE), str(CORPUS)],
        check=True,
        capture_output=True,
        text=True,
    )
    return json.loads(completed.stdout)


def _strip_metrics(results: list[dict]) -> list[dict]:
    stripped = []
    for item in results:
        stripped.append(
            {
                "case_id": item["case_id"],
                "category": item["category"],
                "scenario": item["scenario"],
                "comparison_kind": item["comparison_kind"],
                "semantic": item["semantic"],
            }
        )
    return stripped


class Phase6DifferentialShadowMode(unittest.TestCase):
    def test_shadow_oracle_is_deterministic(self) -> None:
        first = _strip_metrics(_run_oracle())
        second = _strip_metrics(_run_oracle())
        self.assertEqual(first, second)

    def test_shadow_corpus_has_unique_case_ids(self) -> None:
        corpus = json.loads(CORPUS.read_text(encoding="utf-8"))
        case_ids = [case["case_id"] for case in corpus["cases"]]
        self.assertEqual(len(case_ids), len(set(case_ids)))
        self.assertGreater(len(case_ids), 0)


if __name__ == "__main__":
    unittest.main(verbosity=2)
