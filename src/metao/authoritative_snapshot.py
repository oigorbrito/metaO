"""Coordinator for A05/A07/A09 authoritative terminal observations.

This module does not issue metaO acceptance. It resolves one exact, coherent
snapshot from authoritative subject-state, authority and policy sources. The
snapshot is consumed by the Roadmap 8 terminal-precondition coordinator before
any final acceptance decision.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum

from .authoritative_sources import (
    AuthorityRegistryPort,
    AuthorityResolution,
    AuthorityResolutionRequest,
    PolicyBundle,
    PolicyRegistryPort,
    SubjectState,
    SubjectStatePort,
)


class AuthoritativeSnapshotDecision(StrEnum):
    READY = "READY"
    STALE = "STALE"
    BLOCK = "BLOCK"


@dataclass(frozen=True)
class AuthoritativeTerminalSnapshot:
    decision: AuthoritativeSnapshotDecision
    request: AuthorityResolutionRequest
    subject_state: SubjectState
    authority: AuthorityResolution
    policy_bundle: PolicyBundle
    reason: str = ""


def resolve_authoritative_terminal_snapshot(
    *,
    authority_context_id: str,
    request: AuthorityResolutionRequest,
    subject_state_port: SubjectStatePort,
    authority_registry: AuthorityRegistryPort,
    policy_registry: PolicyRegistryPort,
) -> AuthoritativeTerminalSnapshot:
    """Resolve exact authoritative inputs and fail closed on divergence."""

    current_state = subject_state_port.current(request.subject_id)
    authority = authority_registry.resolve(authority_context_id, request)
    policy = policy_registry.get(request.policy_bundle_id)

    if current_state.subject_state_id != request.subject_state_id:
        return AuthoritativeTerminalSnapshot(
            AuthoritativeSnapshotDecision.STALE,
            request,
            current_state,
            authority,
            policy,
            "authoritative_subject_state_changed",
        )
    if authority.request != request or authority.authority_context_id != authority_context_id:
        return AuthoritativeTerminalSnapshot(
            AuthoritativeSnapshotDecision.BLOCK,
            request,
            current_state,
            authority,
            policy,
            "authority_resolution_binding_mismatch",
        )
    if not authority.authorized:
        return AuthoritativeTerminalSnapshot(
            AuthoritativeSnapshotDecision.BLOCK,
            request,
            current_state,
            authority,
            policy,
            authority.reason or "authority_denied",
        )
    if policy.policy_bundle_id != request.policy_bundle_id:
        return AuthoritativeTerminalSnapshot(
            AuthoritativeSnapshotDecision.BLOCK,
            request,
            current_state,
            authority,
            policy,
            "policy_bundle_identity_mismatch",
        )

    return AuthoritativeTerminalSnapshot(
        AuthoritativeSnapshotDecision.READY,
        request,
        current_state,
        authority,
        policy,
    )


__all__ = [
    "AuthoritativeSnapshotDecision",
    "AuthoritativeTerminalSnapshot",
    "resolve_authoritative_terminal_snapshot",
]
