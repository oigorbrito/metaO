from __future__ import annotations

import unittest
from pathlib import Path


INSTALLER = Path("scripts/install_metao_self_hosted_runner.sh")


class LinuxRunnerInstallerRegistrationPolicyTests(unittest.TestCase):
    def test_first_install_does_not_use_replace_semantics(self) -> None:
        source = INSTALLER.read_text(encoding="utf-8")
        self.assertNotIn("--replace", source)
        self.assertIn('registration_mode":"first-install-no-replace', source)

    def test_remote_name_conflict_still_fails_closed(self) -> None:
        source = INSTALLER.read_text(encoding="utf-8")
        self.assertIn(
            '[[ -z "$remote_runner_json" ]] || fail "a GitHub runner named ${RUNNER_NAME} already exists but this install directory is not configured"',
            source,
        )

    def test_existing_matching_registration_remains_idempotent(self) -> None:
        source = INSTALLER.read_text(encoding="utf-8")
        self.assertIn('if [[ -f "${INSTALL_DIR}/.runner" ]]; then', source)
        self.assertIn('registration_mode":"existing-match', source)
        self.assertIn('sudo "${INSTALL_DIR}/svc.sh" start', source)


if __name__ == "__main__":
    unittest.main()
