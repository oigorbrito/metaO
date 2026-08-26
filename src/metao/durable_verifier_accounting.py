"""Durable A02/A18 verifier execution path with attempt-start evidence.

This is the strengthened entry point over :mod:`metao.verifier_accounting`.
A factual attempt-start event is appended before invoking the verifier. Exact
resource usage is still appended only when authoritative measurements exist.
No unknown money/tokens are ever synthesized.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum
from time import time
from typing import Callable

from .acceptance_accounting import AcceptanceAccountingDecision, record_verification_usage
from .acceptance_usage import AcceptanceUsagePort, VerificationOutcome, VerificationUsage
from .governance import AcceptanceBudget
from .verification_attempt import VerificationAttemptPort, VerificationAttemptStarted
from .verifier import VerificationRequest, VerificationStatus, VerifierRegistry, VerifierResult
from .verifier_accounting import VerificationResourceMeterPort


class DurableVerificationDecision(StrEnum):
    CONTINUE = "CONTINUE"
    BLOCK = "BLOCK"


@dataclass(frozen=True)
class DurableVerificationResult:
    decision: DurableVerificationDecision
    attempt_started: VerificationAttemptStarted | None
    verifier_result: VerifierResult | None
    usage: VerificationUsage | None
    budget: AcceptanceBudget
    reason: str = ""


VerificationClock = Callable[[], float]


def _outcome(result: VerifierResult | None, error: Exception | None, binding_error: str) -> VerificationOutcome:
    if binding_error:
        return VerificationOutcome.INVALID_RESULT
    if error is not None:
        return VerificationOutcome.ERROR
    assert result is not None
    if result.status is VerificationStatus.PASS:
        return VerificationOutcome.PASS
    if result.status is VerificationStatus.FAIL:
        return VerificationOutcome.FAIL
    return VerificationOutcome.ERROR


def execute_durable_accounted_verification(
    *,
    request: VerificationRequest,
    registry: VerifierRegistry,
    attempt_port: VerificationAttemptPort,
    usage_port: AcceptanceUsagePort,
    budget: AcceptanceBudget,
    resource_meter: VerificationResourceMeterPort,
    attempt_record_id: str,
    usage_id: str,
    attempt_id: str,
    required_capability: str | None = None,
    clock: VerificationClock | None = None,
) -> DurableVerificationResult:
    if not all((attempt_record_id, usage_id, attempt_id)):
        raise ValueError("attempt_record_id, usage_id and attempt_id are required")

    verifier = registry.select(required_capability=required_capability)
    if verifier is None:
        return DurableVerificationResult(
            DurableVerificationDecision.BLOCK, None, None, None, budget, "verifier_not_found"
        )

    tick = clock or time
    started_at = tick()
    started = VerificationAttemptStarted(
        attempt_record_id=attempt_record_id,
        mission_id=request.mission_id,
        execution_id=request.execution_id,
        verification_request_id=request.request_id,
        attempt_id=attempt_id,
        verifier_id=verifier.descriptor.verifier_id,
        verifier_version=verifier.descriptor.version,
        started_at_epoch=started_at,
    )
    # The attempt becomes factual before untrusted verifier code executes.
    attempt_port.append_started(started)

    result: VerifierResult | None = None
    error: Exception | None = None
    try:
        result = verifier.verify(request)
    except Exception as exc:
        error = exc
    ended_at = tick()

    binding_error = ""
    if result is not None:
        if result.request_id != request.request_id:
            binding_error = "verifier_result_request_mismatch"
        elif result.verifier_id != verifier.descriptor.verifier_id:
            binding_error = "verifier_result_identity_mismatch"
        elif result.verifier_version != verifier.descriptor.version:
            binding_error = "verifier_result_version_mismatch"

    try:
        facts = resource_meter.measure(
            request=request,
            verifier_id=verifier.descriptor.verifier_id,
            result=result,
            error=error,
        )
    except Exception:
        return DurableVerificationResult(
            DurableVerificationDecision.BLOCK,
            started,
            None,
            None,
            budget,
            "usage_measurement_unavailable",
        )

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
        started_at_epoch=started_at,
        ended_at_epoch=ended_at,
        money=facts.money,
        tokens=facts.tokens,
        wall_time_s=ended_at - started_at,
        verifier_attempts=1,
        outcome=_outcome(result, error, binding_error),
    )
    accounting = record_verification_usage(
        budget=budget,
        usage=usage,
        usage_port=usage_port,
    )

    if accounting.decision is AcceptanceAccountingDecision.BLOCK:
        return DurableVerificationResult(
            DurableVerificationDecision.BLOCK,
            started,
            result if not binding_error else None,
            usage,
            accounting.budget,
            "acceptance_budget_exhausted",
        )
    if binding_error:
        return DurableVerificationResult(
            DurableVerificationDecision.BLOCK,
            started,
            None,
            usage,
            accounting.budget,
            binding_error,
        )
    if error is not None:
        return DurableVerificationResult(
            DurableVerificationDecision.BLOCK,
            started,
            None,
            usage,
            accounting.budget,
            "verifier_execution_error",
        )
    assert result is not None
    return DurableVerificationResult(
        DurableVerificationDecision.CONTINUE,
        started,
        result,
        usage,
        accounting.budget,
    )


__all__ = [
    "DurableVerificationDecision",
    "DurableVerificationResult",
    "execute_durable_accounted_verification",
]
