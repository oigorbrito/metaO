"""Provider adapter for the Jules REST API.

The adapter keeps Jules-specific session, HTTP and artifact semantics outside
metaO Core. Scheduling, acceptance, trust admission and budget authority remain
owned by metaO. The production transport uses only the Python standard library;
tests may inject a deterministic transport without provider credentials.
"""

from __future__ import annotations

from hashlib import sha256
import json
from threading import Lock
from time import sleep
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


_JULES_ACTIVE_STATES = frozenset(
    {
        "QUEUED",
        "PLANNING",
        "AWAITING_PLAN_APPROVAL",
        "AWAITING_USER_FEEDBACK",
        "IN_PROGRESS",
        "PAUSED",
    }
)
_JULES_TERMINAL_STATES = frozenset({"COMPLETED", "FAILED"})


class JulesHttpError(RuntimeError):
    def __init__(
        self,
        status_code: int,
        body: Any = None,
        *,
        headers: Mapping[str, str] | None = None,
    ) -> None:
        super().__init__(f"Jules HTTP {status_code}")
        self.status_code = status_code
        self.body = body
        self.headers = dict(headers or {})


def _digest(value: Any) -> str:
    return sha256(
        json.dumps(value, sort_keys=True, default=str, separators=(",", ":")).encode()
    ).hexdigest()


def _recovery_from_headers(
    headers: Mapping[str, str],
    *,
    created_at_epoch: float,
) -> CapacityRecovery | None:
    retry_after_raw = None
    for key, value in headers.items():
        if key.lower() == "retry-after":
            retry_after_raw = value
            break
    try:
        retry_after_s = float(retry_after_raw)
    except (TypeError, ValueError):
        return None
    if retry_after_s < 0:
        return None
    return CapacityRecovery(
        recover_at_epoch=created_at_epoch + retry_after_s,
        evidence_basis=RecoveryEvidenceBasis.ADAPTER_VERIFIED,
        evidence_ref=f"jules:http:429:retry-after:{retry_after_raw}",
    )


def _capacity_observation_from_http_error(
    exc: JulesHttpError,
    *,
    created_at_epoch: float,
) -> CapacityObservation | None:
    if exc.status_code == 401:
        return CapacityObservation(CapacityStatus.AUTHENTICATION_FAILURE)
    if exc.status_code == 403:
        return CapacityObservation(CapacityStatus.UNKNOWN)
    if exc.status_code == 429:
        return CapacityObservation(
            CapacityStatus.TEMPORARILY_RATE_LIMITED,
            _recovery_from_headers(exc.headers, created_at_epoch=created_at_epoch),
        )
    if exc.status_code in {500, 503}:
        return CapacityObservation(CapacityStatus.PROVIDER_UNAVAILABLE)
    return None


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
        provenance_root=f"jules:{orchestrator_id}:{request.execution_id}",
        authority_id=str(context.get("authority_id", "metao-runtime")),
        passed=True,
        created_at_epoch=float(context.get("created_at_epoch", 0.0)),
        expires_at_epoch=context.get("expires_at_epoch"),
    )


