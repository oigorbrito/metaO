"""Framework-neutral approver authority and freshness primitives.

Durable approval records remain transport/history. This module evaluates whether
the recorded approver is currently authorized for the bound approval action.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum


class ApprovalAuthorityDecision(StrEnum):
    ALLOW = "ALLOW"
    STALE = "STALE"
    BLOCK = "BLOCK"


@dataclass(frozen=True)
class ApprovalAuthorityContext:
    authority_context_id: str
    authority_epoch: int
    now_epoch: float

    def __post_init__(self) -> None:
        if not self.authority_context_id:
            raise ValueError("approval authority context requires id")
        if self.authority_epoch < 0 or self.now_epoch < 0:
            raise ValueError("approval authority context values must be non-negative")


@dataclass(frozen=True)
class ApproverCapability:
    capability_id: str
    approver_id: str
    action: str
    target: str
    scope: str
    authority_epoch: int
    not_before_epoch: float
    expires_epoch: float

    def __post_init__(self) -> None:
        if not all(
            (
                self.capability_id,
                self.approver_id,
                self.action,
                self.target,
                self.scope,
            )
        ):
            raise ValueError("approver capability requires all bindings")
        if self.authority_epoch < 0 or self.not_before_epoch < 0 or self.expires_epoch < 0:
            raise ValueError("approver capability time/epoch values must be non-negative")
        if self.expires_epoch < self.not_before_epoch:
            raise ValueError("approver capability expiry cannot precede activation")


@dataclass(frozen=True)
class ApprovalAuthorityRequest:
    approver_id: str
    action: str
    target: str
    scope: str

    def __post_init__(self) -> None:
        if not all((self.approver_id, self.action, self.target, self.scope)):
            raise ValueError("approval authority request requires all bindings")


@dataclass(frozen=True)
class ApprovalAuthorityResult:
    decision: ApprovalAuthorityDecision
    capability_id: str
    reasons: tuple[str, ...] = ()


def evaluate_approval_authority(
    *,
    context: ApprovalAuthorityContext,
    capability: ApproverCapability,
    request: ApprovalAuthorityRequest,
) -> ApprovalAuthorityResult:
    if capability.authority_epoch > context.authority_epoch:
        return ApprovalAuthorityResult(
            ApprovalAuthorityDecision.BLOCK,
            capability.capability_id,
            ("future_authority_epoch",),
        )
    if capability.authority_epoch < context.authority_epoch:
        return ApprovalAuthorityResult(
            ApprovalAuthorityDecision.STALE,
            capability.capability_id,
            ("authority_epoch_stale",),
        )
    if context.now_epoch < capability.not_before_epoch:
        return ApprovalAuthorityResult(
            ApprovalAuthorityDecision.BLOCK,
            capability.capability_id,
            ("capability_not_yet_valid",),
        )
    if context.now_epoch > capability.expires_epoch:
        return ApprovalAuthorityResult(
            ApprovalAuthorityDecision.STALE,
            capability.capability_id,
            ("capability_expired",),
        )
    if request.approver_id != capability.approver_id:
        return ApprovalAuthorityResult(
            ApprovalAuthorityDecision.BLOCK,
            capability.capability_id,
            ("approver_not_capability_holder",),
        )
    if request.action != capability.action:
        return ApprovalAuthorityResult(
            ApprovalAuthorityDecision.BLOCK,
            capability.capability_id,
            ("action_not_authorized",),
        )
    if request.target != capability.target:
        return ApprovalAuthorityResult(
            ApprovalAuthorityDecision.BLOCK,
            capability.capability_id,
            ("target_not_authorized",),
        )
    if request.scope != capability.scope:
        return ApprovalAuthorityResult(
            ApprovalAuthorityDecision.BLOCK,
            capability.capability_id,
            ("scope_not_authorized",),
        )
    return ApprovalAuthorityResult(
        ApprovalAuthorityDecision.ALLOW,
        capability.capability_id,
    )


__all__ = [
    "ApprovalAuthorityDecision",
    "ApprovalAuthorityContext",
    "ApproverCapability",
    "ApprovalAuthorityRequest",
    "ApprovalAuthorityResult",
    "evaluate_approval_authority",
]
