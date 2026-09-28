"""Thin DeepSeek Chat Completions adapter for metaO.

DeepSeek is treated as a stateless replaceable sub-agent. Provider HTTP/account
signals are normalized into metaO capacity contracts while scheduling, trust,
budget authority, work-graph mutation and acceptance stay outside this module.
"""

from __future__ import annotations

from hashlib import sha256
import json
from threading import Lock
from typing import Any, Callable, Mapping
import urllib.error
import urllib.request

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


class DeepSeekHttpError(RuntimeError):
    def __init__(
        self,
        status_code: int,
        body: Any = None,
        *,
        headers: Mapping[str, str] | None = None,
    ) -> None:
        super().__init__(f"DeepSeek HTTP {status_code}")
        self.status_code = status_code
        self.body = body
        self.headers = dict(headers or {})


def _digest(value: Any) -> str:
    return sha256(
        json.dumps(value, sort_keys=True, default=str, separators=(",", ":")).encode()
    ).hexdigest()


def _retry_after_recovery(
    headers: Mapping[str, str],
    *,
    created_at_epoch: float,
) -> CapacityRecovery | None:
    raw = None
    for key, value in headers.items():
        if key.lower() == "retry-after":
            raw = value
            break
    try:
        delay_s = float(raw)
    except (TypeError, ValueError):
        return None
    if delay_s < 0:
        return None
    return CapacityRecovery(
        recover_at_epoch=created_at_epoch + delay_s,
        evidence_basis=RecoveryEvidenceBasis.ADAPTER_VERIFIED,
        evidence_ref=f"deepseek:http:429:retry-after:{raw}",
    )


def _capacity_observation_from_http_error(
    exc: DeepSeekHttpError,
    *,
    created_at_epoch: float,
) -> CapacityObservation | None:
    if exc.status_code == 401:
        return CapacityObservation(CapacityStatus.AUTHENTICATION_FAILURE)
    if exc.status_code == 402:
        return CapacityObservation(CapacityStatus.CREDIT_EXHAUSTED)
    if exc.status_code == 429:
        return CapacityObservation(
            CapacityStatus.TEMPORARILY_RATE_LIMITED,
            _retry_after_recovery(exc.headers, created_at_epoch=created_at_epoch),
        )
    if exc.status_code in {500, 503}:
        return CapacityObservation(CapacityStatus.PROVIDER_UNAVAILABLE)
    if exc.status_code in {400, 422}:
        return None
    return CapacityObservation(CapacityStatus.UNKNOWN)


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
        provenance_root=f"deepseek:{orchestrator_id}:{request.execution_id}",
        authority_id=str(context.get("authority_id", "metao-runtime")),
        passed=True,
        created_at_epoch=float(context.get("created_at_epoch", 0.0)),
        expires_at_epoch=context.get("expires_at_epoch"),
    )


