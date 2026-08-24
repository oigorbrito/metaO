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
from metao.runtime_certification_revocation import revoke_certificate
from metao.runtime_factory import RuntimePlugin, create_operator_from_catalog
from metao.sqlite_runtime_certification import SQLiteRuntimeCertificationStore
from metao.sqlite_runtime_certification_revocation import SQLiteRuntimeCertificationRevocationStore


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
        return "crewai-lifecycle-ok"


class GraphState(TypedDict, total=False):
    objective: str
    result: str


def build_graph(calls: dict[str, int]):
    def step(state: GraphState):
        calls["count"] = calls.get("count", 0) + 1
        return {"result": "langgraph-lifecycle-ok"}

    builder = StateGraph(GraphState)
    builder.add_node("run", step)
    builder.add_edge(START, "run")
    builder.add_edge("run", END)
    return builder.compile()


def build_crew() -> Crew:
    llm = SandboxLLM(model="metao-roadmap5-sandbox")
    agent = Agent(
        role="metaO lifecycle certification worker",
        goal="Complete the deterministic lifecycle certification probe",
        backstory="A local deterministic worker for real CrewAI lifecycle tests.",
        llm=llm,
        allow_delegation=False,
        verbose=False,
        max_iter=1,
    )
    task = Task(
        description="Execute this lifecycle certification objective: {objective}",
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
        "trust_profile": "local-real-lifecycle",
        "certification": {
            "mode": "required",
            "reuse_passed": True,
            "max_age_seconds": 60.0,
            "probe": {
                "execution_id": probe_id,
                "mission_id": f"certify-{orchestrator_id}",
                "objective": f"certify {orchestrator_id} lifecycle boundary",
                "required_capabilities": ["workflow"],
            },
        },
    }


class RealCertificateLifecycleV1Tests(unittest.TestCase):
    def setUp(self) -> None:
        self.module_name = "metao_r5_wu04_real_plugins"
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
                            "r5-cert-langgraph-v1",
                            preferred=True,
                        ),
                        manifest_entry(
                            f"{self.module_name}:crewai_plugin",
                            "crewai-real",
                            "r5-cert-crewai-v1",
                            preferred=False,
                        ),
                    ]
                }
            ),
            encoding="utf-8",
        )
        return path

    @staticmethod
    def stores(db: Path):
        return SQLiteRuntimeCertificationStore(db), SQLiteRuntimeCertificationRevocationStore(db)

    def load(self, path: Path, db: Path, now_epoch: float):
        certifications, revocations = self.stores(db)
        return create_operator_from_catalog(
            path,
            store=InMemoryMissionStore(),
            certifications=certifications,
            certification_revocations=revocations,
            certification_now_epoch=now_epoch,
        )

    def reset_runtime_calls(self) -> None:
        self.graph_calls["count"] = 0
        SandboxLLM.calls = 0
        self.bind_factories()

    def test_01_pinned_real_runtime_versions(self):
        self.assertEqual(package_version("langgraph"), LANGGRAPH_VERSION)
        self.assertEqual(package_version("crewai"), CREWAI_VERSION)

    def test_02_first_load_certifies_both_and_in_window_restart_reuses_both(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            db = root / "metao.db"
            path = self.write_manifest(root / "runtimes.json")
            first = self.load(path, db, 100.0)
            self.assertEqual({item.orchestrator_id for item in first.runtime_entries()}, {"langgraph-real", "crewai-real"})
            self.assertEqual(self.graph_calls["count"], 1)
            self.assertGreaterEqual(SandboxLLM.calls, 1)

            self.reset_runtime_calls()
            second = self.load(path, db, 120.0)
            certifications, _ = self.stores(db)
            self.assertEqual({item.orchestrator_id for item in second.runtime_entries()}, {"langgraph-real", "crewai-real"})
        self.assertEqual(self.graph_calls["count"], 0)
        self.assertEqual(SandboxLLM.calls, 0)
        self.assertEqual(len(certifications.history("langgraph-real")), 1)
        self.assertEqual(len(certifications.history("crewai-real")), 1)

    def test_03_expiry_recertifies_both_real_runtimes_with_new_generations(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            db = root / "metao.db"
            path = self.write_manifest(root / "runtimes.json")
            self.load(path, db, 100.0)
            self.reset_runtime_calls()
            self.load(path, db, 161.0)
            certifications, _ = self.stores(db)
            langgraph = certifications.history("langgraph-real")
            crewai = certifications.history("crewai-real")
        self.assertEqual(self.graph_calls["count"], 1)
        self.assertGreaterEqual(SandboxLLM.calls, 1)
        self.assertEqual([item.certified_at_epoch for item in langgraph], [100.0, 161.0])
        self.assertEqual([item.certified_at_epoch for item in crewai], [100.0, 161.0])

    def test_04_revoking_only_langgraph_selectively_recertifies_langgraph(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            db = root / "metao.db"
            path = self.write_manifest(root / "runtimes.json")
            self.load(path, db, 100.0)
            certifications, revocations = self.stores(db)
            old_graph = certifications.history("langgraph-real")[0]
            revoke_certificate(
                certifications,
                revocations,
                old_graph.certificate_id,
                reason="selective lifecycle rotation",
                actor_id="roadmap5-test",
                revoked_at_epoch=110.0,
            )

            self.reset_runtime_calls()
            self.load(path, db, 120.0)
            certifications, revocations = self.stores(db)
            graph_history = certifications.history("langgraph-real")
            crew_history = certifications.history("crewai-real")
        self.assertEqual(self.graph_calls["count"], 1)
        self.assertEqual(SandboxLLM.calls, 0)
        self.assertEqual(len(graph_history), 2)
        self.assertEqual(len(crew_history), 1)
        self.assertIsNotNone(revocations.get(old_graph.certificate_id))
        self.assertIsNone(revocations.get(graph_history[-1].certificate_id))

    def test_05_new_generation_after_revoke_is_reused_without_sdk_execution(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            db = root / "metao.db"
            path = self.write_manifest(root / "runtimes.json")
            self.load(path, db, 100.0)
            certifications, revocations = self.stores(db)
            old_graph = certifications.history("langgraph-real")[0]
            revoke_certificate(
                certifications,
                revocations,
                old_graph.certificate_id,
                reason="rotate graph certificate",
                actor_id="roadmap5-test",
                revoked_at_epoch=110.0,
            )
            self.reset_runtime_calls()
            self.load(path, db, 120.0)
            self.assertEqual(self.graph_calls["count"], 1)
            self.assertEqual(SandboxLLM.calls, 0)

            self.reset_runtime_calls()
            operator = self.load(path, db, 130.0)
            certifications, _ = self.stores(db)
        self.assertEqual(self.graph_calls["count"], 0)
        self.assertEqual(SandboxLLM.calls, 0)
        self.assertEqual({item.orchestrator_id for item in operator.runtime_entries()}, {"langgraph-real", "crewai-real"})
        self.assertEqual(len(certifications.history("langgraph-real")), 2)
        self.assertEqual(len(certifications.history("crewai-real")), 1)


if __name__ == "__main__":
    unittest.main(verbosity=2)
