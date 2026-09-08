from __future__ import annotations

import json
from io import StringIO
from pathlib import Path
import tempfile
import unittest

from metao.catalog import OrchestratorCatalog
from metao.core import OrchestratorRegistry
from metao.entrypoint import main
from metao.runtime_factory import RuntimeCatalogOperator


def valid_operator_factory(*, store):
    registry = OrchestratorRegistry()
    catalog = OrchestratorCatalog(registry)
    return RuntimeCatalogOperator(registry=registry, catalog=catalog, store=store)


class OperatorDoctorDatabasePathTests(unittest.TestCase):
    def test_existing_directory_is_not_a_valid_database_path(self) -> None:
        factory_spec = f"{__name__}:valid_operator_factory"
        with tempfile.TemporaryDirectory() as tmp:
            db_path = Path(tmp) / "db-path-is-a-directory"
            db_path.mkdir()
            stdout = StringIO()
            stderr = StringIO()

            code = main(
                ["--db", str(db_path), "doctor", "--factory", factory_spec],
                stdout=stdout,
                stderr=stderr,
            )

        self.assertEqual(code, 0)
        self.assertEqual(stderr.getvalue(), "")
        data = json.loads(stdout.getvalue())
        checks = {item["name"]: item for item in data["checks"]}
        self.assertEqual(data["overall_status"], "FAIL")
        self.assertEqual(checks["DATABASE_PATH"]["status"], "FAIL")
        self.assertEqual(
            checks["DATABASE_PATH"]["message"],
            "Database path is a directory",
        )
        self.assertEqual(checks["FACTORY_IMPORT"]["status"], "PASS")
        self.assertEqual(checks["OPERATOR_CONSTRUCTION"]["status"], "PASS")
        self.assertEqual(checks["RUNTIME_CATALOG"]["status"], "PASS")


if __name__ == "__main__":
    unittest.main(verbosity=2)
