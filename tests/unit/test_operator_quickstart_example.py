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


def quickstart_operator_factory(*, store):
    registry = OrchestratorRegistry()
    catalog = OrchestratorCatalog(registry)
    return RuntimeCatalogOperator(registry=registry, catalog=catalog, store=store)


class OperatorQuickstartExampleTests(unittest.TestCase):
    def test_committed_quickstart_mission_runs_to_policy_block(self) -> None:
        repo_root = Path(__file__).resolve().parents[2]
        mission_file = repo_root / "examples" / "mission-policy-deny.json"
        self.assertTrue(mission_file.is_file())

        payload = json.loads(mission_file.read_text(encoding="utf-8"))
        self.assertEqual(
            set(payload),
            {"mission", "policy", "budget", "acceptance_context", "max_attempts"},
        )
        self.assertFalse(payload["policy"]["allowed"])
        self.assertFalse(payload["policy"]["require_human"])

        stdout = StringIO()
        stderr = StringIO()
        factory_spec = f"{__name__}:quickstart_operator_factory"
        with tempfile.TemporaryDirectory() as tmp:
            db_path = Path(tmp) / "metao.db"
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

        self.assertEqual(code, 0)
        self.assertEqual(stderr.getvalue(), "")
        result = json.loads(stdout.getvalue())
        self.assertEqual(result["mission_id"], "quickstart-policy-deny")
        self.assertEqual(result["status"], "BLOCKED")
        self.assertIsNone(result["orchestrator_id"])
        self.assertEqual(result["acceptance_decision"], "BLOCK")
        self.assertEqual(result["attempted_orchestrators"], [])


if __name__ == "__main__":
    unittest.main(verbosity=2)
