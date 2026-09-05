"""Temporary bootstrap gate for the Roadmap 6 runner-context fix.

GitHub validates pull-request workflow definitions from the default branch. This
branch-scoped test proves the same real Codex binary smoke through canonical CI
while the corrected Roadmap 6 definition is being bootstrapped. It must be
removed after the corrected workflow is canonical and has qualified itself.
"""

from __future__ import annotations

import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest


_QUALIFICATION_BRANCH = "post-mvp/codex-smoke-canonicalization-cleanup-v2"
_CODEX_VERSION = "0.153.3"


class CodexRealBinarySmokeGateTests(unittest.TestCase):
    def test_real_codex_app_server_binary_smoke(self) -> None:
        if os.environ.get("GITHUB_HEAD_REF") != _QUALIFICATION_BRANCH:
            self.skipTest("real Codex binary smoke runs only on its qualification branch")

        npm = shutil.which("npm")
        self.assertIsNotNone(npm, "npm is required for the pinned Codex binary smoke")

        with tempfile.TemporaryDirectory(prefix="metao-codex-smoke-") as temp_dir:
            root = Path(temp_dir)
            prefix = root / "npm"
            codex_home = root / "codex-home"
            codex_home.mkdir(parents=True, exist_ok=True)

            install = subprocess.run(
                [
                    str(npm),
                    "install",
                    "--prefix",
                    str(prefix),
                    "--no-audit",
                    "--no-fund",
                    f"@openai/codex@{_CODEX_VERSION}",
                ],
                cwd=Path.cwd(),
                capture_output=True,
                text=True,
                timeout=180,
                check=False,
            )
            self.assertEqual(
                install.returncode,
                0,
                msg=(
                    "failed to install pinned real Codex CLI\n"
                    f"stdout:\n{install.stdout[-4000:]}\n"
                    f"stderr:\n{install.stderr[-4000:]}"
                ),
            )

            bin_dir = prefix / "node_modules" / ".bin"
            codex = bin_dir / ("codex.cmd" if os.name == "nt" else "codex")
            self.assertTrue(codex.exists(), f"Codex executable missing at {codex}")

            version = subprocess.run(
                [str(codex), "--version"],
                cwd=Path.cwd(),
                capture_output=True,
                text=True,
                timeout=30,
                check=False,
            )
            self.assertEqual(version.returncode, 0, msg=version.stderr)
            self.assertIn(_CODEX_VERSION, version.stdout + version.stderr)

            env = os.environ.copy()
            env["PATH"] = str(bin_dir) + os.pathsep + env.get("PATH", "")
            env["CODEX_HOME"] = str(codex_home)
            env["OPENAI_API_KEY"] = ""

            smoke = subprocess.run(
                [sys.executable, "scripts/codex_app_server_real_binary_smoke.py"],
                cwd=Path.cwd(),
                env=env,
                capture_output=True,
                text=True,
                timeout=60,
                check=False,
            )
            self.assertEqual(
                smoke.returncode,
                0,
                msg=(
                    "real Codex App Server smoke failed\n"
                    f"stdout:\n{smoke.stdout[-4000:]}\n"
                    f"stderr:\n{smoke.stderr[-4000:]}"
                ),
            )

            lines = [line for line in smoke.stdout.splitlines() if line.strip()]
            self.assertTrue(lines, "real Codex smoke emitted no evidence")
            evidence = json.loads(lines[-1])
            self.assertEqual(evidence["initialize"], "PASS")
            self.assertEqual(evidence["thread_start"], "PASS")
            self.assertIs(evidence["thread_ephemeral"], True)
            self.assertIs(evidence["thread_id_present"], True)
            self.assertIs(evidence["provider_turn_started"], False)
            self.assertEqual(evidence["provider_backed_execution"], "NOT_TESTED")
            self.assertIs(evidence["openai_api_key_present"], False)


if __name__ == "__main__":
    unittest.main()
