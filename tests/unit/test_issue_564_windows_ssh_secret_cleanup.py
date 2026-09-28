from __future__ import annotations

import unittest
from pathlib import Path


WORKFLOW = Path(".github/workflows/project-multi-provider-pilot-windows-fenced.yml")


class WindowsSshSecretCleanupTests(unittest.TestCase):
    def test_cleanup_runs_on_all_terminal_paths(self) -> None:
        source = WORKFLOW.read_text(encoding="utf-8")
        cleanup = source[source.index("- name: Cleanup SSH verification files") :]
        self.assertIn("if: ${{ always() }}", cleanup)
        self.assertIn("$ErrorActionPreference = 'Stop'", cleanup)

    def test_cleanup_is_contained_and_uses_controlled_literal_paths(self) -> None:
        source = WORKFLOW.read_text(encoding="utf-8")
        cleanup = source[source.index("- name: Cleanup SSH verification files") :]
        self.assertIn("metao-pilot-known-hosts", cleanup)
        self.assertIn("metao-pilot-identity", cleanup)
        self.assertIn("$parent -ne $root", cleanup)
        self.assertIn("Remove-Item -LiteralPath $path", cleanup)
        self.assertNotIn("Remove-Item -Recurse", cleanup)


if __name__ == "__main__":
    unittest.main(verbosity=2)
