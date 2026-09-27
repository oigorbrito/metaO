from __future__ import annotations

import importlib.util
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

MODULE_PATH = Path(__file__).resolve().parents[2] / "scripts" / "engineering_state_report.py"
SPEC = importlib.util.spec_from_file_location("engineering_state_report_boundaries", MODULE_PATH)
assert SPEC is not None and SPEC.loader is not None
reporter = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = reporter
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


class EngineeringStateReportBoundaryTests(unittest.TestCase):
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

    def test_nul_path_parser_preserves_embedded_newlines(self) -> None:
        parsed = reporter._split_nul_paths("plain.txt\0line\nbreak.txt\0trailing space.txt\0")
        self.assertEqual(parsed, ["plain.txt", "line\nbreak.txt", "trailing space.txt"])

    def test_conflicting_document_head_markers_fail_closed(self) -> None:
        head = run_git(self.repo, "rev-parse", "HEAD")
        (self.repo / "conflict.md").write_text(
            f"HEAD = {head}\nHEAD = {'0' * 40}\n",
            encoding="utf-8",
        )
        with self.assertRaises(reporter.ReportError):
            reporter.build_report(self.repo, documents=["conflict.md"])

    def test_repeated_identical_head_marker_remains_unambiguous(self) -> None:
        head = run_git(self.repo, "rev-parse", "HEAD")
        (self.repo / "repeat.md").write_text(
            f"HEAD = {head}\nHEAD = {head}\n",
            encoding="utf-8",
        )
        report = reporter.build_report(self.repo, documents=["repeat.md"])
        self.assertEqual(report["document_drift"][0]["state"], "CURRENT")
        self.assertEqual(report["document_drift"][0]["recorded_head"], head)


if __name__ == "__main__":
    unittest.main()
