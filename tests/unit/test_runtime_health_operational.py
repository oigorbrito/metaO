from __future__ import annotations

import unittest

from metao.adapters.crewai import CrewAIOrchestratorAdapter
from metao.adapters.langgraph import LangGraphOrchestratorAdapter
from metao.core import (
    ExecutionRequest,
    ExecutionStatus,
    HealthStatus,
    Mission,
    OrchestratorRegistry,
)
from metao.runtime_health import (
    RuntimeHealthPolicy,
    RuntimeHealthState,
    RuntimeHealthTracker,
)


class _CallableGraph:
    def invoke(self, payload):
        return {"result": payload["objective"]}


class _CallableCrew:
    def kickoff(self, *, inputs):
        return {"result": inputs["objective"]}


class RuntimeHealthOperationalTests(unittest.TestCase):
    def test_unknown_factual_health_is_not_reported_healthy_but_remains_bootstrappable(self):
        adapter = LangGraphOrchestratorAdapter(
            _CallableGraph(),
            orchestrator_id="langgraph-bootstrap",
            version="1",
            config_id="cfg-a",
        )
        self.assertEqual(adapter.runtime_health_facts().state, RuntimeHealthState.UNKNOWN)
        self.assertEqual(adapter.health().status, HealthStatus.DEGRADED)

        registry = OrchestratorRegistry()
        registry.register(adapter)
        mission = Mission("m-bootstrap", "bootstrap", frozenset({"workflow"}))
        self.assertEqual(
            [item.descriptor.orchestrator_id for item in registry.eligible(mission)],
            ["langgraph-bootstrap"],
        )

    def test_equivalent_adapters_emit_equivalent_factual_health_shape_after_success(self):
        graph = LangGraphOrchestratorAdapter(
            _CallableGraph(),
            orchestrator_id="langgraph",
            version="1",
            config_id="cfg-shared",
        )
        crew = CrewAIOrchestratorAdapter(
            _CallableCrew(),
            orchestrator_id="crewai",
            version="1",
            config_id="cfg-shared",
        )
        mission = Mission("m-success", "ok", frozenset({"workflow"}))

        graph_result = graph.execute(ExecutionRequest("e-graph", mission))
        crew_result = crew.execute(ExecutionRequest("e-crew", mission))

        self.assertEqual(graph_result.status, ExecutionStatus.SUCCEEDED)
        self.assertEqual(crew_result.status, ExecutionStatus.SUCCEEDED)
        self.assertEqual(graph.health().status, HealthStatus.HEALTHY)
        self.assertEqual(crew.health().status, HealthStatus.HEALTHY)

        graph_facts = graph.runtime_health_facts()
        crew_facts = crew.runtime_health_facts()
        comparable_graph = (
            graph_facts.state,
            graph_facts.evidence_basis,
            graph_facts.attempts,
            graph_facts.successes,
            graph_facts.failures,
            graph_facts.consecutive_failures,
            graph_facts.fresh_successes_since_unhealthy,
        )
        comparable_crew = (
            crew_facts.state,
            crew_facts.evidence_basis,
            crew_facts.attempts,
            crew_facts.successes,
            crew_facts.failures,
            crew_facts.consecutive_failures,
            crew_facts.fresh_successes_since_unhealthy,
        )
        self.assertEqual(comparable_graph, comparable_crew)

    def test_failed_execution_overrides_structural_readiness(self):
        class FailingGraph:
            def invoke(self, payload):
                raise RuntimeError("factual graph failure")

        adapter = LangGraphOrchestratorAdapter(
            FailingGraph(),
            orchestrator_id="langgraph-fail",
            version="1",
        )
        mission = Mission("m-fail", "fail", frozenset({"workflow"}))
        result = adapter.execute(ExecutionRequest("e-fail", mission))

        self.assertEqual(result.status, ExecutionStatus.FAILED)
        self.assertEqual(adapter.runtime_health_facts().state, RuntimeHealthState.UNHEALTHY)
        self.assertEqual(adapter.health().status, HealthStatus.UNHEALTHY)

    def test_three_consecutive_failures_quarantine_and_fresh_window_recovers(self):
        tracker = RuntimeHealthTracker(
            runtime_id="runtime",
            runtime_version="1",
            config_id="cfg",
            policy=RuntimeHealthPolicy(
                window_size=3,
                quarantine_consecutive_failures=3,
                unhealthy_failure_percent=60,
                recovery_successes_required=2,
            ),
        )
        for index in range(3):
            facts = tracker.record_execution(ExecutionStatus.FAILED, execution_id=f"f-{index}")
        self.assertEqual(facts.state, RuntimeHealthState.QUARANTINED)
        self.assertEqual(tracker.report().status, HealthStatus.UNHEALTHY)

        states = []
        for index in range(3):
            states.append(
                tracker.record_execution(ExecutionStatus.SUCCEEDED, execution_id=f"s-{index}").state
            )
        self.assertEqual(states[-1], RuntimeHealthState.HEALTHY)
        self.assertEqual(tracker.report().status, HealthStatus.HEALTHY)

    def test_cancelled_execution_does_not_mint_failure_evidence(self):
        adapter = CrewAIOrchestratorAdapter(
            _CallableCrew(),
            orchestrator_id="crewai-cancel",
            version="1",
        )
        adapter.cancel("e-cancel")
        mission = Mission("m-cancel", "cancel", frozenset({"workflow"}))
        result = adapter.execute(ExecutionRequest("e-cancel", mission))

        self.assertEqual(result.status, ExecutionStatus.CANCELLED)
        facts = adapter.runtime_health_facts()
        self.assertEqual(facts.state, RuntimeHealthState.UNKNOWN)
        self.assertEqual(facts.attempts, 0)
        self.assertEqual(facts.failures, 0)

    def test_runtime_health_facts_are_bound_to_runtime_version_and_config(self):
        adapter = CrewAIOrchestratorAdapter(
            _CallableCrew(),
            orchestrator_id="crewai-bound",
            version="1.15.16",
            config_id="crew-config-v2",
        )
        facts = adapter.runtime_health_facts()
        self.assertEqual(facts.runtime_id, "crewai-bound")
        self.assertEqual(facts.runtime_version, "1.15.16")
        self.assertEqual(facts.config_id, "crew-config-v2")
        self.assertEqual(facts.evidence_basis, "ADAPTER_VERIFIED")


if __name__ == "__main__":
    unittest.main(verbosity=2)