class DeepSeekHttpOrchestratorAdapter:
    """Execute one mission through DeepSeek's stateless chat-completions API."""

    def __init__(
        self,
        *,
        api_key: str = "",
        model: str = "deepseek-v4-flash",
        base_url: str = "https://api.deepseek.com",
        orchestrator_id: str = "deepseek",
        version: str = "v1",
        transport: Callable[[str, str, Any | None], Any] | None = None,
    ) -> None:
        if not model.strip():
            raise ValueError("DeepSeek model must be non-empty")
        self._api_key = api_key
        self._model = model
        self._base_url = base_url.rstrip("/")
        self._transport = transport
        self._cancelled: set[str] = set()
        self._lock = Lock()
        self._descriptor = OrchestratorDescriptor(
            orchestrator_id=orchestrator_id,
            version=version,
            capabilities=frozenset({"agent"}),
            metadata={"adapter": "deepseek-http", "model": model},
        )

    @property
    def descriptor(self) -> OrchestratorDescriptor:
        return self._descriptor

    def health(self) -> HealthReport:
        ready = self._transport is not None or bool(self._api_key.strip())
        if ready:
            return HealthReport(HealthStatus.HEALTHY, "DeepSeek transport configured")
        return HealthReport(HealthStatus.UNHEALTHY, "DeepSeek API key is not configured")

    def _default_transport(self, method: str, path: str, body: Any | None) -> Any:
        data = None if body is None else json.dumps(body).encode("utf-8")
        headers = {
            "Authorization": f"Bearer {self._api_key}",
            "Content-Type": "application/json",
        }
        request = urllib.request.Request(
            self._base_url + path,
            data=data,
            method=method,
            headers=headers,
        )
        try:
            with urllib.request.urlopen(request, timeout=60) as response:
                raw = response.read().decode("utf-8")
                return json.loads(raw) if raw else None
        except urllib.error.HTTPError as exc:
            raw = exc.read().decode("utf-8", errors="replace")
            try:
                parsed: Any = json.loads(raw) if raw else None
            except json.JSONDecodeError:
                parsed = raw
            raise DeepSeekHttpError(
                exc.code,
                parsed,
                headers=dict(exc.headers.items()),
            ) from exc

    def _request(self, method: str, path: str, body: Any | None = None) -> Any:
        transport = self._transport or self._default_transport
        return transport(method, path, body)

    def _payload(self, request: ExecutionRequest) -> dict[str, Any]:
        context = dict(request.context)
        content = request.mission.objective
        if context:
            content += "\n\nContext:\n" + json.dumps(
                context,
                sort_keys=True,
                default=str,
                separators=(",", ":"),
            )
        return {
            "model": self._model,
            "messages": [{"role": "user", "content": content}],
            "stream": False,
        }

    @staticmethod
    def _parse_response(response: Any) -> tuple[str, str, Mapping[str, Any]]:
        if not isinstance(response, Mapping):
            raise RuntimeError("DeepSeek returned a non-object response")
        choices = response.get("choices")
        if not isinstance(choices, list) or not choices:
            raise RuntimeError("DeepSeek response does not contain a completion choice")
        first = choices[0]
        if not isinstance(first, Mapping):
            raise RuntimeError("DeepSeek completion choice is not an object")
        finish_reason = str(first.get("finish_reason", ""))
        message = first.get("message")
        if not isinstance(message, Mapping):
            raise RuntimeError("DeepSeek completion choice has no message object")
        content = message.get("content")
        return finish_reason, content if isinstance(content, str) else "", response

    def execute(self, request: ExecutionRequest) -> ExecutionResult:
        with self._lock:
            if request.execution_id in self._cancelled:
                return ExecutionResult(
                    request.execution_id,
                    self.descriptor.orchestrator_id,
                    ExecutionStatus.CANCELLED,
                )

        try:
            response = self._request("POST", "/chat/completions", self._payload(request))
            finish_reason, content, response_map = self._parse_response(response)

            if finish_reason == "insufficient_system_resource":
                return ExecutionResult(
                    request.execution_id,
                    self.descriptor.orchestrator_id,
                    ExecutionStatus.FAILED,
                    output={"response": dict(response_map)},
                    error="DeepSeek inference system reported insufficient resources",
                    capacity_observation=CapacityObservation(
                        CapacityStatus.PROVIDER_UNAVAILABLE
                    ),
                )
            if finish_reason not in {"stop", "length"}:
                return ExecutionResult(
                    request.execution_id,
                    self.descriptor.orchestrator_id,
                    ExecutionStatus.FAILED,
                    output={"response": dict(response_map)},
                    error=f"unsupported DeepSeek finish reason: {finish_reason or '<empty>'}",
                )

            return ExecutionResult(
                request.execution_id,
                self.descriptor.orchestrator_id,
                ExecutionStatus.SUCCEEDED,
                output={
                    "result": content,
                    "finish_reason": finish_reason,
                    "response": dict(response_map),
                },
            )
        except DeepSeekHttpError as exc:
            created_at_epoch = float(request.context.get("created_at_epoch", 0.0))
            return ExecutionResult(
                request.execution_id,
                self.descriptor.orchestrator_id,
                ExecutionStatus.FAILED,
                error=str(exc),
                capacity_observation=_capacity_observation_from_http_error(
                    exc,
                    created_at_epoch=created_at_epoch,
                ),
            )
        except Exception as exc:
            return ExecutionResult(
                request.execution_id,
                self.descriptor.orchestrator_id,
                ExecutionStatus.FAILED,
                error=str(exc),
            )

    def cancel(self, execution_id: str) -> None:
        # Chat Completions is a synchronous stateless request at this boundary;
        # without a provider-side execution handle, cancellation is intentionally
        # limited to pre-dispatch and does not pretend to stop an in-flight HTTP call.
        with self._lock:
            self._cancelled.add(execution_id)


__all__ = [
    "DeepSeekHttpError",
    "DeepSeekHttpOrchestratorAdapter",
    "normalize_evidence",
]
