from __future__ import annotations

from io import StringIO
import json
from pathlib import Path
import sys
import tempfile
from threading import Event, Thread
from time import monotonic, sleep
from types import ModuleType
import unittest

from metao.acceptance import AcceptanceContext, AcceptanceDecision
from metao.adapters.langgraph import normalize_evidence
from metao.catalog import OrchestratorCatalog
from metao.cli import main
from metao.control_plane import MissionStatus
from metao.core import (
    ExecutionRequest,
    ExecutionResult,
    ExecutionStatus,
    HealthReport,
    HealthStatus,
    Mission,
    OrchestratorDescriptor,
    OrchestratorRegistry,
)
from metao.execution_handle import (
    ActiveExecutionHandle,
    ActiveExecutionNotFound,
    ExecutionHandleStatus,
    ExecutionHandleStorePort,
    InMemoryExecutionHandleStore,
)
from metao.governance import AcceptanceBudget, evaluate_policy
from metao.mission_store import InMemoryMissionStore
from metao.observability import MissionEventKind
from metao.observed_operator import ObservableMissionOperator
from metao.operator import MissionNotCancellable, MissionOperator
from metao.replan import ControlAction, FailureClass, evaluate
from metao.sqlite_event_ledger import SQLiteEventLedger
from metao.sqlite_execution_handle import SQLiteExecutionHandleStore
from metao.sqlite_store import SQLiteMissionStore


class CooperativeBlockingRuntime:
    def __init__(self, orchestrator_id: str = "blocking") -> None:
        self._descriptor = OrchestratorDescriptor(orchestrator_id, "v1", frozenset({"workflow"}))
        self.started = Event()
        self.cancelled = Event()
        self.cancel_calls = 0
        self.execute_calls = 0

    @property
    def descriptor(self):
        return self._descriptor

    def health(self):
        return HealthReport(HealthStatus.HEALTHY)

    def execute(self, request: ExecutionRequest):
        self.execute_calls += 1
        self.started.set()
        if self.cancelled.wait(3.0):
            return ExecutionResult(
                request.execution_id,
                self.descriptor.orchestrator_id,
                ExecutionStatus.CANCELLED,
            )
        return ExecutionResult(
            request.execution_id,
            self.descriptor.orchestrator_id,
            ExecutionStatus.FAILED,
            error="test runtime wait expired",
        )

    def cancel(self, execution_id: str) -> None:
        self.cancel_calls += 1
        self.cancelled.set()


class IgnoringCancelRuntime:
    def __init__(self, orchestrator_id: str = "ignores-cancel") -> None:
        self._descriptor = OrchestratorDescriptor(orchestrator_id, "v1", frozenset({"workflow"}))
        self.started = Event()
        self.release = Event()
        self.cancel_calls = 0
        self.execute_calls = 0

    @property
    def descriptor(self):
        return self._descriptor

    def health(self):
        return HealthReport(HealthStatus.HEALTHY)

    def execute(self, request: ExecutionRequest):
        self.execute_calls += 1
        self.started.set()
        self.release.wait(3.0)
        return ExecutionResult(
            request.execution_id,
            self.descriptor.orchestrator_id,
            ExecutionStatus.SUCCEEDED,
            {"result": "late-success"},
        )

    def cancel(self, execution_id: str) -> None:
        self.cancel_calls += 1


class ImmediateRuntime:
    def __init__(self, orchestrator_id: str = "immediate") -> None:
        self._descriptor = OrchestratorDescriptor(orchestrator_id, "v1", frozenset({"workflow"}))
        self.execute_calls = 0
        self.cancel_calls = 0

    @property
    def descriptor(self):
        return self._descriptor

    def health(self):
        return HealthReport(HealthStatus.HEALTHY)

    def execute(self, request: ExecutionRequest):
        self.execute_calls += 1
        return ExecutionResult(
            request.execution_id,
            self.descriptor.orchestrator_id,
            ExecutionStatus.SUCCEEDED,
            {"result": "done"},
        )

    def cancel(self, execution_id: str) -> None:
        self.cancel_calls += 1


