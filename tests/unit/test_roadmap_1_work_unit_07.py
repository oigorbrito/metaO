from __future__ import annotations

from dataclasses import FrozenInstanceError
from pathlib import Path
import sqlite3
import tempfile
import unittest

from metao.acceptance import AcceptanceContext, AcceptanceDecision
from metao.adapters.langgraph import normalize_evidence
from metao.catalog import OrchestratorCatalog
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
from metao.mission_store import InMemoryMissionStore
from metao.observability import EventLedgerPort, InMemoryEventLedger, MissionEventKind
from metao.observed_operator import ObservableMissionOperator
from metao.operator import MissionOperator
from metao.sqlite_event_ledger import EventLedgerCorrupt, SQLiteEventLedger
from metao.sqlite_store import SQLiteMissionStore


class Runtime:
    def __init__(self, orchestrator_id: str, statuses: tuple[ExecutionStatus, ...]) -> None:
        self._descriptor = OrchestratorDescriptor(orchestrator_id, "v1", frozenset({"workflow"}))
        self._statuses = list(statuses)
        self.calls = 0

    @property
    def descriptor(self):
        return self._descriptor

    def health(self):
        return HealthReport(HealthStatus.HEALTHY)

    def execute(self, request: ExecutionRequest):
        self.calls += 1
        status = self._statuses.pop(0) if self._statuses else ExecutionStatus.SUCCEEDED
        return ExecutionResult(
            request.execution_id,
            self.descriptor.orchestrator_id,
            status,
            {"result": f"done:{self.descriptor.orchestrator_id}"},
            error="runtime_failed" if status is ExecutionStatus.FAILED else "",
        )

    def cancel(self, execution_id: str) -> None:
        pass


