from __future__ import annotations

from contextlib import closing
from io import StringIO
import json
from pathlib import Path
import sqlite3
import sys
import tempfile
from types import ModuleType
import unittest

from metao.acceptance import AcceptanceContext, AcceptanceDecision
from metao.adapters.langgraph import normalize_evidence
from metao.catalog import OrchestratorCatalog
from metao.cli import main
from metao.control_plane import execute_mission
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
from metao.governance import AcceptanceBudget, evaluate_policy
from metao.mission_store import MissionRecord
from metao.operator import MissionOperator
from metao.replan import FailureClass
from metao.sqlite_store import SQLiteMissionStore
from metao.strategy import OrchestratorPoolState, OrchestratorStatus


class Runtime:
    def __init__(self, orchestrator_id: str, results: tuple[tuple[ExecutionStatus, str], ...]) -> None:
        self._descriptor = OrchestratorDescriptor(orchestrator_id, "v1", frozenset({"workflow"}))
        self.results = list(results)
        self.calls = 0

    @property
    def descriptor(self):
        return self._descriptor

    def health(self):
        return HealthReport(HealthStatus.HEALTHY)

    def execute(self, request: ExecutionRequest):
        self.calls += 1
        status, error = self.results.pop(0) if self.results else (ExecutionStatus.SUCCEEDED, "")
        return ExecutionResult(
            request.execution_id,
            self.descriptor.orchestrator_id,
            status,
            {"result": self.descriptor.orchestrator_id},
            error=error,
        )

    def cancel(self, execution_id: str) -> None:
        pass


class Clock:
    def __init__(self, values: list[float]) -> None:
        self.values = list(values)

    def __call__(self) -> float:
        if not self.values:
            raise AssertionError("clock exhausted")
        return self.values.pop(0)


