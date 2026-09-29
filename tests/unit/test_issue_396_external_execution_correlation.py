from __future__ import annotations

from pathlib import Path
import sqlite3
import tempfile
import unittest

from metao.adapters.gemini_interactions import GeminiInteractionsOrchestratorAdapter
from metao.adapters.jules_http import JulesHttpOrchestratorAdapter
from metao.core import (
    ExecutionRequest,
    HealthReport,
    HealthStatus,
    Mission,
    OrchestratorDescriptor,
    OrchestratorRegistry,
)
from metao.execution_handle import (
    ActiveExecutionHandle,
    ExternalExecutionBindingConflict,
    InMemoryExecutionHandleStore,
)
from metao.mission_store import InMemoryMissionStore
from metao.operator import MissionOperator
from metao.sqlite_execution_handle import SQLiteExecutionHandleStore


class _RestoreAwareRuntime:
    def __init__(self) -> None:
        self._descriptor = OrchestratorDescriptor(
            "remote-runtime",
            "1",
            frozenset({"workflow"}),
        )
        self.restored: list[tuple[str, str]] = []
        self.cancelled: list[str] = []

    @property
    def descriptor(self):
        return self._descriptor

    def health(self):
        return HealthReport(HealthStatus.HEALTHY)

    def restore_external_execution_id(
        self,
        execution_id: str,
        external_execution_id: str,
    ) -> None:
        self.restored.append((execution_id, external_execution_id))

    def cancel(self, execution_id: str) -> None:
        self.cancelled.append(execution_id)


