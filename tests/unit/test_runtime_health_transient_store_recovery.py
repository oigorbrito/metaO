from __future__ import annotations

import unittest

from metao.adapters.crewai import CrewAIOrchestratorAdapter
from metao.adapters.langgraph import LangGraphOrchestratorAdapter
from metao.core import ExecutionRequest, ExecutionStatus, HealthStatus, Mission
from metao.runtime_health import InMemoryRuntimeHealthStore, RuntimeHealthState


class _HealthyGraph:
    def invoke(self, payload):
        return {"result": payload["objective"]}


class _HealthyCrew:
    def kickoff(self, *, inputs):
        return {"result": inputs["objective"]}


class _FailNWritesStore:
    def __init__(self, failures: int) -> None:
        self.inner = InMemoryRuntimeHealthStore()
        self.remaining_failures = failures

    def record(self, **kwargs):
        if self.remaining_failures > 0:
            self.remaining_failures -= 1
            raise OSError("transient health write failure")
        return self.inner.record(**kwargs)

    def history(self, **kwargs):
        return self.inner.history(**kwargs)


class _FailNReadsStore:
    def __init__(self, failures: int) -> None:
        self.inner = InMemoryRuntimeHealthStore()
        self.remaining_failures = failures

    def record(self, **kwargs):
        return self.inner.record(**kwargs)

    def history(self, **kwargs):
        if self.remaining_failures > 0:
            self.remaining_failures -= 1
            raise OSError("transient health read failure")
        return self.inner.history(**kwargs)


def _request(execution_id: str) -> ExecutionRequest:
    return ExecutionRequest(
        execution_id,
        Mission("health-transient", "exercise transient health store", frozenset({"workflow"})),
    )


class RuntimeHealthTransientStoreRecoveryTests(unittest.TestCase):
    def adapters(self, store):
        return (
            LangGraphOrchestratorAdapter(
                _HealthyGraph(),
                orchestrator_id="langgraph-transient",
                version="1.2.11",
                config_id="cfg",
                health_store=store,
            ),
            CrewAIOrchestratorAdapter(
                _HealthyCrew(),
                orchestrator_id="crewai-transient",
                version="1.15.16",
                config_id="cfg",
                health_store=store,
            ),
        )

    def test_transient_write_failure_replays_original_fact_before_runtime_is_routable(self):
        cases = (
            (
                LangGraphOrchestratorAdapter,
                _HealthyGraph(),
                "langgraph-transient",
                "1.2.11",
            ),
            (
                CrewAIOrchestratorAdapter,
                _HealthyCrew(),
                "crewai-transient",
                "1.15.16",
            ),
        )
        for adapter_type, runtime, orchestrator_id, version in cases:
            with self.subTest(orchestrator_id=orchestrator_id):
                store = _FailNWritesStore(1)
                adapter = adapter_type(
                    runtime,
                    orchestrator_id=orchestrator_id,
                    version=version,
                    config_id="cfg",
                    health_store=store,
                )

                result = adapter.execute(_request(f"{orchestrator_id}-execution"))
                self.assertEqual(result.status, ExecutionStatus.SUCCEEDED)

                # The first durable write failed. The health read must replay that
                # exact observation before the runtime can become routable again.
                self.assertEqual(adapter.health().status, HealthStatus.HEALTHY)
                history = store.inner.history(
                    runtime_id=orchestrator_id,
                    runtime_version=version,
                    config_id="cfg",
                )
                self.assertEqual(len(history), 1)
                self.assertEqual(history[0].execution_id, result.execution_id)
                self.assertEqual(history[0].status, ExecutionStatus.SUCCEEDED)
                self.assertEqual(
                    adapter.runtime_health_facts().state,
                    RuntimeHealthState.HEALTHY,
                )

    def test_transient_read_failure_recovers_without_minting_health_evidence(self):
        cases = (
            (
                LangGraphOrchestratorAdapter,
                _HealthyGraph(),
                "langgraph-read",
            ),
            (
                CrewAIOrchestratorAdapter,
                _HealthyCrew(),
                "crewai-read",
            ),
        )
        for adapter_type, runtime, orchestrator_id in cases:
            with self.subTest(orchestrator_id=orchestrator_id):
                store = _FailNReadsStore(1)
                adapter = adapter_type(
                    runtime,
                    orchestrator_id=orchestrator_id,
                    health_store=store,
                )
                self.assertEqual(adapter.health().status, HealthStatus.UNHEALTHY)
                self.assertEqual(adapter.health().status, HealthStatus.DEGRADED)
                self.assertEqual(
                    adapter.runtime_health_facts().state,
                    RuntimeHealthState.UNKNOWN,
                )
                self.assertEqual(
                    store.inner.history(
                        runtime_id=orchestrator_id,
                        runtime_version="1",
                        config_id="default",
                    ),
                    (),
                )

    def test_multiple_pending_observations_replay_fifo_without_duplicate_facts(self):
        store = _FailNWritesStore(2)
        adapter = LangGraphOrchestratorAdapter(
            _HealthyGraph(),
            orchestrator_id="langgraph-fifo",
            version="1.2.11",
            config_id="cfg",
            health_store=store,
        )

        first = adapter.execute(_request("fifo-1"))
        second = adapter.execute(_request("fifo-2"))
        self.assertEqual(first.status, ExecutionStatus.SUCCEEDED)
        self.assertEqual(second.status, ExecutionStatus.SUCCEEDED)

        self.assertEqual(adapter.health().status, HealthStatus.HEALTHY)
        history = store.inner.history(
            runtime_id="langgraph-fifo",
            runtime_version="1.2.11",
            config_id="cfg",
        )
        self.assertEqual(
            tuple((fact.sequence, fact.execution_id) for fact in history),
            ((1, "fifo-1"), (2, "fifo-2")),
        )


if __name__ == "__main__":
    unittest.main(verbosity=2)
