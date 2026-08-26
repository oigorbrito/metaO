"""Framework-neutral authoritative freshness boundary for Roadmap 8 A04.

Caller timestamps are evidence claims. Terminal acceptance may consult this
boundary to compare those claims with a trusted time source and explicit
freshness policy without granting the time source final acceptance authority.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum
from math import isfinite
from typing import Protocol, runtime_checkable


class FreshnessDecision(StrEnum):
    FRESH = "FRESH"
    STALE = "STALE"
    BLOCK = "BLOCK"


@dataclass(frozen=True)
class FreshnessPolicy:
    max_age_s: float | None = None
    allowed_clock_skew_s: float = 0.0

    def __post_init__(self) -> None:
        for name, value in (("allowed_clock_skew_s", self.allowed_clock_skew_s), ("max_age_s", self.max_age_s)):
            if value is None:
                continue
            if isinstance(value, bool) or not isinstance(value, (int, float)):
                raise TypeError(f"{name} must be numeric")
            if not isfinite(float(value)) or value < 0:
                raise ValueError(f"{name} must be finite and non-negative")


@dataclass(frozen=True)
class FreshnessRequest:
    evidence_id: str
    subject_id: str
    subject_state_id: str
    verification_context_id: str
    created_at_epoch: float
    expires_at_epoch: float | None

    def __post_init__(self) -> None:
        if not all((self.evidence_id, self.subject_id, self.subject_state_id, self.verification_context_id)):
            raise ValueError("freshness request requires all identity bindings")
        for name, value in (("created_at_epoch", self.created_at_epoch), ("expires_at_epoch", self.expires_at_epoch)):
            if value is None:
                continue
            if isinstance(value, bool) or not isinstance(value, (int, float)):
                raise TypeError(f"{name} must be numeric")
            if not isfinite(float(value)) or value < 0:
                raise ValueError(f"{name} must be finite and non-negative")
        if self.expires_at_epoch is not None and self.expires_at_epoch < self.created_at_epoch:
            raise ValueError("expires_at_epoch cannot precede created_at_epoch")


@dataclass(frozen=True)
class FreshnessResult:
    decision: FreshnessDecision
    observed_now_epoch: float
    reason: str = ""

    def __post_init__(self) -> None:
        if isinstance(self.observed_now_epoch, bool) or not isinstance(self.observed_now_epoch, (int, float)):
            raise TypeError("observed_now_epoch must be numeric")
        if not isfinite(float(self.observed_now_epoch)) or self.observed_now_epoch < 0:
            raise ValueError("observed_now_epoch must be finite and non-negative")


@runtime_checkable
class TrustedClockPort(Protocol):
    def now_epoch(self) -> float: ...


class FixedClock:
    def __init__(self, now_epoch: float) -> None:
        self._now = FreshnessResult(FreshnessDecision.FRESH, now_epoch).observed_now_epoch

    def now_epoch(self) -> float:
        return self._now


def evaluate_authoritative_freshness(request: FreshnessRequest, *, clock: TrustedClockPort, policy: FreshnessPolicy = FreshnessPolicy()) -> FreshnessResult:
    now = FreshnessResult(FreshnessDecision.FRESH, clock.now_epoch()).observed_now_epoch
    if request.created_at_epoch > now + policy.allowed_clock_skew_s:
        return FreshnessResult(FreshnessDecision.BLOCK, now, "evidence_from_future")
    if request.expires_at_epoch is not None and now - policy.allowed_clock_skew_s > request.expires_at_epoch:
        return FreshnessResult(FreshnessDecision.STALE, now, "evidence_expired")
    if policy.max_age_s is not None and now - request.created_at_epoch > policy.max_age_s + policy.allowed_clock_skew_s:
        return FreshnessResult(FreshnessDecision.STALE, now, "evidence_too_old")
    return FreshnessResult(FreshnessDecision.FRESH, now)


__all__ = ["FreshnessDecision", "FreshnessPolicy", "FreshnessRequest", "FreshnessResult", "TrustedClockPort", "FixedClock", "evaluate_authoritative_freshness"]
