"""Deterministic local runtime used only by the repository quickstart.

This module provides a zero-network, zero-credential runtime plugin so a clean
clone can exercise the real declarative catalog, certification, admission,
mission execution, acceptance, persistence, and inspection path.

It is demonstration evidence, not an external-provider or production-runtime
claim.
"""

from __future__ import annotations

from hashlib import sha256
import json
from typing import Any

from .acceptance import EvidenceEnvelope
from .core import (
    ExecutionRequest,
    ExecutionResult,
    ExecutionStatus,
    HealthReport,
    HealthStatus,
    OrchestratorDescriptor,
)
from .runtime_factory import RuntimePlugin


ORCHESTRATOR_ID = "quickstart-local"
RUNTIME_VERSION = "1"


def _digest(value: Any) -> str:
    encoded = json.dumps(
        value,
        sort_keys=True,
        default=str,
        separators=(",", ":"),
    ).encode()
    return sha256(encoded).hexdigest()


class QuickstartLocalOrchestrator:
    """Deterministic local runtime for first-run operability checks."""

    def __init__(self) -> None:
        self._cancelled: set[str] = set()
        self._descriptor = OrchestratorDescriptor(
            orchestrator_id=ORCHESTRATOR_ID,
            version=RUNTIME_VERSION,
            capabilities=frozenset({"workflow"}),
            metadata={"adapter": "quickstart-local", "scope": "example-only"},
        )

    @property
    def descriptor(self) -> OrchestratorDescriptor:
        return self._descriptor

    def health(self) -> HealthReport:
        return HealthReport(HealthStatus.HEALTHY, "deterministic quickstart runtime ready")

    def execute(self, request: ExecutionRequest) -> ExecutionResult:
        if request.execution_id in self._cancelled:
            return ExecutionResult(
                request.execution_id,
                ORCHESTRATOR_ID,
                ExecutionStatus.CANCELLED,
            )
        return ExecutionResult(
            request.execution_id,
            ORCHESTRATOR_ID,
            ExecutionStatus.SUCCEEDED,
            output={"result": f"quickstart:{request.mission.objective}"},
        )

    def cancel(self, execution_id: str) -> None:
        self._cancelled.add(execution_id)


def normalize_evidence(
    *,
    request: ExecutionRequest,
    orchestrator_id: str,
    adapter_version: str,
    output: Any,
    attempt_id: str = "attempt-1",
) -> EvidenceEnvelope:
    context = request.context
    return EvidenceEnvelope(
        evidence_id=f"{request.execution_id}:result",
        obligation_id=str(context.get("obligation_id", "execution_result")),
        mission_id=request.mission.mission_id,
        execution_id=request.execution_id,
        orchestrator_id=orchestrator_id,
        adapter_version=adapter_version,
        attempt_id=attempt_id,
        subject_id=str(context.get("subject_id", request.mission.mission_id)),
        subject_state_id=str(context.get("subject_state_id", "state-1")),
        verification_context_id=str(
            context.get("verification_context_id", "quickstart-verification")
        ),
        policy_bundle_id=str(context.get("policy_bundle_id", "quickstart-policy")),
        verifier_id=str(context.get("verifier_id", "adapter-observer")),
        payload_digest=_digest(output),
        provenance_root=f"quickstart-local:{request.execution_id}",
        authority_id=str(context.get("authority_id", "metao-runtime")),
        passed=True,
        created_at_epoch=float(context.get("created_at_epoch", 0.0)),
        expires_at_epoch=context.get("expires_at_epoch"),
    )


def create_plugin() -> RuntimePlugin:
    """Return the repository-owned local quickstart runtime plugin."""

    return RuntimePlugin(QuickstartLocalOrchestrator(), normalize_evidence)


__all__ = [
    "ORCHESTRATOR_ID",
    "RUNTIME_VERSION",
    "QuickstartLocalOrchestrator",
    "normalize_evidence",
    "create_plugin",
]
