from __future__ import annotations

import unittest
from typing_extensions import TypedDict

from langgraph.graph import END, START, StateGraph

from metao.adapters.langgraph import LangGraphOrchestratorAdapter
from metao.core import ExecutionRequest, ExecutionStatus, Mission


class _State(TypedDict, total=False):
    objective: str
    result: str


def _build_real_graph():
    builder = StateGraph(_State)

    def transform(state: _State) -> dict[str, str]:
        return {"result": state["objective"].upper()}

    builder.add_node("transform", transform)
    builder.add_edge(START, "transform")
    builder.add_edge("transform", END)
    return builder.compile()


class O1LangGraphRealRuntime(unittest.TestCase):
    def test_real_langgraph_runs_through_metao_adapter_without_llm(self):
        graph = _build_real_graph()
        adapter = LangGraphOrchestratorAdapter(graph, orchestrator_id="langgraph-real", version="1.2.11")
        request = ExecutionRequest(
            execution_id="o1-exec",
            mission=Mission(
                mission_id="o1-mission",
                objective="prove real langgraph runtime",
                required_capabilities=frozenset({"workflow"}),
            ),
        )

        result = adapter.execute(request)

        self.assertEqual(result.status, ExecutionStatus.SUCCEEDED)
        self.assertEqual(result.orchestrator_id, "langgraph-real")
        self.assertEqual(result.output["result"], "PROVE REAL LANGGRAPH RUNTIME")
        self.assertEqual(adapter.health().status.value, "HEALTHY")


if __name__ == "__main__":
    unittest.main(verbosity=2)
