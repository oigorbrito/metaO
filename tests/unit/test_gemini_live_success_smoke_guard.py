from __future__ import annotations

import unittest

from scripts import gemini_live_success_smoke as smoke


class GeminiLiveSuccessSmokeGuardTests(unittest.TestCase):
    def test_missing_authorization_fails_before_key_use(self) -> None:
        with self.assertRaisesRegex(RuntimeError, "explicit Gemini live-success authorization"):
            smoke.require_authorization({smoke.API_KEY_ENV: "secret-value"})

    def test_wrong_authorization_fails_closed(self) -> None:
        with self.assertRaisesRegex(RuntimeError, "explicit Gemini live-success authorization"):
            smoke.require_authorization(
                {
                    smoke.AUTHORIZATION_ENV: "yes",
                    smoke.API_KEY_ENV: "secret-value",
                }
            )

    def test_missing_key_fails_after_exact_authorization(self) -> None:
        with self.assertRaisesRegex(RuntimeError, "METAO_GEMINI_API_KEY is required"):
            smoke.require_authorization(
                {smoke.AUTHORIZATION_ENV: smoke.AUTHORIZATION_PHRASE}
            )

    def test_exact_authorization_returns_key_without_transforming_it(self) -> None:
        key = "provider-secret-sentinel"
        self.assertEqual(
            smoke.require_authorization(
                {
                    smoke.AUTHORIZATION_ENV: smoke.AUTHORIZATION_PHRASE,
                    smoke.API_KEY_ENV: key,
                }
            ),
            key,
        )

    def test_target_is_fixed_to_free_tier_gemma4_model(self) -> None:
        self.assertEqual(smoke.TARGET, "gemma-4-26b-a4b-it")
        self.assertEqual(smoke.BASE_URL, "https://generativelanguage.googleapis.com/v1")

    def test_authorization_phrase_is_deliberately_specific(self) -> None:
        self.assertEqual(
            smoke.AUTHORIZATION_PHRASE,
            "I_AUTHORIZE_GEMINI_GEMMA4_ZERO_COST_SUCCESS_SMOKE",
        )


if __name__ == "__main__":
    unittest.main()
