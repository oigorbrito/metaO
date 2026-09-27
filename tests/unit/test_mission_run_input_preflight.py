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


_FACTORY_CALLS = 0


def counting_operator_factory(*, store):
    global _FACTORY_CALLS
    _FACTORY_CALLS += 1
    registry = OrchestratorRegistry()
    catalog = OrchestratorCatalog(registry)
    return RuntimeCatalogOperator(registry=registry, catalog=catalog, store=store)


class MissionRunInputPreflightTests(unittest.TestCase):
    def test_invalid_json_precedes_persistence_and_factory_bootstrap(self) -> None:
        global _FACTORY_CALLS
        _FACTORY_CALLS = 0
        factory_spec = f"{__name__}:counting_operator_factory"

        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            mission_file = root / "invalid-mission.json"
            mission_file.write_text("{not-json", encoding="utf-8")
            db_path = root / "metao.db"
            stdout = StringIO()
            stderr = StringIO()

            code = main(
                [
                    "--db",
                    str(db_path),
                    "run",
                    str(mission_file),
                    "--factory",
                    factory_spec,
                ],
                stdout=stdout,
                stderr=stderr,
            )

            self.assertFalse(db_path.exists())

        self.assertEqual(code, 2)
        self.assertEqual(stdout.getvalue(), "")
        error = json.loads(stderr.getvalue())
        self.assertEqual(error["error"], "CLIInputError")
        self.assertIn("invalid mission JSON", error["message"])
        self.assertEqual(_FACTORY_CALLS, 0)


if __name__ == "__main__":
    unittest.main(verbosity=2)
