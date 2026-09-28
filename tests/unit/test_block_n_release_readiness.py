import importlib
import importlib.util
from pathlib import Path
import unittest

import metao
from metao.durable import DurableExecutionSpec, DurableExecutionState, DurableStatus


class FakeDurablePort:
    def __init__(self):
        self.states = {}
        self.cancelled = []
        self.resumed = []

    def start(self, spec):
        execution_id = "exec-final"
        self.states[execution_id] = DurableExecutionState(execution_id, DurableStatus.RUNNING, {"workflow": spec.workflow_name})
        return execution_id

    def state(self, execution_id):
        return self.states[execution_id]

    def pause(self, execution_id):
        pass

    def resume(self, execution_id):
        self.resumed.append(execution_id)

    def cancel(self, execution_id):
        self.cancelled.append(execution_id)


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

    def test_two_orchestrator_adapter_boundaries_are_present(self):
        required = ("metao.adapters.langgraph", "metao.adapters.crewai")
        missing = [name for name in required if importlib.util.find_spec(name) is None]
        self.assertEqual(missing, [], f"missing orchestrator adapters: {missing}")

    def test_public_operator_entrypoints_execute_against_port(self):
        for name in ("run", "status", "inspect", "cancel", "resume"):
            self.assertTrue(hasattr(metao, name), f"missing public entrypoint: {name}")
        port = FakeDurablePort()
        execution_id = metao.run(port, DurableExecutionSpec("wf", "task", {"x": 1}))
        self.assertEqual(execution_id, "exec-final")
        self.assertEqual(metao.status(port, execution_id).status, DurableStatus.RUNNING)
        self.assertEqual(metao.inspect(port, execution_id).execution_id, execution_id)
        metao.resume(port, execution_id)
        metao.cancel(port, execution_id)
        self.assertEqual(port.resumed, [execution_id])
        self.assertEqual(port.cancelled, [execution_id])

    def test_release_readiness_and_quickstart_documentation_exist(self):
        readiness = Path("docs/RELEASE-READINESS.md")
        readme = Path("README.md")
        self.assertTrue(readiness.exists(), "docs/RELEASE-READINESS.md missing")
        self.assertIn("quickstart", readme.read_text(encoding="utf-8").lower())
        readiness_text = readiness.read_text(encoding="utf-8").lower()
        self.assertIn("not claimed", readiness_text)
        self.assertIn("production release requires", readiness_text)


if __name__ == "__main__":
    unittest.main()
