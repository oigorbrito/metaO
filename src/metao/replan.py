"""Mission-level evaluate/halt/replan/escalate control flow.

Adapted from the Block-C CADTopo algorithm-donor role and composed with
metaO's framework-neutral strategy/runtime contracts.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Iterable, Optional, Sequence, Tuple

from .runtime import RecoveryState, recover_preserving_success
from .strategy import OrchestratorPoolState, select_orchestrator


class FailureClass(str, Enum):
    TRANSIENT = "transient"
    TIMEOUT = "timeout"
    POLICY = "policy"
    BUDGET = "budget"
    ACCEPTANCE = "acceptance"
    RUNTIME = "runtime"
    CANCELLED = "cancelled"
    UNKNOWN = "unknown"


class ControlAction(str, Enum):
    CONTINUE = "continue"
    HALT = "halt"
    REPLAN = "replan"
    ESCALATE = "escalate"


@dataclass(frozen=True)
class Evaluation:
    action: ControlAction
    reason: str


@dataclass(frozen=True)
class ReplanLimit:
    max_attempts: int = 3

    def __post_init__(self) -> None:
        if self.max_attempts < 0:
            raise ValueError("max_attempts must be non-negative")


def classify_failure(error: object) -> FailureClass:
    text = str(error).lower()
    if "cancel" in text:
        return FailureClass.CANCELLED
    if "timeout" in text or "timed out" in text:
        return FailureClass.TIMEOUT
    if "policy" in text or "denied" in text or "forbidden" in text:
        return FailureClass.POLICY
    if "budget" in text or "quota" in text or "cost limit" in text:
        return FailureClass.BUDGET
    if "accept" in text or "evidence" in text or "verification" in text:
        return FailureClass.ACCEPTANCE
    if "connection" in text or "temporary" in text or "retry" in text:
        return FailureClass.TRANSIENT
    if "runtime" in text or "worker" in text or "process" in text:
        return FailureClass.RUNTIME
    return FailureClass.UNKNOWN


def evaluate(
    failure: Optional[FailureClass],
    *,
    attempts: int = 0,
    limit: ReplanLimit = ReplanLimit(),
) -> Evaluation:
    if failure is None:
        return Evaluation(ControlAction.CONTINUE, "no failure")
    if failure in {FailureClass.POLICY, FailureClass.BUDGET, FailureClass.CANCELLED}:
        return Evaluation(ControlAction.HALT, f"hard gate: {failure.value}")
    if not replan_allowed(attempts, limit):
        return Evaluation(ControlAction.ESCALATE, "replan limit exhausted")
    return Evaluation(ControlAction.REPLAN, f"recoverable failure: {failure.value}")


def halt(reason: str) -> Evaluation:
    return Evaluation(ControlAction.HALT, reason)


def replan(reason: str) -> Evaluation:
    return Evaluation(ControlAction.REPLAN, reason)


def escalate(reason: str) -> Evaluation:
    return Evaluation(ControlAction.ESCALATE, reason)


def replan_allowed(attempts: int, limit: ReplanLimit = ReplanLimit()) -> bool:
    if attempts < 0:
        raise ValueError("attempts must be non-negative")
    return attempts < limit.max_attempts


def reselect_orchestrator(
    pools: Iterable[OrchestratorPoolState],
    *,
    current_orchestrator_id: Optional[str] = None,
    excluded: Iterable[str] = (),
) -> Optional[str]:
    excluded_ids = set(excluded)
    if current_orchestrator_id:
        excluded_ids.add(current_orchestrator_id)
    candidates = tuple(
        pool for pool in pools if pool.orchestrator_id not in excluded_ids
    )
    return select_orchestrator(candidates)


def preserve_successful_progress(
    successful_steps: Iterable[str], planned_steps: Sequence[str]
) -> Tuple[Tuple[str, ...], Tuple[str, ...]]:
    state = RecoveryState(successful_steps=frozenset(successful_steps))
    return recover_preserving_success(state, planned_steps)


__all__ = [
    "FailureClass",
    "ControlAction",
    "Evaluation",
    "ReplanLimit",
    "classify_failure",
    "evaluate",
    "halt",
    "replan",
    "escalate",
    "replan_allowed",
    "reselect_orchestrator",
    "preserve_successful_progress",
]
