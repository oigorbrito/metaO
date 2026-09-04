"""Thin OpenAI Agents SDK adapter for metaO.

The adapter intentionally depends only on the public runner/result runtime shape
(`run_sync` and `final_output`) via duck typing. OpenAI Agents SDK types stay in
plugin or sandbox composition code and never enter metaO Core.
"""

from __future__ import annotations

from hashlib import sha256
import json
from typing import Any

from metao.acceptance import EvidenceEnvelope
from metao.capacity import (
    CapacityObservation,
    CapacityRecovery,
    CapacityStatus,
    RecoveryEvidenceBasis,
)
from metao.core import (
    ExecutionRequest,
    ExecutionResult,
    ExecutionStatus,
    HealthReport,
    HealthStatus,
    OrchestratorDescriptor,
)


def _digest(value: Any) -> str:
    return sha256(
        json.dumps(value, sort_keys=True, default=str, separators=(",", ":")).encode()
    ).hexdigest()


def _runtime_input(request: ExecutionRequest) -> str:
    """Serialize the framework-neutral mission boundary deterministically."""

    return json.dumps(
        {
            "objective": request.mission.objective,
            "context": dict(request.context),
        },
        sort_keys=True,
        default=str,
        separators=(",", ":"),
    )


def _capacity_observation_from_exception(
    exc: Exception,
    *,
    created_at_epoch: float,
) -> CapacityObservation | None:
    if getattr(exc, "status_code", None) != 429:
        return None
    headers = getattr(exc, "headers", None)
    if not isinstance(headers, dict):
        return None
    retry_after_raw = headers.get("retry-after") or headers.get("Retry-After")
    try:
        retry_after_s = float(retry_after_raw)
    except (TypeError, ValueError):
        return None
    if retry_after_s < 0:
        return None
    recovery = CapacityRecovery(
        recover_at_epoch=created_at_epoch + retry_after_s,
        evidence_basis=RecoveryEvidenceBasis.ADAPTER_VERIFIED,
        evidence_ref=f"http:429:retry-after:{retry_after_raw}",
    )
    return CapacityObservation(
        capacity_status=CapacityStatus.TEMPORARILY_RATE_LIMITED,
        recovery=recovery,
    )


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
            context.get("verification_context_id", "default-verification")
        ),
        policy_bundle_id=str(context.get("policy_bundle_id", "default-policy")),
        verifier_id=str(context.get("verifier_id", "adapter-observer")),
        payload_digest=_digest(output),
        provenance_root=f"openai-agents:{orchestrator_id}:{request.execution_id}",
        authority_id=str(context.get("authority_id", "metao-runtime")),
        passed=True,
        created_at_epoch=float(context.get("created_at_epoch", 0.0)),
        expires_at_epoch=context.get("expires_at_epoch"),
    )


class OpenAIAgentsOrchestratorAdapter:
    """Adapt an Agents SDK-like runner and configured agent via duck typing."""

    def __init__(
        self,
        runner: Any,
        agent: Any,
        *,
        orchestrator_id: str = "openai-agents",
        version: str = "1",
    ) -> None:
        self._runner = runner
        self._agent = agent
        self._cancelled: set[str] = set()
        self._descriptor = OrchestratorDescriptor(
            orchestrator_id=orchestrator_id,
            version=version,
            capabilities=frozenset({"workflow", "agent"}),
            metadata={"adapter": "openai-agents"},
        )

    @property
    def descriptor(self) -> OrchestratorDescriptor:
        return self._descriptor

    def health(self) -> HealthReport:
        run_sync = callable(getattr(self._runner, "run_sync", None))
        configured = self._agent is not None
        healthy = run_sync and configured
        if healthy:
            reason = "run_sync available and agent configured"
        elif not run_sync:
            reason = "run_sync unavailable"
        else:
            reason = "agent unavailable"
        return HealthReport(
            HealthStatus.HEALTHY if healthy else HealthStatus.UNHEALTHY,
            reason,
        )

    def execute(self, request: ExecutionRequest) -> ExecutionResult:
        if request.execution_id in self._cancelled:
            return ExecutionResult(
                request.execution_id,
                self.descriptor.orchestrator_id,
                ExecutionStatus.CANCELLED,
            )
        try:
            run_result = self._runner.run_sync(self._agent, _runtime_input(request))
            final_output = getattr(run_result, "final_output", run_result)
            output = final_output if isinstance(final_output, dict) else {"result": final_output}
            return ExecutionResult(
                request.execution_id,
                self.descriptor.orchestrator_id,
                ExecutionStatus.SUCCEEDED,
                output=output,
            )
        except Exception as exc:
            created_at_epoch = float(request.context.get("created_at_epoch", 0.0))
            return ExecutionResult(
                request.execution_id,
                self.descriptor.orchestrator_id,
                ExecutionStatus.FAILED,
                error=str(exc),
                capacity_observation=_capacity_observation_from_exception(
                    exc,
                    created_at_epoch=created_at_epoch,
                ),
            )

    def cancel(self, execution_id: str) -> None:
        # The current metaO contract exposes synchronous cancellation without an
        # execution handle. Preserve its established pre-dispatch semantics
        # rather than leaking the SDK streaming result type into Core.
        self._cancelled.add(execution_id)


__all__ = ["OpenAIAgentsOrchestratorAdapter", "normalize_evidence"]
