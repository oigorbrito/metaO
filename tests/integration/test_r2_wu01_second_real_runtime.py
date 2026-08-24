from __future__ import annotations

from dataclasses import fields, replace
from importlib.metadata import version as package_version
from threading import Event, Thread
from typing import Any, ClassVar
import unittest

from crewai import Agent, Crew, Process, Task
from crewai.llms.base_llm import BaseLLM
from langgraph.graph import END, START, StateGraph
from typing_extensions import TypedDict

from metao.acceptance import AcceptanceContext, AcceptanceDecision
from metao.adapters.crewai import CrewAIOrchestratorAdapter, normalize_evidence as normalize_crewai
from metao.adapters.langgraph import LangGraphOrchestratorAdapter, normalize_evidence as normalize_langgraph
from metao.catalog import OrchestratorCatalog
from metao.control_plane import MissionStatus, execute_mission, execute_mission_once
from metao.core import ExecutionRequest, ExecutionStatus, Mission, OrchestratorRegistry
from metao.execution_handle import InMemoryExecutionHandleStore
from metao.governance import AcceptanceBudget, evaluate_policy
from metao.mission_store import InMemoryMissionStore
from metao.observability import InMemoryEventLedger
from metao.observed_operator import ObservableMissionOperator
from metao.operator import MissionOperator
from metao.strategy import OrchestratorPoolState, OrchestratorStatus


CREWAI_VERSION = "1.15.16"
LANGGRAPH_VERSION = "1.2.11"


class SandboxLLM(BaseLLM):
    """Deterministic CrewAI LLM used only to exercise the real Crew runtime."""

    response: str = "crewai-real-ok"
    fail: bool = False
    block: bool = False

    calls: ClassVar[int] = 0
    started: ClassVar[Event] = Event()
    release: ClassVar[Event] = Event()

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
        type(self).started.set()
        if self.block and not type(self).release.wait(5.0):
            raise TimeoutError("sandbox CrewAI LLM release timed out")
        if self.fail:
            raise RuntimeError("crewai sandbox failure")
        return self.response

    @classmethod
    def reset(cls) -> None:
        cls.calls = 0
        cls.started.clear()
        cls.release.clear()


class GraphState(TypedDict, total=False):
    objective: str
    result: str


