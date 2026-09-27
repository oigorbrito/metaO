from __future__ import annotations

import json
from io import StringIO
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from metao.entrypoint import main
from metao.runtime_factory import (
    RUNTIME_CERTIFICATION_DB_ENV,
    RUNTIME_CERTIFICATION_REVOCATION_DB_ENV,
    RUNTIME_CONTROL_DB_ENV,
)


class RuntimeCommandStoreIsolationTests(unittest.TestCase):
    @staticmethod
    def run_cli(*args: str) -> tuple[int, str, str]:
        stdout = StringIO()
        stderr = StringIO()
        code = main(args, stdout=stdout, stderr=stderr)
        return code, stdout.getvalue(), stderr.getvalue()

    def test_runtime_history_ignores_unrelated_certificate_stores(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            control_db = root / "control.db"
            certification_dir = root / "certification-is-a-directory"
            revocation_dir = root / "revocation-is-a-directory"
            certification_dir.mkdir()
            revocation_dir.mkdir()
            env = {
                RUNTIME_CONTROL_DB_ENV: str(control_db),
                RUNTIME_CERTIFICATION_DB_ENV: str(certification_dir),
                RUNTIME_CERTIFICATION_REVOCATION_DB_ENV: str(revocation_dir),
            }
            with patch.dict("os.environ", env, clear=False):
                code, out, err = self.run_cli("runtime-history", "runtime-a")

        self.assertEqual(code, 0)
        self.assertEqual(err, "")
        self.assertEqual(json.loads(out), [])

    def test_runtime_certificates_ignores_unrelated_control_store(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            control_dir = root / "control-is-a-directory"
            control_dir.mkdir()
            certification_db = root / "certification.db"
            revocation_db = root / "revocation.db"
            env = {
                RUNTIME_CONTROL_DB_ENV: str(control_dir),
                RUNTIME_CERTIFICATION_DB_ENV: str(certification_db),
                RUNTIME_CERTIFICATION_REVOCATION_DB_ENV: str(revocation_db),
            }
            with patch.dict("os.environ", env, clear=False):
                code, out, err = self.run_cli("runtime-certificates", "runtime-a")

        self.assertEqual(code, 0)
        self.assertEqual(err, "")
        self.assertEqual(json.loads(out), [])

    def test_runtime_certificate_revocations_ignores_other_stores(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            control_dir = root / "control-is-a-directory"
            certification_dir = root / "certification-is-a-directory"
            control_dir.mkdir()
            certification_dir.mkdir()
            revocation_db = root / "revocation.db"
            env = {
                RUNTIME_CONTROL_DB_ENV: str(control_dir),
                RUNTIME_CERTIFICATION_DB_ENV: str(certification_dir),
                RUNTIME_CERTIFICATION_REVOCATION_DB_ENV: str(revocation_db),
            }
            with patch.dict("os.environ", env, clear=False):
                code, out, err = self.run_cli(
                    "runtime-certificate-revocations",
                    "runtime-a",
                )

        self.assertEqual(code, 0)
        self.assertEqual(err, "")
        self.assertEqual(json.loads(out), [])


if __name__ == "__main__":
    unittest.main(verbosity=2)
