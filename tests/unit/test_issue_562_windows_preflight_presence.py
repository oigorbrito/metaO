from __future__ import annotations

import unittest
from pathlib import Path


WORKFLOW = Path(".github/workflows/project-multi-provider-pilot-windows-fenced.yml")
DISPATCH = Path("scripts/dispatch_metao_windows_multi_provider_pilot.ps1")


class WindowsPreflightPresenceTests(unittest.TestCase):
    def test_preflight_exposes_presence_flags_not_provider_key_values(self) -> None:
        source = WORKFLOW.read_text(encoding="utf-8")
        start = source.index("- name: Run no-provider-call Windows operational preflight")
        end = source.index("- name: Install audited metaO", start)
        preflight = source[start:end]
        self.assertIn("METAO_OPENAI_CREDENTIAL_PRESENT", preflight)
        self.assertIn("METAO_GEMINI_CREDENTIAL_PRESENT", preflight)
        self.assertNotIn("METAO_OPENAI_API_KEY:", preflight)
        self.assertNotIn("METAO_GEMINI_API_KEY:", preflight)
        self.assertIn("provider_credential_inputs -ne 'presence-only'", preflight)

    def test_dispatch_reports_presence_only_and_allowlisted_policy(self) -> None:
        source = DISPATCH.read_text(encoding="utf-8")
        self.assertIn("provider_preflight='PRESENCE_ONLY'", source)
        self.assertIn("provider_targets='ALLOWLISTED'", source)
        self.assertIn("$AuditedHead = 'fe2519044f89cdf0111b5e5118a056fce7524e8d'", source)


if __name__ == "__main__":
    unittest.main(verbosity=2)
