"""Global policy, acceptance budget, approval and confidence governance.

Composition roles frozen in Block C:
- OMA-style policy identity/evidence semantics;
- Conductor durable HUMAN-task semantics as the transport target;
- Inspect-AI-style verification limits and escalation patterns.

This module owns framework-neutral governance decisions only; it does not import
Conductor or any orchestrator SDK.
"""

from __future__ import annotations

import math
import threading
from dataclasses import dataclass, replace
from enum import Enum
from typing import Optional

from .acceptance import AcceptanceDecision


class PolicyEffect(str, Enum):
    ALLOW = "ALLOW"
    DENY = "DENY"
    REQUIRE_HUMAN = "REQUIRE_HUMAN"


@dataclass(frozen=True)
class PolicyDecision:
    effect: PolicyEffect
    policy_bundle_id: str
    reason: str = ""


def evaluate_policy(*, policy_bundle_id: str, allowed: bool, require_human: bool = False, reason: str = "") -> PolicyDecision:
    if not allowed:
        return PolicyDecision(PolicyEffect.DENY, policy_bundle_id, reason or "policy_denied")
    if require_human:
        return PolicyDecision(PolicyEffect.REQUIRE_HUMAN, policy_bundle_id, reason or "human_approval_required")
    return PolicyDecision(PolicyEffect.ALLOW, policy_bundle_id, reason)


class BudgetExhausted(RuntimeError):
    pass


def _budget_values_are_finite(*values: float | int) -> bool:
    try:
        return all(isinstance(value, int) or math.isfinite(value) for value in values)
    except (TypeError, OverflowError):
        return False


@dataclass(frozen=True)
class AcceptanceBudget:
    money_limit: float
    token_limit: int
    wall_time_limit_s: float
    verifier_attempt_limit: int
    money_used: float = 0.0
    tokens_used: int = 0
    wall_time_used_s: float = 0.0
    verifier_attempts_used: int = 0

    def __post_init__(self) -> None:
        if not _budget_values_are_finite(
            self.money_limit,
            self.token_limit,
            self.wall_time_limit_s,
            self.verifier_attempt_limit,
            self.money_used,
            self.tokens_used,
            self.wall_time_used_s,
            self.verifier_attempts_used,
        ):
            raise ValueError("budget values must be finite")
        if (
            self.money_limit < 0
            or self.token_limit < 0
            or self.wall_time_limit_s < 0
            or self.verifier_attempt_limit < 0
        ):
            raise ValueError("budget limits cannot be negative")
        if (
            self.money_used < 0
            or self.tokens_used < 0
            or self.wall_time_used_s < 0
            or self.verifier_attempts_used < 0
        ):
            raise ValueError("budget usage cannot be negative")
        if self.money_used > self.money_limit:
            raise ValueError("initial money usage cannot exceed limit")
        if self.tokens_used > self.token_limit:
            raise ValueError("initial token usage cannot exceed limit")
        if self.wall_time_used_s > self.wall_time_limit_s:
            raise ValueError("initial wall-time usage cannot exceed limit")
        if self.verifier_attempts_used > self.verifier_attempt_limit:
            raise ValueError("initial verifier-attempt usage cannot exceed limit")

    def remaining_money(self) -> float:
        return self.money_limit - self.money_used

    def consume(
        self,
        *,
        money: float = 0.0,
        tokens: int = 0,
        wall_time_s: float = 0.0,
        verifier_attempts: int = 0,
    ) -> "AcceptanceBudget":
        if not _budget_values_are_finite(money, tokens, wall_time_s, verifier_attempts):
            raise ValueError("budget consumption must be finite")
        if min(money, tokens, wall_time_s, verifier_attempts) < 0:
            raise ValueError("budget consumption cannot be negative")
        money_used = self.money_used + money
        tokens_used = self.tokens_used + tokens
        wall_time_used_s = self.wall_time_used_s + wall_time_s
        verifier_attempts_used = self.verifier_attempts_used + verifier_attempts
        if money_used > self.money_limit:
            raise BudgetExhausted("acceptance money budget exhausted")
        if tokens_used > self.token_limit:
            raise BudgetExhausted("acceptance token budget exhausted")
        if wall_time_used_s > self.wall_time_limit_s:
            raise BudgetExhausted("acceptance wall-time budget exhausted")
        if verifier_attempts_used > self.verifier_attempt_limit:
            raise BudgetExhausted("acceptance verifier-attempt budget exhausted")
        updated = replace(
            self,
            money_used=money_used,
            tokens_used=tokens_used,
            wall_time_used_s=wall_time_used_s,
            verifier_attempts_used=verifier_attempts_used,
        )
        return updated


@dataclass(frozen=True)
class BudgetReservation:
    """A stable logical reservation owned by one shared budget authority."""

    reservation_id: str
    money: float = 0.0
    tokens: int = 0
    wall_time_s: float = 0.0
    verifier_attempts: int = 0
    settled: bool = False

    def request_tuple(self) -> tuple[float, int, float, int]:
        return (self.money, self.tokens, self.wall_time_s, self.verifier_attempts)


