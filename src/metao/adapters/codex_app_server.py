"""Codex App Server adapter boundary for metaO.

This adapter treats Codex App Server as an executor boundary only. Scheduling,
trust admission, budget authority, work-graph mutation and final acceptance
remain metaO-owned. The adapter consumes structured App Server thread/turn/error
signals and does not infer provider semantics from free-form error text.
"""

from __future__ import annotations

from hashlib import sha256
import json
from threading import Lock
from typing import Any, Callable, Mapping

from metao.acceptance import EvidenceEnvelope
from metao.capacity import CapacityObservation, CapacityStatus
from metao.core import (
    ExecutionRequest,
    ExecutionResult,
    ExecutionStatus,
    HealthReport,
    HealthStatus,
    OrchestratorDescriptor,
)


JsonRpcCall = Callable[[str, Mapping[str, Any] | None], Mapping[str, Any]]
JsonRpcNotify = Callable[[str, Mapping[str, Any] | None], None]
NotificationReader = Callable[[], Mapping[str, Any]]


class CodexAppServerProtocolError(RuntimeError):
    """Raised when the App Server returns a structurally invalid response."""


class CodexAppServerRpcError(RuntimeError):
    """Structured JSON-RPC error surfaced by an injected transport."""

    def __init__(self, code: int, message: str, data: Any = None) -> None:
        super().__init__(f"Codex App Server RPC {code}: {message}")
        self.code = code
        self.message = message
        self.data = data


def _digest(value: Any) -> str:
    return sha256(
        json.dumps(value, sort_keys=True, default=str, separators=(",", ":")).encode()
    ).hexdigest()


def _codex_error_info(error: Any) -> Any:
    if not isinstance(error, Mapping):
        return None
    return error.get("codexErrorInfo")


def _codex_error_kind(error: Any) -> str | None:
    info = _codex_error_info(error)
    if isinstance(info, str):
        return info
    if isinstance(info, Mapping):
        kind = info.get("type") or info.get("kind")
        if isinstance(kind, str) and kind.strip():
            return kind
        # Generated tagged-union encodings may use a single variant key.
        if len(info) == 1:
            key = next(iter(info))
            if isinstance(key, str):
                return key
    return None


def _http_status_from_error(error: Any) -> int | None:
    info = _codex_error_info(error)
    if isinstance(info, Mapping):
        value = info.get("httpStatusCode")
        if isinstance(value, int):
            return value
        if len(info) == 1:
            payload = next(iter(info.values()))
            if isinstance(payload, Mapping) and isinstance(payload.get("httpStatusCode"), int):
                return int(payload["httpStatusCode"])
    return None


def _capacity_observation_from_turn_error(error: Any) -> CapacityObservation | None:
    kind = _codex_error_kind(error)
    status_code = _http_status_from_error(error)

    if kind == "unauthorized" or status_code == 401:
        return CapacityObservation(CapacityStatus.AUTHENTICATION_FAILURE)
    if kind == "rateLimitExceeded":
        return CapacityObservation(CapacityStatus.TEMPORARILY_RATE_LIMITED)
    if kind == "usageLimitExceeded":
        # The public App Server contract exposes a usage limit signal but does
        # not establish that it is always a specific quota window with a known
        # recovery boundary. Preserve the signal fail-closed without inventing
        # recovery evidence.
        return CapacityObservation(CapacityStatus.TEMPORARILY_QUOTA_EXHAUSTED)
    if kind in {
        "serverOverloaded",
        "internalServerError",
        "httpConnectionFailed",
        "responseStreamConnectionFailed",
        "responseStreamDisconnected",
        "responseTooManyFailedAttempts",
    }:
        return CapacityObservation(CapacityStatus.PROVIDER_UNAVAILABLE)

    # Structured 429 without a more specific kind proves transient pressure but
    # not a reset time or quota class.
    if status_code == 429:
        return CapacityObservation(CapacityStatus.TEMPORARILY_RATE_LIMITED)

    # Context-window, sandbox, cyber-policy, bad-request, misalignment and other
    # task/policy failures are execution failures rather than global capacity.
    if kind in {
        "contextWindowExceeded",
        "sessionBudgetExceeded",
        "cyberPolicy",
        "misalignmentPolicyViolation",
        "badRequest",
        "threadRollbackFailed",
        "sandboxError",
        "activeTurnNotSteerable",
    }:
        return None

    if kind == "other":
        return CapacityObservation(CapacityStatus.UNKNOWN)
    return None


