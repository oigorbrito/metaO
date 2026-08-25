from __future__ import annotations

import math
import unittest

from metao.retry_history import (
    InMemoryRetryHistoryStore,
    RetryHistoryDuplicate,
    RetryHistoryEntry,
    RetryOutcome,
)


class RetryHistoryPrimitiveTests(unittest.TestCase):
    def _entry(
        self,
        *,
        history_id: str = "h-1",
        mission_id: str = "m-1",
        attempt: int = 1,
        started: float = 10.0,
        execution_id: str | None = None,
    ) -> RetryHistoryEntry:
        return RetryHistoryEntry(
            history_id=history_id,
            mission_id=mission_id,
            attempt_number=attempt,
            execution_id=execution_id or f"exec-{attempt}",
            orchestrator_id="runtime-1",
            started_at_epoch=started,
            ended_at_epoch=started + 1.0,
            outcome=RetryOutcome.FAILED,
            execution_cost=2.5,
            failure_class="TRANSIENT",
        )

    def test_append_is_factual_and_duplicate_id_fails_closed(self) -> None:
        store = InMemoryRetryHistoryStore()
        entry = self._entry()
        store.append(entry)
        self.assertEqual(store.all(), (entry,))
        with self.assertRaises(RetryHistoryDuplicate):
            store.append(entry)

    def test_same_factual_attempt_cannot_use_new_history_id(self) -> None:
        store = InMemoryRetryHistoryStore()
        store.append(self._entry(history_id="h-1"))
        with self.assertRaises(RetryHistoryDuplicate):
            store.append(self._entry(history_id="h-forged"))

    def test_history_is_not_replaceable_operational_snapshot(self) -> None:
        store = InMemoryRetryHistoryStore()
        first = self._entry(history_id="h-1", attempt=1, started=20.0)
        second = self._entry(history_id="h-2", attempt=2, started=30.0)
        store.append(first)
        store.append(second)
        self.assertEqual(store.for_mission("m-1"), (first, second))

    def test_mission_query_is_deterministic_by_attempt(self) -> None:
        store = InMemoryRetryHistoryStore()
        later = self._entry(history_id="h-2", attempt=2, started=20.0)
        earlier = self._entry(history_id="h-1", attempt=1, started=30.0)
        store.append(later)
        store.append(earlier)
        self.assertEqual(store.for_mission("m-1"), (earlier, later))

    def test_missing_history_returns_empty_not_fabricated_entries(self) -> None:
        self.assertEqual(InMemoryRetryHistoryStore().for_mission("missing"), ())

    def test_invalid_attempt_and_timestamps_are_rejected(self) -> None:
        for attempt in (0, True, 1.5):
            with self.subTest(attempt=attempt), self.assertRaises(ValueError):
                RetryHistoryEntry("h", "m", attempt, "e", "o", 0.0, 1.0, RetryOutcome.FAILED)  # type: ignore[arg-type]
        with self.assertRaises(ValueError):
            RetryHistoryEntry("h", "m", 1, "e", "o", 2.0, 1.0, RetryOutcome.FAILED)

    def test_non_finite_numeric_values_are_rejected(self) -> None:
        for value in (math.nan, math.inf, -math.inf):
            with self.subTest(field="started", value=value), self.assertRaises(ValueError):
                RetryHistoryEntry("h", "m", 1, "e", "o", value, 1.0, RetryOutcome.FAILED)
            with self.subTest(field="ended", value=value), self.assertRaises(ValueError):
                RetryHistoryEntry("h", "m", 1, "e", "o", 0.0, value, RetryOutcome.FAILED)
            with self.subTest(field="cost", value=value), self.assertRaises(ValueError):
                RetryHistoryEntry("h", "m", 1, "e", "o", 0.0, 1.0, RetryOutcome.FAILED, execution_cost=value)

    def test_negative_execution_cost_is_rejected(self) -> None:
        with self.assertRaises(ValueError):
            RetryHistoryEntry("h", "m", 1, "e", "o", 0.0, 1.0, RetryOutcome.FAILED, execution_cost=-0.01)

    def test_a11_does_not_smuggle_a18_usage_dimensions(self) -> None:
        entry = self._entry()
        for forbidden in ("tokens", "verification_wall_time_s", "verifier_attempts", "verification_money"):
            self.assertFalse(hasattr(entry, forbidden))


if __name__ == "__main__":
    unittest.main()
