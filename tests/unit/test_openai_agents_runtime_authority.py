from __future__ import annotations

import hashlib
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from scripts.fetch_openai_agents_runtime_lock import git_blob_sha1, load_authority


class OpenAIAgentsRuntimeAuthorityTests(unittest.TestCase):
    def test_git_blob_sha1_matches_git_object_format(self) -> None:
        content = b"runtime-lock\n"
        expected = hashlib.sha1(b"blob 13\0" + content).hexdigest()
        self.assertEqual(expected, git_blob_sha1(content))

    def test_authority_requires_all_identity_fields(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "authority.json"
            path.write_text(json.dumps({"package": "openai-agents"}), encoding="utf-8")
            with self.assertRaises(SystemExit):
                load_authority(path)

    def test_repository_authority_has_expected_release_identity(self) -> None:
        authority = load_authority()
        self.assertEqual("openai-agents", authority["package"])
        self.assertEqual("0.20.0", authority["version"])
        self.assertEqual(
            "d2bda3f3110415bf02e526a3983b0d0fa903e0d7",
            authority["source_commit"],
        )
        self.assertEqual(
            "c092e351b5f7919c9972a335426e899d0bcb588f",
            authority["source_uv_lock_blob_sha1"],
        )
        self.assertEqual(
            "aaff662b802fa90762ad539e131b9ea387e12e3664b87bc75157ad1b3fc88850",
            authority["pypi_wheel_sha256"],
        )


if __name__ == "__main__":
    unittest.main()
