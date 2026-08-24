from __future__ import annotations

import unittest
from typing_extensions import TypedDict
from langgraph.graph import END, START, StateGraph

from metao.acceptance import AcceptanceContext, AcceptanceDecision
from metao.adapters.langgraph import LangGraphOrchestratorAdapter, normalize_evidence
from metao.control_plane import execute_mission
from metao.core import (
    ExecutionRequest,
    ExecutionResult,
    ExecutionStatus,
    HealthReport,
    HealthStatus,
    Mission,
    OrchestratorDescriptor,
    OrchestratorRegistry,
)
from metao.governance import AcceptanceBudget, evaluate_policy
from metao.strategy import OrchestratorPoolState, OrchestratorStatus


class FailingOrchestrator:
    def __init__(self) -> None:
        self.calls = 0
        self._descriptor = OrchestratorDescriptor("primary", "1", frozenset({"workflow"}))

    @property
    def descriptor(self):
        return self._descriptor

    def health(self):
        return HealthReport(HealthStatus.HEALTHY)

    def execute(self, request: ExecutionRequest):
        self.calls += 1
        return ExecutionResult(request.execution_id, "primary", ExecutionStatus.FAILED, error="runtime failure")

    def cancel(self, execution_id: str) -> None:
        pass


class State(TypedDict, total=False):
    objective: str
    result: str


def fallback_graph():
    builder = StateGraph(State)
    builder.add_node("fallback", lambda state: {"result": "fallback:" + state["objective"]})
    builder.add_edge(START, "fallback")
    builder.add_edge("fallback", END)
    return builder.compile()


class O3FailoverSandbox(unittest.TestCase):
    def test_failed_preferred_runtime_is_excluded_and_second_runtime_accepts(self):
        primary = FailingOrchestrator()
        fallback = LangGraphOrchestratorAdapter(fallback_graph(), orchestrator_id="fallback", version="1.2.11")
        registry = OrchestratorRegistry()
        registry.register(primary)
        registry.register(fallback)

        outcome = execute_mission(
            mission=Mission("o3-mission", "recover in sandbox", frozenset({"workflow"})),
            registry=registry,
            pools=(
                OrchestratorPoolState("primary", OrchestratorStatus.HEALTHY, frozenset({"workflow"}), 1.0, 1.0, 1.0, 1.0, 0.0),
                OrchestratorPoolState("fallback", OrchestratorStatus.HEALTHY, frozenset({"workflow"}), 0.8, 0.8, 0.8, 20.0, 0.02),
            ),
            normalizers={"primary": normalize_evidence, "fallback": normalize_evidence},
            policy=evaluate_policy(policy_bundle_id="policy-o3", allowed=True),
            budget=AcceptanceBudget(1.0, 1000, 60.0, 3),
            acceptance_context=AcceptanceContext("subject-o3", "state-o3", "verify-o3", "policy-o3", frozenset({"execution_result"})),
            execution_id_prefix="o3-exec",
            now_epoch=100.0,
            max_attempts=2,
        )

        self.assertEqual(primary.calls, 1)
        self.assertEqual(outcome.attempted_orchestrators, ("primary", "fallback"))
        self.assertEqual(outcome.orchestrator_id, "fallback")
        self.assertEqual(outcome.execution.output["result"], "fallback:recover in sandbox")
        self.assertEqual(outcome.acceptance.decision, AcceptanceDecision.ACCEPT)


if __name__ == "__main__":
    unittest.main(verbosity=2)
