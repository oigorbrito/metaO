from __future__ import annotations

import unittest
from pathlib import Path


WORKFLOW = Path(".github/workflows/project-multi-provider-pilot-windows-fenced.yml")
DISPATCH = Path("scripts/dispatch_metao_windows_multi_provider_pilot.ps1")


class WindowsProviderAllowlistTests(unittest.TestCase):
    def test_workflow_validates_targets_before_secret_bearing_steps(self) -> None:
        source = WORKFLOW.read_text(encoding="utf-8")
        gate = source[source.index("- name: Validate authorization audited target") :]
        self.assertIn("gpt-5.6-luna", gate)
        self.assertIn("gemma-4-26b-a4b-it", gate)
        first_secret = gate.index("METAO_OPENAI_API_KEY")
        self.assertLess(gate.index("gpt-5.6-luna"), first_secret)
        self.assertLess(gate.index("gemma-4-26b-a4b-it"), first_secret)

    def test_workflow_and_dispatch_helper_emit_allowlist_evidence(self) -> None:
        workflow = WORKFLOW.read_text(encoding="utf-8")
        dispatch = DISPATCH.read_text(encoding="utf-8")
        self.assertIn("provider_targets_approved", workflow)
        self.assertIn("operational_target_policy -ne 'ALLOWLISTED'", workflow)
        self.assertIn("provider_targets='ALLOWLISTED'", dispatch)
        self.assertIn("$OpenAIModel -ne 'gpt-5.6-luna'", dispatch)
        self.assertIn("$GeminiTarget -ne 'gemma-4-26b-a4b-it'", dispatch)


if __name__ == "__main__":
    unittest.main(verbosity=2)
