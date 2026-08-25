"""Canonical framework-neutral evidence contract for metaO.

This module owns the single EvidenceEnvelope type shared by Core, runtime
normalizers and final acceptance. It intentionally imports no orchestrator SDK
and contains no acceptance authority of its own.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Optional


@dataclass(frozen=True)
class EvidenceEnvelope:
    """Evidence normalized at the metaO/orchestrator boundary.

    The operational field set follows the envelope already exercised by the
    multi-orchestrator acceptance path. Compatibility properties expose the
    unambiguous read aliases from the earlier Core-only envelope so callers do
    not need two independent evidence models.
    """

    evidence_id: str
    obligation_id: str
    mission_id: str
    execution_id: str
    orchestrator_id: str
    adapter_version: str
    attempt_id: str
    subject_id: str
    subject_state_id: str
    verification_context_id: str
    policy_bundle_id: str
    verifier_id: str
    payload_digest: str
    provenance_root: str
    authority_id: str
    passed: bool
    created_at_epoch: float = 0.0
    expires_at_epoch: Optional[float] = None
    approval_id: Optional[str] = None
    confidence: Optional[float] = None
    adapter_id: str = ""
    verification_cost_units: int = 0

    def __post_init__(self) -> None:
        # Older normalizers predate the explicit adapter_id field. Using the
        # orchestrator identity is a deterministic, framework-neutral fallback;
        # dedicated adapters may provide a distinct adapter_id later without a
        # Core schema change.
        if not self.adapter_id:
            object.__setattr__(self, "adapter_id", self.orchestrator_id)
        if self.verification_cost_units < 0:
            raise ValueError("verification_cost_units must be non-negative")

    @property
    def obligation_ids(self) -> frozenset[str]:
        """Compatibility read alias for the former Core envelope."""

        return frozenset({self.obligation_id})

    @property
    def evidence_payload_digest(self) -> str:
        """Compatibility read alias for the former Core envelope."""

        return self.payload_digest

    @property
    def provenance(self) -> str:
        """Compatibility read alias for the former Core envelope."""

        return self.provenance_root

    @property
    def approval_evidence(self) -> str:
        """Compatibility read alias for the former Core envelope."""

        return self.approval_id or ""


__all__ = ["EvidenceEnvelope"]
