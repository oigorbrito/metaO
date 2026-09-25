from __future__ import annotations

from pathlib import Path
import sqlite3
import tempfile
import unittest

from metao.routing_decision import (
    RoutingCandidateReceipt,
    RoutingDecisionConflict,
    RoutingDecisionCorrupt,
    RoutingDecisionReceipt,
    SQLiteRoutingDecisionStore,
    routing_receipt_id,
)


def candidates() -> tuple[RoutingCandidateReceipt, ...]:
    return (
        RoutingCandidateReceipt(
            executor_id="b",
            rank=1,
            total_score=0.9,
            base_score=0.4,
            benchmark_score=0.95,
            evidence_id="bench-b",
            reason="exact_fresh_benchmark_evidence",
        ),
        RoutingCandidateReceipt(
            executor_id="a",
            rank=2,
            total_score=0.5,
            base_score=0.8,
            benchmark_score=0.1,
            evidence_id="bench-a",
            reason="exact_fresh_benchmark_evidence",
        ),
    )


def receipt() -> RoutingDecisionReceipt:
    items = candidates()
    receipt_id = routing_receipt_id(
        mission_id="mission-1",
        execution_id="exec-1",
        attempt_number=1,
        now_epoch=120.0,
        policy_digest="sha256:policy",
        selected_executor_id="b",
        candidates=items,
    )
    return RoutingDecisionReceipt(
        receipt_id=receipt_id,
        mission_id="mission-1",
        execution_id="exec-1",
        attempt_number=1,
        now_epoch=120.0,
        policy_digest="sha256:policy",
        selected_executor_id="b",
        candidates=items,
    )


class RoutingDecisionStoreTests(unittest.TestCase):
    def test_record_get_history_and_identical_replay_are_deterministic(self):
        with tempfile.TemporaryDirectory() as temp:
            store = SQLiteRoutingDecisionStore(Path(temp) / "routing.db")
            value = receipt()
            self.assertEqual(store.record(value), value)
            self.assertEqual(store.record(value), value)
            self.assertEqual(store.get(value.receipt_id), value)
            self.assertEqual(store.history("mission-1"), (value,))

    def test_same_receipt_id_with_different_payload_fails_closed(self):
        with tempfile.TemporaryDirectory() as temp:
            store = SQLiteRoutingDecisionStore(Path(temp) / "routing.db")
            value = receipt()
            store.record(value)
            conflict = RoutingDecisionReceipt(
                receipt_id=value.receipt_id,
                mission_id=value.mission_id,
                execution_id=value.execution_id,
                attempt_number=value.attempt_number,
                now_epoch=value.now_epoch,
                policy_digest=value.policy_digest,
                selected_executor_id="a",
                candidates=value.candidates,
            )
            with self.assertRaises(RoutingDecisionConflict):
                store.record(conflict)

    def test_corrupt_persisted_payload_is_detected(self):
        with tempfile.TemporaryDirectory() as temp:
            path = Path(temp) / "routing.db"
            store = SQLiteRoutingDecisionStore(path)
            value = receipt()
            store.record(value)
            with sqlite3.connect(path) as connection:
                connection.execute(
                    "UPDATE routing_decision_receipts SET payload_json=? WHERE receipt_id=?",
                    ("{}", value.receipt_id),
                )
                connection.commit()
            with self.assertRaises(RoutingDecisionCorrupt):
                store.get(value.receipt_id)

    def test_selected_executor_must_be_one_of_ranked_candidates(self):
        with self.assertRaisesRegex(ValueError, "selected executor"):
            RoutingDecisionReceipt(
                receipt_id="receipt",
                mission_id="mission",
                execution_id="exec",
                attempt_number=1,
                now_epoch=1.0,
                policy_digest="sha256:policy",
                selected_executor_id="outside",
                candidates=candidates(),
            )


if __name__ == "__main__":
    unittest.main(verbosity=2)
