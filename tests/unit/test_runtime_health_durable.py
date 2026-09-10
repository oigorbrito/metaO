from __future__ import annotations

from pathlib import Path
import tempfile
import unittest

from metao.adapters.crewai import CrewAIOrchestratorAdapter
from metao.adapters.langgraph import LangGraphOrchestratorAdapter
from metao.core import ExecutionRequest, ExecutionStatus, HealthStatus, Mission
from metao.runtime_health import (
    RuntimeHealthConflict,
    RuntimeHealthPolicy,
    RuntimeHealthState,
    RuntimeHealthTracker,
)
from metao.sqlite_runtime_health import SQLiteRuntimeHealthStore


class _FailingGraph:
    def invoke(self, payload):
        raise RuntimeError("runtime failure")


class _HealthyGraph:
    def invoke(self, payload):
        return {"result": payload["objective"]}


class _HealthyCrew:
    def kickoff(self, *, inputs):
        return {"result": inputs["objective"]}


class _BrokenHealthStore:
    def record(self, **kwargs):
        raise OSError("health persistence unavailable")

    def history(self, **kwargs):
        return ()


def _request(execution_id: str) -> ExecutionRequest:
    return ExecutionRequest(
        execution_id,
        Mission("health-durable", "exercise durable health", frozenset({"workflow"})),
    )


