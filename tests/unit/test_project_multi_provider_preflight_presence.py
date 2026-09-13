from __future__ import annotations

import os
import unittest
from unittest.mock import patch

from scripts.project_multi_provider_preflight import _presence


class ProjectMultiProviderPreflightPresenceTests(unittest.TestCase):
    def test_presence_accepts_boolean_indicators(self) -> None:
        for raw in ("1", "true", "TRUE", "yes"):
            with self.subTest(raw=raw), patch.dict(os.environ, {"METAO_PRESENT": raw}, clear=False):
                self.assertTrue(_presence("METAO_PRESENT"))
        for raw in ("0", "false", "FALSE", "no", ""):
            with self.subTest(raw=raw), patch.dict(os.environ, {"METAO_PRESENT": raw}, clear=False):
                self.assertFalse(_presence("METAO_PRESENT"))

    def test_presence_rejects_non_boolean_secret_like_content(self) -> None:
        with patch.dict(os.environ, {"METAO_PRESENT": "sk-provider-secret"}, clear=False):
            with self.assertRaises(RuntimeError):
                _presence("METAO_PRESENT")


if __name__ == "__main__":
    unittest.main()
