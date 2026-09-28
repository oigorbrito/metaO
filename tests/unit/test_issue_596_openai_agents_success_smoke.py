from __future__ import annotations

import os
import unittest
from unittest.mock import patch

from scripts.openai_agents_live_success_smoke import (
    _AUTHORIZATION,
    _authorized_api_key,
)


class Issue596OpenAIAgentsSuccessSmokeTests(unittest.TestCase):
    def test_missing_authorization_fails_closed(self) -> None:
        with patch.dict(os.environ, {"METAO_OPENAI_API_KEY": "secret"}, clear=True):
            with self.assertRaises(SystemExit):
                _authorized_api_key()

    def test_wrong_authorization_fails_closed(self) -> None:
        with patch.dict(
            os.environ,
            {
                "METAO_OPENAI_AGENTS_SUCCESS_AUTHORIZATION": "wrong",
                "METAO_OPENAI_API_KEY": "secret",
            },
            clear=True,
        ):
            with self.assertRaises(SystemExit):
                _authorized_api_key()

    def test_missing_provider_key_fails_closed(self) -> None:
        with patch.dict(
            os.environ,
            {"METAO_OPENAI_AGENTS_SUCCESS_AUTHORIZATION": _AUTHORIZATION},
            clear=True,
        ):
            with self.assertRaises(SystemExit):
                _authorized_api_key()

    def test_exact_authorization_and_key_return_key_without_mutation(self) -> None:
        with patch.dict(
            os.environ,
            {
                "METAO_OPENAI_AGENTS_SUCCESS_AUTHORIZATION": _AUTHORIZATION,
                "METAO_OPENAI_API_KEY": "  secret  ",
            },
            clear=True,
        ):
            self.assertEqual(_authorized_api_key(), "secret")


if __name__ == "__main__":
    unittest.main()
