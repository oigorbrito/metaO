from __future__ import annotations

from io import StringIO
import json
from pathlib import Path
import tempfile
import unittest

from metao.entrypoint import main


def evidence_payload() -> dict:
    return {
        "evidence_id": "bench-1",
        "benchmark_id": "software-engineering",
        "benchmark_version": "v1",
        "task_set": "verified",
        "executor_id": "runtime-a",
        "executor_version": "1.0",
        "harness_id": "harness-a",
        "harness_version": "2.0",
        "model_id": "model-a",
        "provider_id": "provider-a",
        "model_version": "2026-09",
        "runtime_config_digest": "runtime-config-sha256",
        "tool_policy_digest": "tool-policy-sha256",
        "environment_id": "linux-container-v1",
        "observed_at_epoch": 100.0,
        "source": "METAO_REPRODUCED",
        "raw_result_ref": "artifact://run-1/results.json",
        "metrics": [{"name": "resolved_rate", "value": 0.72, "unit": "ratio"}],
    }


class BenchmarkEvidenceCliTests(unittest.TestCase):
    @staticmethod
    def invoke(argv):
        stdout = StringIO()
        stderr = StringIO()
        code = main(argv, stdout=stdout, stderr=stderr)
        return code, stdout.getvalue(), stderr.getvalue()

    def test_help_exposes_benchmark_evidence_commands(self):
        code, stdout, stderr = self.invoke(["--help"])
        self.assertEqual(code, 0, stderr)
        self.assertIn("benchmark-import", stdout)
        self.assertIn("runtime-benchmarks", stdout)

    def test_import_and_list_round_trip(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            db = root / "metao.db"
            evidence_file = root / "evidence.json"
            evidence_file.write_text(json.dumps(evidence_payload()), encoding="utf-8")

            code, stdout, stderr = self.invoke(
                ["--db", str(db), "benchmark-import", str(evidence_file)]
            )
            self.assertEqual(code, 0, stderr)
            imported = json.loads(stdout)
            self.assertEqual(imported["evidence_id"], "bench-1")
            self.assertEqual(imported["executor_id"], "runtime-a")
            self.assertEqual(imported["source"], "METAO_REPRODUCED")
            self.assertEqual(imported["metrics"][0]["name"], "resolved_rate")

            code, stdout, stderr = self.invoke(
                ["--db", str(db), "runtime-benchmarks", "runtime-a"]
            )

        self.assertEqual(code, 0, stderr)
        items = json.loads(stdout)
        self.assertEqual(len(items), 1)
        self.assertEqual(items[0]["benchmark_version"], "v1")

    def test_duplicate_import_is_idempotent(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            db = root / "metao.db"
            evidence_file = root / "evidence.json"
            evidence_file.write_text(json.dumps(evidence_payload()), encoding="utf-8")

            argv = ["--db", str(db), "benchmark-import", str(evidence_file)]
            self.assertEqual(self.invoke(argv)[0], 0)
            self.assertEqual(self.invoke(argv)[0], 0)
            code, stdout, stderr = self.invoke(
                ["--db", str(db), "runtime-benchmarks", "runtime-a"]
            )

        self.assertEqual(code, 0, stderr)
        self.assertEqual(len(json.loads(stdout)), 1)

    def test_conflicting_duplicate_fails_closed(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            db = root / "metao.db"
            evidence_file = root / "evidence.json"
            changed_file = root / "evidence-changed.json"
            evidence_file.write_text(json.dumps(evidence_payload()), encoding="utf-8")
            changed = evidence_payload()
            changed["metrics"][0]["value"] = 0.91
            changed_file.write_text(json.dumps(changed), encoding="utf-8")

            self.assertEqual(
                self.invoke(["--db", str(db), "benchmark-import", str(evidence_file)])[0],
                0,
            )
            code, stdout, stderr = self.invoke(
                ["--db", str(db), "benchmark-import", str(changed_file)]
            )

        self.assertEqual(code, 2)
        self.assertEqual(stdout, "")
        self.assertEqual(json.loads(stderr)["error"], "BenchmarkEvidenceConflict")


if __name__ == "__main__":
    unittest.main(verbosity=2)
