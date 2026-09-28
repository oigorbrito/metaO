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
)


class RuntimeCertificatesInputPreflightTests(unittest.TestCase):
    def test_incomplete_freshness_pair_does_not_create_certificate_stores(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            certification_db = root / "certification.db"
            revocation_db = root / "revocation.db"
            env = {
                RUNTIME_CERTIFICATION_DB_ENV: str(certification_db),
                RUNTIME_CERTIFICATION_REVOCATION_DB_ENV: str(revocation_db),
            }
            stdout = StringIO()
            stderr = StringIO()

            with patch.dict("os.environ", env, clear=False):
                code = main(
                    [
                        "runtime-certificates",
                        "runtime-a",
                        "--now-epoch",
                        "10",
                    ],
                    stdout=stdout,
                    stderr=stderr,
                )

            self.assertFalse(certification_db.exists())
            self.assertFalse(revocation_db.exists())

        self.assertEqual(code, 2)
        self.assertEqual(stdout.getvalue(), "")
        error = json.loads(stderr.getvalue())
        self.assertEqual(error["error"], "CLIInputError")
        self.assertEqual(
            error["message"],
            "runtime-certificates freshness requires both --now-epoch and --max-age-seconds",
        )


if __name__ == "__main__":
    unittest.main(verbosity=2)
