"""Gemini Interactions API adapter for models and managed agents.

The Interactions API is treated as a provider boundary only. metaO retains
scheduling, work-graph mutation, trust admission, budget authority and final
acceptance. The adapter normalizes provider statuses and capacity evidence while
keeping Google SDK types out of Core.
"""

from __future__ import annotations

from datetime import datetime, time, timedelta
from hashlib import sha256
import json
from threading import Lock
from time import sleep
from typing import Any, Callable, Mapping
import urllib.error
import urllib.request
from zoneinfo import ZoneInfo

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


_PACIFIC = ZoneInfo("America/Los_Angeles")
_ACTIVE_STATUSES = frozenset({"queued", "in_progress"})


class GeminiHttpError(RuntimeError):
    def __init__(
        self,
        status_code: int,
        body: Any = None,
        *,
        headers: Mapping[str, str] | None = None,
    ) -> None:
        code = _error_code(body)
        suffix = f" ({code})" if code else ""
        super().__init__(f"Gemini HTTP {status_code}{suffix}")
        self.status_code = status_code
        self.body = body
        self.headers = dict(headers or {})


def _digest(value: Any) -> str:
    return sha256(
        json.dumps(value, sort_keys=True, default=str, separators=(",", ":")).encode()
    ).hexdigest()


def _error_code(body: Any) -> str | None:
    if not isinstance(body, Mapping):
        return None
    error = body.get("error")
    if not isinstance(error, Mapping):
        return None
    code = error.get("code")
    return code if isinstance(code, str) and code.strip() else None


def _retry_after_recovery(
    headers: Mapping[str, str],
    *,
    created_at_epoch: float,
    evidence_prefix: str,
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
        evidence_ref=f"{evidence_prefix}:retry-after:{raw}",
    )


def _next_daily_quota_reset(created_at_epoch: float) -> CapacityRecovery:
    observed = datetime.fromtimestamp(created_at_epoch, tz=_PACIFIC)
    next_day = observed.date() + timedelta(days=1)
    reset = datetime.combine(next_day, time.min, tzinfo=_PACIFIC)
    return CapacityRecovery(
        recover_at_epoch=reset.timestamp(),
        evidence_basis=RecoveryEvidenceBasis.PROVIDER_DOCUMENTATION,
        evidence_ref="gemini:quota_exceeded:rpd-reset-midnight-pacific",
    )


def _capacity_observation_from_http_error(
    exc: GeminiHttpError,
    *,
    created_at_epoch: float,
) -> CapacityObservation | None:
    code = _error_code(exc.body)

    if code == "authentication" or exc.status_code == 401:
        return CapacityObservation(CapacityStatus.AUTHENTICATION_FAILURE)
    if code == "permission_denied" or exc.status_code == 403:
        return CapacityObservation(CapacityStatus.UNKNOWN)
    if code == "quota_exceeded":
        recovery = _retry_after_recovery(
            exc.headers,
            created_at_epoch=created_at_epoch,
            evidence_prefix="gemini:quota_exceeded",
        ) or _next_daily_quota_reset(created_at_epoch)
        return CapacityObservation(
            CapacityStatus.TEMPORARILY_QUOTA_EXHAUSTED,
            recovery,
        )
    if code in {"rate_limit_exceeded", "too_many_requests"}:
        return CapacityObservation(
            CapacityStatus.TEMPORARILY_RATE_LIMITED,
            _retry_after_recovery(
                exc.headers,
                created_at_epoch=created_at_epoch,
                evidence_prefix=f"gemini:{code}",
            ),
        )
    if code in {"api_error", "service_unavailable"} or exc.status_code in {500, 503}:
        return CapacityObservation(CapacityStatus.PROVIDER_UNAVAILABLE)

    # Gemini uses HTTP 429 for both short rate limits and daily quota exhaustion.
    # Without the machine-readable error code, status alone is insufficient.
    if exc.status_code == 429:
        return CapacityObservation(CapacityStatus.UNKNOWN)

    # Request/model/policy errors are not provider capacity observations.
    if exc.status_code in {400, 404, 409, 416, 422, 499, 501, 504}:
        return None
    return CapacityObservation(CapacityStatus.UNKNOWN)


