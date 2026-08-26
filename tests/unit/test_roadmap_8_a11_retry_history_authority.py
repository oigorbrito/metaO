from __future__ import annotations

import unittest

from metao.retry_history import (
    InMemoryRetryHistoryStore,
    RetryHistoryEntry,
    RetryOutcome,
)
from metao.retry_history_authority import (
    RetryHistoryAuthorityDecision,
    observe_retry_history,
)


class RetryHistoryAuthorityTests(unittest.TestCase):
    def entry(self, attempt: int, *, execution_id: str | None = None, cost: float = 1.0) -> RetryHistoryEntry:
        return RetryHistoryEntry(
            history_id=f"h-{attempt}-{execution_id or attempt}",
            mission_id="m-1",
            attempt_number=attempt,
            execution_id=execution_id or f"exec-{attempt}",
            orchestrator_id=f"runtime-{attempt}",
            started_at_epoch=float(attempt),
            ended_at_epoch=float(attempt) + 0.5,
            outcome=RetryOutcome.FAILED,
            execution_cost=cost,
            failure_class="TRANSIENT",
        )

    def test_empty_authoritative_history_is_ready_without_fabrication(self) -> None:
        result = observe_retry_history("m-1", history=InMemoryRetryHistoryStore())
        self.assertEqual(result.decision, RetryHistoryAuthorityDecision.READY)
        self.assertEqual(result.entries, ())
        self.assertEqual(result.total_execution_cost, 0.0)

    def test_contiguous_authoritative_history_is_ready(self) -> None:
        store = InMemoryRetryHistoryStore()
        store.append(self.entry(1, cost=1.25))
        store.append(self.entry(2, cost=2.75))
        result = observe_retry_history("m-1", history=store)
        self.assertEqual(result.decision, RetryHistoryAuthorityDecision.READY)
        self.assertEqual(tuple(item.attempt_number for item in result.entries), (1, 2))
        self.assertEqual(result.total_execution_cost, 4.0)

    def test_sequence_gap_blocks(self) -> None:
        class GapHistory:
            def append(self, entry: RetryHistoryEntry) -> None:  # pragma: no cover
                raise NotImplementedError
            def all(self) -> tuple[RetryHistoryEntry, ...]:
                return ()
            def for_mission(self, mission_id: str) -> tuple[RetryHistoryEntry, ...]:
                return (self_outer.entry(1), self_outer.entry(3))
        self_outer = self
        result = observe_retry_history("m-1", history=GapHistory())
        self.assertEqual(result.decision, RetryHistoryAuthorityDecision.BLOCK)
        self.assertEqual(result.reason, "retry_history_sequence_gap")

    def test_duplicate_execution_blocks(self) -> None:
        class DuplicateExecutionHistory:
            def append(self, entry: RetryHistoryEntry) -> None:  # pragma: no cover
                raise NotImplementedError
            def all(self) -> tuple[RetryHistoryEntry, ...]:
                return ()
            def for_mission(self, mission_id: str) -> tuple[RetryHistoryEntry, ...]:
                return (self_outer.entry(1, execution_id="same"), self_outer.entry(2, execution_id="same"))
        self_outer = self
        result = observe_retry_history("m-1", history=DuplicateExecutionHistory())
        self.assertEqual(result.decision, RetryHistoryAuthorityDecision.BLOCK)
        self.assertEqual(result.reason, "retry_history_duplicate_execution")

    def test_caller_history_is_not_an_input(self) -> None:
        self.assertNotIn("caller_history", observe_retry_history.__annotations__)


if __name__ == "__main__":
    unittest.main()
