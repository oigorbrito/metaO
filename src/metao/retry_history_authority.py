"""Authoritative retry-history coordination for Roadmap 8 A11."""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum

from .retry_history import RetryHistoryEntry, RetryHistoryPort


class RetryHistoryAuthorityDecision(StrEnum):
    READY = "READY"
    BLOCK = "BLOCK"


@dataclass(frozen=True)
class RetryHistoryAuthorityObservation:
    mission_id: str
    decision: RetryHistoryAuthorityDecision
    entries: tuple[RetryHistoryEntry, ...]
    total_execution_cost: float
    reason: str = ""


def observe_retry_history(
    mission_id: str,
    *,
    history: RetryHistoryPort,
) -> RetryHistoryAuthorityObservation:
    if not mission_id:
        raise ValueError("mission_id is required")

    entries = history.for_mission(mission_id)
    if not entries:
        return RetryHistoryAuthorityObservation(
            mission_id,
            RetryHistoryAuthorityDecision.READY,
            (),
            0.0,
        )

    expected_attempt = 1
    seen_executions: set[str] = set()
    total_cost = 0.0
    for entry in entries:
        if entry.mission_id != mission_id:
            return RetryHistoryAuthorityObservation(
                mission_id,
                RetryHistoryAuthorityDecision.BLOCK,
                entries,
                total_cost,
                "retry_history_mission_mismatch",
            )
        if entry.attempt_number != expected_attempt:
            return RetryHistoryAuthorityObservation(
                mission_id,
                RetryHistoryAuthorityDecision.BLOCK,
                entries,
                total_cost,
                "retry_history_sequence_gap",
            )
        if entry.execution_id in seen_executions:
            return RetryHistoryAuthorityObservation(
                mission_id,
                RetryHistoryAuthorityDecision.BLOCK,
                entries,
                total_cost,
                "retry_history_duplicate_execution",
            )
        seen_executions.add(entry.execution_id)
        total_cost += entry.execution_cost
        expected_attempt += 1

    return RetryHistoryAuthorityObservation(
        mission_id,
        RetryHistoryAuthorityDecision.READY,
        entries,
        total_cost,
    )


__all__ = [
    "RetryHistoryAuthorityDecision",
    "RetryHistoryAuthorityObservation",
    "observe_retry_history",
]