def _extract_text(interaction: Mapping[str, Any]) -> str:
    pieces: list[str] = []
    steps = interaction.get("steps")
    if not isinstance(steps, list):
        return ""
    for step in steps:
        if not isinstance(step, Mapping) or step.get("type") != "model_output":
            continue
        content = step.get("content")
        if not isinstance(content, list):
            continue
        for item in content:
            if not isinstance(item, Mapping) or item.get("type") != "text":
                continue
            text_value = item.get("text")
            if isinstance(text_value, str):
                pieces.append(text_value)
    return "".join(pieces)


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
        provenance_root=f"gemini:{orchestrator_id}:{request.execution_id}",
        authority_id=str(context.get("authority_id", "metao-runtime")),
        passed=True,
        created_at_epoch=float(context.get("created_at_epoch", 0.0)),
        expires_at_epoch=context.get("expires_at_epoch"),
    )


class GeminiInteractionsOrchestratorAdapter:
    """Execute metaO missions through Gemini models or managed agents."""

    def __init__(
        self,
        *,
        api_key: str = "",
        target: str = "gemini-3.8-flash",
        target_kind: str = "model",
        environment: str | None = None,
        base_url: str = "https://generativelanguage.googleapis.com/v1beta",
        orchestrator_id: str = "gemini-interactions",
        version: str = "v1beta",
        background: bool = False,
        max_polls: int = 120,
        poll_interval_s: float = 1.0,
        transport: Callable[[str, str, Any | None], Any] | None = None,
        sleep_fn: Callable[[float], None] = sleep,
    ) -> None:
        if target_kind not in {"model", "agent"}:
            raise ValueError("Gemini target_kind must be 'model' or 'agent'")
        if not target.strip():
            raise ValueError("Gemini target must be non-empty")
        if max_polls <= 0:
            raise ValueError("max_polls must be positive")
        if poll_interval_s < 0:
            raise ValueError("poll_interval_s must be non-negative")

        self._api_key = api_key
        self._target = target
        self._target_kind = target_kind
        self._environment = environment or ("remote" if target_kind == "agent" else None)
        self._base_url = base_url.rstrip("/")
        self._background = background
        self._max_polls = max_polls
        self._poll_interval_s = poll_interval_s
        self._transport = transport
        self._sleep_fn = sleep_fn
        self._cancelled: set[str] = set()
        self._interactions: dict[str, str] = {}
        self._lock = Lock()

        capabilities = {"agent"}
        if target_kind == "agent":
            capabilities.add("workflow")
        self._descriptor = OrchestratorDescriptor(
            orchestrator_id=orchestrator_id,
            version=version,
            capabilities=frozenset(capabilities),
            metadata={
                "adapter": "gemini-interactions",
                "target_kind": target_kind,
                "target": target,
            },
        )

    @property
    def descriptor(self) -> OrchestratorDescriptor:
        return self._descriptor

    def health(self) -> HealthReport:
        ready = self._transport is not None or bool(self._api_key.strip())
        if ready:
            return HealthReport(HealthStatus.HEALTHY, "Gemini Interactions transport configured")
        return HealthReport(HealthStatus.UNHEALTHY, "Gemini API key is not configured")

    def _default_transport(self, method: str, path: str, body: Any | None) -> Any:
        data = None if body is None else json.dumps(body).encode("utf-8")
        headers = {"x-goog-api-key": self._api_key}
        if data is not None:
            headers["Content-Type"] = "application/json"
        request = urllib.request.Request(
            self._base_url + path,
            data=data,
            method=method,
            headers=headers,
        )
        try:
            with urllib.request.urlopen(request, timeout=300) as response:
                raw = response.read().decode("utf-8")
                return json.loads(raw) if raw else None
        except urllib.error.HTTPError as exc:
            raw = exc.read().decode("utf-8", errors="replace")
            try:
                parsed: Any = json.loads(raw) if raw else None
            except json.JSONDecodeError:
                parsed = raw
            raise GeminiHttpError(
                exc.code,
                parsed,
                headers=dict(exc.headers.items()),
            ) from exc

    def _request(self, method: str, path: str, body: Any | None = None) -> Any:
        transport = self._transport or self._default_transport
        return transport(method, path, body)

    def _input(self, request: ExecutionRequest) -> str:
        content = request.mission.objective
        context = dict(request.context)
        if context:
            content += "\n\nContext:\n" + json.dumps(
                context,
                sort_keys=True,
                default=str,
                separators=(",", ":"),
            )
        return content

    def _create_payload(self, request: ExecutionRequest) -> dict[str, Any]:
        payload: dict[str, Any] = {
            self._target_kind: self._target,
            "input": self._input(request),
        }
        if self._background:
            payload["background"] = True
        if self._target_kind == "agent" and self._environment:
            payload["environment"] = self._environment
        return payload

    @staticmethod
    def _validate_interaction(value: Any) -> Mapping[str, Any]:
        if not isinstance(value, Mapping):
            raise RuntimeError("Gemini returned a non-object interaction")
        interaction_id = value.get("id")
        status = value.get("status")
        if not isinstance(interaction_id, str) or not interaction_id.strip():
            raise RuntimeError("Gemini interaction is missing an id")
        if not isinstance(status, str) or not status.strip():
            raise RuntimeError("Gemini interaction is missing a status")
        return value

    def _remember_interaction(self, execution_id: str, interaction_id: str) -> None:
        with self._lock:
            self._interactions[execution_id] = interaction_id

    def get_interaction(self, interaction_id: str) -> Mapping[str, Any]:
        value = self._request("GET", f"/interactions/{interaction_id}")
        return self._validate_interaction(value)

    def cancel_interaction(self, interaction_id: str) -> Mapping[str, Any]:
        value = self._request("POST", f"/interactions/{interaction_id}/cancel", {})
        return self._validate_interaction(value)

    def _terminal_result(
        self,
        request: ExecutionRequest,
        interaction: Mapping[str, Any],
    ) -> ExecutionResult:
        status = str(interaction.get("status", ""))
        output = {
            "result": _extract_text(interaction),
            "interaction": dict(interaction),
        }
        if status == "completed":
            return ExecutionResult(
                request.execution_id,
                self.descriptor.orchestrator_id,
                ExecutionStatus.SUCCEEDED,
                output=output,
            )
        if status == "cancelled":
            return ExecutionResult(
                request.execution_id,
                self.descriptor.orchestrator_id,
                ExecutionStatus.CANCELLED,
                output=output,
            )
        if status in {"failed", "incomplete", "requires_action", "budget_exceeded"}:
            return ExecutionResult(
                request.execution_id,
                self.descriptor.orchestrator_id,
                ExecutionStatus.FAILED,
                output=output,
                error=f"Gemini interaction ended with status: {status}",
            )
        return ExecutionResult(
            request.execution_id,
            self.descriptor.orchestrator_id,
            ExecutionStatus.FAILED,
            output=output,
            error=f"unsupported Gemini interaction status: {status or '<empty>'}",
        )

    def execute(self, request: ExecutionRequest) -> ExecutionResult:
        with self._lock:
            if request.execution_id in self._cancelled:
                return ExecutionResult(
                    request.execution_id,
                    self.descriptor.orchestrator_id,
                    ExecutionStatus.CANCELLED,
                )

        try:
            interaction = self._validate_interaction(
                self._request("POST", "/interactions", self._create_payload(request))
            )
            interaction_id = str(interaction["id"])
            self._remember_interaction(request.execution_id, interaction_id)

            for _ in range(self._max_polls):
                status = str(interaction.get("status", ""))
                if status not in _ACTIVE_STATUSES:
                    return self._terminal_result(request, interaction)

                with self._lock:
                    cancelled = request.execution_id in self._cancelled
                if cancelled:
                    cancelled_interaction = self.cancel_interaction(interaction_id)
                    return self._terminal_result(request, cancelled_interaction)

                self._sleep_fn(self._poll_interval_s)
                interaction = self.get_interaction(interaction_id)

            return ExecutionResult(
                request.execution_id,
                self.descriptor.orchestrator_id,
                ExecutionStatus.FAILED,
                output={"interaction": dict(interaction)},
                error="Gemini interaction did not reach a terminal state within the polling bound",
            )
        except GeminiHttpError as exc:
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
        with self._lock:
            self._cancelled.add(execution_id)
            interaction_id = self._interactions.get(execution_id)
        if interaction_id is not None:
            self.cancel_interaction(interaction_id)


__all__ = [
    "GeminiHttpError",
    "GeminiInteractionsOrchestratorAdapter",
    "normalize_evidence",
]