class AcceptanceBudgetAuthority:
    """Serialize shared reservations and make settlement retries idempotent.

    AcceptanceBudget remains an immutable value object. This authority owns the
    mutable reservation ledger for one shared budget and is the only place where
    concurrent reserve/settle transitions are serialized.
    """

    def __init__(self, budget: AcceptanceBudget) -> None:
        self._budget = budget
        self._reservations: dict[str, BudgetReservation] = {}
        self._lock = threading.RLock()

    def snapshot(self) -> AcceptanceBudget:
        with self._lock:
            return self._budget

    def reservation(self, reservation_id: str) -> Optional[BudgetReservation]:
        with self._lock:
            return self._reservations.get(reservation_id)

    def _pending_totals(self) -> tuple[float, int, float, int]:
        pending = [reservation for reservation in self._reservations.values() if not reservation.settled]
        return (
            sum(reservation.money for reservation in pending),
            sum(reservation.tokens for reservation in pending),
            sum(reservation.wall_time_s for reservation in pending),
            sum(reservation.verifier_attempts for reservation in pending),
        )

    def reserve(
        self,
        reservation_id: str,
        *,
        money: float = 0.0,
        tokens: int = 0,
        wall_time_s: float = 0.0,
        verifier_attempts: int = 0,
    ) -> BudgetReservation:
        if not reservation_id:
            raise ValueError("reservation_id cannot be empty")
        if not _budget_values_are_finite(money, tokens, wall_time_s, verifier_attempts):
            raise ValueError("budget reservation must be finite")
        if min(money, tokens, wall_time_s, verifier_attempts) < 0:
            raise ValueError("budget reservation cannot be negative")

        requested = (money, tokens, wall_time_s, verifier_attempts)
        with self._lock:
            existing = self._reservations.get(reservation_id)
            if existing is not None:
                if existing.request_tuple() != requested:
                    raise ValueError("reservation replay conflicts with existing request")
                return existing

            pending_money, pending_tokens, pending_wall_time_s, pending_verifier_attempts = self._pending_totals()
            if self._budget.money_used + pending_money + money > self._budget.money_limit:
                raise BudgetExhausted("acceptance money budget exhausted")
            if self._budget.tokens_used + pending_tokens + tokens > self._budget.token_limit:
                raise BudgetExhausted("acceptance token budget exhausted")
            if self._budget.wall_time_used_s + pending_wall_time_s + wall_time_s > self._budget.wall_time_limit_s:
                raise BudgetExhausted("acceptance wall-time budget exhausted")
            if (
                self._budget.verifier_attempts_used
                + pending_verifier_attempts
                + verifier_attempts
                > self._budget.verifier_attempt_limit
            ):
                raise BudgetExhausted("acceptance verifier-attempt budget exhausted")

            reservation = BudgetReservation(
                reservation_id=reservation_id,
                money=money,
                tokens=tokens,
                wall_time_s=wall_time_s,
                verifier_attempts=verifier_attempts,
            )
            self._reservations[reservation_id] = reservation
            return reservation

    def settle(self, reservation_id: str) -> AcceptanceBudget:
        with self._lock:
            reservation = self._reservations.get(reservation_id)
            if reservation is None:
                raise KeyError(f"unknown reservation: {reservation_id}")
            if reservation.settled:
                return self._budget

            self._budget = self._budget.consume(
                money=reservation.money,
                tokens=reservation.tokens,
                wall_time_s=reservation.wall_time_s,
                verifier_attempts=reservation.verifier_attempts,
            )
            self._reservations[reservation_id] = replace(reservation, settled=True)
            return self._budget


@dataclass(frozen=True)
class ApprovalRequest:
    approval_id: str
    mission_id: str
    execution_id: str
    subject_state_id: str
    policy_bundle_id: str
    reason: str


@dataclass(frozen=True)
class ApprovalRecord:
    approval_id: str
    mission_id: str
    execution_id: str
    subject_state_id: str
    policy_bundle_id: str
    approver_id: str
    approved: bool


def require_human(
    *,
    approval_id: str,
    mission_id: str,
    execution_id: str,
    subject_state_id: str,
    policy_bundle_id: str,
    reason: str,
) -> ApprovalRequest:
    return ApprovalRequest(
        approval_id=approval_id,
        mission_id=mission_id,
        execution_id=execution_id,
        subject_state_id=subject_state_id,
        policy_bundle_id=policy_bundle_id,
        reason=reason,
    )


def resume_after_approval(request: ApprovalRequest, record: ApprovalRecord) -> AcceptanceDecision:
    bindings = (
        request.approval_id == record.approval_id,
        request.mission_id == record.mission_id,
        request.execution_id == record.execution_id,
        request.subject_state_id == record.subject_state_id,
        request.policy_bundle_id == record.policy_bundle_id,
    )
    if not all(bindings):
        return AcceptanceDecision.BLOCK
    return AcceptanceDecision.ACCEPT if record.approved else AcceptanceDecision.BLOCK


def apply_confidence_after_hard_gates(
    hard_gate_decision: AcceptanceDecision,
    *,
    confidence: float,
    threshold: float = 0.8,
) -> AcceptanceDecision:
    if hard_gate_decision != AcceptanceDecision.ACCEPT:
        return hard_gate_decision
    if not 0.0 <= confidence <= 1.0:
        raise ValueError("confidence must be in [0, 1]")
    if not 0.0 <= threshold <= 1.0:
        raise ValueError("threshold must be in [0, 1]")
    if confidence < threshold:
        return AcceptanceDecision.REQUIRE_HUMAN
    return AcceptanceDecision.ACCEPT


__all__ = [
    "PolicyEffect",
    "PolicyDecision",
    "evaluate_policy",
    "BudgetExhausted",
    "AcceptanceBudget",
    "BudgetReservation",
    "AcceptanceBudgetAuthority",
    "ApprovalRequest",
    "ApprovalRecord",
    "require_human",
    "resume_after_approval",
    "apply_confidence_after_hard_gates",
]
