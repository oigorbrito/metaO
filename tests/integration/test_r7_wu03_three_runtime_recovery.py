from __future__ import annotations

from importlib.metadata import version as package_version
import json
from pathlib import Path
import sys
import tempfile
from types import ModuleType
from typing import Any
import unittest

from agents import Agent as OpenAIAgent, Runner, set_tracing_disabled
from agents.testing import ScriptedModel, assistant_message
from crewai import Agent, Crew, Process, Task
from crewai.llms.base_llm import BaseLLM
from langgraph.graph import END, START, StateGraph
from typing_extensions import TypedDict

from metao.acceptance import AcceptanceContext, AcceptanceDecision
from metao.adapters.crewai import CrewAIOrchestratorAdapter, normalize_evidence as normalize_crewai
from metao.adapters.langgraph import LangGraphOrchestratorAdapter, normalize_evidence as normalize_langgraph
from metao.adapters.openai_agents import (
    OpenAIAgentsOrchestratorAdapter,
    normalize_evidence as normalize_openai_agents,
)
from metao.control_plane import MissionStatus
from metao.core import Mission
from metao.governance import AcceptanceBudget, evaluate_policy
from metao.mission_store import InMemoryMissionStore
from metao.runtime_control import InMemoryRuntimeControlStore, quarantine
from metao.runtime_factory import RuntimePlugin, create_operator_from_catalog
from metao.sqlite_runtime_certification import SQLiteRuntimeCertificationStore
from metao.sqlite_runtime_certification_revocation import SQLiteRuntimeCertificationRevocationStore
from metao.sqlite_store import SQLiteMissionStore


OPENAI_AGENTS_VERSION = "0.21.1"
CREWAI_VERSION = "1.15.16"
LANGGRAPH_VERSION = "1.2.11"


class ScriptedCrewLLM(BaseLLM):
    """Real CrewAI BaseLLM: certification succeeds, mission fails deterministically."""

    def __init__(self, *, model: str) -> None:
        super().__init__(model=model)
        self.calls = 0

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
        self.calls += 1
        if self.calls == 1:
            return "crewai-certification-ok"
        raise TimeoutError("request timed out in deterministic CrewAI mission")


class GraphState(TypedDict, total=False):
    objective: str
    result: str


def build_graph(counter: dict[str, int]):
    def step(state: GraphState):
        counter["count"] = counter.get("count", 0) + 1
        return {"result": "langgraph-human-approved-recovery"}

    builder = StateGraph(GraphState)
    builder.add_node("run", step)
    builder.add_edge(START, "run")
    builder.add_edge("run", END)
    return builder.compile()


def manifest_entry(
    factory: str,
    orchestrator_id: str,
    probe_id: str,
    *,
    rank: int,
) -> dict:
    score = 1.0 - ((rank - 1) * 0.05)
    return {
        "factory": factory,
        "cost": 0.01 * rank,
        "latency_ms": 5.0 * rank,
        "success_rate": score,
        "quality": score,
        "reliability": score,
        "trust_profile": "local-real-roadmap7-recovery",
        "certification": {
            "mode": "required",
            "reuse_passed": True,
            "max_age_seconds": 60.0,
            "probe": {
                "execution_id": probe_id,
                "mission_id": f"certify-{orchestrator_id}",
                "objective": f"certify {orchestrator_id} roadmap7 recovery boundary",
                "required_capabilities": ["workflow"],
            },
        },
    }


