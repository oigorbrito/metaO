from __future__ import annotations

from pathlib import Path
import sqlite3
import tempfile
import unittest

from metao.acceptance import AcceptanceDecision, AcceptanceProof, AcceptanceResult
from metao.control_plane import MissionAttempt, MissionOutcome, MissionState, MissionStatus
from metao.core import EvidenceEnvelope, ExecutionResult, ExecutionStatus, Mission
from metao.governance import AcceptanceBudget
from metao.mission_store import MissionAlreadyExists, MissionNotFound, MissionRecord, MissionStorePort
from metao.sqlite_store import MissionStoreCorrupt, SQLiteMissionStore


def make_record(mission_id: str = "m-1", *, revision: int = 1, failed_then_accepted: bool = True) -> MissionRecord:
    mission = Mission(mission_id, "persist mission lifecycle", frozenset({"workflow"}))
    evidence = EvidenceEnvelope(
        mission_id=mission_id,
        execution_id=f"{mission_id}-exec-2",
        orchestrator_id="runtime-b",
        adapter_id="adapter-b",
        adapter_version="1",
        attempt_id="attempt-2",
        subject_id="subject-1",
        subject_state_id="state-1",
        verification_context_id="verify-1",
        policy_bundle_id="policy-1",
        obligation_ids=frozenset({"result"}),
        evidence_payload_digest="payload-digest",
        provenance="runtime-b:exec-2",
        verifier_id="verifier-1",
        approval_evidence="approval-1",
        confidence=0.95,
        verification_cost_units=2,
    )
    execution = ExecutionResult(
        f"{mission_id}-exec-2",
        "runtime-b",
        ExecutionStatus.SUCCEEDED,
        output={"answer": 42, "nested": {"ok": True}, "items": [1, 2, 3]},
        evidence=(evidence,),
    )
    proof = AcceptanceProof(
        AcceptanceDecision.ACCEPT,
        ("all_required_evidence_passed",),
        (f"{mission_id}-exec-2:result",),
        "proof-digest",
    )
    acceptance = AcceptanceResult(
        AcceptanceDecision.ACCEPT,
        ("all_required_evidence_passed",),
        proof,
    )
    first = MissionAttempt(
        1,
        f"{mission_id}-exec-1",
        "runtime-a",
        ExecutionStatus.FAILED,
        AcceptanceDecision.NOT_DONE,
        ("execution_not_succeeded",),
    )
    second = MissionAttempt(
        2,
        f"{mission_id}-exec-2",
        "runtime-b",
        ExecutionStatus.SUCCEEDED,
        AcceptanceDecision.ACCEPT,
        (),
    )
    attempts = (first, second) if failed_then_accepted else (second,)
    history = (
        MissionStatus.CREATED,
        MissionStatus.PLANNING,
        MissionStatus.SELECTING,
        MissionStatus.RUNNING,
        MissionStatus.REPLANNING,
        MissionStatus.SELECTING,
        MissionStatus.RUNNING,
        MissionStatus.VERIFYING,
        MissionStatus.ACCEPTED,
    ) if failed_then_accepted else (
        MissionStatus.CREATED,
        MissionStatus.PLANNING,
        MissionStatus.SELECTING,
        MissionStatus.RUNNING,
        MissionStatus.VERIFYING,
        MissionStatus.ACCEPTED,
    )
    state = MissionState(mission_id, MissionStatus.ACCEPTED, attempts, history)
    budget = AcceptanceBudget(
        money_limit=10.0,
        token_limit=1000,
        wall_time_limit_s=60.0,
        verifier_attempt_limit=5,
        money_used=1.25,
        tokens_used=120,
        wall_time_used_s=2.5,
        verifier_attempts_used=2,
    )
    outcome = MissionOutcome(
        mission_id,
        "runtime-b",
        execution,
        acceptance,
        budget,
        ("runtime-a", "runtime-b") if failed_then_accepted else ("runtime-b",),
        state,
    )
    return MissionRecord(mission, outcome, revision)


