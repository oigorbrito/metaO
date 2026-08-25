"""Framework-neutral authoritative terminal source boundaries.

Caller-provided acceptance context is a candidate claim. These ports represent
sources that terminal acceptance may consult for current state, authority and
policy truth before issuing a metaO decision.
"""

from __future__ import annotations

from dataclasses import dataclass
from types import MappingProxyType
from typing import Mapping, Protocol, runtime_checkable


@dataclass(frozen=True)
class SubjectState:
    subject_id: str
    subject_state_id: str

    def __post_init__(self) -> None:
        if not self.subject_id or not self.subject_state_id:
            raise ValueError("subject state requires subject_id and subject_state_id")


@dataclass(frozen=True)
class AuthorityResolutionRequest:
    mission_id: str
    execution_id: str
    subject_id: str
    subject_state_id: str
    verification_context_id: str
    policy_bundle_id: str
    verifier_id: str

    def __post_init__(self) -> None:
        if not all(
            (
                self.mission_id,
                self.execution_id,
                self.subject_id,
                self.subject_state_id,
                self.verification_context_id,
                self.policy_bundle_id,
                self.verifier_id,
            )
        ):
            raise ValueError("authority resolution requires all identity bindings")


@dataclass(frozen=True)
class AuthorityResolution:
    authority_context_id: str
    authority_id: str
    authorized: bool
    reason: str = ""

    def __post_init__(self) -> None:
        if not self.authority_context_id or not self.authority_id:
            raise ValueError("authority resolution requires context and authority ids")


@dataclass(frozen=True)
class PolicyBundle:
    policy_bundle_id: str
    version: str
    rules: Mapping[str, object]

    def __post_init__(self) -> None:
        if not self.policy_bundle_id or not self.version:
            raise ValueError("policy bundle requires id and version")
        object.__setattr__(self, "rules", MappingProxyType(dict(self.rules)))


@runtime_checkable
class SubjectStatePort(Protocol):
    def current(self, subject_id: str) -> SubjectState: ...


@runtime_checkable
class AuthorityRegistryPort(Protocol):
    def resolve(
        self,
        authority_context_id: str,
        request: AuthorityResolutionRequest,
    ) -> AuthorityResolution: ...


@runtime_checkable
class PolicyRegistryPort(Protocol):
    def get(self, policy_bundle_id: str) -> PolicyBundle: ...


class AuthoritativeSourceNotFound(KeyError):
    pass


class InMemorySubjectStateStore:
    def __init__(self, states: Mapping[str, SubjectState] | None = None) -> None:
        self._states = dict(states or {})

    def put(self, state: SubjectState) -> None:
        self._states[state.subject_id] = state

    def current(self, subject_id: str) -> SubjectState:
        try:
            return self._states[subject_id]
        except KeyError as exc:
            raise AuthoritativeSourceNotFound(subject_id) from exc


class InMemoryAuthorityRegistry:
    def __init__(self) -> None:
        self._entries: dict[tuple[str, str], AuthorityResolution] = {}

    def put(self, *, authority_context_id: str, verifier_id: str, authority_id: str, authorized: bool, reason: str = "") -> None:
        resolution = AuthorityResolution(authority_context_id, authority_id, authorized, reason)
        self._entries[(authority_context_id, verifier_id)] = resolution

    def resolve(self, authority_context_id: str, request: AuthorityResolutionRequest) -> AuthorityResolution:
        try:
            return self._entries[(authority_context_id, request.verifier_id)]
        except KeyError as exc:
            raise AuthoritativeSourceNotFound(f"{authority_context_id}:{request.verifier_id}") from exc


class InMemoryPolicyRegistry:
    def __init__(self, bundles: Mapping[str, PolicyBundle] | None = None) -> None:
        self._bundles = dict(bundles or {})

    def put(self, bundle: PolicyBundle) -> None:
        self._bundles[bundle.policy_bundle_id] = bundle

    def get(self, policy_bundle_id: str) -> PolicyBundle:
        try:
            return self._bundles[policy_bundle_id]
        except KeyError as exc:
            raise AuthoritativeSourceNotFound(policy_bundle_id) from exc


__all__ = [
    "SubjectState",
    "AuthorityResolutionRequest",
    "AuthorityResolution",
    "PolicyBundle",
    "SubjectStatePort",
    "AuthorityRegistryPort",
    "PolicyRegistryPort",
    "AuthoritativeSourceNotFound",
    "InMemorySubjectStateStore",
    "InMemoryAuthorityRegistry",
    "InMemoryPolicyRegistry",
]
