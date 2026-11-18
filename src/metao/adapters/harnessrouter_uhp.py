"""HarnessRouter adapter for metaO, speaking the Unified Harness Protocol (UHP).

A HarnessRouter server puts many agent harnesses (Codex, Claude Code, Pi, ...) behind one
HTTP contract. This adapter lets metaO use that server as one more executor. It owns only
transport and translation: policy, budget, admission and acceptance stay in metaO.

Protocol reference: UHP 2026-09-12 (``POST /v1/responses``, ``GET /v1/responses/{id}``,
``POST /v1/responses/{id}/cancel``, ``GET /v1/harnesses/{id}``, ``GET /v1/uhp``).

Fail-closed rules applied here:

- a task is ``SUCCEEDED`` only when UHP reports ``completed``;
- ``incomplete``, ``failed`` and ``cancelled`` map to a non-success ``ExecutionStatus``;
- a silently substituted model (``metadata.model_fallback``) is a failure unless the caller
  explicitly allowed it, because the result would not be the work that was asked for.
"""

from __future__ import annotations

from hashlib import sha256
import json
import time
from threading import Lock
from typing import Any, Callable, Mapping
import urllib.error
import urllib.request

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

PROTOCOL_VERSION = "2026-09-12"
_TERMINAL_STATES = frozenset({"completed", "failed", "incomplete", "cancelled"})

Transport = Callable[[str, str, Any | None], Any]


class HarnessRouterHttpError(RuntimeError):
    """A non-2xx UHP response. The message never carries the credential."""

    def __init__(
        self,
        status_code: int,
        body: Any = None,
        *,
        headers: Mapping[str, str] | None = None,
    ) -> None:
        code = _error_code(body)
        super().__init__(f"HarnessRouter HTTP {status_code}" + (f" ({code})" if code else ""))
        self.status_code = status_code
        self.body = body
        self.headers = dict(headers or {})


def _error_code(body: Any) -> str:
    if isinstance(body, Mapping):
        error = body.get("error")
        if isinstance(error, Mapping) and isinstance(error.get("code"), str):
            return error["code"]
    return ""


def _error_message(body: Any) -> str:
    if isinstance(body, Mapping):
        error = body.get("error")
        if isinstance(error, Mapping) and isinstance(error.get("message"), str):
            return error["message"]
    return ""


def _digest(value: Any) -> str:
    return sha256(
        json.dumps(value, sort_keys=True, default=str, separators=(",", ":")).encode()
    ).hexdigest()


def _header(headers: Mapping[str, str], name: str) -> str | None:
    for key, value in headers.items():
        if key.lower() == name.lower():
            return value
    return None


def _capacity_observation_from_http_error(
    exc: HarnessRouterHttpError,
    *,
    created_at_epoch: float,
) -> CapacityObservation | None:
    status = exc.status_code
    if status == 401:
        return CapacityObservation(CapacityStatus.AUTHENTICATION_FAILURE)
    if status == 429:
        recovery = None
        raw = _header(exc.headers, "Retry-After")
        try:
            delay_s = float(raw) if raw is not None else -1.0
        except ValueError:
            delay_s = -1.0
        if delay_s >= 0:
            recovery = CapacityRecovery(
                recover_at_epoch=created_at_epoch + delay_s,
                evidence_basis=RecoveryEvidenceBasis.PROVIDER_API,
                evidence_ref=f"harnessrouter:http:429:retry-after:{raw}",
            )
        return CapacityObservation(CapacityStatus.TEMPORARILY_RATE_LIMITED, recovery)
    if status >= 500:
        return CapacityObservation(CapacityStatus.PROVIDER_UNAVAILABLE)
    if status in {400, 403, 404, 409, 413, 422}:
        # The request or its target was wrong; the executor itself is not out of capacity.
        return None
    return CapacityObservation(CapacityStatus.UNKNOWN)


