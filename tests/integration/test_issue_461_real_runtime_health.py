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
from metao.core import ExecutionRequest, ExecutionStatus, HealthStatus, Mission, OrchestratorRegistry
from metao.failure_origin import BoundFailureOriginEvidence, FailureOrigin, FactualFailureOutcome
from metao.runtime_health import RuntimeHealthState
from metao.strategy import OrchestratorStatus, select_orchestrator


CREWAI_VERSION = "1.15.16"
LANGGRAPH_VERSION = "1.2.11"


class _SandboxLLM(BaseLLM):
    response: str = "crewai-real-ok"
    fail: bool = False
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
        if self.fail:
            raise RuntimeError("crewai factual runtime failure")
        return self.response


class _GraphState(TypedDict, total=False):
    objective: str
    result: str


class _RuntimeLocalAuthority:
    def resolve_failure_origin(self, *, request, runtime_id, runtime_version, config_id, error):
        return BoundFailureOriginEvidence(
            producer_id=f"runtime-authority:{runtime_id}",
            mission_id=request.mission.mission_id,
            execution_id=request.execution_id,
            origin=FailureOrigin.RUNTIME_LOCAL,
            outcome=FactualFailureOutcome.FAILED,
            evidence_ref=f"runtime-local://{runtime_id}/{request.execution_id}",
        )


