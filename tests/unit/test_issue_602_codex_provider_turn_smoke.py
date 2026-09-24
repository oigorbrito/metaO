from __future__ import annotations

import os
import unittest
from unittest.mock import patch

from scripts.codex_app_server_provider_turn_smoke import (
    _AUTHORIZATION,
    _require_authorized_environment,
)


class Issue602CodexProviderTurnSmokeTests(unittest.TestCase):
    def test_missing_authorization_fails_closed(self) -> None:
        with patch.dict(os.environ, {"OPENAI_API_KEY": "secret"}, clear=True):
            with self.assertRaises(SystemExit):
                _require_authorized_environment()

    def test_wrong_authorization_fails_closed(self) -> None:
        with patch.dict(
            os.environ,
            {
                "METAO_CODEX_TURN_SMOKE_AUTHORIZATION": "wrong",
                "OPENAI_API_KEY": "secret",
            },
            clear=True,
        ):
            with self.assertRaises(SystemExit):
                _require_authorized_environment()

    def test_missing_provider_key_fails_closed(self) -> None:
        with patch.dict(
            os.environ,
            {"METAO_CODEX_TURN_SMOKE_AUTHORIZATION": _AUTHORIZATION},
            clear=True,
        ):
            with self.assertRaises(SystemExit):
                _require_authorized_environment()

    def test_exact_authorization_and_key_are_accepted(self) -> None:
        with patch.dict(
            os.environ,
            {
                "METAO_CODEX_TURN_SMOKE_AUTHORIZATION": _AUTHORIZATION,
                "OPENAI_API_KEY": "secret",
            },
            clear=True,
        ):
            self.assertIsNone(_require_authorized_environment())


if __name__ == "__main__":
    unittest.main()