class HarnessRouterUhpAdapter:
    """Run one mission as a UHP task on a configured HarnessRouter harness."""

    def __init__(
        self,
        *,
        base_url: str,
        harness_id: str,
        api_token: str = "",
        model: str | None = None,
        allow_model_fallback: bool = False,
        store: bool = True,
        orchestrator_id: str = "harnessrouter",
        version: str = "v1",
        timeout_seconds: int | None = None,
        poll_interval_s: float = 2.0,
        max_wait_s: float = 1800.0,
        http_timeout_s: float = 60.0,
        transport: Transport | None = None,
        clock: Callable[[], float] = time.monotonic,
        sleep: Callable[[float], None] = time.sleep,
    ) -> None:
        if not base_url.strip():
            raise ValueError("HarnessRouter base_url must be non-empty")
        if not harness_id.strip():
            raise ValueError("HarnessRouter harness_id must be non-empty")
        if model is not None and not model.strip():
            raise ValueError("HarnessRouter model must be non-empty when provided")
        if poll_interval_s <= 0 or max_wait_s <= 0:
            raise ValueError("poll interval and max wait must be positive")
        self._base_url = base_url.rstrip("/")
        self._harness_id = harness_id
        self._api_token = api_token
        self._model = model
        self._allow_model_fallback = allow_model_fallback
        self._store = store
        self._timeout_seconds = timeout_seconds
        self._poll_interval_s = poll_interval_s
        self._max_wait_s = max_wait_s
        self._http_timeout_s = http_timeout_s
        self._transport = transport
        self._clock = clock
        self._sleep = sleep
        self._lock = Lock()
        # execution_id -> UHP response id, known once the task has been accepted.
        self._responses: dict[str, str] = {}
        self._cancelled: set[str] = set()
        self._descriptor = OrchestratorDescriptor(
            orchestrator_id=orchestrator_id,
            version=version,
            capabilities=frozenset({"agent"}),
            metadata={
                "adapter": "harnessrouter-uhp",
                "protocol_version": PROTOCOL_VERSION,
                "harness_id": harness_id,
                **({"model": model} if model else {}),
            },
        )

    @property
    def descriptor(self) -> OrchestratorDescriptor:
        return self._descriptor

    # ----- transport -------------------------------------------------------

    def _default_transport(self, method: str, path: str, body: Any | None) -> Any:
        data = None if body is None else json.dumps(body).encode("utf-8")
        headers = {"Content-Type": "application/json", "Accept": "application/json"}
        if self._api_token:
            headers["Authorization"] = f"Bearer {self._api_token}"
        request = urllib.request.Request(
            self._base_url + path, data=data, method=method, headers=headers
        )
        try:
            with urllib.request.urlopen(request, timeout=self._http_timeout_s) as response:
                raw = response.read().decode("utf-8")
                return json.loads(raw) if raw else None
        except urllib.error.HTTPError as exc:
            raw = exc.read().decode("utf-8", errors="replace")
            try:
                parsed: Any = json.loads(raw) if raw else None
            except json.JSONDecodeError:
                parsed = None
            raise HarnessRouterHttpError(exc.code, parsed, headers=dict(exc.headers.items())) from exc

    def _request(self, method: str, path: str, body: Any | None = None) -> Any:
        transport = self._transport or self._default_transport
        return transport(method, path, body)

    # ----- ExecutorContract ------------------------------------------------

    def health(self) -> HealthReport:
        if self._transport is None and not self._api_token.strip():
            return HealthReport(HealthStatus.UNHEALTHY, "HarnessRouter API token is not configured")
        try:
            self._request("GET", "/v1/uhp")
        except (HarnessRouterHttpError, OSError) as exc:
            return HealthReport(HealthStatus.UNHEALTHY, f"HarnessRouter unreachable: {exc}")
        try:
            self._request("GET", f"/v1/harnesses/{self._harness_id}")
        except HarnessRouterHttpError as exc:
            if exc.status_code == 404:
                return HealthReport(HealthStatus.UNHEALTHY, "configured harness not found")
            return HealthReport(HealthStatus.DEGRADED, f"harness check failed: {exc}")
        except OSError as exc:
            return HealthReport(HealthStatus.DEGRADED, f"harness check failed: {exc}")
        return HealthReport(HealthStatus.HEALTHY, "HarnessRouter reachable, harness present")

    def _input_text(self, request: ExecutionRequest) -> str:
        text = request.mission.objective
        if request.context:
            text += "\n\nContext:\n" + json.dumps(
                dict(request.context), sort_keys=True, default=str, separators=(",", ":")
            )
        return text

    def _create_body(self, request: ExecutionRequest) -> dict[str, Any]:
        body: dict[str, Any] = {
            "input": self._input_text(request),
            "background": True,
            "stream": False,
            "store": self._store,
            "metadata": {
                "harness_id": self._harness_id,
                "metao_execution_id": request.execution_id,
            },
        }
        if self._model is not None:
            body["model"] = self._model
        if self._timeout_seconds is not None:
            body["timeout_seconds"] = self._timeout_seconds
        return body

    @staticmethod
    def _output_text(response: Mapping[str, Any]) -> str:
        parts: list[str] = []
        for item in response.get("output") or []:
            if not isinstance(item, Mapping) or item.get("type") != "message":
                continue
            for part in item.get("content") or []:
                if isinstance(part, Mapping) and part.get("type") == "output_text":
                    text = part.get("text")
                    if isinstance(text, str):
                        parts.append(text)
        return "".join(parts)

    def _result_for(self, execution_id: str, response: Mapping[str, Any]) -> ExecutionResult:
        orchestrator_id = self._descriptor.orchestrator_id
        state = str(response.get("status", ""))
        metadata = response.get("metadata") if isinstance(response.get("metadata"), Mapping) else {}
        output: dict[str, Any] = {
            "response_id": response.get("id"),
            "model": response.get("model"),
            "usage": response.get("usage"),
            "ignored_fields": list(metadata.get("ignored_fields") or []),
        }

        if state == "completed":
            if metadata.get("model_fallback") and not self._allow_model_fallback:
                return ExecutionResult(
                    execution_id, orchestrator_id, ExecutionStatus.FAILED,
                    output=output,
                    error=(
                        f"model substituted: requested {metadata.get('requested_model')!r}, "
                        f"served {response.get('model')!r}"
                    ),
                )
            output["result"] = self._output_text(response)
            output["model_fallback"] = bool(metadata.get("model_fallback", False))
            return ExecutionResult(
                execution_id, orchestrator_id, ExecutionStatus.SUCCEEDED, output=output
            )
        if state == "cancelled":
            return ExecutionResult(execution_id, orchestrator_id, ExecutionStatus.CANCELLED, output=output)
        if state == "incomplete":
            reason = (response.get("incomplete_details") or {}).get("reason", "unknown")
            return ExecutionResult(
                execution_id, orchestrator_id, ExecutionStatus.FAILED, output=output,
                error=f"task incomplete: {reason}",
            )
        error = response.get("error") or {}
        message = error.get("message") if isinstance(error, Mapping) else None
        return ExecutionResult(
            execution_id, orchestrator_id, ExecutionStatus.FAILED, output=output,
            error=message or f"task ended in state {state or '<empty>'}",
        )

    def _cancel_upstream(self, response_id: str) -> None:
        try:
            self._request("POST", f"/v1/responses/{response_id}/cancel")
        except (HarnessRouterHttpError, OSError):
            # Cancelling a terminal task succeeds by spec; any other failure is retried by
            # the caller's next cancel or ends in the deadline path below.
            pass

    def execute(self, request: ExecutionRequest) -> ExecutionResult:
        execution_id = request.execution_id
        orchestrator_id = self._descriptor.orchestrator_id
        with self._lock:
            if execution_id in self._cancelled:
                return ExecutionResult(execution_id, orchestrator_id, ExecutionStatus.CANCELLED)

        created_at = float(request.context.get("created_at_epoch", 0.0))
        try:
            accepted = self._request("POST", "/v1/responses", self._create_body(request))
            response_id = accepted.get("id") if isinstance(accepted, Mapping) else None
            if not isinstance(response_id, str) or not response_id:
                return ExecutionResult(
                    execution_id, orchestrator_id, ExecutionStatus.FAILED,
                    error="HarnessRouter accepted the task without a response id",
                )
            with self._lock:
                self._responses[execution_id] = response_id
                cancel_now = execution_id in self._cancelled
            if cancel_now:
                self._cancel_upstream(response_id)

            deadline = self._clock() + self._max_wait_s
            while True:
                response = self._request("GET", f"/v1/responses/{response_id}")
                if not isinstance(response, Mapping):
                    raise RuntimeError("HarnessRouter returned a non-object response")
                if str(response.get("status", "")) in _TERMINAL_STATES:
                    return self._result_for(execution_id, response)
                if self._clock() >= deadline:
                    self._cancel_upstream(response_id)
                    return ExecutionResult(
                        execution_id, orchestrator_id, ExecutionStatus.FAILED,
                        error=f"no terminal state after {self._max_wait_s:g}s; cancel requested",
                    )
                self._sleep(self._poll_interval_s)
        except HarnessRouterHttpError as exc:
            return ExecutionResult(
                execution_id, orchestrator_id, ExecutionStatus.FAILED,
                output={"error_code": _error_code(exc.body), "error_message": _error_message(exc.body)},
                error=str(exc),
                capacity_observation=_capacity_observation_from_http_error(
                    exc, created_at_epoch=created_at
                ),
            )
        except OSError as exc:
            return ExecutionResult(
                execution_id, orchestrator_id, ExecutionStatus.FAILED,
                error=f"HarnessRouter transport error: {type(exc).__name__}",
            )
        except (ValueError, RuntimeError) as exc:
            # Malformed JSON or a non-object body: a protocol violation, not a crash.
            return ExecutionResult(
                execution_id, orchestrator_id, ExecutionStatus.FAILED,
                error=f"HarnessRouter protocol violation: {exc}",
            )
        finally:
            with self._lock:
                self._responses.pop(execution_id, None)

    def cancel(self, execution_id: str) -> None:
        with self._lock:
            self._cancelled.add(execution_id)
            response_id = self._responses.get(execution_id)
        if response_id is not None:
            self._cancel_upstream(response_id)


__all__ = [
    "HarnessRouterHttpError",
    "HarnessRouterUhpAdapter",
    "PROTOCOL_VERSION",
]
