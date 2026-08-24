from __future__ import annotations

import unittest
from typing_extensions import TypedDict
from langgraph.graph import END, START, StateGraph

from metao.acceptance import AcceptanceContext, AcceptanceDecision
from metao.adapters.langgraph import LangGraphOrchestratorAdapter, normalize_evidence
from metao.control_plane import execute_mission_once
from metao.core import Mission, OrchestratorRegistry
from metao.governance import AcceptanceBudget, evaluate_policy
from metao.strategy import OrchestratorPoolState, OrchestratorStatus


class State(TypedDict, total=False):
    objective: str
    result: str


def build_graph():
    builder = StateGraph(State)
    builder.add_node("step", lambda state: {"result": "done:" + state["objective"]})
    builder.add_edge(START, "step")
    builder.add_edge("step", END)
    return builder.compile()


class O2EndToEndSandbox(unittest.TestCase):
    def test_complete_mission_path(self):
        adapter = LangGraphOrchestratorAdapter(build_graph(), orchestrator_id="lg-e2e", version="1.2.11")
        registry = OrchestratorRegistry()
        registry.register(adapter)
        mission = Mission("o2-mission", "sandbox end to end", frozenset({"workflow"}))
        context = AcceptanceContext("subject-o2", "state-o2", "verify-o2", "policy-o2", frozenset({"execution_result"}))
        outcome = execute_mission_once(
            mission=mission,
            registry=registry,
            pools=(OrchestratorPoolState("lg-e2e", OrchestratorStatus.HEALTHY, frozenset({"workflow"}), 0.95, 0.95, 0.95, 10.0, 0.01),),
            normalizers={"lg-e2e": normalize_evidence},
            policy=evaluate_policy(policy_bundle_id="policy-o2", allowed=True),
            budget=AcceptanceBudget(1.0, 1000, 60.0, 3),
            acceptance_context=context,
            execution_id="o2-exec",
            now_epoch=100.0,
        )
        self.assertEqual(outcome.orchestrator_id, "lg-e2e")
        self.assertEqual(outcome.execution.output["result"], "done:sandbox end to end")
        self.assertEqual(outcome.acceptance.decision, AcceptanceDecision.ACCEPT)
        self.assertEqual(outcome.budget.verifier_attempts_used, 1)
        self.assertIsNotNone(outcome.acceptance.proof)


if __name__ == "__main__":
    unittest.main(verbosity=2)
