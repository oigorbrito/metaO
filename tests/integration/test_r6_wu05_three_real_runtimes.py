from __future__ import annotations

from importlib.metadata import version as package_version
import json
from pathlib import Path
import sys
import tempfile
from types import ModuleType
from typing import Any, ClassVar
import unittest

from agents import Agent as OpenAIAgent, Runner, set_tracing_disabled
from crewai import Agent, Crew, Process, Task
from crewai.llms.base_llm import BaseLLM
from langgraph.graph import END, START, StateGraph
from typing_extensions import TypedDict

from _openai_agents_model import ScriptedModel, assistant_message
from metao.acceptance import AcceptanceContext, AcceptanceDecision
from metao.adapters.crewai import CrewAIOrchestratorAdapter, normalize_evidence as normalize_crewai
from metao.adapters.langgraph import LangGraphOrchestratorAdapter, normalize_evidence as normalize_langgraph
from metao.adapters.openai_agents import (
    OpenAIAgentsOrchestratorAdapter,
    normalize_evidence as normalize_openai_agents,
)
from metao.core import Mission
from metao.governance import AcceptanceBudget, evaluate_policy
from metao.mission_store import InMemoryMissionStore
from metao.runtime_certification_revocation import revoke_certificate
from metao.runtime_control import InMemoryRuntimeControlStore, quarantine
from metao.runtime_factory import RuntimePlugin, create_operator_from_catalog
from metao.sqlite_runtime_certification import SQLiteRuntimeCertificationStore
from metao.sqlite_runtime_certification_revocation import SQLiteRuntimeCertificationRevocationStore
from metao.strategy import OrchestratorStatus


OPENAI_AGENTS_VERSION = "0.20.0"
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
        return "crewai-three-runtime-ok"


class GraphState(TypedDict, total=False):
    objective: str
    result: str


def build_graph(calls: dict[str, int]):
    def step(state: GraphState):
        calls["count"] = calls.get("count", 0) + 1
        return {"result": "langgraph-three-runtime-ok"}

    builder = StateGraph(GraphState)
    builder.add_node("run", step)
    builder.add_edge(START, "run")
    builder.add_edge("run", END)
    return builder.compile()