class ObservabilityEventLedgerV1Tests(unittest.TestCase):
    def setUp(self) -> None:
        self.context = AcceptanceContext(
            "subject-1",
            "state-1",
            "verify-1",
            "policy-1",
            frozenset({"execution_result"}),
        )
        self.budget = AcceptanceBudget(2.0, 1000, 60.0, 5)
        self.allow = evaluate_policy(policy_bundle_id="policy-1", allowed=True)

    def _operator(
        self,
        *,
        store,
        ledger,
        primary_statuses: tuple[ExecutionStatus, ...] = (ExecutionStatus.SUCCEEDED,),
        include_fallback: bool = False,
    ):
        registry = OrchestratorRegistry()
        primary = Runtime("primary", primary_statuses)
        registry.register(primary)
        catalog = OrchestratorCatalog(registry)
        catalog.register(
            "primary",
            normalizer=normalize_evidence,
            cost=0.01,
            latency_ms=10.0,
            success_rate=0.99,
            quality=0.99,
            reliability=0.99,
        )
        fallback = None
        if include_fallback:
            fallback = Runtime("fallback", (ExecutionStatus.SUCCEEDED,))
            registry.register(fallback)
            catalog.register(
                "fallback",
                normalizer=normalize_evidence,
                cost=5.0,
                latency_ms=5000.0,
                success_rate=0.2,
                quality=0.2,
                reliability=0.2,
            )
        base = MissionOperator(registry=registry, catalog=catalog, store=store)
        return ObservableMissionOperator(base, ledger), primary, fallback

    def test_in_memory_ledger_is_append_only_monotonic_and_payload_immutable(self):
        ledger = InMemoryEventLedger()
        first = ledger.append(
            "m1",
            MissionEventKind.MISSION_CREATED,
            payload={"nested": {"items": [1, 2]}},
            occurred_at_epoch=10.0,
        )
        second = ledger.append("m1", MissionEventKind.POLICY_EVALUATED, occurred_at_epoch=11.0)

        self.assertEqual((first.sequence, second.sequence), (1, 2))
        self.assertEqual((first.event_id, second.event_id), ("m1:event:1", "m1:event:2"))
        self.assertEqual(first.payload["nested"]["items"], (1, 2))
        with self.assertRaises(TypeError):
            first.payload["x"] = 1
        with self.assertRaises(FrozenInstanceError):
            first.sequence = 9

    def test_sqlite_ledger_satisfies_port_and_survives_restart(self):
        with tempfile.TemporaryDirectory() as temp:
            path = Path(temp) / "events.db"
            ledger = SQLiteEventLedger(path)
            self.assertIsInstance(ledger, EventLedgerPort)
            ledger.append("m1", MissionEventKind.MISSION_CREATED, payload={"value": 1}, occurred_at_epoch=1.0)
            ledger.append("m1", MissionEventKind.POLICY_EVALUATED, payload={"value": 2}, occurred_at_epoch=2.0)

            reopened = SQLiteEventLedger(path)
            events = reopened.list("m1")
            self.assertEqual([event.sequence for event in events], [1, 2])
            self.assertEqual([event.kind for event in events], [MissionEventKind.MISSION_CREATED, MissionEventKind.POLICY_EVALUATED])
            self.assertEqual(events[1].payload["value"], 2)

    def test_accepted_mission_emits_uniform_control_plane_trace(self):
        ledger = InMemoryEventLedger()
        operator, primary, _ = self._operator(store=InMemoryMissionStore(), ledger=ledger)
        outcome = operator.run(
            Mission("m-accepted", "exercise observability", frozenset({"workflow"})),
            policy=self.allow,
            budget=self.budget,
            acceptance_context=self.context,
            now_epoch=100.0,
        )

        self.assertEqual(outcome.acceptance.decision, AcceptanceDecision.ACCEPT)
        self.assertEqual(primary.calls, 1)
        self.assertEqual(
            [event.kind for event in operator.events("m-accepted")],
            [
                MissionEventKind.MISSION_CREATED,
                MissionEventKind.POLICY_EVALUATED,
                MissionEventKind.ORCHESTRATOR_SELECTED,
                MissionEventKind.RUNTIME_STARTED,
                MissionEventKind.RUNTIME_COMPLETED,
                MissionEventKind.EVIDENCE_RECORDED,
                MissionEventKind.ACCEPTANCE_EVALUATED,
                MissionEventKind.MISSION_TERMINAL,
            ],
        )
        terminal = operator.events("m-accepted")[-1]
        self.assertEqual(terminal.payload["status"], "ACCEPTED")
        self.assertEqual(terminal.payload["verifier_attempts_used"], 1)

    def test_policy_deny_emits_no_runtime_or_selection_events(self):
        ledger = InMemoryEventLedger()
        operator, primary, _ = self._operator(store=InMemoryMissionStore(), ledger=ledger)
        deny = evaluate_policy(policy_bundle_id="policy-1", allowed=False, reason="denied")
        outcome = operator.run(
            Mission("m-deny", "deny", frozenset({"workflow"})),
            policy=deny,
            budget=self.budget,
            acceptance_context=self.context,
            now_epoch=100.0,
        )

        self.assertEqual(outcome.state.status.value, "BLOCKED")
        self.assertEqual(primary.calls, 0)
        kinds = [event.kind for event in operator.events("m-deny")]
        self.assertEqual(kinds, [MissionEventKind.MISSION_CREATED, MissionEventKind.POLICY_EVALUATED, MissionEventKind.MISSION_TERMINAL])

    def test_failover_trace_records_replan_between_attempts(self):
        ledger = InMemoryEventLedger()
        operator, primary, fallback = self._operator(
            store=InMemoryMissionStore(),
            ledger=ledger,
            primary_statuses=(ExecutionStatus.FAILED,),
            include_fallback=True,
        )
        outcome = operator.run(
            Mission("m-failover", "fail then recover", frozenset({"workflow"})),
            policy=self.allow,
            budget=self.budget,
            acceptance_context=self.context,
            now_epoch=100.0,
            max_attempts=2,
        )

        self.assertEqual(outcome.state.status.value, "ACCEPTED")
        self.assertEqual(primary.calls, 1)
        self.assertEqual(fallback.calls, 1)
        events = operator.events("m-failover")
        kinds = [event.kind for event in events]
        self.assertEqual(kinds.count(MissionEventKind.ORCHESTRATOR_SELECTED), 2)
        self.assertEqual(kinds.count(MissionEventKind.RUNTIME_COMPLETED), 2)
        self.assertEqual(kinds.count(MissionEventKind.REPLAN_REQUESTED), 1)
        replan_index = kinds.index(MissionEventKind.REPLAN_REQUESTED)
        second_selection_index = [i for i, kind in enumerate(kinds) if kind is MissionEventKind.ORCHESTRATOR_SELECTED][1]
        self.assertLess(replan_index, second_selection_index)
        self.assertEqual(events[-1].payload["attempted_orchestrators"], ("primary", "fallback"))

    def test_wait_approve_resume_trace_is_monotonic_across_sqlite_restarts(self):
        with tempfile.TemporaryDirectory() as temp:
            path = Path(temp) / "metao.db"
            require_human = evaluate_policy(
                policy_bundle_id="policy-1",
                allowed=True,
                require_human=True,
                reason="operator approval",
            )

            operator1, runtime1, _ = self._operator(
                store=SQLiteMissionStore(path),
                ledger=SQLiteEventLedger(path),
            )
            outcome = operator1.run(
                Mission("m-approval", "approval flow", frozenset({"workflow"})),
                policy=require_human,
                budget=self.budget,
                acceptance_context=self.context,
                now_epoch=100.0,
            )
            self.assertEqual(outcome.state.status.value, "WAITING_APPROVAL")
            self.assertEqual(runtime1.calls, 0)

            operator2, runtime2, _ = self._operator(
                store=SQLiteMissionStore(path),
                ledger=SQLiteEventLedger(path),
            )
            approved = operator2.approve("m-approval", approver_id="igor", now_epoch=101.0)
            self.assertTrue(approved.approval_record.approved)
            self.assertEqual(runtime2.calls, 0)

            operator3, runtime3, _ = self._operator(
                store=SQLiteMissionStore(path),
                ledger=SQLiteEventLedger(path),
            )
            resumed = operator3.resume("m-approval", now_epoch=102.0)
            self.assertEqual(resumed.state.status.value, "ACCEPTED")
            self.assertEqual(runtime3.calls, 1)

            events = SQLiteEventLedger(path).list("m-approval")
            self.assertEqual([event.sequence for event in events], list(range(1, len(events) + 1)))
            self.assertEqual(
                [event.kind for event in events],
                [
                    MissionEventKind.MISSION_CREATED,
                    MissionEventKind.POLICY_EVALUATED,
                    MissionEventKind.APPROVAL_REQUESTED,
                    MissionEventKind.APPROVAL_RECORDED,
                    MissionEventKind.MISSION_RESUMED,
                    MissionEventKind.ORCHESTRATOR_SELECTED,
                    MissionEventKind.RUNTIME_STARTED,
                    MissionEventKind.RUNTIME_COMPLETED,
                    MissionEventKind.EVIDENCE_RECORDED,
                    MissionEventKind.ACCEPTANCE_EVALUATED,
                    MissionEventKind.MISSION_TERMINAL,
                ],
            )
            self.assertEqual([event.occurred_at_epoch for event in events[:3]], [100.0, 100.0, 100.0])
            self.assertEqual(events[3].occurred_at_epoch, 101.0)
            self.assertEqual(events[4].occurred_at_epoch, 102.0)

    def test_denied_approval_terminally_records_block_without_runtime(self):
        ledger = InMemoryEventLedger()
        operator, runtime, _ = self._operator(store=InMemoryMissionStore(), ledger=ledger)
        require_human = evaluate_policy(policy_bundle_id="policy-1", allowed=True, require_human=True)
        operator.run(
            Mission("m-denied-approval", "approval deny", frozenset({"workflow"})),
            policy=require_human,
            budget=self.budget,
            acceptance_context=self.context,
            now_epoch=10.0,
        )
        denied = operator.approve("m-denied-approval", approver_id="igor", approved=False, now_epoch=11.0)
        self.assertEqual(denied.status.value, "BLOCKED")
        self.assertEqual(runtime.calls, 0)
        kinds = [event.kind for event in operator.events("m-denied-approval")]
        self.assertEqual(kinds[-2:], [MissionEventKind.APPROVAL_RECORDED, MissionEventKind.MISSION_TERMINAL])
        self.assertNotIn(MissionEventKind.RUNTIME_STARTED, kinds)

    def test_sqlite_rejects_non_json_payload_and_detects_binding_corruption(self):
        with tempfile.TemporaryDirectory() as temp:
            path = Path(temp) / "events.db"
            ledger = SQLiteEventLedger(path)
            with self.assertRaises(TypeError):
                ledger.append("m1", MissionEventKind.MISSION_CREATED, payload={"bad": {1, 2}})
            ledger.append("m1", MissionEventKind.MISSION_CREATED)
            with sqlite3.connect(path) as connection:
                connection.execute("UPDATE mission_events SET event_id='forged' WHERE mission_id='m1'")
            with self.assertRaises(EventLedgerCorrupt):
                SQLiteEventLedger(path).list("m1")

    def test_all_events_are_deterministic_across_missions(self):
        ledger = InMemoryEventLedger()
        ledger.append("z", MissionEventKind.MISSION_CREATED)
        ledger.append("a", MissionEventKind.MISSION_CREATED)
        ledger.append("a", MissionEventKind.POLICY_EVALUATED)
        self.assertEqual(
            [(event.mission_id, event.sequence) for event in ledger.all()],
            [("a", 1), ("a", 2), ("z", 1)],
        )

    def test_observability_boundary_remains_orchestrator_sdk_neutral(self):
        root = Path(__file__).resolve().parents[2]
        for relative in (
            "src/metao/observability.py",
            "src/metao/sqlite_event_ledger.py",
            "src/metao/observed_operator.py",
        ):
            source = (root / relative).read_text(encoding="utf-8").lower()
            for forbidden in ("import langgraph", "from langgraph", "import crewai", "from crewai"):
                self.assertNotIn(forbidden, source)


if __name__ == "__main__":
    unittest.main(verbosity=2)
