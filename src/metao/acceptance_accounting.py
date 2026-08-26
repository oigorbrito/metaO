"""A18 composition between factual verification usage and AcceptanceBudget.

The accounting order is intentionally fail closed:

    append factual usage -> apply usage -> block if actual usage exceeds limits

A verifier attempt remains a fact even when that attempt pushes the mission over
budget. This module therefore never rolls back or hides an appended usage record.
It does not make a final acceptance decision.
"""

from __future__ import annotations

from dataclasses import dataclass, replace
from enum import StrEnum

from .acceptance_usage import AcceptanceUsagePort, VerificationUsage
from .governance import AcceptanceBudget, BudgetExhausted


class AcceptanceAccountingDecision(StrEnum):
    CONTINUE = "CONTINUE"
    BLOCK = "BLOCK"


@dataclass(frozen=True)
class AcceptanceAccountingResult:
    decision: AcceptanceAccountingDecision
    usage: VerificationUsage
    budget: AcceptanceBudget
    reason: str = ""


def _observed_budget_after_usage(
    budget: AcceptanceBudget,
    usage: VerificationUsage,
) -> AcceptanceBudget:
    """Represent factual totals even when they exceed configured limits."""

    return replace(
        budget,
        money_used=budget.money_used + usage.money,
        tokens_used=budget.tokens_used + usage.tokens,
        wall_time_used_s=budget.wall_time_used_s + usage.wall_time_s,
        verifier_attempts_used=budget.verifier_attempts_used + usage.verifier_attempts,
    )


def record_verification_usage(
    *,
    budget: AcceptanceBudget,
    usage: VerificationUsage,
    usage_port: AcceptanceUsagePort,
) -> AcceptanceAccountingResult:
    """Persist one factual attempt before applying it to the acceptance budget.

    `AcceptanceBudget.consume` raises on overage, so the over-budget branch also
    returns an observed budget containing the real factual totals. That prevents
    later code from mistaking the pre-attempt budget for authoritative state.
    """

    usage_port.append(usage)
    try:
        updated = budget.consume(
            money=usage.money,
            tokens=usage.tokens,
            wall_time_s=usage.wall_time_s,
            verifier_attempts=usage.verifier_attempts,
        )
    except BudgetExhausted as exc:
        return AcceptanceAccountingResult(
            AcceptanceAccountingDecision.BLOCK,
            usage,
            _observed_budget_after_usage(budget, usage),
            str(exc),
        )

    return AcceptanceAccountingResult(
        AcceptanceAccountingDecision.CONTINUE,
        usage,
        updated,
    )


__all__ = [
    "AcceptanceAccountingDecision",
    "AcceptanceAccountingResult",
    "record_verification_usage",
]
