from __future__ import annotations

import ast
from pathlib import Path
import unittest

from metao import (
    ExecutionRequest,
    ExecutionResult,
    ExecutionStatus,
    HealthReport,
    HealthStatus,
    Mission,
    OrchestratorDescriptor,
    OrchestratorRegistry,
)


class StubOrchestrator:
    def __init__(self, orchestrator_id: str, marker: str, *, healthy: bool = True):
        self._descriptor = OrchestratorDescriptor(
            orchestrator_id=orchestrator_id,
            version="1",
            capabilities=frozenset({"code", "test"}),
        )
        self.marker = marker
        self.healthy = healthy
        self.cancelled: list[str] = []

    @property
    def descriptor(self):
        return self._descriptor

    def health(self):
        return HealthReport(HealthStatus.HEALTHY if self.healthy else HealthStatus.UNHEALTHY)

    def execute(self, request):
        return ExecutionResult(
            execution_id=request.execution_id,
            orchestrator_id=self.descriptor.orchestrator_id,
            status=ExecutionStatus.SUCCEEDED,
            output={"marker": self.marker},
        )

    def cancel(self, execution_id: str):
        self.cancelled.append(execution_id)


class CoreContractTests(unittest.TestCase):
    def test_entire_orchestrator_is_replaceable_without_core_change(self):
        mission = Mission("m1", "implement and test", frozenset({"code", "test"}))
        request = ExecutionRequest("e1", mission)
        registry = OrchestratorRegistry()
        alpha = StubOrchestrator("alpha", "A")
        registry.register(alpha)
        self.assertEqual(registry.get("alpha").execute(request).output["marker"], "A")
        registry.unregister("alpha")
        beta = StubOrchestrator("beta", "B")
        registry.register(beta)
        self.assertEqual(registry.get("beta").execute(request).output["marker"], "B")
        self.assertEqual([d.orchestrator_id for d in registry.descriptors()], ["beta"])

    def test_eligibility_is_capability_and_health_based(self):
        mission = Mission("m1", "task", frozenset({"code"}))
        registry = OrchestratorRegistry()
        registry.register(StubOrchestrator("healthy", "ok"))
        registry.register(StubOrchestrator("down", "no", healthy=False))
        self.assertEqual([x.descriptor.orchestrator_id for x in registry.eligible(mission)], ["healthy"])

    def test_duplicate_registration_fails(self):
        registry = OrchestratorRegistry()
        registry.register(StubOrchestrator("same", "A"))
        with self.assertRaises(ValueError):
            registry.register(StubOrchestrator("same", "B"))

    def test_core_has_no_orchestrator_specific_imports(self):
        forbidden = {"langgraph", "crewai", "openai", "autogen"}
        root = Path(__file__).parents[2] / "src" / "metao"
        offenders = []
        for path in root.rglob("*.py"):
            tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
            for node in ast.walk(tree):
                names = []
                if isinstance(node, ast.Import):
                    names.extend(alias.name for alias in node.names)
                elif isinstance(node, ast.ImportFrom) and node.module:
                    names.append(node.module)
                for name in names:
                    if name.split(".")[0] in forbidden:
                        offenders.append((str(path), name))
        self.assertEqual(offenders, [])


if __name__ == "__main__":
    unittest.main()