class DetailedAttemptTelemetryV1Tests(unittest.TestCase):
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

    @staticmethod
    def _pool(orchestrator_id: str, *, cost: float, quality: float) -> OrchestratorPoolState:
        return OrchestratorPoolState(
            orchestrator_id,
            OrchestratorStatus.HEALTHY,
            frozenset({"workflow"}),
            success_rate=quality,
            quality=quality,
            reliability=quality,
            latency_ms=10.0,
            cost=cost,
        )

    def _execute(
        self,
        *,
        primary_results: tuple[tuple[ExecutionStatus, str], ...] = ((ExecutionStatus.SUCCEEDED, ""),),
        fallback: bool = False,
        context: AcceptanceContext | None = None,
        clock_values: list[float] | None = None,
    ):
        registry = OrchestratorRegistry()
        primary = Runtime("primary", primary_results)
        registry.register(primary)
        pools = [self._pool("primary", cost=0.25, quality=0.99)]
        normalizers = {"primary": normalize_evidence}
        fallback_runtime = None
        if fallback:
            fallback_runtime = Runtime("fallback", ((ExecutionStatus.SUCCEEDED, ""),))
            registry.register(fallback_runtime)
            pools.append(self._pool("fallback", cost=0.50, quality=0.20))
            normalizers["fallback"] = normalize_evidence
        outcome = execute_mission(
            mission=Mission("telemetry-mission", "record attempt telemetry", frozenset({"workflow"})),
            registry=registry,
            pools=tuple(pools),
            normalizers=normalizers,
            policy=self.allow,
            budget=self.budget,
            acceptance_context=context or self.context,
            execution_id_prefix="telemetry-exec",
            now_epoch=100.0,
            max_attempts=2 if fallback else 1,
            attempt_clock=Clock(clock_values or [10.0, 11.0]),
        )
        return outcome, primary, fallback_runtime

    def test_accepted_attempt_records_start_end_cost_and_no_failure(self):
        outcome, _, _ = self._execute(clock_values=[10.0, 12.5])
        attempt = outcome.state.attempts[0]
        self.assertEqual(attempt.started_at_epoch, 10.0)
        self.assertEqual(attempt.ended_at_epoch, 12.5)
        self.assertEqual(attempt.cost, 0.25)
        self.assertIsNone(attempt.failure_class)
        self.assertEqual(attempt.acceptance_decision, AcceptanceDecision.ACCEPT)

    def test_timeout_failure_uses_existing_failure_classifier(self):
        outcome, _, _ = self._execute(
            primary_results=((ExecutionStatus.FAILED, "worker timed out"),),
            clock_values=[20.0, 23.0],
        )
        attempt = outcome.state.attempts[0]
        self.assertEqual(attempt.failure_class, FailureClass.TIMEOUT)
        self.assertEqual(attempt.started_at_epoch, 20.0)
        self.assertEqual(attempt.ended_at_epoch, 23.0)
        self.assertEqual(attempt.cost, 0.25)

    def test_generic_failed_execution_is_classified_as_runtime(self):
        outcome, _, _ = self._execute(
            primary_results=((ExecutionStatus.FAILED, "opaque failure"),),
            clock_values=[30.0, 31.0],
        )
        self.assertEqual(outcome.state.attempts[0].failure_class, FailureClass.RUNTIME)

    def test_successful_execution_rejected_by_acceptance_is_classified_as_acceptance(self):
        hostile_context = AcceptanceContext(
            "subject-1",
            "state-1",
            "verify-1",
            "policy-1",
            frozenset({"execution_result"}),
            trusted_verifiers=frozenset({"different-verifier"}),
        )
        outcome, _, _ = self._execute(context=hostile_context, clock_values=[40.0, 41.0])
        attempt = outcome.state.attempts[0]
        self.assertEqual(attempt.execution_status, ExecutionStatus.SUCCEEDED)
        self.assertEqual(attempt.failure_class, FailureClass.ACCEPTANCE)
        self.assertNotEqual(attempt.acceptance_decision, AcceptanceDecision.ACCEPT)

    def test_failover_preserves_distinct_telemetry_for_each_attempt(self):
        outcome, primary, fallback = self._execute(
            primary_results=((ExecutionStatus.FAILED, "temporary connection failure"),),
            fallback=True,
            clock_values=[50.0, 51.0, 60.0, 62.0],
        )
        first, second = outcome.state.attempts
        self.assertEqual(primary.calls, 1)
        self.assertEqual(fallback.calls, 1)
        self.assertEqual(first.failure_class, FailureClass.TRANSIENT)
        self.assertEqual((first.started_at_epoch, first.ended_at_epoch, first.cost), (50.0, 51.0, 0.25))
        self.assertIsNone(second.failure_class)
        self.assertEqual((second.started_at_epoch, second.ended_at_epoch, second.cost), (60.0, 62.0, 0.50))
        self.assertEqual(outcome.state.status.value, "ACCEPTED")

    def test_attempt_telemetry_survives_sqlite_restart(self):
        outcome, _, _ = self._execute(clock_values=[70.0, 71.5])
        with tempfile.TemporaryDirectory() as temp:
            path = Path(temp) / "metao.db"
            SQLiteMissionStore(path).create(MissionRecord(Mission("telemetry-mission", "record attempt telemetry", frozenset({"workflow"})), outcome))
            restored = SQLiteMissionStore(path).get("telemetry-mission")
            attempt = restored.outcome.state.attempts[0]
            self.assertEqual(attempt.started_at_epoch, 70.0)
            self.assertEqual(attempt.ended_at_epoch, 71.5)
            self.assertEqual(attempt.cost, 0.25)
            self.assertIsNone(attempt.failure_class)

    def test_v2_snapshot_without_telemetry_remains_readable_with_truthful_defaults(self):
        outcome, _, _ = self._execute(clock_values=[80.0, 81.0])
        mission = Mission("telemetry-mission", "record attempt telemetry", frozenset({"workflow"}))
        with tempfile.TemporaryDirectory() as temp:
            path = Path(temp) / "metao.db"
            store = SQLiteMissionStore(path)
            store.create(MissionRecord(mission, outcome))
            with closing(sqlite3.connect(path)) as connection, connection:
                raw = connection.execute(
                    "SELECT record_json FROM mission_records WHERE mission_id='telemetry-mission'"
                ).fetchone()[0]
                payload = json.loads(raw)
                payload["schema_version"] = 2
                for attempt in payload["outcome"]["state"]["attempts"]:
                    for key in ("started_at_epoch", "ended_at_epoch", "failure_class", "cost"):
                        attempt.pop(key, None)
                connection.execute(
                    "UPDATE mission_records SET schema_version=2, record_json=? WHERE mission_id='telemetry-mission'",
                    (json.dumps(payload, sort_keys=True, separators=(",", ":")),),
                )
            restored = SQLiteMissionStore(path).get("telemetry-mission")
            attempt = restored.outcome.state.attempts[0]
            self.assertIsNone(attempt.started_at_epoch)
            self.assertIsNone(attempt.ended_at_epoch)
            self.assertIsNone(attempt.failure_class)
            self.assertEqual(attempt.cost, 0.0)

    def test_cli_inspect_and_events_expose_attempt_telemetry(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            db = root / "metao.db"
            mission_file = root / "mission.json"
            mission_file.write_text(
                json.dumps(
                    {
                        "mission": {
                            "mission_id": "cli-telemetry",
                            "objective": "expose telemetry",
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
                    }
                ),
                encoding="utf-8",
            )
            registry = OrchestratorRegistry()
            runtime = Runtime("cli-runtime", ((ExecutionStatus.SUCCEEDED, ""),))
            registry.register(runtime)
            catalog = OrchestratorCatalog(registry)
            catalog.register(
                "cli-runtime",
                normalizer=normalize_evidence,
                cost=0.75,
                latency_ms=10,
                success_rate=0.99,
                quality=0.99,
                reliability=0.99,
            )
            module = ModuleType("metao_attempt_telemetry_factory")
            module.create_operator = lambda *, store: MissionOperator(registry=registry, catalog=catalog, store=store)
            sys.modules["metao_attempt_telemetry_factory"] = module
            try:
                stdout, stderr = StringIO(), StringIO()
                code = main(
                    ["--db", str(db), "run", str(mission_file), "--factory", "metao_attempt_telemetry_factory:create_operator"],
                    stdout=stdout,
                    stderr=stderr,
                )
                self.assertEqual(code, 0, stderr.getvalue())
                stdout, stderr = StringIO(), StringIO()
                self.assertEqual(main(["--db", str(db), "inspect", "cli-telemetry"], stdout=stdout, stderr=stderr), 0)
                detail = json.loads(stdout.getvalue())
                attempt = detail["attempts"][0]
                self.assertIsInstance(attempt["started_at_epoch"], float)
                self.assertGreaterEqual(attempt["ended_at_epoch"], attempt["started_at_epoch"])
                self.assertEqual(attempt["cost"], 0.75)
                self.assertIsNone(attempt["failure_class"])

                stdout, stderr = StringIO(), StringIO()
                self.assertEqual(
                    main(
                        ["--db", str(db), "events", "cli-telemetry", "--kind", "RUNTIME_COMPLETED"],
                        stdout=stdout,
                        stderr=stderr,
                    ),
                    0,
                )
                event = json.loads(stdout.getvalue())[0]
                self.assertEqual(event["payload"]["cost"], 0.75)
                self.assertIsNotNone(event["payload"]["started_at_epoch"])
                self.assertIsNotNone(event["payload"]["ended_at_epoch"])
            finally:
                sys.modules.pop("metao_attempt_telemetry_factory", None)

    def test_attempt_telemetry_validation_fails_closed(self):
        outcome, _, _ = self._execute(clock_values=[90.0, 91.0])
        attempt = outcome.state.attempts[0]
        with self.assertRaises(ValueError):
            type(attempt)(
                attempt.attempt_number,
                attempt.execution_id,
                attempt.orchestrator_id,
                attempt.execution_status,
                attempt.acceptance_decision,
                attempt.reasons,
                started_at_epoch=10.0,
                ended_at_epoch=9.0,
            )
        with self.assertRaises(ValueError):
            type(attempt)(
                attempt.attempt_number,
                attempt.execution_id,
                attempt.orchestrator_id,
                attempt.execution_status,
                attempt.acceptance_decision,
                cost=-0.01,
            )

    def test_telemetry_boundary_remains_orchestrator_sdk_neutral(self):
        root = Path(__file__).resolve().parents[2]
        for relative in ("src/metao/control_plane.py", "src/metao/sqlite_store.py"):
            source = (root / relative).read_text(encoding="utf-8").lower()
            for forbidden in ("import langgraph", "from langgraph", "import crewai", "from crewai"):
                self.assertNotIn(forbidden, source)


if __name__ == "__main__":
    unittest.main(verbosity=2)
