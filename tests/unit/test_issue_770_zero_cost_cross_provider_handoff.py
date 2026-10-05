from __future__ import annotations

import hashlib
import tempfile
import unittest
from pathlib import Path

from scripts import run_b6_zero_cost_cross_provider_handoff as handoff


class B6ZeroCostCrossProviderHandoffGuardTests(unittest.TestCase):
    def test_missing_authorization_fails_before_key_use(self) -> None:
        with self.assertRaisesRegex(RuntimeError, "explicit zero-cost B6 cross-provider authorization"):
            handoff.require_authorization({handoff.API_KEY_ENV: "secret-value"})

    def test_wrong_authorization_fails_closed(self) -> None:
        with self.assertRaisesRegex(RuntimeError, "explicit zero-cost B6 cross-provider authorization"):
            handoff.require_authorization(
                {
                    handoff.AUTHORIZATION_ENV: "yes",
                    handoff.API_KEY_ENV: "secret-value",
                }
            )

    def test_missing_key_fails_after_exact_authorization(self) -> None:
        with self.assertRaisesRegex(RuntimeError, "METAO_GEMINI_API_KEY is required"):
            handoff.require_authorization(
                {handoff.AUTHORIZATION_ENV: handoff.AUTHORIZATION_PHRASE}
            )

    def test_exact_authorization_returns_key_unchanged(self) -> None:
        key = "provider-secret-sentinel"
        self.assertEqual(
            handoff.require_authorization(
                {
                    handoff.AUTHORIZATION_ENV: handoff.AUTHORIZATION_PHRASE,
                    handoff.API_KEY_ENV: key,
                }
            ),
            key,
        )

    def test_checkpoint_binding_is_exact(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "handoff.txt"
            path.write_text(handoff.EXPECTED_SOURCE, encoding="utf-8")
            data, digest = handoff.validate_checkpoint(path)

        self.assertEqual(data, handoff.EXPECTED_SOURCE)
        self.assertEqual(
            digest,
            hashlib.sha256(handoff.EXPECTED_SOURCE.encode("utf-8")).hexdigest(),
        )

    def test_checkpoint_mismatch_fails_closed(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "handoff.txt"
            path.write_text(
                "METAO_HANDOFF_VERSION=1\nCODEX_LEG=ALTERED\n",
                encoding="utf-8",
            )
            with self.assertRaisesRegex(RuntimeError, "checkpoint content mismatch"):
                handoff.validate_checkpoint(path)

    def test_destination_is_fixed_to_zero_cost_gemma_target(self) -> None:
        self.assertEqual(handoff.TARGET, "gemma-4-26b-a4b-it")
        self.assertEqual(
            handoff.AUTHORIZATION_PHRASE,
            "I_AUTHORIZE_B6_ZERO_COST_CROSS_PROVIDER_HANDOFF",
        )

    def test_continuation_binds_exact_source_commit_and_digest(self) -> None:
        digest = "a" * 64
        self.assertEqual(
            handoff.expected_continuation(digest),
            (
                "METAO_GOOGLE_LEG=COMPLETE\n"
                f"PARENT_SHA={handoff.SOURCE_COMMIT}\n"
                f"SOURCE_SHA256={digest}"
            ),
        )


if __name__ == "__main__":
    unittest.main()