class ThreeRuntimeRecoveryV1Tests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        set_tracing_disabled(True)

    def setUp(self) -> None:
        self.module_name = "metao_r7_wu03_real_plugins"
        self.module = ModuleType(self.module_name)
        sys.modules[self.module_name] = self.module
        self.openai_models: list[ScriptedModel] = []
        self.crewai_models: list[ScriptedCrewLLM] = []
        self.graph_counters: list[dict[str, int]] = []
        self.bind_factories()

    def tearDown(self) -> None:
        sys.modules.pop(self.module_name, None)

    def bind_factories(self) -> None:
        parent = self

        def openai_agents_plugin():
            model = ScriptedModel(
                [
                    [assistant_message("openai-agents-certification-ok")],
                    RuntimeError("scripted OpenAI Agents runtime failure"),
                ]
            )
            parent.openai_models.append(model)
            agent = OpenAIAgent(
                name="metaO Roadmap 7 OpenAI Agents worker",
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
            llm = ScriptedCrewLLM(model="metao-roadmap7-crewai-sandbox")
            parent.crewai_models.append(llm)
            agent = Agent(
                role="metaO Roadmap 7 recovery worker",
                goal="Execute deterministic recovery work",
                backstory="A provider-free CrewAI runtime used for recovery regression.",
                llm=llm,
                allow_delegation=False,
                verbose=False,
                max_iter=1,
            )
            task = Task(
                description="Execute this recovery objective: {objective}",
                expected_output="A short deterministic recovery result.",
                agent=agent,
            )
            crew = Crew(
                agents=[agent],
                tasks=[task],
                process=Process.sequential,
                verbose=False,
                memory=False,
                cache=False,
            )
            return RuntimePlugin(
                CrewAIOrchestratorAdapter(
                    crew,
                    orchestrator_id="crewai-real",
                    version=CREWAI_VERSION,
                ),
                normalize_crewai,
            )

        def langgraph_plugin():
            counter = {"count": 0}
            parent.graph_counters.append(counter)
            return RuntimePlugin(
                LangGraphOrchestratorAdapter(
                    build_graph(counter),
                    orchestrator_id="langgraph-real",
                    version=LANGGRAPH_VERSION,
                ),
                normalize_langgraph,
            )

        setattr(self.module, "openai_agents_plugin", openai_agents_plugin)
        setattr(self.module, "crewai_plugin", crewai_plugin)
        setattr(self.module, "langgraph_plugin", langgraph_plugin)

    def write_manifest(self, path: Path) -> Path:
        path.write_text(
            json.dumps(
                {
                    "runtimes": [
                        manifest_entry(
                            f"{self.module_name}:openai_agents_plugin",
                            "openai-agents-real",
                            "r7-cert-openai-v1",
                            rank=1,
                        ),
                        manifest_entry(
                            f"{self.module_name}:crewai_plugin",
                            "crewai-real",
                            "r7-cert-crewai-v1",
                            rank=2,
                        ),
                        manifest_entry(
                            f"{self.module_name}:langgraph_plugin",
                            "langgraph-real",
                            "r7-cert-langgraph-v1",
                            rank=3,
                        ),
                    ]
                }
            ),
            encoding="utf-8",
        )
        return path

    def load(
        self,
        path: Path,
        db: Path,
        *,
        now_epoch: float,
        store,
        controls: InMemoryRuntimeControlStore | None = None,
    ):
        return create_operator_from_catalog(
            path,
            store=store,
            controls=controls,
            certifications=SQLiteRuntimeCertificationStore(db),
            certification_revocations=SQLiteRuntimeCertificationRevocationStore(db),
            certification_now_epoch=now_epoch,
        )

    @staticmethod
    def run_mission(operator, mission_id: str = "r7-real-recovery"):
        return operator.run(
            Mission(
                mission_id,
                "recover across heterogeneous real runtimes",
                frozenset({"workflow"}),
            ),
            policy=evaluate_policy(policy_bundle_id="policy-r7-real", allowed=True),
            budget=AcceptanceBudget(1.0, 1000, 60.0, 6),
            acceptance_context=AcceptanceContext(
                "subject-r7-real",
                "state-r7-real",
                "verify-r7-real",
                "policy-r7-real",
                frozenset({"execution_result"}),
            ),
            execution_id_prefix=f"{mission_id}-exec",
            now_epoch=100.0,
            max_attempts=2,
        )

    def test_01_pinned_real_runtime_versions(self):
        self.assertEqual(package_version("openai-agents"), OPENAI_AGENTS_VERSION)
        self.assertEqual(package_version("crewai"), CREWAI_VERSION)
        self.assertEqual(package_version("langgraph"), LANGGRAPH_VERSION)

    def test_02_two_real_runtime_failures_escalate_then_human_approval_runs_third_runtime(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            operator = self.load(
                self.write_manifest(root / "runtimes.json"),
                root / "metao.db",
                now_epoch=100.0,
                store=InMemoryMissionStore(),
            )
            graph_after_certification = self.graph_counters[0]["count"]

            waiting = self.run_mission(operator)
            openai_calls_after_wait = len(self.openai_models[0].calls)
            crew_calls_after_wait = self.crewai_models[0].calls

            self.assertEqual(waiting.state.status, MissionStatus.WAITING_APPROVAL)
            self.assertEqual(waiting.acceptance.decision, AcceptanceDecision.REQUIRE_HUMAN)
            self.assertEqual(
                waiting.attempted_orchestrators,
                ("openai-agents-real", "crewai-real"),
            )
            self.assertEqual(self.graph_counters[0]["count"], graph_after_certification)

            operator.approve("r7-real-recovery", approver_id="human-r7-real")
            outcome = operator.resume("r7-real-recovery", now_epoch=120.0)

        self.assertEqual(outcome.acceptance.decision, AcceptanceDecision.ACCEPT)
        self.assertEqual(outcome.state.status, MissionStatus.ACCEPTED)
        self.assertEqual(
            outcome.attempted_orchestrators,
            ("openai-agents-real", "crewai-real", "langgraph-real"),
        )
        self.assertEqual([item.attempt_number for item in outcome.state.attempts], [1, 2, 3])
        self.assertEqual(
            [item.orchestrator_id for item in outcome.state.attempts],
            ["openai-agents-real", "crewai-real", "langgraph-real"],
        )
        self.assertEqual(outcome.execution.output["result"], "langgraph-human-approved-recovery")
        self.assertEqual(len(self.openai_models[0].calls), openai_calls_after_wait)
        self.assertEqual(self.crewai_models[0].calls, crew_calls_after_wait)
        self.assertEqual(self.graph_counters[0]["count"], graph_after_certification + 1)

    def test_03_quarantine_of_only_remaining_runtime_after_wait_blocks_approved_continuation(self):
        controls = InMemoryRuntimeControlStore()
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            operator = self.load(
                self.write_manifest(root / "runtimes.json"),
                root / "metao.db",
                now_epoch=100.0,
                store=InMemoryMissionStore(),
                controls=controls,
            )
            graph_after_certification = self.graph_counters[0]["count"]
            waiting = self.run_mission(operator, "r7-real-quarantine")
            self.assertEqual(waiting.state.status, MissionStatus.WAITING_APPROVAL)

            quarantine(
                controls,
                "langgraph-real",
                reason="remaining runtime quarantined before approved resume",
                actor_id="roadmap7-test",
                updated_at_epoch=110.0,
            )
            operator.approve("r7-real-quarantine", approver_id="human-r7-real")
            outcome = operator.resume("r7-real-quarantine", now_epoch=120.0)

        self.assertEqual(outcome.state.status, MissionStatus.BLOCKED)
        self.assertIn("approved_escalation_no_remaining_runtime", outcome.acceptance.reasons)
        self.assertEqual(self.graph_counters[0]["count"], graph_after_certification)

    def test_04_sqlite_restart_reuses_certificates_and_preserves_real_runtime_lineage(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            db = root / "metao.db"
            path = self.write_manifest(root / "runtimes.json")

            first = self.load(
                path,
                db,
                now_epoch=100.0,
                store=SQLiteMissionStore(db),
            )
            waiting = self.run_mission(first, "r7-real-restart")
            self.assertEqual(waiting.state.status, MissionStatus.WAITING_APPROVAL)

            second = self.load(
                path,
                db,
                now_epoch=120.0,
                store=SQLiteMissionStore(db),
            )
            self.assertEqual(len(self.openai_models[-1].calls), 0)
            self.assertEqual(self.crewai_models[-1].calls, 0)
            self.assertEqual(self.graph_counters[-1]["count"], 0)
            second.approve("r7-real-restart", approver_id="human-after-restart")

            third = self.load(
                path,
                db,
                now_epoch=130.0,
                store=SQLiteMissionStore(db),
            )
            latest_openai = self.openai_models[-1]
            latest_crew = self.crewai_models[-1]
            latest_graph = self.graph_counters[-1]
            outcome = third.resume("r7-real-restart", now_epoch=130.0)
            final = SQLiteMissionStore(db).get("r7-real-restart")

        self.assertEqual(outcome.acceptance.decision, AcceptanceDecision.ACCEPT)
        self.assertEqual(final.status, MissionStatus.ACCEPTED)
        self.assertEqual([item.attempt_number for item in final.outcome.state.attempts], [1, 2, 3])
        self.assertEqual(
            final.outcome.attempted_orchestrators,
            ("openai-agents-real", "crewai-real", "langgraph-real"),
        )
        self.assertEqual(len(latest_openai.calls), 0)
        self.assertEqual(latest_crew.calls, 0)
        self.assertEqual(latest_graph["count"], 1)
        self.assertEqual(final.approval_record.approver_id, "human-after-restart")


if __name__ == "__main__":
    unittest.main(verbosity=2)