def _build_crew(*, fail: bool = False, response: str = "crewai-real-ok") -> Crew:
    llm = _SandboxLLM(model="metao-health-sandbox", response=response, fail=fail)
    agent = Agent(
        role="metaO health worker",
        goal="Execute the deterministic runtime-health task",
        backstory="A deterministic worker used to validate factual runtime health.",
        llm=llm,
        allow_delegation=False,
        verbose=False,
        max_iter=1,
    )
    task = Task(
        description="Process this objective through the Crew runtime: {objective}",
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


def _build_graph(*, fail: bool = False, result: str = "langgraph-real-ok"):
    def step(state: _GraphState):
        if fail:
            raise RuntimeError("langgraph factual runtime failure")
        return {"result": result}

    builder = StateGraph(_GraphState)
    builder.add_node("run", step)
    builder.add_edge(START, "run")
    builder.add_edge("run", END)
    return builder.compile()


def _request(execution_id: str) -> ExecutionRequest:
    return ExecutionRequest(
        execution_id,
        Mission("issue-461-health", "exercise factual runtime health", frozenset({"workflow"})),
    )


class Issue461RealRuntimeHealthTests(unittest.TestCase):
    def test_two_real_runtimes_feed_equivalent_failed_health_facts(self):
        self.assertEqual(package_version("langgraph"), LANGGRAPH_VERSION)
        self.assertEqual(package_version("crewai"), CREWAI_VERSION)
        authority = _RuntimeLocalAuthority()

        graph = LangGraphOrchestratorAdapter(
            _build_graph(fail=True),
            orchestrator_id="langgraph-real-health",
            version=LANGGRAPH_VERSION,
            config_id="issue-461",
            failure_origin_authority=authority,
        )
        crew = CrewAIOrchestratorAdapter(
            _build_crew(fail=True),
            orchestrator_id="crewai-real-health",
            version=CREWAI_VERSION,
            config_id="issue-461",
            failure_origin_authority=authority,
        )

        graph_result = graph.execute(_request("issue-461-lg-fail"))
        crew_result = crew.execute(_request("issue-461-crew-fail"))

        self.assertEqual(graph_result.status, ExecutionStatus.FAILED)
        self.assertEqual(crew_result.status, ExecutionStatus.FAILED)
        self.assertEqual(graph.health().status, HealthStatus.UNHEALTHY)
        self.assertEqual(crew.health().status, HealthStatus.UNHEALTHY)

        graph_facts = graph.runtime_health_facts()
        crew_facts = crew.runtime_health_facts()
        self.assertEqual(graph_facts.state, RuntimeHealthState.UNHEALTHY)
        self.assertEqual(crew_facts.state, RuntimeHealthState.UNHEALTHY)
        self.assertEqual(
            (
                graph_facts.evidence_basis,
                graph_facts.attempts,
                graph_facts.successes,
                graph_facts.failures,
                graph_facts.consecutive_failures,
                graph_facts.fresh_successes_since_unhealthy,
            ),
            (
                crew_facts.evidence_basis,
                crew_facts.attempts,
                crew_facts.successes,
                crew_facts.failures,
                crew_facts.consecutive_failures,
                crew_facts.fresh_successes_since_unhealthy,
            ),
        )

    def test_catalog_strategy_excludes_failed_real_runtime_in_favor_of_factually_healthy_peer(self):
        graph = LangGraphOrchestratorAdapter(
            _build_graph(fail=True),
            orchestrator_id="langgraph-real-health",
            version=LANGGRAPH_VERSION,
            config_id="issue-461",
            failure_origin_authority=_RuntimeLocalAuthority(),
        )
        crew = CrewAIOrchestratorAdapter(
            _build_crew(response="crewai factual success"),
            orchestrator_id="crewai-real-health",
            version=CREWAI_VERSION,
            config_id="issue-461",
        )

        self.assertEqual(graph.execute(_request("issue-461-lg-route")).status, ExecutionStatus.FAILED)
        self.assertEqual(crew.execute(_request("issue-461-crew-route")).status, ExecutionStatus.SUCCEEDED)

        registry = OrchestratorRegistry()
        registry.register(graph)
        registry.register(crew)
        catalog = OrchestratorCatalog(registry)
        catalog.register(
            "langgraph-real-health",
            normalizer=normalize_langgraph,
            cost=0.0,
            latency_ms=1.0,
            success_rate=1.0,
            quality=1.0,
            reliability=1.0,
        )
        catalog.register(
            "crewai-real-health",
            normalizer=normalize_crewai,
            cost=10.0,
            latency_ms=10_000.0,
            success_rate=0.1,
            quality=0.1,
            reliability=0.1,
        )

        pools = {pool.orchestrator_id: pool for pool in catalog.pools()}
        self.assertEqual(pools["langgraph-real-health"].status, OrchestratorStatus.UNHEALTHY)
        self.assertEqual(pools["crewai-real-health"].status, OrchestratorStatus.HEALTHY)
        self.assertEqual(select_orchestrator(tuple(pools.values())), "crewai-real-health")

    def test_unknown_real_runtime_is_bootstrap_only_behind_factually_healthy_peer(self):
        self.assertEqual(package_version("langgraph"), LANGGRAPH_VERSION)
        self.assertEqual(package_version("crewai"), CREWAI_VERSION)

        graph = LangGraphOrchestratorAdapter(
            _build_graph(result="langgraph factual success"),
            orchestrator_id="langgraph-known-health",
            version=LANGGRAPH_VERSION,
            config_id="issue-461",
        )
        crew = CrewAIOrchestratorAdapter(
            _build_crew(response="crewai bootstrap candidate"),
            orchestrator_id="crewai-unknown-health",
            version=CREWAI_VERSION,
            config_id="issue-461",
        )

        self.assertEqual(
            graph.execute(_request("issue-461-lg-known")).status,
            ExecutionStatus.SUCCEEDED,
        )
        self.assertEqual(graph.runtime_health_facts().state, RuntimeHealthState.HEALTHY)
        self.assertEqual(crew.runtime_health_facts().state, RuntimeHealthState.UNKNOWN)

        registry = OrchestratorRegistry()
        registry.register(graph)
        registry.register(crew)
        catalog = OrchestratorCatalog(registry)
        catalog.register(
            "langgraph-known-health",
            normalizer=normalize_langgraph,
            cost=10.0,
            latency_ms=10_000.0,
            success_rate=0.1,
            quality=0.1,
            reliability=0.1,
        )
        catalog.register(
            "crewai-unknown-health",
            normalizer=normalize_crewai,
            cost=0.0,
            latency_ms=1.0,
            success_rate=1.0,
            quality=1.0,
            reliability=1.0,
        )

        pools = {pool.orchestrator_id: pool for pool in catalog.pools()}
        self.assertEqual(pools["langgraph-known-health"].status, OrchestratorStatus.HEALTHY)
        self.assertEqual(pools["crewai-unknown-health"].status, OrchestratorStatus.UNKNOWN)
        self.assertEqual(select_orchestrator(tuple(pools.values())), "langgraph-known-health")
        self.assertEqual(
            select_orchestrator((pools["crewai-unknown-health"],)),
            "crewai-unknown-health",
        )


if __name__ == "__main__":
    unittest.main(verbosity=2)
