from __future__ import annotations

from importlib.metadata import version as package_version
from typing import Any, ClassVar
import unittest

from crewai import Agent, Crew, Process, Task
from crewai.llms.base_llm import BaseLLM
from langgraph.graph import END, START, StateGraph
from typing_extensions import TypedDict

from metao.adapters.crewai import CrewAIOrchestratorAdapter, normalize_evidence as normalize_crewai
from metao.adapters.langgraph import LangGraphOrchestratorAdapter, normalize_evidence as normalize_langgraph
from metao.catalog import OrchestratorCatalog
from metao.core import ExecutionRequest, Mission, OrchestratorRegistry
from metao.runtime_admission import RuntimeAdmissionGate
from metao.runtime_certification import InMemoryRuntimeCertificationStore


CREWAI_VERSION = "1.15.16"
LANGGRAPH_VERSION = "1.2.11"


class SandboxLLM(BaseLLM):
    response: str = "crewai-certification-ok"
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
        return self.response

    @classmethod
    def reset(cls) -> None:
        cls.calls = 0


class GraphState(TypedDict, total=False):
    objective: str
    result: str


def build_crew() -> Crew:
    llm = SandboxLLM(model="metao-certification-sandbox")
    agent = Agent(
        role="metaO certification worker",
        goal="Complete the deterministic certification probe",
        backstory="A local deterministic worker used only for runtime certification tests.",
        llm=llm,
        allow_delegation=False,
        verbose=False,
        max_iter=1,
    )
    task = Task(
        description="Process this certification objective: {objective}",
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


def build_graph():
    def step(state: GraphState):
        return {"result": "langgraph-certification-ok"}

    builder = StateGraph(GraphState)
    builder.add_node("run", step)
    builder.add_edge(START, "run")
    builder.add_edge("run", END)
    return builder.compile()


def request(execution_id: str) -> ExecutionRequest:
    return ExecutionRequest(
        execution_id,
        Mission(
            f"mission-{execution_id}",
            "certify real orchestrator boundary",
            frozenset({"workflow"}),
        ),
        {
            "obligation_id": "execution_result",
            "subject_id": "r3-subject",
            "subject_state_id": "r3-state",
            "verification_context_id": "r3-verify",
            "policy_bundle_id": "r3-policy",
            "verifier_id": "adapter-observer",
            "authority_id": "metao-runtime",
            "created_at_epoch": 100.0,
        },
    )


def admission_fixture():
    registry = OrchestratorRegistry()
    catalog = OrchestratorCatalog(registry)
    certifications = InMemoryRuntimeCertificationStore()
    gate = RuntimeAdmissionGate(registry, catalog, certifications)
    return registry, catalog, certifications, gate


class RealRuntimeCertificationV1Tests(unittest.TestCase):
    def setUp(self) -> None:
        SandboxLLM.reset()

    def test_01_pinned_real_runtime_versions_are_the_expected_evidence_targets(self):
        self.assertEqual(package_version("langgraph"), LANGGRAPH_VERSION)
        self.assertEqual(package_version("crewai"), CREWAI_VERSION)

    def test_02_real_langgraph_adapter_is_conformant_certified_and_admitted(self):
        registry, catalog, certifications, gate = admission_fixture()
        adapter = LangGraphOrchestratorAdapter(
            build_graph(),
            orchestrator_id="langgraph-certified-real",
            version=LANGGRAPH_VERSION,
        )
        record = gate.admit(
            adapter,
            normalize_langgraph,
            request("r3-langgraph-certification"),
            cost=0.1,
            latency_ms=10.0,
        )
        self.assertTrue(record.conformance.passed)
        self.assertIsNotNone(record.certification)
        self.assertTrue(record.certification.passed)
        self.assertEqual(record.certification.runtime_version, LANGGRAPH_VERSION)
        self.assertIs(registry.get("langgraph-certified-real"), adapter)
        self.assertEqual(len(catalog.entries()), 1)
        self.assertEqual(certifications.history("langgraph-certified-real"), (record.certification,))

    def test_03_real_crewai_adapter_is_conformant_certified_and_admitted(self):
        registry, catalog, certifications, gate = admission_fixture()
        adapter = CrewAIOrchestratorAdapter(
            build_crew(),
            orchestrator_id="crewai-certified-real",
            version=CREWAI_VERSION,
        )
        record = gate.admit(
            adapter,
            normalize_crewai,
            request("r3-crewai-certification"),
            cost=0.2,
            latency_ms=20.0,
        )
        self.assertTrue(record.conformance.passed)
        self.assertIsNotNone(record.certification)
        self.assertTrue(record.certification.passed)
        self.assertEqual(record.certification.runtime_version, CREWAI_VERSION)
        self.assertGreaterEqual(SandboxLLM.calls, 1)
        self.assertIs(registry.get("crewai-certified-real"), adapter)
        self.assertEqual(len(catalog.entries()), 1)
        self.assertEqual(certifications.history("crewai-certified-real"), (record.certification,))

    def test_04_two_real_frameworks_share_one_certification_and_admission_boundary(self):
        registry, catalog, certifications, gate = admission_fixture()
        langgraph = LangGraphOrchestratorAdapter(
            build_graph(),
            orchestrator_id="langgraph-certified-real",
            version=LANGGRAPH_VERSION,
        )
        crewai = CrewAIOrchestratorAdapter(
            build_crew(),
            orchestrator_id="crewai-certified-real",
            version=CREWAI_VERSION,
        )
        langgraph_record = gate.admit(
            langgraph,
            normalize_langgraph,
            request("r3-shared-langgraph"),
        )
        crewai_record = gate.admit(
            crewai,
            normalize_crewai,
            request("r3-shared-crewai"),
        )
        self.assertTrue(langgraph_record.certification.passed)
        self.assertTrue(crewai_record.certification.passed)
        self.assertEqual(
            {item.orchestrator_id for item in catalog.entries()},
            {"langgraph-certified-real", "crewai-certified-real"},
        )
        self.assertEqual(len(certifications.history("langgraph-certified-real")), 1)
        self.assertEqual(len(certifications.history("crewai-certified-real")), 1)
        self.assertIs(registry.get("langgraph-certified-real"), langgraph)
        self.assertIs(registry.get("crewai-certified-real"), crewai)


if __name__ == "__main__":
    unittest.main(verbosity=2)