class ExternalExecutionCorrelationTests(unittest.TestCase):
    def test_in_memory_binding_is_idempotent_and_conflicting_rewrite_fails(self):
        store = InMemoryExecutionHandleStore()
        store.activate(
            ActiveExecutionHandle(
                "mission-1",
                "exec-1",
                "runtime-1",
                1,
                10.0,
            )
        )

        first = store.bind_external_execution("exec-1", "provider-job-1")
        again = store.bind_external_execution("exec-1", "provider-job-1")

        self.assertEqual(first.external_execution_id, "provider-job-1")
        self.assertEqual(again.external_execution_id, "provider-job-1")
        with self.assertRaises(ExternalExecutionBindingConflict):
            store.bind_external_execution("exec-1", "provider-job-2")

    def test_retry_attempt_replaces_prior_external_identity_without_aliasing(self):
        store = InMemoryExecutionHandleStore()
        store.activate(
            ActiveExecutionHandle("mission-1", "exec-1", "runtime-1", 1, 10.0)
        )
        store.bind_external_execution("exec-1", "provider-job-1")

        retry = store.activate(
            ActiveExecutionHandle("mission-1", "exec-2", "runtime-2", 2, 20.0)
        )
        self.assertIsNone(retry.external_execution_id)

        rebound = store.bind_external_execution("exec-2", "provider-job-2")
        self.assertEqual(rebound.attempt_number, 2)
        self.assertEqual(rebound.external_execution_id, "provider-job-2")

    def test_sqlite_binding_survives_restart(self):
        with tempfile.TemporaryDirectory() as temp:
            path = Path(temp) / "metao.db"
            first = SQLiteExecutionHandleStore(path)
            first.activate(
                ActiveExecutionHandle("mission-1", "exec-1", "runtime-1", 1, 10.0)
            )
            first.bind_external_execution("exec-1", "sessions/abc")

            restored = SQLiteExecutionHandleStore(path).get("mission-1")

            self.assertEqual(restored.execution_id, "exec-1")
            self.assertEqual(restored.external_execution_id, "sessions/abc")

    def test_sqlite_migrates_legacy_handle_table_without_losing_state(self):
        with tempfile.TemporaryDirectory() as temp:
            path = Path(temp) / "legacy.db"
            with sqlite3.connect(path) as connection:
                connection.execute(
                    """
                    CREATE TABLE active_mission_executions (
                        mission_id TEXT PRIMARY KEY,
                        execution_id TEXT NOT NULL,
                        orchestrator_id TEXT NOT NULL,
                        attempt_number INTEGER NOT NULL,
                        started_at_epoch REAL NOT NULL,
                        cost REAL NOT NULL,
                        status TEXT NOT NULL,
                        cancel_requested INTEGER NOT NULL,
                        cancel_delegated INTEGER NOT NULL,
                        ended_at_epoch REAL,
                        execution_status TEXT
                    )
                    """
                )
                connection.execute(
                    """INSERT INTO active_mission_executions
                       VALUES(?,?,?,?,?,?,?,?,?,?,?)""",
                    (
                        "mission-1",
                        "exec-1",
                        "runtime-1",
                        1,
                        10.0,
                        0.5,
                        "ACTIVE",
                        0,
                        0,
                        None,
                        None,
                    ),
                )

            store = SQLiteExecutionHandleStore(path)
            before = store.get("mission-1")
            self.assertIsNone(before.external_execution_id)

            after = store.bind_external_execution("exec-1", "provider-job-1")
            self.assertEqual(after.external_execution_id, "provider-job-1")

    def test_fresh_operator_restores_durable_external_id_before_cancel(self):
        with tempfile.TemporaryDirectory() as temp:
            path = Path(temp) / "metao.db"
            handles = SQLiteExecutionHandleStore(path)
            handles.activate(
                ActiveExecutionHandle(
                    "mission-1",
                    "exec-1",
                    "remote-runtime",
                    1,
                    10.0,
                )
            )
            handles.bind_external_execution("exec-1", "provider-job-1")

            runtime = _RestoreAwareRuntime()
            registry = OrchestratorRegistry()
            registry.register(runtime)
            operator = MissionOperator(
                registry=registry,
                store=InMemoryMissionStore(),
                normalizers={},
            ).configure_execution_handles(handles)

            cancelled = operator.cancel("mission-1")

            self.assertEqual(
                runtime.restored,
                [("exec-1", "provider-job-1")],
            )
            self.assertEqual(runtime.cancelled, ["exec-1"])
            self.assertTrue(cancelled.cancel_requested)
            self.assertFalse(cancelled.cancel_delegated)

    def test_gemini_observes_external_id_at_creation_boundary(self):
        observed: list[str] = []

        def transport(method, path, body):
            self.assertEqual((method, path), ("POST", "/interactions"))
            return {"id": "interaction-1", "status": "completed", "steps": []}

        adapter = GeminiInteractionsOrchestratorAdapter(
            transport=transport,
            max_polls=1,
            poll_interval_s=0.0,
            sleep_fn=lambda _: None,
        )
        request = ExecutionRequest(
            "exec-gemini",
            Mission("mission-gemini", "run", frozenset({"agent"})),
            external_execution_id_observer=observed.append,
        )

        adapter.execute(request)

        self.assertEqual(observed, ["interaction-1"])

    def test_jules_observes_external_id_at_creation_boundary(self):
        observed: list[str] = []
        calls = iter(
            [
                ("POST", "/sessions", {"name": "sessions/abc"}),
                ("GET", "/sessions/abc", {"name": "sessions/abc", "state": "FAILED"}),
            ]
        )

        def transport(method, path, body):
            expected_method, expected_path, result = next(calls)
            self.assertEqual((method, path), (expected_method, expected_path))
            return result

        adapter = JulesHttpOrchestratorAdapter(
            transport=transport,
            max_polls=1,
            poll_interval_s=0.0,
            sleep_fn=lambda _: None,
        )
        request = ExecutionRequest(
            "exec-jules",
            Mission("mission-jules", "run", frozenset({"workflow"})),
            external_execution_id_observer=observed.append,
        )

        adapter.execute(request)

        self.assertEqual(observed, ["sessions/abc"])


if __name__ == "__main__":
    unittest.main()
