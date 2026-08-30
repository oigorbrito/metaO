from __future__ import annotations

import importlib.util
import json
import os
import subprocess
import tempfile
import unittest
from pathlib import Path

MODULE_PATH = Path(__file__).resolve().parents[2] / "scripts" / "engineering_state_report.py"
SPEC = importlib.util.spec_from_file_location("engineering_state_report", MODULE_PATH)
assert SPEC is not None and SPEC.loader is not None
reporter = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(reporter)


def run_git(repo: Path, *args: str) -> str:
    completed = subprocess.run(
        ["git", *args],
        cwd=repo,
        check=True,
        text=True,
        encoding="utf-8",
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )
    return completed.stdout.strip()


class EngineeringStateReportTests(unittest.TestCase):
    def setUp(self) -> None:
        self.tempdir = tempfile.TemporaryDirectory()
        self.repo = Path(self.tempdir.name)
        run_git(self.repo, "init")
        run_git(self.repo, "config", "user.email", "fixture@example.invalid")
        run_git(self.repo, "config", "user.name", "Fixture User")
        (self.repo / "tracked.txt").write_text("baseline\n", encoding="utf-8")
        run_git(self.repo, "add", "tracked.txt")
        run_git(self.repo, "commit", "-m", "fixture baseline")

    def tearDown(self) -> None:
        self.tempdir.cleanup()

    def test_clean_then_dirty_changed_paths_are_factual(self) -> None:
        clean = reporter.build_report(self.repo)
        self.assertTrue(clean["baseline"]["clean"])
        self.assertEqual(clean["baseline"]["changed_paths"], [])
        self.assertEqual(len(clean["baseline"]["head"]), 40)

        (self.repo / "tracked.txt").write_text("changed\n", encoding="utf-8")
        (self.repo / "untracked.txt").write_text("new\n", encoding="utf-8")
        dirty = reporter.build_report(self.repo)
        self.assertFalse(dirty["baseline"]["clean"])
        self.assertEqual(
            dirty["baseline"]["changed_paths"],
            ["tracked.txt", "untracked.txt"],
        )

    def test_document_drift_current_stale_and_no_marker(self) -> None:
        head = run_git(self.repo, "rev-parse", "HEAD")
        (self.repo / "current.md").write_text(f"status\nHEAD = {head}\n", encoding="utf-8")
        (self.repo / "stale.md").write_text(f"HEAD = {'0' * 40}\n", encoding="utf-8")
        (self.repo / "nomarker.md").write_text("no embedded commit\n", encoding="utf-8")

        report = reporter.build_report(
            self.repo,
            documents=["current.md", "stale.md", "nomarker.md", "missing.md"],
        )
        states = {entry["path"]: entry["state"] for entry in report["document_drift"]}
        self.assertEqual(states["current.md"], "CURRENT")
        self.assertEqual(states["stale.md"], "STALE")
        self.assertEqual(states["nomarker.md"], "NO_MARKER")
        self.assertEqual(states["missing.md"], "MISSING")

    def test_evidence_states_are_preserved_without_promotion(self) -> None:
        facts = [
            reporter.TestFact("cargo", "NOT_RUN"),
            reporter.TestFact("hosted", "BLOCKED"),
            reporter.TestFact("fixture", "PASS"),
            reporter.TestFact("optional", "NOT_REQUESTED"),
            reporter.TestFact("selected-no-env", "SKIPPED"),
            reporter.TestFact("negative", "FAIL"),
        ]
        report = reporter.build_report(self.repo, test_facts=facts)
        states = {entry["test_id"]: entry["state"] for entry in report["tests"]}
        self.assertEqual(
            set(states.values()),
            {"NOT_RUN", "BLOCKED", "PASS", "NOT_REQUESTED", "SKIPPED", "FAIL"},
        )
        self.assertFalse(report["authority_boundary"]["test_state_promotion"])
        self.assertFalse(report["authority_boundary"]["product_acceptance"])

    def test_invalid_evidence_state_fails_closed(self) -> None:
        with self.assertRaises(reporter.ReportError):
            reporter.build_report(
                self.repo,
                test_facts=[reporter.TestFact("bad", "ACCEPTED")],
            )

    def test_blockers_are_data_and_sorted(self) -> None:
        blockers = [
            reporter.BlockerFact("z", "BLOCKED_EXTERNAL", "runner unavailable"),
            reporter.BlockerFact("a", "BLOCKED_TOOLCHAIN", "linker unavailable"),
        ]
        report = reporter.build_report(self.repo, blockers=blockers)
        self.assertEqual(
            [entry["blocker_id"] for entry in report["blockers"]],
            ["a", "z"],
        )
        self.assertEqual(report["handoff"]["blockers"], report["blockers"])

    def test_environment_secret_is_not_copied_to_output(self) -> None:
        key = "METAO_TEST_SECRET_SHOULD_NOT_APPEAR"
        previous = os.environ.get(key)
        os.environ[key] = "sentinel-secret-value"
        try:
            serialized = json.dumps(reporter.build_report(self.repo), sort_keys=True)
        finally:
            if previous is None:
                os.environ.pop(key, None)
            else:
                os.environ[key] = previous
        self.assertNotIn(key, serialized)
        self.assertNotIn("sentinel-secret-value", serialized)

    def test_report_is_deterministic_for_unchanged_repository(self) -> None:
        first = json.dumps(reporter.build_report(self.repo), sort_keys=True, separators=(",", ":"))
        second = json.dumps(reporter.build_report(self.repo), sort_keys=True, separators=(",", ":"))
        self.assertEqual(first, second)

    def test_document_path_cannot_escape_repository(self) -> None:
        with self.assertRaises(reporter.ReportError):
            reporter.build_report(self.repo, documents=["../outside.md"])


if __name__ == "__main__":
    unittest.main()