def build_crew(*, response: str = "crewai-real-ok", fail: bool = False, block: bool = False) -> Crew:
    llm = SandboxLLM(model="metao-sandbox", response=response, fail=fail, block=block)
    agent = Agent(
        role="metaO sandbox worker",
        goal="Complete the assigned deterministic sandbox task",
        backstory="A deterministic worker used to validate CrewAI runtime integration.",
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


def build_graph(*, result: str = "langgraph-real-ok", fail: bool = False, calls: dict[str, int] | None = None):
    def step(state: GraphState):
        if calls is not None:
            calls["count"] = calls.get("count", 0) + 1
        if fail:
            raise RuntimeError("langgraph sandbox failure")
        return {"result": result}

    builder = StateGraph(GraphState)
    builder.add_node("run", step)
    builder.add_edge(START, "run")
    builder.add_edge("run", END)
    return builder.compile()


def context() -> AcceptanceContext:
    return AcceptanceContext(
        "r2-subject",
        "r2-state",
        "r2-verify",
        "r2-policy",
        frozenset({"execution_result"}),
    )


def allow_policy():
    return evaluate_policy(policy_bundle_id="r2-policy", allowed=True)


def budget(*, money: float = 10.0) -> AcceptanceBudget:
    return AcceptanceBudget(money, 10_000, 60.0, 10)


def pool(orchestrator_id: str, *, preferred: bool) -> OrchestratorPoolState:
    if preferred:
        return OrchestratorPoolState(
            orchestrator_id,
            OrchestratorStatus.HEALTHY,
            frozenset({"workflow"}),
            success_rate=1.0,
            quality=1.0,
            reliability=1.0,
            latency_ms=1.0,
            cost=0.0,
        )
    return OrchestratorPoolState(
        orchestrator_id,
        OrchestratorStatus.HEALTHY,
        frozenset({"workflow"}),
        success_rate=0.1,
        quality=0.1,
        reliability=0.1,
        latency_ms=10_000.0,
        cost=10.0,
    )


def run_once(*, mission: Mission, adapter, normalizer, execution_id: str, policy=None, acceptance_budget=None):
    registry = OrchestratorRegistry()
    registry.register(adapter)
    return execute_mission_once(
        mission=mission,
        registry=registry,
        pools=(pool(adapter.descriptor.orchestrator_id, preferred=True),),
        normalizers={adapter.descriptor.orchestrator_id: normalizer},
        policy=policy or allow_policy(),
        budget=acceptance_budget or budget(),
        acceptance_context=context(),
        execution_id=execution_id,
        now_epoch=100.0,
    )


def stale_normalizer(normalizer):
    def normalize(**kwargs):
        return replace(normalizer(**kwargs), subject_state_id="stale-runtime-state")

    return normalize


def observable_run(*, mission_id: str, adapter, normalizer):
    registry = OrchestratorRegistry()
    registry.register(adapter)
    catalog = OrchestratorCatalog(registry)
    catalog.register(
        adapter.descriptor.orchestrator_id,
        normalizer=normalizer,
        cost=0.1,
        latency_ms=10.0,
        success_rate=0.99,
        quality=0.99,
        reliability=0.99,
    )
    ledger = InMemoryEventLedger()
    operator = ObservableMissionOperator(
        MissionOperator(registry=registry, catalog=catalog, store=InMemoryMissionStore()),
        ledger,
    )
    outcome = operator.run(
        Mission(mission_id, "compare runtime observability", frozenset({"workflow"})),
        policy=allow_policy(),
        budget=budget(),
        acceptance_context=context(),
        now_epoch=100.0,
    )
    return outcome, operator.events(mission_id)


class SecondRealRuntimeSandboxV1Tests(unittest.TestCase):
    def setUp(self) -> None:
        SandboxLLM.reset()

    def test_01_real_crewai_executes_through_orchestrator_contract(self):
        self.assertEqual(package_version("crewai"), CREWAI_VERSION)
        adapter = CrewAIOrchestratorAdapter(
            build_crew(response="crewai-real-contract"),
            orchestrator_id="crewai-real",
            version=CREWAI_VERSION,
        )
        outcome = run_once(
            mission=Mission("r2-crewai-real", "execute real CrewAI", frozenset({"workflow"})),
            adapter=adapter,
            normalizer=normalize_crewai,
            execution_id="r2-crewai-exec",
        )
        self.assertEqual(outcome.execution.status, ExecutionStatus.SUCCEEDED)
        self.assertEqual(outcome.orchestrator_id, "crewai-real")
        self.assertEqual(outcome.execution.output["result"], "crewai-real-contract")
        self.assertEqual(outcome.acceptance.decision, AcceptanceDecision.ACCEPT)
        self.assertGreaterEqual(SandboxLLM.calls, 1)

    def test_02_crewai_produces_normalized_evidence_envelope(self):
        adapter = CrewAIOrchestratorAdapter(build_crew(), orchestrator_id="crewai-evidence", version=CREWAI_VERSION)
        mission = Mission("r2-evidence", "normalize CrewAI evidence", frozenset({"workflow"}))
        request = ExecutionRequest(
            "r2-evidence-exec",
            mission,
            {
                "obligation_id": "execution_result",
                "subject_id": "r2-subject",
                "subject_state_id": "r2-state",
                "verification_context_id": "r2-verify",
                "policy_bundle_id": "r2-policy",
                "verifier_id": "adapter-observer",
                "authority_id": "metao-runtime",
                "created_at_epoch": 100.0,
            },
        )
        result = adapter.execute(request)
        evidence = normalize_crewai(
            request=request,
            orchestrator_id=adapter.descriptor.orchestrator_id,
            adapter_version=adapter.descriptor.version,
            output=result.output,
            attempt_id="attempt-1",
        )
        self.assertEqual(result.status, ExecutionStatus.SUCCEEDED)
        self.assertEqual(evidence.mission_id, mission.mission_id)
        self.assertEqual(evidence.orchestrator_id, "crewai-evidence")
        self.assertTrue(evidence.payload_digest)
        self.assertTrue(evidence.provenance_root.startswith("crewai:"))
        self.assertTrue(evidence.passed)

    def test_03_same_mission_runs_in_real_langgraph_or_real_crewai(self):
        self.assertEqual(package_version("langgraph"), LANGGRAPH_VERSION)
        mission = Mission("r2-same-mission", "same mission across runtimes", frozenset({"workflow"}))
        langgraph = run_once(
            mission=mission,
            adapter=LangGraphOrchestratorAdapter(build_graph(result="langgraph:same"), orchestrator_id="langgraph-real", version=LANGGRAPH_VERSION),
            normalizer=normalize_langgraph,
            execution_id="r2-same-lg",
        )
        SandboxLLM.reset()
        crewai = run_once(
            mission=mission,
            adapter=CrewAIOrchestratorAdapter(build_crew(response="crewai:same"), orchestrator_id="crewai-real", version=CREWAI_VERSION),
            normalizer=normalize_crewai,
            execution_id="r2-same-crew",
        )
        self.assertEqual(langgraph.acceptance.decision, AcceptanceDecision.ACCEPT)
        self.assertEqual(crewai.acceptance.decision, AcceptanceDecision.ACCEPT)
        self.assertEqual(langgraph.execution.output["result"], "langgraph:same")
        self.assertEqual(crewai.execution.output["result"], "crewai:same")

    def test_04_strategy_selects_between_two_real_runtimes(self):
        registry = OrchestratorRegistry()
        registry.register(LangGraphOrchestratorAdapter(build_graph(result="langgraph:not-selected"), orchestrator_id="langgraph-real", version=LANGGRAPH_VERSION))
        registry.register(CrewAIOrchestratorAdapter(build_crew(response="crewai:selected"), orchestrator_id="crewai-real", version=CREWAI_VERSION))
        outcome = execute_mission_once(
            mission=Mission("r2-select", "select a runtime", frozenset({"workflow"})),
            registry=registry,
            pools=(pool("langgraph-real", preferred=False), pool("crewai-real", preferred=True)),
            normalizers={"langgraph-real": normalize_langgraph, "crewai-real": normalize_crewai},
            policy=allow_policy(),
            budget=budget(),
            acceptance_context=context(),
            execution_id="r2-select-exec",
            now_epoch=100.0,
        )
        self.assertEqual(outcome.orchestrator_id, "crewai-real")
        self.assertEqual(outcome.execution.output["result"], "crewai:selected")

    def test_05_langgraph_failure_falls_back_to_real_crewai(self):
        registry = OrchestratorRegistry()
        registry.register(LangGraphOrchestratorAdapter(build_graph(fail=True), orchestrator_id="langgraph-real", version=LANGGRAPH_VERSION))
        registry.register(CrewAIOrchestratorAdapter(build_crew(response="crewai:fallback"), orchestrator_id="crewai-real", version=CREWAI_VERSION))
        outcome = execute_mission(
            mission=Mission("r2-lg-to-crew", "fallback from LangGraph", frozenset({"workflow"})),
            registry=registry,
            pools=(pool("langgraph-real", preferred=True), pool("crewai-real", preferred=False)),
            normalizers={"langgraph-real": normalize_langgraph, "crewai-real": normalize_crewai},
            policy=allow_policy(),
            budget=budget(),
            acceptance_context=context(),
            execution_id_prefix="r2-lg-to-crew",
            now_epoch=100.0,
            max_attempts=2,
        )
        self.assertEqual(outcome.attempted_orchestrators, ("langgraph-real", "crewai-real"))
        self.assertEqual(outcome.orchestrator_id, "crewai-real")
        self.assertEqual(outcome.acceptance.decision, AcceptanceDecision.ACCEPT)

    def test_06_crewai_failure_falls_back_to_real_langgraph(self):
        registry = OrchestratorRegistry()
        registry.register(CrewAIOrchestratorAdapter(build_crew(fail=True), orchestrator_id="crewai-real", version=CREWAI_VERSION))
        registry.register(LangGraphOrchestratorAdapter(build_graph(result="langgraph:fallback"), orchestrator_id="langgraph-real", version=LANGGRAPH_VERSION))
        outcome = execute_mission(
            mission=Mission("r2-crew-to-lg", "fallback from CrewAI", frozenset({"workflow"})),
            registry=registry,
            pools=(pool("crewai-real", preferred=True), pool("langgraph-real", preferred=False)),
            normalizers={"crewai-real": normalize_crewai, "langgraph-real": normalize_langgraph},
            policy=allow_policy(),
            budget=budget(),
            acceptance_context=context(),
            execution_id_prefix="r2-crew-to-lg",
            now_epoch=100.0,
            max_attempts=2,
        )
        self.assertEqual(outcome.attempted_orchestrators, ("crewai-real", "langgraph-real"))
        self.assertEqual(outcome.orchestrator_id, "langgraph-real")
        self.assertEqual(outcome.execution.output["result"], "langgraph:fallback")
        self.assertEqual(outcome.acceptance.decision, AcceptanceDecision.ACCEPT)

    def test_07_policy_gate_is_identical_for_both_real_runtimes(self):
        deny = evaluate_policy(policy_bundle_id="r2-policy", allowed=False, reason="roadmap2 deny")
        graph_calls = {"count": 0}
        graph = run_once(
            mission=Mission("r2-policy-lg", "deny LangGraph", frozenset({"workflow"})),
            adapter=LangGraphOrchestratorAdapter(build_graph(calls=graph_calls), orchestrator_id="langgraph-real", version=LANGGRAPH_VERSION),
            normalizer=normalize_langgraph,
            execution_id="r2-policy-lg-exec",
            policy=deny,
        )
        SandboxLLM.reset()
        crew = run_once(
            mission=Mission("r2-policy-crew", "deny CrewAI", frozenset({"workflow"})),
            adapter=CrewAIOrchestratorAdapter(build_crew(), orchestrator_id="crewai-real", version=CREWAI_VERSION),
            normalizer=normalize_crewai,
            execution_id="r2-policy-crew-exec",
            policy=deny,
        )
        self.assertEqual(graph.acceptance.decision, AcceptanceDecision.BLOCK)
        self.assertEqual(crew.acceptance.decision, AcceptanceDecision.BLOCK)
        self.assertEqual(graph_calls["count"], 0)
        self.assertEqual(SandboxLLM.calls, 0)

    def test_08_budget_gate_is_identical_for_both_real_runtimes(self):
        graph_calls = {"count": 0}
        graph = run_once(
            mission=Mission("r2-budget-lg", "budget LangGraph", frozenset({"workflow"})),
            adapter=LangGraphOrchestratorAdapter(build_graph(calls=graph_calls), orchestrator_id="langgraph-real", version=LANGGRAPH_VERSION),
            normalizer=normalize_langgraph,
            execution_id="r2-budget-lg-exec",
            acceptance_budget=budget(money=0.0),
        )
        SandboxLLM.reset()
        crew = run_once(
            mission=Mission("r2-budget-crew", "budget CrewAI", frozenset({"workflow"})),
            adapter=CrewAIOrchestratorAdapter(build_crew(), orchestrator_id="crewai-real", version=CREWAI_VERSION),
            normalizer=normalize_crewai,
            execution_id="r2-budget-crew-exec",
            acceptance_budget=budget(money=0.0),
        )
        self.assertEqual(graph.acceptance.decision, AcceptanceDecision.BLOCK)
        self.assertEqual(crew.acceptance.decision, AcceptanceDecision.BLOCK)
        self.assertEqual(graph_calls["count"], 0)
        self.assertEqual(SandboxLLM.calls, 0)

    def test_09_independent_acceptance_rejects_stale_evidence_from_either_runtime(self):
        graph = run_once(
            mission=Mission("r2-accept-lg", "stale LangGraph", frozenset({"workflow"})),
            adapter=LangGraphOrchestratorAdapter(build_graph(), orchestrator_id="langgraph-real", version=LANGGRAPH_VERSION),
            normalizer=stale_normalizer(normalize_langgraph),
            execution_id="r2-accept-lg-exec",
        )
        SandboxLLM.reset()
        crew = run_once(
            mission=Mission("r2-accept-crew", "stale CrewAI", frozenset({"workflow"})),
            adapter=CrewAIOrchestratorAdapter(build_crew(), orchestrator_id="crewai-real", version=CREWAI_VERSION),
            normalizer=stale_normalizer(normalize_crewai),
            execution_id="r2-accept-crew-exec",
        )
        self.assertEqual(graph.execution.status, ExecutionStatus.SUCCEEDED)
        self.assertEqual(crew.execution.status, ExecutionStatus.SUCCEEDED)
        self.assertEqual(graph.acceptance.decision, AcceptanceDecision.STALE)
        self.assertEqual(crew.acceptance.decision, AcceptanceDecision.STALE)
        self.assertIn("subject_state_mismatch", graph.acceptance.reasons)
        self.assertIn("subject_state_mismatch", crew.acceptance.reasons)

    def test_10_observability_event_shape_is_runtime_neutral(self):
        graph_outcome, graph_events = observable_run(
            mission_id="r2-events-lg",
            adapter=LangGraphOrchestratorAdapter(build_graph(), orchestrator_id="langgraph-real", version=LANGGRAPH_VERSION),
            normalizer=normalize_langgraph,
        )
        SandboxLLM.reset()
        crew_outcome, crew_events = observable_run(
            mission_id="r2-events-crew",
            adapter=CrewAIOrchestratorAdapter(build_crew(), orchestrator_id="crewai-real", version=CREWAI_VERSION),
            normalizer=normalize_crewai,
        )
        self.assertEqual(graph_outcome.acceptance.decision, AcceptanceDecision.ACCEPT)
        self.assertEqual(crew_outcome.acceptance.decision, AcceptanceDecision.ACCEPT)
        self.assertEqual([event.kind for event in graph_events], [event.kind for event in crew_events])
        self.assertEqual([set(event.payload.keys()) for event in graph_events], [set(event.payload.keys()) for event in crew_events])

    def test_11_attempt_telemetry_shape_is_runtime_neutral(self):
        mission = Mission("r2-telemetry", "compare attempt telemetry", frozenset({"workflow"}))
        graph = run_once(
            mission=mission,
            adapter=LangGraphOrchestratorAdapter(build_graph(), orchestrator_id="langgraph-real", version=LANGGRAPH_VERSION),
            normalizer=normalize_langgraph,
            execution_id="r2-telemetry-lg",
        )
        SandboxLLM.reset()
        crew = run_once(
            mission=mission,
            adapter=CrewAIOrchestratorAdapter(build_crew(), orchestrator_id="crewai-real", version=CREWAI_VERSION),
            normalizer=normalize_crewai,
            execution_id="r2-telemetry-crew",
        )
        graph_attempt = graph.state.attempts[0]
        crew_attempt = crew.state.attempts[0]
        self.assertEqual([item.name for item in fields(graph_attempt)], [item.name for item in fields(crew_attempt)])
        self.assertEqual(graph_attempt.execution_status, ExecutionStatus.SUCCEEDED)
        self.assertEqual(crew_attempt.execution_status, ExecutionStatus.SUCCEEDED)
        self.assertEqual(graph_attempt.acceptance_decision, AcceptanceDecision.ACCEPT)
        self.assertEqual(crew_attempt.acceptance_decision, AcceptanceDecision.ACCEPT)

    def test_12_inflight_crewai_cancel_is_fail_closed_when_runtime_finishes_late(self):
        SandboxLLM.reset()
        adapter = CrewAIOrchestratorAdapter(
            build_crew(response="crewai:late-success", block=True),
            orchestrator_id="crewai-real",
            version=CREWAI_VERSION,
        )
        registry = OrchestratorRegistry()
        registry.register(adapter)
        catalog = OrchestratorCatalog(registry)
        catalog.register(
            "crewai-real",
            normalizer=normalize_crewai,
            cost=0.1,
            latency_ms=10.0,
            success_rate=0.99,
            quality=0.99,
            reliability=0.99,
        )
        operator = MissionOperator(registry=registry, catalog=catalog, store=InMemoryMissionStore())
        operator.configure_execution_handles(InMemoryExecutionHandleStore(), poll_interval_s=0.01)
        result: dict[str, Any] = {}

        def run_mission() -> None:
            result["outcome"] = operator.run(
                Mission("r2-cancel-crew", "cancel real CrewAI", frozenset({"workflow"})),
                policy=allow_policy(),
                budget=budget(),
                acceptance_context=context(),
            )

        thread = Thread(target=run_mission)
        thread.start()
        self.assertTrue(SandboxLLM.started.wait(3.0))
        operator.cancel("r2-cancel-crew")
        SandboxLLM.release.set()
        thread.join(5.0)
        self.assertFalse(thread.is_alive())
        outcome = result["outcome"]
        self.assertEqual(outcome.execution.status, ExecutionStatus.SUCCEEDED)
        self.assertEqual(outcome.state.status, MissionStatus.BLOCKED)
        self.assertEqual(outcome.acceptance.decision, AcceptanceDecision.BLOCK)
        self.assertIn("cancel_requested_runtime_completed", outcome.acceptance.reasons)

    def test_13_runtime_swap_requires_no_core_specific_code_path(self):
        graph = LangGraphOrchestratorAdapter(build_graph(), orchestrator_id="runtime", version=LANGGRAPH_VERSION)
        crew = CrewAIOrchestratorAdapter(build_crew(), orchestrator_id="runtime", version=CREWAI_VERSION)
        mission = Mission("r2-swap", "swap complete runtime", frozenset({"workflow"}))
        graph_result = run_once(mission=mission, adapter=graph, normalizer=normalize_langgraph, execution_id="r2-swap-lg")
        SandboxLLM.reset()
        crew_result = run_once(mission=mission, adapter=crew, normalizer=normalize_crewai, execution_id="r2-swap-crew")
        self.assertEqual(graph_result.acceptance.decision, AcceptanceDecision.ACCEPT)
        self.assertEqual(crew_result.acceptance.decision, AcceptanceDecision.ACCEPT)
        self.assertEqual(graph.descriptor.capabilities, crew.descriptor.capabilities)
        self.assertEqual(graph.descriptor.orchestrator_id, crew.descriptor.orchestrator_id)


if __name__ == "__main__":
    unittest.main(verbosity=2)
