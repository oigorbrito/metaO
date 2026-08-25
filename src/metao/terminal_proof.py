"""Framework-neutral deterministic terminal decision proof primitives.

These structures bind authoritative observations into a reconstructible proof
record. The digest is deterministic integrity material only; it is not a
cryptographic authenticity or authorization mechanism.
"""

from __future__ import annotations

from dataclasses import dataclass
from hashlib import sha256
import json
from typing import Iterable


class TerminalProofError(ValueError):
    pass


@dataclass(frozen=True)
class TerminalObservation:
    domain: str
    source_id: str
    observation_id: str
    value_digest: str

    def __post_init__(self) -> None:
        if not all((self.domain, self.source_id, self.observation_id, self.value_digest)):
            raise TerminalProofError("terminal observation requires all bindings")


@dataclass(frozen=True)
class TerminalValidationProfile:
    profile_id: str
    version: str
    required_domains: frozenset[str]

    def __post_init__(self) -> None:
        if not self.profile_id or not self.version or not self.required_domains:
            raise TerminalProofError("terminal validation profile is incomplete")
        if not all(self.required_domains):
            raise TerminalProofError("terminal validation profile has empty domain")


@dataclass(frozen=True)
class TerminalDecisionProof:
    mission_id: str
    execution_id: str
    decision: str
    profile_id: str
    profile_version: str
    observation_ids: tuple[str, ...]
    observation_digests: tuple[str, ...]
    proof_digest: str


class TerminalProofBuilder:
    def build(
        self,
        *,
        mission_id: str,
        execution_id: str,
        decision: str,
        profile: TerminalValidationProfile,
        observations: Iterable[TerminalObservation],
    ) -> TerminalDecisionProof:
        if not mission_id or not execution_id or not decision:
            raise TerminalProofError("terminal proof requires mission/execution/decision")

        items = tuple(observations)
        if not items:
            raise TerminalProofError("terminal proof requires observations")

        domains = [item.domain for item in items]
        if len(domains) != len(set(domains)):
            raise TerminalProofError("terminal proof has duplicate observation domain")

        missing = profile.required_domains.difference(domains)
        unexpected = set(domains).difference(profile.required_domains)
        if missing:
            raise TerminalProofError(
                "terminal proof missing required domains: " + ",".join(sorted(missing))
            )
        if unexpected:
            raise TerminalProofError(
                "terminal proof has unexpected domains: " + ",".join(sorted(unexpected))
            )

        ordered = tuple(sorted(items, key=lambda item: item.domain))
        ids = [item.observation_id for item in ordered]
        if len(ids) != len(set(ids)):
            raise TerminalProofError("terminal proof has duplicate observation id")

        material = {
            "mission_id": mission_id,
            "execution_id": execution_id,
            "decision": decision,
            "profile_id": profile.profile_id,
            "profile_version": profile.version,
            "observations": [
                {
                    "domain": item.domain,
                    "source_id": item.source_id,
                    "observation_id": item.observation_id,
                    "value_digest": item.value_digest,
                }
                for item in ordered
            ],
        }
        canonical = json.dumps(material, sort_keys=True, separators=(",", ":"))
        digest = sha256(canonical.encode("utf-8")).hexdigest()

        return TerminalDecisionProof(
            mission_id=mission_id,
            execution_id=execution_id,
            decision=decision,
            profile_id=profile.profile_id,
            profile_version=profile.version,
            observation_ids=tuple(item.observation_id for item in ordered),
            observation_digests=tuple(item.value_digest for item in ordered),
            proof_digest=digest,
        )


__all__ = [
    "TerminalProofError",
    "TerminalObservation",
    "TerminalValidationProfile",
    "TerminalDecisionProof",
    "TerminalProofBuilder",
]