def _last_agent_message(turn: Mapping[str, Any]) -> str:
    items = turn.get("items")
    if not isinstance(items, list):
        return ""
    for item in reversed(items):
        if not isinstance(item, Mapping):
            continue
        if item.get("type") != "agentMessage":
            continue
        text = item.get("text")
        if isinstance(text, str):
            return text
        content = item.get("content")
        if isinstance(content, list):
            parts: list[str] = []
            for part in content:
                if isinstance(part, Mapping) and isinstance(part.get("text"), str):
                    parts.append(part["text"])
            if parts:
                return "".join(parts)
    return ""


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
        provenance_root=f"codex-app-server:{orchestrator_id}:{request.execution_id}",
        authority_id=str(context.get("authority_id", "metao-runtime")),
        passed=True,
        created_at_epoch=float(context.get("created_at_epoch", 0.0)),
        expires_at_epoch=context.get("expires_at_epoch"),
    )


class CodexAppServerOrchestratorAdapter:
    """Execute metaO missions through the Codex App Server JSON-RPC contract."""

    def __init__(
        self,
        *,
        request_fn: JsonRpcCall,
        notify_fn: JsonRpcNotify,
        read_notification_fn: NotificationReader,
        cwd: str | None = None,
        model: str | None = None,
        approval_policy: str = "on-request",
        sandbox: str = "workspace-write",
        ephemeral: bool = True,
        orchestrator_id: str = "codex-app-server",
        version: str = "v2",
        max_notifications: int = 10000,
    ) -> None:
        if max_notifications <= 0:
            raise ValueError("max_notifications must be positive")
        self._request_fn = request_fn
        self._notify_fn = notify_fn
        self._read_notification_fn = read_notification_fn
        self._cwd = cwd
        self._model = model
        self._approval_policy = approval_policy
        self._sandbox = sandbox
        self._ephemeral = ephemeral
        self._max_notifications = max_notifications
        self._lock = Lock()
        self._initialized = False
        self._active: dict[str, tuple[str, str]] = {}
        self._cancelled: set[str] = set()
        self._descriptor = OrchestratorDescriptor(
            orchestrator_id=orchestrator_id,
            version=version,
            capabilities=frozenset({"agent", "workflow", "coding"}),
            metadata={"adapter": "codex-app-server", "protocol": "json-rpc-v2"},
        )

    @property
    def descriptor(self) -> OrchestratorDescriptor:
        return self._descriptor

    def health(self) -> HealthReport:
        return HealthReport(HealthStatus.HEALTHY, "Codex App Server transport configured")

    def _initialize(self) -> None:
        with self._lock:
            if self._initialized:
                return
            response = self._request_fn(
                "initialize",
                {
                    "clientInfo": {
                        "name": "metao",
                        "title": "metaO",
                        "version": self.descriptor.version,
                    }
                },
            )
            if not isinstance(response, Mapping):
                raise CodexAppServerProtocolError("initialize returned a non-object result")
            self._notify_fn("initialized", {})
            self._initialized = True

    def _thread_start_params(self) -> dict[str, Any]:
        params: dict[str, Any] = {
            "approvalPolicy": self._approval_policy,
            "sandbox": self._sandbox,
            "ephemeral": self._ephemeral,
        }
        if self._cwd is not None:
            params["cwd"] = self._cwd
        if self._model is not None:
            params["model"] = self._model
        return params

    @staticmethod
    def _extract_thread_id(result: Any) -> str:
        if not isinstance(result, Mapping):
            raise CodexAppServerProtocolError("thread/start returned a non-object result")
        thread = result.get("thread")
        if not isinstance(thread, Mapping):
            raise CodexAppServerProtocolError("thread/start result is missing thread")
        thread_id = thread.get("id")
        if not isinstance(thread_id, str) or not thread_id.strip():
            raise CodexAppServerProtocolError("thread/start result is missing thread id")
        return thread_id

    @staticmethod
    def _extract_turn(result: Any) -> Mapping[str, Any]:
        if not isinstance(result, Mapping):
            raise CodexAppServerProtocolError("turn/start returned a non-object result")
        turn = result.get("turn")
        if not isinstance(turn, Mapping):
            raise CodexAppServerProtocolError("turn/start result is missing turn")
        turn_id = turn.get("id")
        status = turn.get("status")
        if not isinstance(turn_id, str) or not turn_id.strip():
            raise CodexAppServerProtocolError("turn/start result is missing turn id")
        if not isinstance(status, str) or not status.strip():
            raise CodexAppServerProtocolError("turn/start result is missing turn status")
        return turn

    @staticmethod
    def _turn_from_notification(notification: Mapping[str, Any]) -> Mapping[str, Any] | None:
        if notification.get("method") != "turn/completed":
            return None
        params = notification.get("params")
        if not isinstance(params, Mapping):
            raise CodexAppServerProtocolError("turn/completed notification missing params")
        turn = params.get("turn")
        if not isinstance(turn, Mapping):
            raise CodexAppServerProtocolError("turn/completed notification missing turn")
        return turn

    def _wait_for_turn(self, thread_id: str, turn_id: str) -> Mapping[str, Any]:
        for _ in range(self._max_notifications):
            notification = self._read_notification_fn()
            if not isinstance(notification, Mapping):
                raise CodexAppServerProtocolError("App Server emitted a non-object notification")
            turn = self._turn_from_notification(notification)
            if turn is None:
                continue
            if turn.get("id") != turn_id:
                continue
            status = turn.get("status")
            if status not in {"completed", "interrupted", "failed"}:
                raise CodexAppServerProtocolError(
                    f"turn/completed emitted unsupported status: {status!r}"
                )
            return turn
        raise CodexAppServerProtocolError(
            f"turn {turn_id} did not complete within notification bound"
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
            self._initialize()
            thread_result = self._request_fn("thread/start", self._thread_start_params())
            thread_id = self._extract_thread_id(thread_result)
            prompt = request.mission.objective
            if request.context:
                prompt += "\n\nContext:\n" + json.dumps(
                    dict(request.context),
                    sort_keys=True,
                    default=str,
                    separators=(",", ":"),
                )
            turn = self._extract_turn(
                self._request_fn(
                    "turn/start",
                    {
                        "threadId": thread_id,
                        "input": [{"type": "text", "text": prompt}],
                    },
                )
            )
            turn_id = str(turn["id"])
            with self._lock:
                self._active[request.execution_id] = (thread_id, turn_id)
                cancelled = request.execution_id in self._cancelled
            if cancelled:
                self._request_fn(
                    "turn/interrupt", {"threadId": thread_id, "turnId": turn_id}
                )

            if turn.get("status") in {"completed", "interrupted", "failed"}:
                final_turn = turn
            else:
                final_turn = self._wait_for_turn(thread_id, turn_id)
        except CodexAppServerRpcError as exc:
            observation = (
                CapacityObservation(CapacityStatus.TEMPORARILY_RATE_LIMITED)
                if exc.code == -32001
                else None
            )
            return ExecutionResult(
                request.execution_id,
                self.descriptor.orchestrator_id,
                ExecutionStatus.FAILED,
                error=str(exc),
                capacity_observation=observation,
            )
        except Exception as exc:
            return ExecutionResult(
                request.execution_id,
                self.descriptor.orchestrator_id,
                ExecutionStatus.FAILED,
                error=str(exc),
            )
        finally:
            with self._lock:
                self._active.pop(request.execution_id, None)

        status = str(final_turn.get("status"))
        output = {
            "result": _last_agent_message(final_turn),
            "thread_id": thread_id,
            "turn": dict(final_turn),
        }
        if status == "completed":
            return ExecutionResult(
                request.execution_id,
                self.descriptor.orchestrator_id,
                ExecutionStatus.SUCCEEDED,
                output=output,
            )
        if status == "interrupted":
            return ExecutionResult(
                request.execution_id,
                self.descriptor.orchestrator_id,
                ExecutionStatus.CANCELLED,
                output=output,
            )
        if status == "failed":
            error = final_turn.get("error")
            observation = _capacity_observation_from_turn_error(error)
            message = "Codex turn failed"
            if isinstance(error, Mapping) and isinstance(error.get("message"), str):
                message = str(error["message"])
            return ExecutionResult(
                request.execution_id,
                self.descriptor.orchestrator_id,
                ExecutionStatus.FAILED,
                output=output,
                error=message,
                capacity_observation=observation,
            )
        return ExecutionResult(
            request.execution_id,
            self.descriptor.orchestrator_id,
            ExecutionStatus.FAILED,
            output=output,
            error=f"unsupported Codex turn status: {status}",
        )

    def cancel(self, execution_id: str) -> bool:
        with self._lock:
            self._cancelled.add(execution_id)
            active = self._active.get(execution_id)
        if active is None:
            return True
        thread_id, turn_id = active
        self._request_fn("turn/interrupt", {"threadId": thread_id, "turnId": turn_id})
        return True

    def normalize_evidence(
        self,
        request: ExecutionRequest,
        output: Any,
    ) -> EvidenceEnvelope:
        return normalize_evidence(
            request=request,
            orchestrator_id=self.descriptor.orchestrator_id,
            adapter_version=self.descriptor.version,
            output=output,
        )
