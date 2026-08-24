import importlib
import importlib.util
from pathlib import Path
import unittest


class BlockNReleaseReadinessAcceptance(unittest.TestCase):
    def test_current_foundation_core_and_durable_boundary_import(self):
        self.assertIsNotNone(importlib.import_module("metao.core"))
        self.assertIsNotNone(importlib.import_module("metao.durable"))
        self.assertIsNotNone(importlib.import_module("metao.adapters.conductor_http"))

    def test_all_critical_control_plane_modules_are_present(self):
        required = (
            "metao.runtime",
            "metao.strategy",
            "metao.replan",
            "metao.acceptance",
            "metao.governance",
            "metao.security",
        )
        missing = [name for name in required if importlib.util.find_spec(name) is None]
        self.assertEqual(missing, [], f"missing critical modules: {missing}")

    def test_two_real_orchestrator_adapters_are_present(self):
        required = ("metao.adapters.langgraph", "metao.adapters.crewai")
        missing = [name for name in required if importlib.util.find_spec(name) is None]
        self.assertEqual(missing, [], f"missing orchestrator adapters: {missing}")

    def test_public_operator_entrypoints_exist(self):
        metao = importlib.import_module("metao")
        for name in ("run", "status", "inspect", "cancel", "resume"):
            self.assertTrue(hasattr(metao, name), f"missing public entrypoint: {name}")

    def test_release_readiness_and_quickstart_documentation_exist(self):
        readiness = Path("docs/RELEASE-READINESS.md")
        readme = Path("README.md")
        self.assertTrue(readiness.exists(), "docs/RELEASE-READINESS.md missing")
        self.assertIn("quickstart", readme.read_text(encoding="utf-8").lower())


if __name__ == "__main__":
    unittest.main()