class DurableRuntimeHealthTests(unittest.TestCase):
    def policy(self) -> RuntimeHealthPolicy:
        return RuntimeHealthPolicy(
            window_size=3,
            quarantine_consecutive_failures=3,
            unhealthy_failure_percent=60,
            recovery_successes_required=2,
        )

    def test_sqlite_quarantine_survives_tracker_restart_and_recovers_from_fresh_facts(self):
        with tempfile.TemporaryDirectory() as temp:
            path = Path(temp) / "runtime.db"
            first = RuntimeHealthTracker(
                runtime_id="runtime",
                runtime_version="1",
                config_id="cfg",
                policy=self.policy(),
                store=SQLiteRuntimeHealthStore(path),
            )
            for index in range(3):
                facts = first.record_execution(
                    ExecutionStatus.FAILED,
                    execution_id=f"failure-{index}",
                )
            self.assertEqual(facts.state, RuntimeHealthState.QUARANTINED)

            restarted = RuntimeHealthTracker(
                runtime_id="runtime",
                runtime_version="1",
                config_id="cfg",
                policy=self.policy(),
                store=SQLiteRuntimeHealthStore(path),
            )
            self.assertEqual(
                restarted.facts().state,
                RuntimeHealthState.QUARANTINED,
            )

            states = tuple(
                restarted.record_execution(
                    ExecutionStatus.SUCCEEDED,
                    execution_id=f"success-{index}",
                ).state
                for index in range(3)
            )
            self.assertEqual(
                states,
                (
                    RuntimeHealthState.UNHEALTHY,
                    RuntimeHealthState.RECOVERING,
                    RuntimeHealthState.HEALTHY,
                ),
            )

    def test_durable_history_isolated_by_runtime_version_and_config(self):
        with tempfile.TemporaryDirectory() as temp:
            path = Path(temp) / "runtime.db"
            v1 = RuntimeHealthTracker(
                runtime_id="runtime",
                runtime_version="1",
                config_id="cfg-a",
                store=SQLiteRuntimeHealthStore(path),
            )
            v1.record_execution(ExecutionStatus.FAILED, execution_id="v1-failure")

            for version, config in (("2", "cfg-a"), ("1", "cfg-b")):
                fresh_binding = RuntimeHealthTracker(
                    runtime_id="runtime",
                    runtime_version=version,
                    config_id=config,
                    store=SQLiteRuntimeHealthStore(path),
                )
                self.assertEqual(
                    fresh_binding.facts().state,
                    RuntimeHealthState.UNKNOWN,
                )

    def test_two_sqlite_store_instances_converge_on_one_authoritative_sequence(self):
        with tempfile.TemporaryDirectory() as temp:
            path = Path(temp) / "runtime.db"
            first = RuntimeHealthTracker(
                runtime_id="runtime",
                runtime_version="1",
                config_id="cfg",
                store=SQLiteRuntimeHealthStore(path),
            )
            second = RuntimeHealthTracker(
                runtime_id="runtime",
                runtime_version="1",
                config_id="cfg",
                store=SQLiteRuntimeHealthStore(path),
            )

            first.record_execution(ExecutionStatus.FAILED, execution_id="failure")
            second.record_execution(ExecutionStatus.SUCCEEDED, execution_id="success")

            first_facts = first.facts()
            second_facts = second.facts()
            self.assertEqual(first_facts, second_facts)
            self.assertEqual(first_facts.window_start_sequence, 1)
            self.assertEqual(first_facts.window_end_sequence, 2)

    def test_conflicting_rewrite_of_execution_identity_fails_closed(self):
        with tempfile.TemporaryDirectory() as temp:
            store = SQLiteRuntimeHealthStore(Path(temp) / "runtime.db")
            fields = {
                "runtime_id": "runtime",
                "runtime_version": "1",
                "config_id": "cfg",
                "execution_id": "same-execution",
            }
            original = store.record(**fields, status=ExecutionStatus.SUCCEEDED)
            replay = store.record(**fields, status=ExecutionStatus.SUCCEEDED)
            self.assertEqual(original, replay)

            with self.assertRaises(RuntimeHealthConflict):
                store.record(**fields, status=ExecutionStatus.FAILED)

    def test_adapter_recreation_does_not_reset_quarantine_to_unknown(self):
        with tempfile.TemporaryDirectory() as temp:
            path = Path(temp) / "runtime.db"
            first = LangGraphOrchestratorAdapter(
                _FailingGraph(),
                orchestrator_id="langgraph",
                version="1.2.11",
                config_id="cfg",
                health_policy=self.policy(),
                health_store=SQLiteRuntimeHealthStore(path),
            )
            for index in range(3):
                self.assertEqual(
                    first.execute(_request(f"failure-{index}")).status,
                    ExecutionStatus.FAILED,
                )
            self.assertEqual(
                first.runtime_health_facts().state,
                RuntimeHealthState.QUARANTINED,
            )

            restarted = LangGraphOrchestratorAdapter(
                _HealthyGraph(),
                orchestrator_id="langgraph",
                version="1.2.11",
                config_id="cfg",
                health_policy=self.policy(),
                health_store=SQLiteRuntimeHealthStore(path),
            )
            self.assertEqual(
                restarted.runtime_health_facts().state,
                RuntimeHealthState.QUARANTINED,
            )
            self.assertEqual(restarted.health().status, HealthStatus.UNHEALTHY)

    def test_health_store_failure_does_not_rewrite_successful_runtime_outcome(self):
        adapter = CrewAIOrchestratorAdapter(
            _HealthyCrew(),
            orchestrator_id="crewai",
            version="1.15.16",
            health_store=_BrokenHealthStore(),
        )
        result = adapter.execute(_request("successful-runtime-execution"))

        self.assertEqual(result.status, ExecutionStatus.SUCCEEDED)
        self.assertEqual(adapter.health().status, HealthStatus.UNHEALTHY)
        self.assertIn("health evidence unavailable", adapter.health().reason)
        self.assertEqual(
            adapter.runtime_health_facts().state,
            RuntimeHealthState.UNKNOWN,
        )

    def test_store_cannot_be_replaced_after_local_factual_history_exists(self):
        tracker = RuntimeHealthTracker(
            runtime_id="runtime",
            runtime_version="1",
            config_id="cfg",
        )
        tracker.record_execution(ExecutionStatus.SUCCEEDED, execution_id="already-local")

        with tempfile.TemporaryDirectory() as temp:
            with self.assertRaises(RuntimeError):
                tracker.configure_store(
                    SQLiteRuntimeHealthStore(Path(temp) / "runtime.db")
                )


if __name__ == "__main__":
    unittest.main(verbosity=2)