class JulesHttpOrchestratorAdapter:
    """Map a Jules coding session into the provider-neutral runtime contract."""

    def __init__(
        self,
        *,
        api_key: str = "",
        source: str | None = None,
        starting_branch: str = "main",
        base_url: str = "https://jules.googleapis.com/v1alpha",
        orchestrator_id: str = "jules",
        version: str = "v1alpha",
        require_plan_approval: bool = True,
        max_polls: int = 120,
        poll_interval_s: float = 1.0,
        transport: Callable[[str, str, Any | None], Any] | None = None,
        sleep_fn: Callable[[float], None] = sleep,
    ) -> None:
        if max_polls <= 0:
            raise ValueError("max_polls must be positive")
        if poll_interval_s < 0:
            raise ValueError("poll_interval_s must be non-negative")
        self._api_key = api_key
        self._source = source
        self._starting_branch = starting_branch
        self._base_url = base_url.rstrip("/")
        self._require_plan_approval = require_plan_approval
        self._max_polls = max_polls
        self._poll_interval_s = poll_interval_s
        self._transport = transport
        self._sleep_fn = sleep_fn
        self._cancelled: set[str] = set()
        self._sessions: dict[str, str] = {}
        self._lock = Lock()

        capabilities = {"workflow", "agent", "artifacts"}
        if source:
            capabilities.add("repository")
        self._descriptor = OrchestratorDescriptor(
            orchestrator_id=orchestrator_id,
            version=version,
            capabilities=frozenset(capabilities),
            metadata={"adapter": "jules-rest", "api_version": "v1alpha"},
        )

    @property
    def descriptor(self) -> OrchestratorDescriptor:
        return self._descriptor

    def health(self) -> HealthReport:
        transport_ready = self._transport is not None or bool(self._api_key.strip())
        if transport_ready:
            return HealthReport(HealthStatus.HEALTHY, "Jules transport configured")
        return HealthReport(HealthStatus.UNHEALTHY, "Jules API key is not configured")

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
            with urllib.request.urlopen(request, timeout=30) as response:
                raw = response.read().decode("utf-8")
                if not raw:
                    return None
                return json.loads(raw)
        except urllib.error.HTTPError as exc:
            raw = exc.read().decode("utf-8", errors="replace")
            try:
                parsed: Any = json.loads(raw) if raw else None
            except json.JSONDecodeError:
                parsed = raw
            raise JulesHttpError(
                exc.code,
                parsed,
                headers=dict(exc.headers.items()),
            ) from exc

    def _request(self, method: str, path: str, body: Any | None = None) -> Any:
        transport = self._transport or self._default_transport
        return transport(method, path, body)

    @staticmethod
    def _canonical_session_name(value: Any) -> str:
        name = str(value or "")
        parts = name.split("/")
        if len(parts) != 2 or parts[0] != "sessions" or not parts[1]:
            raise RuntimeError("Jules returned an invalid session resource name")
        return name

    def _session_name(self, execution_id: str) -> str:
        with self._lock:
            try:
                return self._sessions[execution_id]
            except KeyError as exc:
                raise KeyError(f"no Jules session for execution: {execution_id}") from exc

    def start_session(self, request: ExecutionRequest) -> str:
        with self._lock:
            existing = self._sessions.get(request.execution_id)
            cancelled = request.execution_id in self._cancelled
        if existing is not None:
            return existing
        if cancelled:
            raise RuntimeError("execution was cancelled before Jules session creation")

        payload: dict[str, Any] = {
            "prompt": request.mission.objective,
            "title": request.mission.mission_id,
            "requirePlanApproval": self._require_plan_approval,
        }
        if self._source:
            payload["sourceContext"] = {
                "source": self._source,
                "githubRepoContext": {"startingBranch": self._starting_branch},
            }

        created = self._request("POST", "/sessions", payload)
        if not isinstance(created, Mapping):
            raise RuntimeError("Jules session creation returned a non-object response")
        session_name = self._canonical_session_name(created.get("name"))
        with self._lock:
            self._sessions[request.execution_id] = session_name
            cancelled = request.execution_id in self._cancelled
        if cancelled:
            self._request("DELETE", f"/{session_name}")
        return session_name

    def get_session(self, execution_id: str) -> Mapping[str, Any]:
        session_name = self._session_name(execution_id)
        item = self._request("GET", f"/{session_name}")
        if not isinstance(item, Mapping):
            raise RuntimeError("Jules session lookup returned a non-object response")
        return item

    def list_activities(self, execution_id: str) -> tuple[Mapping[str, Any], ...]:
        session_name = self._session_name(execution_id)
        payload = self._request("GET", f"/{session_name}/activities?pageSize=100")
        if not isinstance(payload, Mapping):
            raise RuntimeError("Jules activities lookup returned a non-object response")
        activities = payload.get("activities", ())
        if not isinstance(activities, list):
            raise RuntimeError("Jules activities response contains invalid activities")
        if not all(isinstance(item, Mapping) for item in activities):
            raise RuntimeError("Jules activities response contains a non-object activity")
        return tuple(activities)

    def approve_plan(self, execution_id: str) -> None:
        session_name = self._session_name(execution_id)
        self._request("POST", f"/{session_name}:approvePlan", {})

    def send_message(self, execution_id: str, prompt: str) -> None:
        if not prompt.strip():
            raise ValueError("Jules message prompt must be non-empty")
        session_name = self._session_name(execution_id)
        self._request("POST", f"/{session_name}:sendMessage", {"prompt": prompt})

    def execute(self, request: ExecutionRequest) -> ExecutionResult:
        with self._lock:
            if request.execution_id in self._cancelled:
                return ExecutionResult(
                    request.execution_id,
                    self.descriptor.orchestrator_id,
                    ExecutionStatus.CANCELLED,
                )

        try:
            self.start_session(request)
            for _ in range(self._max_polls):
                with self._lock:
                    if request.execution_id in self._cancelled:
                        return ExecutionResult(
                            request.execution_id,
                            self.descriptor.orchestrator_id,
                            ExecutionStatus.CANCELLED,
                        )
                session = self.get_session(request.execution_id)
                state = str(session.get("state", "")).upper()
                if state == "COMPLETED":
                    activities = self.list_activities(request.execution_id)
                    return ExecutionResult(
                        request.execution_id,
                        self.descriptor.orchestrator_id,
                        ExecutionStatus.SUCCEEDED,
                        output={
                            "session": dict(session),
                            "activities": [dict(item) for item in activities],
                        },
                    )
                if state == "FAILED":
                    return ExecutionResult(
                        request.execution_id,
                        self.descriptor.orchestrator_id,
                        ExecutionStatus.FAILED,
                        output={"session": dict(session)},
                        error="Jules session failed",
                    )
                if state not in _JULES_ACTIVE_STATES:
                    return ExecutionResult(
                        request.execution_id,
                        self.descriptor.orchestrator_id,
                        ExecutionStatus.FAILED,
                        output={"session": dict(session)},
                        error=f"unsupported Jules session state: {state or '<empty>'}",
                    )
                self._sleep_fn(self._poll_interval_s)

            return ExecutionResult(
                request.execution_id,
                self.descriptor.orchestrator_id,
                ExecutionStatus.FAILED,
                error="Jules session did not reach a terminal state within the polling bound",
            )
        except JulesHttpError as exc:
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
            session_name = self._sessions.get(execution_id)
        if session_name is not None:
            self._request("DELETE", f"/{session_name}")


__all__ = [
    "JulesHttpError",
    "JulesHttpOrchestratorAdapter",
    "normalize_evidence",
]
