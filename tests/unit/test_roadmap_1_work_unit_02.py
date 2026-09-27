from __future__ import annotations

from pathlib import Path
import unittest

import metao
from metao.acceptance import AcceptanceContext, AcceptanceDecision
from metao.adapters.langgraph import LangGraphOrchestratorAdapter, normalize_evidence
from metao.control_plane import MissionStatus
from metao.core import Mission, OrchestratorRegistry
from metao.governance import AcceptanceBudget, evaluate_policy
from metao.mission_store import (
    InMemoryMissionStore,
    MissionAlreadyExists,
    MissionNotFound,
    MissionStorePort,
)
from metao.operator import MissionOperator
from metao.strategy import OrchestratorPoolState, OrchestratorStatus


class FakeGraph:
    def __init__(self) -> None:
        self.calls = 0

    def invoke(self, state):
        self.calls += 1
        return {"result": "done:" + state["objective"]}


class MissionStoreOperatorV1Tests(unittest.TestCase):
    def setUp(self) -> None:
        self.graph = FakeGraph()
        adapter = LangGraphOrchestratorAdapter(self.graph, orchestrator_id="runtime-a", version="1")
        registry = OrchestratorRegistry()
        registry.register(adapter)
        self.store = InMemoryMissionStore()
        self.operator = MissionOperator(
            registry=registry,
            pools=(
                OrchestratorPoolState(
                    "runtime-a",
                    OrchestratorStatus.HEALTHY,
                    frozenset({"workflow"}),
                    0.95,
                    0.95,
                    0.95,
                    10.0,
                    0.01,
                ),
            ),
            normalizers={"runtime-a": normalize_evidence},
            store=self.store,
        )
        self.context = AcceptanceContext(
            "subject-1",
            "state-1",
            "verify-1",
            "policy-1",
            frozenset({"execution_result"}),
        )
        self.budget = AcceptanceBudget(1.0, 1000, 60.0, 3)
        self.allow = evaluate_policy(policy_bundle_id="policy-1", allowed=True)

    def _mission(self, mission_id: str = "mission-1") -> Mission:
        return Mission(mission_id, "operate mission", frozenset({"workflow"}))

    def _run(self, mission_id: str = "mission-1"):
        return self.operator.run(
            self._mission(mission_id),
            policy=self.allow,
            budget=self.budget,
            acceptance_context=self.context,
            now_epoch=100.0,
        )

    def test_store_port_and_in_memory_implementation(self):
        self.assertIsInstance(self.store, MissionStorePort)
        self.assertEqual(self.store.list(), ())
        self.assertFalse(self.store.contains("missing"))

    def test_run_persists_auditable_accepted_outcome(self):
        outcome = self._run()
        record = self.store.get("mission-1")

        self.assertEqual(outcome.acceptance.decision, AcceptanceDecision.ACCEPT)
        self.assertEqual(record.status, MissionStatus.ACCEPTED)
        self.assertEqual(record.outcome.state.attempts[0].orchestrator_id, "runtime-a")
        self.assertEqual(record.revision, 1)

    def test_status_inspect_and_list_use_mission_store(self):
        self._run("mission-b")
        self._run("mission-a")

        self.assertEqual(self.operator.status("mission-a"), MissionStatus.ACCEPTED)
        self.assertEqual(self.operator.inspect("mission-b").mission.objective, "operate mission")
        self.assertEqual(
            tuple(record.mission_id for record in self.operator.list()),
            ("mission-a", "mission-b"),
        )

    def test_duplicate_mission_is_rejected_before_second_runtime_execution(self):
        self._run()
        self.assertEqual(self.graph.calls, 1)

        with self.assertRaises(MissionAlreadyExists):
            self._run()

        self.assertEqual(self.graph.calls, 1)

    def test_policy_block_is_persisted_without_runtime_execution(self):
        denied = evaluate_policy(policy_bundle_id="policy-1", allowed=False)
        outcome = self.operator.run(
            self._mission("mission-denied"),
            policy=denied,
            budget=self.budget,
            acceptance_context=self.context,
            now_epoch=100.0,
        )

        self.assertEqual(outcome.state.status, MissionStatus.BLOCKED)
        self.assertEqual(self.operator.status("mission-denied"), MissionStatus.BLOCKED)
        self.assertEqual(self.graph.calls, 0)

    def test_unknown_mission_fails_closed(self):
        with self.assertRaises(MissionNotFound):
            self.operator.status("missing")
        with self.assertRaises(MissionNotFound):
            self.operator.inspect("missing")

    def test_replace_increments_record_revision(self):
        self._run()
        original = self.store.get("mission-1")
        updated = self.store.replace(original)

        self.assertEqual(updated.revision, 2)
        self.assertEqual(self.store.get("mission-1").revision, 2)

    def test_public_exports_preserve_legacy_operator_and_add_mission_surface(self):
        for name in ("run", "status", "inspect", "cancel", "resume"):
            self.assertTrue(callable(getattr(metao, name)))
        for name in ("MissionOperator", "MissionStorePort", "InMemoryMissionStore"):
            self.assertTrue(hasattr(metao, name))

    def test_core_and_store_remain_framework_sdk_neutral(self):
        root = Path(__file__).resolve().parents[2]
        core_source = (root / "src" / "metao" / "core.py").read_text(encoding="utf-8").lower()
        store_source = (root / "src" / "metao" / "mission_store.py").read_text(encoding="utf-8").lower()
        for forbidden in ("import langgraph", "from langgraph", "import crewai", "from crewai"):
            self.assertNotIn(forbidden, core_source)
            self.assertNotIn(forbidden, store_source)


if __name__ == "__main__":
    unittest.main(verbosity=2)
