from __future__ import annotations

from importlib.metadata import version as package_version
import json
from pathlib import Path
import sys
import tempfile
from types import ModuleType
from typing import Any, ClassVar
import unittest

from crewai import Agent, Crew, Process, Task
from crewai.llms.base_llm import BaseLLM
from langgraph.graph import END, START, StateGraph
from typing_extensions import TypedDict

from metao.adapters.crewai import CrewAIOrchestratorAdapter, normalize_evidence as normalize_crewai
from metao.adapters.langgraph import LangGraphOrchestratorAdapter, normalize_evidence as normalize_langgraph
from metao.mission_store import InMemoryMissionStore
from metao.runtime_factory import RuntimePlugin, create_operator_from_catalog
from metao.sqlite_runtime_certification import SQLiteRuntimeCertificationStore


CREWAI_VERSION = "1.15.16"
LANGGRAPH_VERSION = "1.2.11"


class SandboxLLM(BaseLLM):
    calls: ClassVar[int] = 0

    def call(
        self,
        messages: Any,
        tools: Any = None,
        callbacks: Any = None,
        available_functions: Any = None,
        from_task: Any = None,
        from_agent: Any = None,
        response_model: Any = None,
    ) -> str:
        type(self).calls += 1
        return "crewai-certified-ok"


class GraphState(TypedDict, total=False):
    objective: str
    result: str


def build_graph(calls: dict[str, int]):
    def step(state: GraphState):
        calls["count"] = calls.get("count", 0) + 1
        return {"result": "langgraph-certified-ok"}

    builder = StateGraph(GraphState)
    builder.add_node("run", step)
    builder.add_edge(START, "run")
    builder.add_edge("run", END)
    return builder.compile()


def build_crew() -> Crew:
    llm = SandboxLLM(model="metao-roadmap4-sandbox")
    agent = Agent(
        role="metaO certification worker",
        goal="Complete the deterministic certification probe",
        backstory="A local deterministic worker for real CrewAI SDK certification tests.",
        llm=llm,
        allow_delegation=False,
        verbose=False,
        max_iter=1,
    )
    task = Task(
        description="Execute this certification objective: {objective}",
        expected_output="A short deterministic certification result.",
        agent=agent,
    )
    return Crew(
        agents=[agent],
        tasks=[task],
        process=Process.sequential,
        verbose=False,
        memory=False,
        cache=False,
    )


def manifest_entry(factory: str, orchestrator_id: str, probe_id: str, *, preferred: bool) -> dict:
    return {
        "factory": factory,
        "cost": 0.01 if preferred else 0.1,
        "latency_ms": 10.0 if preferred else 20.0,
        "success_rate": 0.9,
        "quality": 0.9,
        "reliability": 0.9,
        "trust_profile": "local-real-sandbox",
        "certification": {
            "mode": "required",
            "reuse_passed": True,
            "probe": {
                "execution_id": probe_id,
                "mission_id": f"certify-{orchestrator_id}",
                "objective": f"certify {orchestrator_id} neutral boundary",
                "required_capabilities": ["workflow"],
            },
        },
    }


class RealDeclarativeCertifiedRuntimesV1Tests(unittest.TestCase):
    def setUp(self) -> None:
        self.module_name = "metao_r4_wu03_real_plugins"
        self.module = ModuleType(self.module_name)
        sys.modules[self.module_name] = self.module
        self.graph_calls: dict[str, int] = {"count": 0}
        SandboxLLM.calls = 0
        self.bind_factories()

    def tearDown(self) -> None:
        sys.modules.pop(self.module_name, None)

    def bind_factories(self) -> None:
        graph_calls = self.graph_calls

        def langgraph_plugin():
            return RuntimePlugin(
                LangGraphOrchestratorAdapter(
                    build_graph(graph_calls),
                    orchestrator_id="langgraph-real",
                    version=LANGGRAPH_VERSION,
                ),
                normalize_langgraph,
            )

        def crewai_plugin():
            return RuntimePlugin(
                CrewAIOrchestratorAdapter(
                    build_crew(),
                    orchestrator_id="crewai-real",
                    version=CREWAI_VERSION,
                ),
                normalize_crewai,
            )

        setattr(self.module, "langgraph_plugin", langgraph_plugin)
        setattr(self.module, "crewai_plugin", crewai_plugin)

    def write_manifest(self, path: Path) -> Path:
        path.write_text(
            json.dumps(
                {
                    "runtimes": [
                        manifest_entry(
                            f"{self.module_name}:langgraph_plugin",
                            "langgraph-real",
                            "r4-cert-langgraph-v1",
                            preferred=True,
                        ),
                        manifest_entry(
                            f"{self.module_name}:crewai_plugin",
                            "crewai-real",
                            "r4-cert-crewai-v1",
                            preferred=False,
                        ),
                    ]
                }
            ),
            encoding="utf-8",
        )
        return path

    def test_01_pinned_real_runtime_versions(self):
        self.assertEqual(package_version("langgraph"), LANGGRAPH_VERSION)
        self.assertEqual(package_version("crewai"), CREWAI_VERSION)

    def test_02_first_declarative_load_actively_certifies_both_real_runtimes(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            db = root / "metao.db"
            path = self.write_manifest(root / "runtimes.json")
            operator = create_operator_from_catalog(
                path,
                store=InMemoryMissionStore(),
                certifications=SQLiteRuntimeCertificationStore(db),
            )
            ids = {item.orchestrator_id for item in operator.runtime_entries()}
            certificates = SQLiteRuntimeCertificationStore(db)
            langgraph_history = certificates.history("langgraph-real")
            crewai_history = certificates.history("crewai-real")
        self.assertEqual(ids, {"langgraph-real", "crewai-real"})
        self.assertEqual(self.graph_calls["count"], 1)
        self.assertGreaterEqual(SandboxLLM.calls, 1)
        self.assertEqual(len(langgraph_history), 1)
        self.assertEqual(len(crewai_history), 1)
        self.assertTrue(langgraph_history[0].passed)
        self.assertTrue(crewai_history[0].passed)

    def test_03_restart_reuses_both_persisted_passes_without_reexecuting_sdk_runtimes(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            db = root / "metao.db"
            path = self.write_manifest(root / "runtimes.json")
            create_operator_from_catalog(
                path,
                store=InMemoryMissionStore(),
                certifications=SQLiteRuntimeCertificationStore(db),
            )
            self.assertEqual(self.graph_calls["count"], 1)
            self.assertGreaterEqual(SandboxLLM.calls, 1)

            self.graph_calls["count"] = 0
            SandboxLLM.calls = 0
            self.bind_factories()
            restarted = create_operator_from_catalog(
                path,
                store=InMemoryMissionStore(),
                certifications=SQLiteRuntimeCertificationStore(db),
            )
            ids = {item.orchestrator_id for item in restarted.runtime_entries()}
            certificates = SQLiteRuntimeCertificationStore(db)
            langgraph_history = certificates.history("langgraph-real")
            crewai_history = certificates.history("crewai-real")
        self.assertEqual(ids, {"langgraph-real", "crewai-real"})
        self.assertEqual(self.graph_calls["count"], 0)
        self.assertEqual(SandboxLLM.calls, 0)
        self.assertEqual(len(langgraph_history), 1)
        self.assertEqual(len(crewai_history), 1)


if __name__ == "__main__":
    unittest.main(verbosity=2)