class DurableMissionCancellationV1Tests(unittest.TestCase):
    def setUp(self) -> None:
        self.allow = evaluate_policy(policy_bundle_id="policy-1", allowed=True)
        self.context = AcceptanceContext(
            "subject-1",
            "state-1",
            "verify-1",
            "policy-1",
            frozenset({"execution_result"}),
        )
        self.budget = AcceptanceBudget(10.0, 10_000, 60.0, 10)

    def _operator(self, runtime, *, store=None, handles=None, fallback=None):
        registry = OrchestratorRegistry()
        registry.register(runtime)
        catalog = OrchestratorCatalog(registry)
        catalog.register(
            runtime.descriptor.orchestrator_id,
            normalizer=normalize_evidence,
            cost=0.1,
            latency_ms=10.0,
            success_rate=0.99,
            quality=0.99,
            reliability=0.99,
        )
        if fallback is not None:
            registry.register(fallback)
            catalog.register(
                fallback.descriptor.orchestrator_id,
                normalizer=normalize_evidence,
                cost=5.0,
                latency_ms=5000.0,
                success_rate=0.2,
                quality=0.2,
                reliability=0.2,
            )
        operator = MissionOperator(
            registry=registry,
            catalog=catalog,
            store=store or InMemoryMissionStore(),
        )
        if handles is not None:
            operator.configure_execution_handles(handles, poll_interval_s=0.01)
        return operator

    @staticmethod
    def _wait_until(predicate, timeout: float = 2.0):
        deadline = monotonic() + timeout
        while monotonic() < deadline:
            value = predicate()
            if value:
                return value
            sleep(0.01)
        raise AssertionError("condition was not satisfied before timeout")

    def test_in_memory_execution_handle_store_tracks_durable_cancellation_state(self):
        store = InMemoryExecutionHandleStore()
        self.assertIsInstance(store, ExecutionHandleStorePort)
        handle = store.activate(
            ActiveExecutionHandle("m1", "exec-1", "runtime-1", 1, 10.0, cost=0.25)
        )
        self.assertEqual(handle.status, ExecutionHandleStatus.ACTIVE)
        requested = store.request_cancel("m1")
        self.assertTrue(requested.cancel_requested)
        self.assertFalse(requested.cancel_delegated)
        delegated = store.mark_cancel_delegated("m1")
        self.assertTrue(delegated.cancel_delegated)
        completed = store.complete("m1", ended_at_epoch=11.0, execution_status=ExecutionStatus.CANCELLED)
        self.assertEqual(completed.status, ExecutionHandleStatus.COMPLETED)
        self.assertEqual(completed.execution_status, ExecutionStatus.CANCELLED)

    def test_sqlite_execution_handle_survives_restart_with_cancel_request(self):
        with tempfile.TemporaryDirectory() as temp:
            path = Path(temp) / "metao.db"
            first = SQLiteExecutionHandleStore(path)
            first.activate(ActiveExecutionHandle("m1", "exec-1", "runtime-1", 1, 10.0, cost=0.4))
            first.request_cancel("m1")

            restored = SQLiteExecutionHandleStore(path).get("m1")
            self.assertTrue(restored.cancel_requested)
            self.assertFalse(restored.cancel_delegated)
            self.assertEqual(restored.execution_id, "exec-1")
            self.assertEqual(restored.cost, 0.4)

    def test_cooperative_runtime_cancels_running_mission_and_never_replans(self):
        runtime = CooperativeBlockingRuntime("primary")
        fallback = ImmediateRuntime("fallback")
        handles = InMemoryExecutionHandleStore()
        store = InMemoryMissionStore()
        operator = self._operator(runtime, store=store, handles=handles, fallback=fallback)
        result: dict[str, object] = {}

        def run_mission():
            result["outcome"] = operator.run(
                Mission("cancel-running", "cancel running mission", frozenset({"workflow"})),
                policy=self.allow,
                budget=self.budget,
                acceptance_context=self.context,
                max_attempts=2,
            )

        thread = Thread(target=run_mission)
        thread.start()
        self.assertTrue(runtime.started.wait(1.0))
        self.assertEqual(operator.status("cancel-running"), MissionStatus.RUNNING)

        requested = operator.cancel("cancel-running")
        self.assertTrue(requested.cancel_requested)
        thread.join(2.0)
        self.assertFalse(thread.is_alive())

        outcome = result["outcome"]
        self.assertEqual(outcome.state.status, MissionStatus.CANCELLED)
        self.assertEqual(outcome.acceptance.decision, AcceptanceDecision.BLOCK)
        self.assertIn("operator_cancelled", outcome.acceptance.reasons)
        self.assertEqual(runtime.cancel_calls, 1)
        self.assertEqual(fallback.execute_calls, 0)
        self.assertNotIn(MissionStatus.REPLANNING, outcome.state.history)
        final_handle = handles.get("cancel-running")
        self.assertTrue(final_handle.cancel_delegated)
        self.assertEqual(final_handle.execution_status, ExecutionStatus.CANCELLED)

    def test_runtime_ignoring_cancel_can_never_force_late_acceptance(self):
        runtime = IgnoringCancelRuntime()
        handles = InMemoryExecutionHandleStore()
        operator = self._operator(runtime, handles=handles)
        result: dict[str, object] = {}

        def run_mission():
            result["outcome"] = operator.run(
                Mission("ignore-cancel", "runtime ignores cancellation", frozenset({"workflow"})),
                policy=self.allow,
                budget=self.budget,
                acceptance_context=self.context,
            )

        thread = Thread(target=run_mission)
        thread.start()
        self.assertTrue(runtime.started.wait(1.0))
        operator.cancel("ignore-cancel")
        runtime.release.set()
        thread.join(2.0)
        self.assertFalse(thread.is_alive())

        outcome = result["outcome"]
        self.assertEqual(outcome.execution.status, ExecutionStatus.SUCCEEDED)
        self.assertEqual(outcome.state.status, MissionStatus.BLOCKED)
        self.assertEqual(outcome.acceptance.decision, AcceptanceDecision.BLOCK)
        self.assertIn("cancel_requested_runtime_completed", outcome.acceptance.reasons)
        self.assertNotEqual(outcome.state.status, MissionStatus.ACCEPTED)

    def test_waiting_approval_can_be_cancelled_without_runtime_and_survives_restart(self):
        with tempfile.TemporaryDirectory() as temp:
            path = Path(temp) / "metao.db"
            runtime = ImmediateRuntime()
            handles = SQLiteExecutionHandleStore(path)
            operator = self._operator(runtime, store=SQLiteMissionStore(path), handles=handles)
            require_human = evaluate_policy(
                policy_bundle_id="policy-1",
                allowed=True,
                require_human=True,
                reason="approval needed",
            )
            waiting = operator.run(
                Mission("cancel-waiting", "cancel before runtime", frozenset({"workflow"})),
                policy=require_human,
                budget=self.budget,
                acceptance_context=self.context,
            )
            self.assertEqual(waiting.state.status, MissionStatus.WAITING_APPROVAL)
            cancelled = operator.cancel("cancel-waiting")
            self.assertEqual(cancelled.status, MissionStatus.CANCELLED)
            self.assertEqual(runtime.execute_calls, 0)
            self.assertEqual(SQLiteMissionStore(path).get("cancel-waiting").status, MissionStatus.CANCELLED)
            with self.assertRaises(ActiveExecutionNotFound):
                SQLiteExecutionHandleStore(path).get("cancel-waiting")

    def test_terminal_mission_and_unknown_mission_fail_closed_on_cancel(self):
        runtime = ImmediateRuntime()
        handles = InMemoryExecutionHandleStore()
        operator = self._operator(runtime, handles=handles)
        accepted = operator.run(
            Mission("terminal", "finish first", frozenset({"workflow"})),
            policy=self.allow,
            budget=self.budget,
            acceptance_context=self.context,
        )
        self.assertEqual(accepted.state.status, MissionStatus.ACCEPTED)
        with self.assertRaises(MissionNotCancellable):
            operator.cancel("terminal")
        with self.assertRaises(MissionNotCancellable):
            operator.cancel("missing")

    def test_cancelled_failure_class_is_a_non_replannable_halt(self):
        decision = evaluate(FailureClass.CANCELLED, attempts=0)
        self.assertEqual(decision.action, ControlAction.HALT)
        self.assertIn("cancelled", decision.reason)

    def test_cli_cross_invocation_cancel_reaches_original_live_runtime(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            db = root / "metao.db"
            mission_file = root / "mission.json"
            mission_file.write_text(
                json.dumps(
                    {
                        "mission": {
                            "mission_id": "cli-cross-cancel",
                            "objective": "cancel across invocations",
                            "required_capabilities": ["workflow"],
                        },
                        "policy": {"policy_bundle_id": "policy-1", "allowed": True},
                        "budget": {
                            "money_limit": 10,
                            "token_limit": 1000,
                            "wall_time_limit_s": 60,
                            "verifier_attempt_limit": 3,
                        },
                        "acceptance_context": {
                            "subject_id": "subject-1",
                            "subject_state_id": "state-1",
                            "verification_context_id": "verify-1",
                            "policy_bundle_id": "policy-1",
                            "required_obligations": ["execution_result"],
                        },
                        "now_epoch": 100,
                    }
                ),
                encoding="utf-8",
            )

            module = ModuleType("metao_cancel_factory")
            module.instances = []

            def create_operator(*, store):
                runtime = CooperativeBlockingRuntime("cli-blocking")
                module.instances.append(runtime)
                registry = OrchestratorRegistry()
                registry.register(runtime)
                catalog = OrchestratorCatalog(registry)
                catalog.register(
                    "cli-blocking",
                    normalizer=normalize_evidence,
                    cost=0.1,
                    latency_ms=10,
                    success_rate=0.99,
                    quality=0.99,
                    reliability=0.99,
                )
                return MissionOperator(registry=registry, catalog=catalog, store=store)

            module.create_operator = create_operator
            sys.modules["metao_cancel_factory"] = module
            run_result: dict[str, object] = {}

            def call_run():
                stdout, stderr = StringIO(), StringIO()
                run_result["code"] = main(
                    [
                        "--db",
                        str(db),
                        "run",
                        str(mission_file),
                        "--factory",
                        "metao_cancel_factory:create_operator",
                    ],
                    stdout=stdout,
                    stderr=stderr,
                )
                run_result["out"] = stdout.getvalue()
                run_result["err"] = stderr.getvalue()

            try:
                run_thread = Thread(target=call_run)
                run_thread.start()
                self._wait_until(lambda: len(module.instances) >= 1 and module.instances[0].started.is_set())
                original_runtime = module.instances[0]

                status_out, status_err = StringIO(), StringIO()
                self.assertEqual(
                    main(["--db", str(db), "status", "cli-cross-cancel"], stdout=status_out, stderr=status_err),
                    0,
                    status_err.getvalue(),
                )
                status_payload = json.loads(status_out.getvalue())
                self.assertEqual(status_payload["status"], "RUNNING")
                self.assertEqual(status_payload["active_execution"]["orchestrator_id"], "cli-blocking")

                inspect_out, inspect_err = StringIO(), StringIO()
                self.assertEqual(
                    main(["--db", str(db), "inspect", "cli-cross-cancel"], stdout=inspect_out, stderr=inspect_err),
                    0,
                    inspect_err.getvalue(),
                )
                self.assertTrue(json.loads(inspect_out.getvalue())["active_execution"]["execution_id"].endswith("-1"))

                cancel_out, cancel_err = StringIO(), StringIO()
                self.assertEqual(
                    main(
                        [
                            "--db",
                            str(db),
                            "cancel",
                            "cli-cross-cancel",
                            "--factory",
                            "metao_cancel_factory:create_operator",
                            "--now-epoch",
                            "101",
                        ],
                        stdout=cancel_out,
                        stderr=cancel_err,
                    ),
                    0,
                    cancel_err.getvalue(),
                )
                cancel_payload = json.loads(cancel_out.getvalue())
                self.assertTrue(cancel_payload["active_execution"]["cancel_requested"])
                self.assertFalse(cancel_payload["active_execution"]["cancel_delegated"])
                self.assertGreaterEqual(len(module.instances), 2)
                fresh_cancel_runtime = module.instances[1]
                self.assertEqual(fresh_cancel_runtime.cancel_calls, 1)

                self._wait_until(
                    lambda: SQLiteExecutionHandleStore(db).get("cli-cross-cancel").cancel_delegated
                )
                self.assertEqual(original_runtime.cancel_calls, 1)

                run_thread.join(2.0)
                self.assertFalse(run_thread.is_alive())
                self.assertEqual(run_result["code"], 0, run_result["err"])
                self.assertEqual(json.loads(run_result["out"])["status"], "CANCELLED")

                final_handle = SQLiteExecutionHandleStore(db).get("cli-cross-cancel")
                self.assertEqual(final_handle.status, ExecutionHandleStatus.COMPLETED)
                self.assertTrue(final_handle.cancel_requested)
                self.assertTrue(final_handle.cancel_delegated)
                self.assertEqual(final_handle.execution_status, ExecutionStatus.CANCELLED)
                self.assertEqual(SQLiteMissionStore(db).get("cli-cross-cancel").status, MissionStatus.CANCELLED)

                events = SQLiteEventLedger(db).list("cli-cross-cancel")
                kinds = [event.kind for event in events]
                self.assertIn(MissionEventKind.CANCELLATION_REQUESTED, kinds)
                self.assertEqual(kinds[-1], MissionEventKind.MISSION_TERMINAL)
                self.assertEqual(events[-1].payload["status"], "CANCELLED")
            finally:
                sys.modules.pop("metao_cancel_factory", None)

    def test_cli_unknown_cancel_returns_structured_error(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            db = root / "metao.db"
            module = ModuleType("metao_cancel_missing_factory")
            runtime = ImmediateRuntime("missing-runtime")
            registry = OrchestratorRegistry()
            registry.register(runtime)
            catalog = OrchestratorCatalog(registry)
            catalog.register("missing-runtime", normalizer=normalize_evidence)
            module.create_operator = lambda *, store: MissionOperator(registry=registry, catalog=catalog, store=store)
            sys.modules["metao_cancel_missing_factory"] = module
            try:
                stdout, stderr = StringIO(), StringIO()
                code = main(
                    [
                        "--db",
                        str(db),
                        "cancel",
                        "missing",
                        "--factory",
                        "metao_cancel_missing_factory:create_operator",
                    ],
                    stdout=stdout,
                    stderr=stderr,
                )
                self.assertEqual(code, 2)
                self.assertFalse(stdout.getvalue())
                error = json.loads(stderr.getvalue())
                self.assertEqual(error["error"], "MissionNotCancellable")
            finally:
                sys.modules.pop("metao_cancel_missing_factory", None)

    def test_cancellation_boundary_remains_orchestrator_sdk_neutral(self):
        root = Path(__file__).resolve().parents[2]
        for relative in (
            "src/metao/execution_handle.py",
            "src/metao/sqlite_execution_handle.py",
            "src/metao/control_plane.py",
            "src/metao/operator.py",
            "src/metao/cli.py",
        ):
            source = (root / relative).read_text(encoding="utf-8").lower()
            for forbidden in ("import langgraph", "from langgraph", "import crewai", "from crewai"):
                self.assertNotIn(forbidden, source)


if __name__ == "__main__":
    unittest.main(verbosity=2)