def build_crew() -> Crew:
    llm = SandboxLLM(model="metao-roadmap6-three-runtime-sandbox")
    agent = Agent(
        role="metaO three-runtime worker",
        goal="Complete the deterministic runtime objective",
        backstory="A local deterministic CrewAI worker for metaO regression tests.",
        llm=llm,
        allow_delegation=False,
        verbose=False,
        max_iter=1,
    )
    task = Task(
        description="Execute this deterministic objective: {objective}",
        expected_output="A short deterministic result.",
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


def manifest_entry(
    factory: str,
    orchestrator_id: str,
    probe_id: str,
    *,
    cost: float,
    latency_ms: float,
    score: float,
) -> dict:
    return {
        "factory": factory,
        "cost": cost,
        "latency_ms": latency_ms,
        "success_rate": score,
        "quality": score,
        "reliability": score,
        "trust_profile": "local-real-three-runtime",
        "certification": {
            "mode": "required",
            "reuse_passed": True,
            "max_age_seconds": 60.0,
            "probe": {
                "execution_id": probe_id,
                "mission_id": f"certify-{orchestrator_id}",
                "objective": f"certify {orchestrator_id} three-runtime boundary",
                "required_capabilities": ["workflow"],
            },
        },
    }


class ThreeRealRuntimesV1Tests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        set_tracing_disabled(True)

    def setUp(self) -> None:
        self.module_name = "metao_r6_wu05_real_plugins"
        self.module = ModuleType(self.module_name)
        sys.modules[self.module_name] = self.module
        self.graph_calls: dict[str, int] = {"count": 0}
        self.openai_models: list[ScriptedModel] = []
        self.openai_fail_mission = False
        SandboxLLM.calls = 0
        self.bind_factories()

    def tearDown(self) -> None:
        sys.modules.pop(self.module_name, None)

    def bind_factories(self) -> None:
        graph_calls = self.graph_calls
        parent = self

        def openai_agents_plugin():
            second_step = (
                RuntimeError("scripted OpenAI Agents mission failure")
                if parent.openai_fail_mission
                else [assistant_message("openai-agents-mission-ok")]
            )
            model = ScriptedModel(
                [
                    [assistant_message("openai-agents-certification-ok")],
                    second_step,
                ]
            )
            parent.openai_models.append(model)
            agent = OpenAIAgent(
                name="metaO OpenAI Agents three-runtime worker",
                model=model,
            )
            return RuntimePlugin(
                OpenAIAgentsOrchestratorAdapter(
                    Runner,
                    agent,
                    orchestrator_id="openai-agents-real",
                    version=OPENAI_AGENTS_VERSION,
                ),
                normalize_openai_agents,
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

        def langgraph_plugin():
            return RuntimePlugin(
                LangGraphOrchestratorAdapter(
                    build_graph(graph_calls),
                    orchestrator_id="langgraph-real",
                    version=LANGGRAPH_VERSION,
                ),
                normalize_langgraph,
            )

        setattr(self.module, "openai_agents_plugin", openai_agents_plugin)
        setattr(self.module, "crewai_plugin", crewai_plugin)
        setattr(self.module, "langgraph_plugin", langgraph_plugin)

    def write_manifest(self, path: Path) -> Path:
        payload = {
            "runtimes": [
                manifest_entry(
                    f"{self.module_name}:openai_agents_plugin",
                    "openai-agents-real",
                    "r6-cert-openai-agents-v1",
                    cost=0.01,
                    latency_ms=5.0,
                    score=0.99,
                ),
                manifest_entry(
                    f"{self.module_name}:crewai_plugin",
                    "crewai-real",
                    "r6-cert-crewai-v1",
                    cost=0.02,
                    latency_ms=10.0,
                    score=0.95,
                ),
                manifest_entry(
                    f"{self.module_name}:langgraph_plugin",
                    "langgraph-real",
                    "r6-cert-langgraph-v1",
                    cost=0.03,
                    latency_ms=15.0,
                    score=0.90,
                ),
            ]
        }
        path.write_text(json.dumps(payload), encoding="utf-8")
        return path

    @staticmethod
    def stores(db: Path):
        return (
            SQLiteRuntimeCertificationStore(db),
            SQLiteRuntimeCertificationRevocationStore(db),
        )

    def load(
        self,
        path: Path,
        db: Path,
        now_epoch: float,
        *,
        controls: InMemoryRuntimeControlStore | None = None,
    ):
        certifications, revocations = self.stores(db)
        return create_operator_from_catalog(
            path,
            store=InMemoryMissionStore(),
            controls=controls,
            certifications=certifications,
            certification_revocations=revocations,
            certification_now_epoch=now_epoch,
        )

    def reset_runtime_calls(self) -> None:
        self.graph_calls["count"] = 0
        SandboxLLM.calls = 0
        self.openai_models = []
        self.bind_factories()

    @staticmethod
    def run_mission(operator, mission_id: str, *, max_attempts: int = 3):
        return operator.run(
            Mission(mission_id, "complete the three-runtime mission", frozenset({"workflow"})),
            policy=evaluate_policy(policy_bundle_id="policy-r6", allowed=True),
            budget=AcceptanceBudget(1.0, 1000, 60.0, 3),
            acceptance_context=AcceptanceContext(
                "subject-r6",
                "state-r6",
                "verify-r6",
                "policy-r6",
                frozenset({"execution_result"}),
            ),
            execution_id_prefix=f"{mission_id}-exec",
            now_epoch=120.0,
            max_attempts=max_attempts,
        )

    def test_01_pinned_real_runtime_versions(self):
        self.assertEqual(package_version("openai-agents"), OPENAI_AGENTS_VERSION)
        self.assertEqual(package_version("crewai"), CREWAI_VERSION)
        self.assertEqual(package_version("langgraph"), LANGGRAPH_VERSION)

    def test_02_one_manifest_actively_certifies_all_three_real_runtimes(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            db = root / "metao.db"
            path = self.write_manifest(root / "runtimes.json")
            operator = self.load(path, db, 100.0)
            certifications, _ = self.stores(db)

            ids = {entry.orchestrator_id for entry in operator.runtime_entries()}
            histories = {runtime_id: certifications.history(runtime_id) for runtime_id in ids}

        self.assertEqual(ids, {"openai-agents-real", "crewai-real", "langgraph-real"})
        self.assertEqual(len(self.openai_models), 1)
        self.assertEqual(len(self.openai_models[0].calls), 1)
        self.assertGreaterEqual(SandboxLLM.calls, 1)
        self.assertEqual(self.graph_calls["count"], 1)
        self.assertTrue(all(len(history) == 1 and history[0].passed for history in histories.values()))

    def test_03_in_window_restart_reuses_all_three_certificates_without_sdk_execution(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            db = root / "metao.db"
            path = self.write_manifest(root / "runtimes.json")
            self.load(path, db, 100.0)

            self.reset_runtime_calls()
            restarted = self.load(path, db, 120.0)
            certifications, _ = self.stores(db)

        self.assertEqual(
            {entry.orchestrator_id for entry in restarted.runtime_entries()},
            {"openai-agents-real", "crewai-real", "langgraph-real"},
        )
        self.assertEqual(self.graph_calls["count"], 0)
        self.assertEqual(SandboxLLM.calls, 0)
        self.assertEqual(len(self.openai_models), 1)
        self.assertEqual(len(self.openai_models[0].calls), 0)
        self.assertEqual(len(certifications.history("openai-agents-real")), 1)
        self.assertEqual(len(certifications.history("crewai-real")), 1)
        self.assertEqual(len(certifications.history("langgraph-real")), 1)

    def test_04_expiry_recetifies_all_three_as_new_generations(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            db = root / "metao.db"
            path = self.write_manifest(root / "runtimes.json")
            self.load(path, db, 100.0)

            self.reset_runtime_calls()
            self.load(path, db, 161.0)
            certifications, _ = self.stores(db)

        self.assertEqual(self.graph_calls["count"], 1)
        self.assertGreaterEqual(SandboxLLM.calls, 1)
        self.assertEqual(len(self.openai_models[0].calls), 1)
        for runtime_id in ("openai-agents-real", "crewai-real", "langgraph-real"):
            self.assertEqual(
                [item.certified_at_epoch for item in certifications.history(runtime_id)],
                [100.0, 161.0],
            )

    def test_05_revoking_only_openai_certificate_selectively_recertifies_openai(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            db = root / "metao.db"
            path = self.write_manifest(root / "runtimes.json")
            self.load(path, db, 100.0)
            certifications, revocations = self.stores(db)
            old = certifications.history("openai-agents-real")[0]
            revoke_certificate(
                certifications,
                revocations,
                old.certificate_id,
                reason="rotate selected third-runtime certificate",
                actor_id="roadmap6-test",
                revoked_at_epoch=110.0,
            )

            self.reset_runtime_calls()
            self.load(path, db, 120.0)
            certifications, _ = self.stores(db)

        self.assertEqual(len(self.openai_models[0].calls), 1)
        self.assertEqual(SandboxLLM.calls, 0)
        self.assertEqual(self.graph_calls["count"], 0)
        self.assertEqual(len(certifications.history("openai-agents-real")), 2)
        self.assertEqual(len(certifications.history("crewai-real")), 1)
        self.assertEqual(len(certifications.history("langgraph-real")), 1)

    def test_06_deterministic_selection_prefers_openai_agents_across_three_runtimes(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            operator = self.load(
                self.write_manifest(root / "runtimes.json"),
                root / "metao.db",
                100.0,
            )
            crew_calls_after_certification = SandboxLLM.calls
            graph_calls_after_certification = self.graph_calls["count"]

            outcome = self.run_mission(operator, "r6-select-three")

        self.assertEqual(outcome.orchestrator_id, "openai-agents-real")
        self.assertEqual(outcome.attempted_orchestrators, ("openai-agents-real",))
        self.assertEqual(outcome.execution.output["result"], "openai-agents-mission-ok")
        self.assertEqual(outcome.acceptance.decision, AcceptanceDecision.ACCEPT)
        self.assertEqual(len(self.openai_models[0].calls), 2)
        self.assertEqual(SandboxLLM.calls, crew_calls_after_certification)
        self.assertEqual(self.graph_calls["count"], graph_calls_after_certification)

    def test_07_failed_preferred_openai_agents_fails_over_to_crewai(self):
        self.openai_fail_mission = True
        self.bind_factories()
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            operator = self.load(
                self.write_manifest(root / "runtimes.json"),
                root / "metao.db",
                100.0,
            )
            crew_calls_after_certification = SandboxLLM.calls

            outcome = self.run_mission(operator, "r6-failover-three")

        self.assertEqual(
            outcome.attempted_orchestrators,
            ("openai-agents-real", "crewai-real"),
        )
        self.assertEqual(outcome.orchestrator_id, "crewai-real")
        self.assertEqual(outcome.acceptance.decision, AcceptanceDecision.ACCEPT)
        self.assertGreater(SandboxLLM.calls, crew_calls_after_certification)
        self.assertEqual(len(self.openai_models[0].calls), 2)

    def test_08_quarantine_overrides_preferred_runtime_and_routes_to_crewai(self):
        controls = InMemoryRuntimeControlStore()
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            operator = self.load(
                self.write_manifest(root / "runtimes.json"),
                root / "metao.db",
                100.0,
                controls=controls,
            )
            quarantine(
                controls,
                "openai-agents-real",
                reason="roadmap6 quarantine proof",
                actor_id="roadmap6-test",
                updated_at_epoch=110.0,
            )
            entries = {entry.orchestrator_id: entry for entry in operator.runtime_entries()}
            crew_calls_after_certification = SandboxLLM.calls

            outcome = self.run_mission(operator, "r6-quarantine-three")

        self.assertIs(entries["openai-agents-real"].health, OrchestratorStatus.QUARANTINED)
        self.assertEqual(outcome.orchestrator_id, "crewai-real")
        self.assertEqual(outcome.attempted_orchestrators, ("crewai-real",))
        self.assertEqual(outcome.acceptance.decision, AcceptanceDecision.ACCEPT)
        self.assertGreater(SandboxLLM.calls, crew_calls_after_certification)
        self.assertEqual(len(self.openai_models[0].calls), 1)


if __name__ == "__main__":
    unittest.main(verbosity=2)