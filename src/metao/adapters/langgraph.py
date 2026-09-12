"""Thin LangGraph adapter for metaO.

The adapter intentionally depends only on LangGraph's public runtime shape
(`invoke`) via duck typing, keeping LangGraph SDK types outside metaO Core.
"""

from __future__ import annotations

from collections import deque
from hashlib import sha256
import json
from threading import RLock
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
from metao.runtime_health import (
    RuntimeHealthFacts,
    RuntimeHealthPolicy,
    RuntimeHealthStorePort,
    RuntimeHealthTracker,
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

    def __init__(
        self,
        graph: Any,
        *,
        orchestrator_id: str = "langgraph",
        version: str = "1",
        config_id: str = "default",
        health_policy: RuntimeHealthPolicy | None = None,
        health_store: RuntimeHealthStorePort | None = None,
    ) -> None:
        self._graph = graph
        self._cancelled: set[str] = set()
        self._health_persistence_error: Exception | None = None
        self._pending_health_facts: deque[tuple[ExecutionStatus, str]] = deque()
        self._health_lock = RLock()
        self._descriptor = OrchestratorDescriptor(
            orchestrator_id=orchestrator_id,
            version=version,
            capabilities=frozenset({"workflow", "agent"}),
            metadata={"adapter": "langgraph"},
        )
        self._runtime_health = RuntimeHealthTracker(
            runtime_id=orchestrator_id,
            runtime_version=version,
            config_id=config_id,
            policy=health_policy,
            store=health_store,
        )

    @property
    def descriptor(self) -> OrchestratorDescriptor:
        return self._descriptor

    def health(self) -> HealthReport:
        if not callable(getattr(self._graph, "invoke", None)):
            return HealthReport(HealthStatus.UNHEALTHY, "invoke unavailable")
        with self._health_lock:
            try:
                self._flush_pending_health_facts()
                return self._runtime_health.report()
            except Exception as exc:
                self._health_persistence_error = exc
                return HealthReport(
                    HealthStatus.UNHEALTHY,
                    f"runtime health evidence unavailable: {type(exc).__name__}",
                )

    def runtime_health_facts(self) -> RuntimeHealthFacts:
        with self._health_lock:
            try:
                self._flush_pending_health_facts()
            except Exception as exc:
                self._health_persistence_error = exc
            return self._runtime_health.facts()

    def configure_runtime_health_store(self, store: RuntimeHealthStorePort) -> None:
        with self._health_lock:
            self._runtime_health.configure_store(store)
            self._health_persistence_error = None

    def _flush_pending_health_facts(self) -> None:
        while self._pending_health_facts:
            status, execution_id = self._pending_health_facts[0]
            self._runtime_health.record_execution(status, execution_id=execution_id)
            self._pending_health_facts.popleft()
        self._health_persistence_error = None

    def _record_runtime_health(self, status: ExecutionStatus, *, execution_id: str) -> None:
        if status is ExecutionStatus.CANCELLED:
            return
        with self._health_lock:
            self._pending_health_facts.append((status, execution_id))
            try:
                self._flush_pending_health_facts()
            except Exception as exc:
                self._health_persistence_error = exc

    def execute(self, request: ExecutionRequest) -> ExecutionResult:
        if request.execution_id in self._cancelled:
            return ExecutionResult(request.execution_id, self.descriptor.orchestrator_id, ExecutionStatus.CANCELLED)
        try:
            raw = self._graph.invoke({"objective": request.mission.objective, **dict(request.context)})
            output = raw if isinstance(raw, dict) else {"result": raw}
            result = ExecutionResult(
                request.execution_id,
                self.descriptor.orchestrator_id,
                ExecutionStatus.SUCCEEDED,
                output=output,
            )
        except Exception as exc:
            result = ExecutionResult(
                request.execution_id,
                self.descriptor.orchestrator_id,
                ExecutionStatus.FAILED,
                error=str(exc),
            )
        self._record_runtime_health(result.status, execution_id=request.execution_id)
        return result

    def cancel(self, execution_id: str) -> None:
        self._cancelled.add(execution_id)


__all__ = ["LangGraphOrchestratorAdapter", "normalize_evidence"]