class SQLiteMissionStoreV1Tests(unittest.TestCase):
    def setUp(self):
        self.tempdir = tempfile.TemporaryDirectory()
        self.db_path = Path(self.tempdir.name) / "metao.db"

    def tearDown(self):
        self.tempdir.cleanup()

    def test_sqlite_store_satisfies_mission_store_port(self):
        store = SQLiteMissionStore(self.db_path)
        self.assertIsInstance(store, MissionStorePort)

    def test_create_restart_get_preserves_canonical_record(self):
        SQLiteMissionStore(self.db_path).create(make_record())
        restarted = SQLiteMissionStore(self.db_path)
        record = restarted.get("m-1")
        self.assertEqual(record.mission.objective, "persist mission lifecycle")
        self.assertEqual(record.mission.required_capabilities, frozenset({"workflow"}))
        self.assertEqual(record.status, MissionStatus.ACCEPTED)
        self.assertEqual(record.revision, 1)
        self.assertEqual(dict(record.outcome.execution.output), {"answer": 42, "nested": {"ok": True}, "items": [1, 2, 3]})

    def test_attempt_ledger_and_replan_history_survive_restart(self):
        SQLiteMissionStore(self.db_path).create(make_record())
        state = SQLiteMissionStore(self.db_path).get("m-1").outcome.state
        self.assertIsNotNone(state)
        self.assertEqual([item.orchestrator_id for item in state.attempts], ["runtime-a", "runtime-b"])
        self.assertEqual([item.execution_id for item in state.attempts], ["m-1-exec-1", "m-1-exec-2"])
        self.assertIn(MissionStatus.REPLANNING, state.history)
        self.assertEqual(state.history[-1], MissionStatus.ACCEPTED)

    def test_acceptance_proof_budget_and_execution_evidence_survive_restart(self):
        SQLiteMissionStore(self.db_path).create(make_record())
        outcome = SQLiteMissionStore(self.db_path).get("m-1").outcome
        self.assertEqual(outcome.acceptance.proof.digest, "proof-digest")
        self.assertEqual(outcome.acceptance.proof.evidence_ids, ("m-1-exec-2:result",))
        self.assertEqual(outcome.budget.money_used, 1.25)
        self.assertEqual(outcome.budget.verifier_attempts_used, 2)
        self.assertEqual(outcome.execution.evidence[0].approval_evidence, "approval-1")
        self.assertEqual(outcome.execution.evidence[0].obligation_ids, frozenset({"result"}))

    def test_duplicate_mission_id_is_rejected_across_restarts(self):
        SQLiteMissionStore(self.db_path).create(make_record())
        restarted = SQLiteMissionStore(self.db_path)
        with self.assertRaises(MissionAlreadyExists):
            restarted.create(make_record())

    def test_replace_increments_revision_and_persists_it(self):
        store = SQLiteMissionStore(self.db_path)
        original = make_record()
        store.create(original)
        updated = store.replace(original)
        self.assertEqual(updated.revision, 2)
        self.assertEqual(SQLiteMissionStore(self.db_path).get("m-1").revision, 2)

    def test_two_missions_list_deterministically_after_restart(self):
        store = SQLiteMissionStore(self.db_path)
        store.create(make_record("m-2"))
        store.create(make_record("m-1"))
        restarted = SQLiteMissionStore(self.db_path)
        self.assertEqual([record.mission_id for record in restarted.list()], ["m-1", "m-2"])

    def test_unknown_mission_fails_closed(self):
        with self.assertRaises(MissionNotFound):
            SQLiteMissionStore(self.db_path).get("missing")

    def test_cross_column_corruption_is_detected(self):
        store = SQLiteMissionStore(self.db_path)
        store.create(make_record())
        with sqlite3.connect(self.db_path) as connection:
            connection.execute("UPDATE mission_records SET status='FAILED' WHERE mission_id='m-1'")
        with self.assertRaises(MissionStoreCorrupt):
            store.get("m-1")

    def test_non_json_runtime_output_is_rejected_instead_of_stringified(self):
        record = make_record()
        execution = ExecutionResult(
            record.outcome.execution.execution_id,
            record.outcome.execution.orchestrator_id,
            ExecutionStatus.SUCCEEDED,
            output={"opaque": object()},
        )
        outcome = MissionOutcome(
            record.outcome.mission_id,
            record.outcome.orchestrator_id,
            execution,
            record.outcome.acceptance,
            record.outcome.budget,
            record.outcome.attempted_orchestrators,
            record.outcome.state,
        )
        with self.assertRaises(TypeError):
            SQLiteMissionStore(self.db_path).create(MissionRecord(record.mission, outcome))
        self.assertFalse(SQLiteMissionStore(self.db_path).contains("m-1"))

    def test_sqlite_dependency_stays_outside_core_and_store_boundary(self):
        root = Path(__file__).resolve().parents[2]
        core = (root / "src" / "metao" / "core.py").read_text(encoding="utf-8").lower()
        boundary = (root / "src" / "metao" / "mission_store.py").read_text(encoding="utf-8").lower()
        adapter = (root / "src" / "metao" / "sqlite_store.py").read_text(encoding="utf-8").lower()
        self.assertNotIn("import sqlite3", core)
        self.assertNotIn("import sqlite3", boundary)
        self.assertNotIn("langgraph", adapter)
        self.assertNotIn("crewai", adapter)

    def test_process_local_sqlite_memory_mode_is_rejected(self):
        with self.assertRaises(ValueError):
            SQLiteMissionStore(":memory:")


if __name__ == "__main__":
    unittest.main()
