"""Thin LangGraph adapter for metaO.

The adapter intentionally depends only on LangGraph's public runtime shape
(`invoke`) via duck typing, keeping LangGraph SDK types outside metaO Core.
"""

from __future__ import annotations

from hashlib import sha256
import json
from typing import Any

from metao.acceptance import EvidenceEnvelope
from metao.core import (
    ExecutionRequest,
    ExecutionResult,
    ExecutionStatus,
    HealthReport,
    HealthStatus,
    OrchestratorDescriptor,
)


def _digest(value: Any) -> str:
    return sha256(json.dumps(value, sort_keys=True, default=str, separators=(",", ":")).encode()).hexdigest()


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
        verification_context_id=str(context.get("verification_context_id", "default-verification")),
        policy_bundle_id=str(context.get("policy_bundle_id", "default-policy")),
        verifier_id=str(context.get("verifier_id", "adapter-observer")),
        payload_digest=_digest(output),
        provenance_root=f"langgraph:{orchestrator_id}:{request.execution_id}",
        authority_id=str(context.get("authority_id", "metao-runtime")),
        passed=True,
        created_at_epoch=float(context.get("created_at_epoch", 0.0)),
        expires_at_epoch=context.get("expires_at_epoch"),
    )


class LangGraphOrchestratorAdapter:
    """Adapts a compiled LangGraph-like object exposing ``invoke``."""

    def __init__(self, graph: Any, *, orchestrator_id: str = "langgraph", version: str = "1") -> None:
        self._graph = graph
        self._cancelled: set[str] = set()
        self._descriptor = OrchestratorDescriptor(
            orchestrator_id=orchestrator_id,
            version=version,
            capabilities=frozenset({"workflow", "agent"}),
            metadata={"adapter": "langgraph"},
        )

    @property
    def descriptor(self) -> OrchestratorDescriptor:
        return self._descriptor

    def health(self) -> HealthReport:
        return HealthReport(
            HealthStatus.HEALTHY if callable(getattr(self._graph, "invoke", None)) else HealthStatus.UNHEALTHY,
            "invoke available" if callable(getattr(self._graph, "invoke", None)) else "invoke unavailable",
        )

    def execute(self, request: ExecutionRequest) -> ExecutionResult:
        if request.execution_id in self._cancelled:
            return ExecutionResult(request.execution_id, self.descriptor.orchestrator_id, ExecutionStatus.CANCELLED)
        try:
            raw = self._graph.invoke({"objective": request.mission.objective, **dict(request.context)})
            output = raw if isinstance(raw, dict) else {"result": raw}
            return ExecutionResult(
                request.execution_id,
                self.descriptor.orchestrator_id,
                ExecutionStatus.SUCCEEDED,
                output=output,
            )
        except Exception as exc:
            return ExecutionResult(
                request.execution_id,
                self.descriptor.orchestrator_id,
                ExecutionStatus.FAILED,
                error=str(exc),
            )

    def cancel(self, execution_id: str) -> None:
        self._cancelled.add(execution_id)


__all__ = ["LangGraphOrchestratorAdapter", "normalize_evidence"]
