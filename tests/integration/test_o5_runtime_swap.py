from __future__ import annotations

from hashlib import sha256
from pathlib import Path
import unittest
from typing_extensions import TypedDict
from langgraph.graph import END, START, StateGraph

import metao.core as core_module
from metao.acceptance import AcceptanceContext, AcceptanceDecision
from metao.adapters.crewai import CrewAIOrchestratorAdapter, normalize_evidence as normalize_crewai
from metao.adapters.langgraph import LangGraphOrchestratorAdapter, normalize_evidence as normalize_langgraph
from metao.control_plane import execute_mission_once
from metao.core import Mission, OrchestratorRegistry
from metao.governance import AcceptanceBudget, evaluate_policy
from metao.strategy import OrchestratorPoolState, OrchestratorStatus


class State(TypedDict, total=False):
    objective: str
    result: str


def langgraph_runtime():
    builder = StateGraph(State)
    builder.add_node("run", lambda state: {"result": "langgraph:" + state["objective"]})
    builder.add_edge(START, "run")
    builder.add_edge("run", END)
    return builder.compile()


class EmulatedCrew:
    def kickoff(self, *, inputs):
        return {"result": "crewai:" + inputs["objective"]}


def core_digest() -> str:
    return sha256(Path(core_module.__file__).read_bytes()).hexdigest()


class O5RuntimeSwap(unittest.TestCase):
    def test_entire_runtime_swaps_behind_same_core_contract(self):
        before = core_digest()
        registry = OrchestratorRegistry()
        mission = Mission("o5-mission", "same mission", frozenset({"workflow"}))
        pool = (OrchestratorPoolState("runtime", OrchestratorStatus.HEALTHY, frozenset({"workflow"})),)
        policy = evaluate_policy(policy_bundle_id="policy-o5", allowed=True)
        context = AcceptanceContext("subject-o5", "state-o5", "verify-o5", "policy-o5", frozenset({"execution_result"}))

        registry.register(LangGraphOrchestratorAdapter(langgraph_runtime(), orchestrator_id="runtime", version="1.2.11"))
        first = execute_mission_once(
            mission=mission,
            registry=registry,
            pools=pool,
            normalizers={"runtime": normalize_langgraph},
            policy=policy,
            budget=AcceptanceBudget(1.0, 1000, 60.0, 2),
            acceptance_context=context,
            execution_id="o5-langgraph",
            now_epoch=100.0,
        )

        registry.unregister("runtime")
        registry.register(CrewAIOrchestratorAdapter(EmulatedCrew(), orchestrator_id="runtime", version="1"))
        second = execute_mission_once(
            mission=mission,
            registry=registry,
            pools=pool,
            normalizers={"runtime": normalize_crewai},
            policy=policy,
            budget=AcceptanceBudget(1.0, 1000, 60.0, 2),
            acceptance_context=context,
            execution_id="o5-crewai",
            now_epoch=100.0,
        )

        self.assertEqual(first.acceptance.decision, AcceptanceDecision.ACCEPT)
        self.assertEqual(second.acceptance.decision, AcceptanceDecision.ACCEPT)
        self.assertEqual(first.execution.output["result"], "langgraph:same mission")
        self.assertEqual(second.execution.output["result"], "crewai:same mission")
        self.assertEqual(before, core_digest())


if __name__ == "__main__":
    unittest.main(verbosity=2)
