from __future__ import annotations

import json
from io import StringIO
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from metao.catalog import OrchestratorCatalog
from metao.core import OrchestratorRegistry
from metao.entrypoint import main
from metao.runtime_factory import (
    RUNTIME_CERTIFICATION_DB_ENV,
    RUNTIME_CERTIFICATION_REVOCATION_DB_ENV,
    RUNTIME_CONTROL_DB_ENV,
    RuntimeCatalogOperator,
)


def runtime_listing_factory(*, store):
    registry = OrchestratorRegistry()
    catalog = OrchestratorCatalog(registry)
    return RuntimeCatalogOperator(registry=registry, catalog=catalog, store=store)


class RuntimeListPreflightTests(unittest.TestCase):
    def test_runtimes_does_not_initialize_unconsumed_control_stores(self) -> None:
        factory_spec = f"{__name__}:runtime_listing_factory"
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            mission_db = root / "mission.db"
            invalid_control_db = root / "control-db-is-a-directory"
            invalid_certification_db = root / "certification-db-is-a-directory"
            invalid_revocation_db = root / "revocation-db-is-a-directory"
            invalid_control_db.mkdir()
            invalid_certification_db.mkdir()
            invalid_revocation_db.mkdir()

            env = {
                RUNTIME_CONTROL_DB_ENV: str(invalid_control_db),
                RUNTIME_CERTIFICATION_DB_ENV: str(invalid_certification_db),
                RUNTIME_CERTIFICATION_REVOCATION_DB_ENV: str(invalid_revocation_db),
            }
            stdout = StringIO()
            stderr = StringIO()
            with patch.dict("os.environ", env, clear=False):
                code = main(
                    ["--db", str(mission_db), "runtimes", "--factory", factory_spec],
                    stdout=stdout,
                    stderr=stderr,
                )

            self.assertEqual(code, 0)
            self.assertEqual(stderr.getvalue(), "")
            self.assertEqual(json.loads(stdout.getvalue()), [])
            self.assertTrue(invalid_control_db.is_dir())
            self.assertTrue(invalid_certification_db.is_dir())
            self.assertTrue(invalid_revocation_db.is_dir())
            self.assertEqual(list(invalid_control_db.iterdir()), [])
            self.assertEqual(list(invalid_certification_db.iterdir()), [])
            self.assertEqual(list(invalid_revocation_db.iterdir()), [])


if __name__ == "__main__":
    unittest.main(verbosity=2)
