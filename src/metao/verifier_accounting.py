"""A02/A18 bridge: execute an independent verifier and account factual usage.

This module deliberately stops before EvidenceEnvelope normalization and final
acceptance. A verifier result is evidence input only, never `METAO_ACCEPTED`.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum
from math import isfinite
from time import time
from typing import Callable, Protocol, runtime_checkable

from .acceptance_accounting import (
    AcceptanceAccountingDecision,
    AcceptanceAccountingResult,
    record_verification_usage,
)
from .acceptance_usage import (
    AcceptanceUsagePort,
    VerificationOutcome,
    VerificationUsage,
)
from .governance import AcceptanceBudget
from .verifier import (
    VerificationRequest,
    VerificationStatus,
    VerifierRegistry,
    VerifierResult,
)


class AccountedVerificationDecision(StrEnum):
    CONTINUE = "CONTINUE"
    BLOCK = "BLOCK"


@dataclass(frozen=True)
class VerificationResourceFacts:
    money: float
    tokens: int

    def __post_init__(self) -> None:
        if isinstance(self.money, bool) or not isinstance(self.money, (int, float)):
            raise ValueError("verification money usage must be numeric and non-boolean")
        if not isfinite(float(self.money)) or self.money < 0:
            raise ValueError("verification money usage must be finite and non-negative")
        if isinstance(self.tokens, bool) or not isinstance(self.tokens, int) or self.tokens < 0:
            raise ValueError("verification token usage must be a non-negative integer")


@runtime_checkable
class VerificationResourceMeterPort(Protocol):
    def measure(
        self,
        *,
        request: VerificationRequest,
        verifier_id: str,
        result: VerifierResult | None,
        error: BaseException | None,
    ) -> VerificationResourceFacts: ...


@dataclass(frozen=True)
class AccountedVerificationResult:
    decision: AccountedVerificationDecision
    verifier_result: VerifierResult | None
    accounting: AcceptanceAccountingResult | None
    budget: AcceptanceBudget
    reason: str = ""


VerificationClock = Callable[[], float]


def _outcome_for_result(result: VerifierResult | None, error: BaseException | None) -> VerificationOutcome:
    if error is not None:
        return VerificationOutcome.ERROR
    assert result is not None
    if result.status is VerificationStatus.PASS:
        return VerificationOutcome.PASS
    if result.status is VerificationStatus.FAIL:
        return VerificationOutcome.FAIL
    return VerificationOutcome.ERROR


def execute_accounted_verification(
    *,
    request: VerificationRequest,
    registry: VerifierRegistry,
    usage_port: AcceptanceUsagePort,
    budget: AcceptanceBudget,
    resource_meter: VerificationResourceMeterPort,
    usage_id: str,
    attempt_id: str,
    required_capability: str | None = None,
    clock: VerificationClock | None = None,
) -> AccountedVerificationResult:
    """Execute one metaO-selected verifier attempt and record factual usage.

    Missing verifier blocks before an attempt begins. Once verification begins,
    success, failure, or raised verifier error is accounted. Result identity is
    checked before it can proceed toward later evidence normalization.
    """

    if not usage_id or not attempt_id:
        raise ValueError("usage_id and attempt_id are required")

    verifier = registry.select(required_capability=required_capability)
    if verifier is None:
        return AccountedVerificationResult(
            AccountedVerificationDecision.BLOCK,
            None,
            None,
            budget,
            "verifier_not_found",
        )

    tick = clock or time
    started = tick()
    result: VerifierResult | None = None
    error: BaseException | None = None
    try:
        result = verifier.verify(request)
    except BaseException as exc:  # verifier boundary must fail closed
        error = exc
    ended = tick()

    try:
        facts = resource_meter.measure(
            request=request,
            verifier_id=verifier.descriptor.verifier_id,
            result=result,
            error=error,
        )
    except BaseException:
        return AccountedVerificationResult(
            AccountedVerificationDecision.BLOCK,
            None,
            None,
            budget,
            "usage_measurement_unavailable",
        )

    binding_error = ""
    if result is not None:
        if result.request_id != request.request_id:
            binding_error = "verifier_result_request_mismatch"
        elif result.verifier_id != verifier.descriptor.verifier_id:
            binding_error = "verifier_result_identity_mismatch"
        elif result.verifier_version != verifier.descriptor.version:
            binding_error = "verifier_result_version_mismatch"

    outcome = VerificationOutcome.INVALID_RESULT if binding_error else _outcome_for_result(result, error)
    usage = VerificationUsage(
        usage_id=usage_id,
        mission_id=request.mission_id,
        execution_id=request.execution_id,
        attempt_id=attempt_id,
        verifier_id=verifier.descriptor.verifier_id,
        verification_request_id=request.request_id,
        subject_id=request.subject_id,
        subject_state_id=request.subject_state_id,
        verification_context_id=request.verification_context_id,
        policy_bundle_id=request.policy_bundle_id,
        started_at_epoch=started,
        ended_at_epoch=ended,
        money=facts.money,
        tokens=facts.tokens,
        wall_time_s=ended - started,
        verifier_attempts=1,
        outcome=outcome,
    )
    accounting = record_verification_usage(
        budget=budget,
        usage=usage,
        usage_port=usage_port,
    )

    if accounting.decision is AcceptanceAccountingDecision.BLOCK:
        return AccountedVerificationResult(
            AccountedVerificationDecision.BLOCK,
            result if not binding_error else None,
            accounting,
            accounting.budget,
            "acceptance_budget_exhausted",
        )
    if binding_error:
        return AccountedVerificationResult(
            AccountedVerificationDecision.BLOCK,
            None,
            accounting,
            accounting.budget,
            binding_error,
        )
    if error is not None:
        return AccountedVerificationResult(
            AccountedVerificationDecision.BLOCK,
            None,
            accounting,
            accounting.budget,
            "verifier_execution_error",
        )
    assert result is not None
    return AccountedVerificationResult(
        AccountedVerificationDecision.CONTINUE,
        result,
        accounting,
        accounting.budget,
    )


__all__ = [
    "AccountedVerificationDecision",
    "VerificationResourceFacts",
    "VerificationResourceMeterPort",
    "AccountedVerificationResult",
    "execute_accounted_verification",
]
