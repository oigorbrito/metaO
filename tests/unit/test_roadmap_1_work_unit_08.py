from __future__ import annotations

from io import StringIO
import json
from pathlib import Path
import sqlite3
import sys
import tempfile
from types import ModuleType
import unittest

from metao.adapters.langgraph import normalize_evidence
from metao.catalog import OrchestratorCatalog
from metao.cli import main
from metao.core import (
    ExecutionRequest,
    ExecutionResult,
    ExecutionStatus,
    HealthReport,
    HealthStatus,
    OrchestratorDescriptor,
    OrchestratorRegistry,
)
from metao.operator import MissionOperator


class Runtime:
    def __init__(self) -> None:
        self._descriptor = OrchestratorDescriptor("cli-observed-runtime", "v1", frozenset({"workflow"}))
        self.calls = 0

    @property
    def descriptor(self):
        return self._descriptor

    def health(self):
        return HealthReport(HealthStatus.HEALTHY)

    def execute(self, request: ExecutionRequest):
        self.calls += 1
        return ExecutionResult(
            request.execution_id,
            self.descriptor.orchestrator_id,
            ExecutionStatus.SUCCEEDED,
            {"result": "observed"},
        )

    def cancel(self, execution_id: str) -> None:
        pass


class CliObservabilitySurfaceV1Tests(unittest.TestCase):
    def setUp(self) -> None:
        self.tempdir = tempfile.TemporaryDirectory()
        self.root = Path(self.tempdir.name)
        self.db = self.root / "metao.db"
        self.runtime = Runtime()
        registry = OrchestratorRegistry()
        registry.register(self.runtime)
        catalog = OrchestratorCatalog(registry)
        catalog.register(
            "cli-observed-runtime",
            normalizer=normalize_evidence,
            cost=0.01,
            latency_ms=10.0,
            success_rate=0.99,
            quality=0.99,
            reliability=0.99,
        )

        module = ModuleType("metao_cli_observed_factory")

        def create_operator(*, store):
            return MissionOperator(registry=registry, catalog=catalog, store=store)

        module.create_operator = create_operator
        sys.modules["metao_cli_observed_factory"] = module
        self.factory = "metao_cli_observed_factory:create_operator"

    def tearDown(self) -> None:
        sys.modules.pop("metao_cli_observed_factory", None)
        self.tempdir.cleanup()

    def _mission_file(self, mission_id: str, *, require_human: bool = False, allowed: bool = True, now_epoch: float = 100.0) -> Path:
        path = self.root / f"{mission_id}.json"
        path.write_text(
            json.dumps(
                {
                    "mission": {
                        "mission_id": mission_id,
                        "objective": "exercise cli observability",
                        "required_capabilities": ["workflow"],
                    },
                    "policy": {
                        "policy_bundle_id": "policy-1",
                        "allowed": allowed,
                        "require_human": require_human,
                        "reason": "human gate" if require_human else "",
                    },
                    "budget": {
                        "money_limit": 2.0,
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
                    "execution_id_prefix": f"{mission_id}-exec",
                    "now_epoch": now_epoch,
                    "max_attempts": 2,
                }
            ),
            encoding="utf-8",
        )
        return path

    def _call(self, *args: str):
        stdout = StringIO()
        stderr = StringIO()
        code = main(["--db", str(self.db), *args], stdout=stdout, stderr=stderr)
        out = json.loads(stdout.getvalue()) if stdout.getvalue() else None
        err = json.loads(stderr.getvalue()) if stderr.getvalue() else None
        return code, out, err

    def test_run_automatically_persists_observability_without_factory_changes(self):
        code, _, err = self._call("run", str(self._mission_file("cli-events")), "--factory", self.factory)
        self.assertEqual(code, 0)
        self.assertIsNone(err)

        code, events, err = self._call("events", "cli-events")
        self.assertEqual(code, 0)
        self.assertIsNone(err)
        self.assertEqual([event["sequence"] for event in events], list(range(1, 9)))
        self.assertEqual(
            [event["kind"] for event in events],
            [
                "MISSION_CREATED",
                "POLICY_EVALUATED",
                "ORCHESTRATOR_SELECTED",
                "RUNTIME_STARTED",
                "RUNTIME_COMPLETED",
                "EVIDENCE_RECORDED",
                "ACCEPTANCE_EVALUATED",
                "MISSION_TERMINAL",
            ],
        )

    def test_events_query_requires_no_runtime_factory(self):
        self._call("run", str(self._mission_file("cli-no-factory")), "--factory", self.factory)
        sys.modules.pop("metao_cli_observed_factory", None)
        code, events, err = self._call("events", "cli-no-factory")
        self.assertEqual(code, 0)
        self.assertIsNone(err)
        self.assertEqual(events[-1]["kind"], "MISSION_TERMINAL")

    def test_events_kind_filter_is_machine_readable(self):
        self._call("run", str(self._mission_file("cli-filter")), "--factory", self.factory)
        code, events, _ = self._call("events", "cli-filter", "--kind", "RUNTIME_COMPLETED")
        self.assertEqual(code, 0)
        self.assertEqual(len(events), 1)
        self.assertEqual(events[0]["payload"]["execution_status"], "SUCCEEDED")
        self.assertEqual(events[0]["payload"]["orchestrator_id"], "cli-observed-runtime")

    def test_wait_approve_resume_events_span_cli_invocations_with_timestamps(self):
        self._call(
            "run",
            str(self._mission_file("cli-observed-approval", require_human=True, now_epoch=100.0)),
            "--factory",
            self.factory,
        )
        self.assertEqual(self.runtime.calls, 0)
        self._call(
            "approve",
            "cli-observed-approval",
            "--approver",
            "igor",
            "--factory",
            self.factory,
            "--now-epoch",
            "101",
        )
        self.assertEqual(self.runtime.calls, 0)
        self._call(
            "resume",
            "cli-observed-approval",
            "--factory",
            self.factory,
            "--now-epoch",
            "102",
        )
        self.assertEqual(self.runtime.calls, 1)

        _, events, _ = self._call("events", "cli-observed-approval")
        self.assertEqual(
            [event["kind"] for event in events],
            [
                "MISSION_CREATED",
                "POLICY_EVALUATED",
                "APPROVAL_REQUESTED",
                "APPROVAL_RECORDED",
                "MISSION_RESUMED",
                "ORCHESTRATOR_SELECTED",
                "RUNTIME_STARTED",
                "RUNTIME_COMPLETED",
                "EVIDENCE_RECORDED",
                "ACCEPTANCE_EVALUATED",
                "MISSION_TERMINAL",
            ],
        )
        self.assertEqual([event["occurred_at_epoch"] for event in events[:3]], [100.0, 100.0, 100.0])
        self.assertEqual(events[3]["occurred_at_epoch"], 101.0)
        self.assertEqual(events[4]["occurred_at_epoch"], 102.0)

    def test_read_only_cli_commands_do_not_append_events(self):
        self._call("run", str(self._mission_file("cli-read-only")), "--factory", self.factory)
        _, before, _ = self._call("events", "cli-read-only")
        self._call("status", "cli-read-only")
        self._call("inspect", "cli-read-only")
        self._call("list")
        _, after, _ = self._call("events", "cli-read-only")
        self.assertEqual(after, before)

    def test_policy_deny_trace_contains_no_runtime_events(self):
        self._call(
            "run",
            str(self._mission_file("cli-policy-deny", allowed=False)),
            "--factory",
            self.factory,
        )
        self.assertEqual(self.runtime.calls, 0)
        _, events, _ = self._call("events", "cli-policy-deny")
        kinds = [event["kind"] for event in events]
        self.assertEqual(kinds, ["MISSION_CREATED", "POLICY_EVALUATED", "MISSION_TERMINAL"])

    def test_unknown_mission_events_returns_structured_error(self):
        code, out, err = self._call("events", "missing")
        self.assertEqual(code, 2)
        self.assertIsNone(out)
        self.assertEqual(err["error"], "MissionNotFound")

    def test_mission_and_event_tables_share_one_sqlite_database(self):
        self._call("run", str(self._mission_file("cli-one-db")), "--factory", self.factory)
        with sqlite3.connect(self.db) as connection:
            tables = {
                row[0]
                for row in connection.execute(
                    "SELECT name FROM sqlite_master WHERE type='table' AND name IN ('mission_records','mission_events')"
                ).fetchall()
            }
        self.assertEqual(tables, {"mission_records", "mission_events"})

    def test_cli_observability_remains_orchestrator_sdk_neutral(self):
        root = Path(__file__).resolve().parents[2]
        source = (root / "src" / "metao" / "cli.py").read_text(encoding="utf-8").lower()
        for forbidden in ("import langgraph", "from langgraph", "import crewai", "from crewai"):
            self.assertNotIn(forbidden, source)


if __name__ == "__main__":
    unittest.main(verbosity=2)
