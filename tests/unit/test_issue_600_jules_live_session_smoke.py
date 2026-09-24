from __future__ import annotations

import os
import unittest
from unittest.mock import patch

from scripts.jules_live_session_smoke import _AUTHORIZATION, _authorized_api_key


class Issue600JulesLiveSessionSmokeTests(unittest.TestCase):
    def test_missing_authorization_fails_closed(self) -> None:
        with patch.dict(os.environ, {"METAO_JULES_API_KEY": "secret"}, clear=True):
            with self.assertRaises(SystemExit):
                _authorized_api_key()

    def test_wrong_authorization_fails_closed(self) -> None:
        with patch.dict(
            os.environ,
            {
                "METAO_JULES_SESSION_SMOKE_AUTHORIZATION": "wrong",
                "METAO_JULES_API_KEY": "secret",
            },
            clear=True,
        ):
            with self.assertRaises(SystemExit):
                _authorized_api_key()

    def test_missing_provider_key_fails_closed(self) -> None:
        with patch.dict(
            os.environ,
            {"METAO_JULES_SESSION_SMOKE_AUTHORIZATION": _AUTHORIZATION},
            clear=True,
        ):
            with self.assertRaises(SystemExit):
                _authorized_api_key()

    def test_exact_authorization_and_key_return_trimmed_key(self) -> None:
        with patch.dict(
            os.environ,
            {
                "METAO_JULES_SESSION_SMOKE_AUTHORIZATION": _AUTHORIZATION,
                "METAO_JULES_API_KEY": "  secret  ",
            },
            clear=True,
        ):
            self.assertEqual(_authorized_api_key(), "secret")


if __name__ == "__main__":
    unittest.main()
