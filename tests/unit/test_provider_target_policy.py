from __future__ import annotations

import unittest

from scripts.provider_target_policy import validate_operational_provider_targets


class ProviderTargetPolicyTests(unittest.TestCase):
    def test_approved_operational_targets_are_accepted(self) -> None:
        approved = validate_operational_provider_targets(
            "gpt-5.6-luna",
            "gemma-4-26b-a4b-it",
        )
        self.assertEqual(approved.openai_model, "gpt-5.6-luna")
        self.assertEqual(approved.gemini_target, "gemma-4-26b-a4b-it")

    def test_unknown_openai_target_fails_closed(self) -> None:
        with self.assertRaisesRegex(RuntimeError, "OpenAI model is not approved"):
            validate_operational_provider_targets("experimental-model", "gemma-4-26b-a4b-it")

    def test_unknown_gemini_target_fails_closed(self) -> None:
        with self.assertRaisesRegex(RuntimeError, "Gemini target is not approved"):
            validate_operational_provider_targets("gpt-5.6-luna", "experimental-target")


if __name__ == "__main__":
    unittest.main()
