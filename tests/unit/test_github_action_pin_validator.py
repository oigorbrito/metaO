from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from scripts.validate_github_action_pins import find_mutable_action_refs


class GithubActionPinValidatorTests(unittest.TestCase):
    def _scan(self, workflow: str) -> list[str]:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "ci.yml").write_text(workflow, encoding="utf-8")
            return find_mutable_action_refs(root)

    def test_accepts_full_commit_sha_and_local_actions(self) -> None:
        violations = self._scan(
            "steps:\n"
            "  - uses: actions/checkout@11d5960a326750d5838078e36cf38b85af677262 # v4\n"
            "  - uses: ./.github/actions/local\n"
        )
        self.assertEqual([], violations)

    def test_rejects_mutable_tag(self) -> None:
        violations = self._scan("steps:\n  - uses: actions/checkout@v4\n")
        self.assertEqual(1, len(violations))
        self.assertIn("mutable action ref", violations[0])

    def test_rejects_mutable_branch_for_third_party_action(self) -> None:
        violations = self._scan("steps:\n  - uses: dtolnay/rust-toolchain@stable\n")
        self.assertEqual(1, len(violations))
        self.assertIn("dtolnay/rust-toolchain@stable", violations[0])


if __name__ == "__main__":
    unittest.main()
