from __future__ import annotations

import pytest

from metao.capacity import CapacityStatus
from metao.core import (
    ExecutionRequest,
    ExecutionStatus,
    ExecutorContract,
    HealthStatus,
    Mission,
)
from metao.adapters.harnessrouter_uhp import (
    HarnessRouterHttpError,
    HarnessRouterUhpAdapter,
)

HARNESS = "chrn_test"


def _request(execution_id: str = "exec-1", **context: object) -> ExecutionRequest:
    return ExecutionRequest(
        execution_id=execution_id,
        mission=Mission(mission_id="m-1", objective="Summarise README.md"),
        context=context,
    )


def _completed(text: str = "- a\n- b", **metadata: object) -> dict:
    return {
        "id": "resp_1",
        "status": "completed",
        "model": "claude-sonnet-4.6",
        "output": [
            {"type": "reasoning", "content": []},
            {
                "type": "message",
                "content": [{"type": "output_text", "text": text, "annotations": []}],
            },
        ],
        "usage": {"input_tokens": 1, "output_tokens": 2, "total_tokens": 3},
        "metadata": {"harness_id": HARNESS, **metadata},
    }


class FakeUhp:
    """Scripted UHP server: records calls and replays canned answers."""

    def __init__(self, *, create=None, polls=None, cancel_ok=True):
        self.calls: list[tuple[str, str, object]] = []
        self.create = create if create is not None else {"id": "resp_1", "status": "in_progress"}
        self.polls = list(polls) if polls is not None else [_completed()]
        self.cancel_ok = cancel_ok

    def __call__(self, method, path, body):
        self.calls.append((method, path, body))
        if method == "GET" and path == "/v1/uhp":
            return {"protocol": "uhp"}
        if method == "GET" and path == f"/v1/harnesses/{HARNESS}":
            return {"id": HARNESS}
        if method == "POST" and path == "/v1/responses":
            if isinstance(self.create, Exception):
                raise self.create
            return self.create
        if method == "GET" and path == "/v1/responses/resp_1":
            return self.polls.pop(0) if len(self.polls) > 1 else self.polls[0]
        if method == "POST" and path == "/v1/responses/resp_1/cancel":
            return {"id": "resp_1", "status": "cancelled"}
        raise AssertionError(f"unexpected call {method} {path}")

    def paths(self, method: str) -> list[str]:
        return [p for m, p, _ in self.calls if m == method]


def _adapter(fake: FakeUhp, **kwargs) -> HarnessRouterUhpAdapter:
    options = dict(
        base_url="https://hr.example/",
        harness_id=HARNESS,
        api_token="secret-token",
        transport=fake,
        sleep=lambda _s: None,
        poll_interval_s=0.01,
    )
    options.update(kwargs)
    return HarnessRouterUhpAdapter(**options)


def test_satisfies_executor_contract_and_descriptor() -> None:
    adapter = _adapter(FakeUhp())
    assert isinstance(adapter, ExecutorContract)
    assert adapter.descriptor.orchestrator_id == "harnessrouter"
    assert adapter.descriptor.metadata["harness_id"] == HARNESS
    assert adapter.descriptor.capabilities == frozenset({"agent"})


def test_success_polls_until_completed_and_returns_text() -> None:
    fake = FakeUhp(polls=[{"id": "resp_1", "status": "in_progress"}, _completed()])
    result = _adapter(fake).execute(_request())

    assert result.status is ExecutionStatus.SUCCEEDED
    assert result.output["result"] == "- a\n- b"
    assert result.output["response_id"] == "resp_1"
    assert result.output["model_fallback"] is False
    assert fake.paths("GET").count("/v1/responses/resp_1") == 2


def test_create_body_is_background_non_streaming_with_harness_and_trace() -> None:
    fake = FakeUhp(polls=[_completed()])
    _adapter(fake, model="claude-sonnet-4.6", timeout_seconds=300).execute(_request(subject="x"))

    _, _, body = next(c for c in fake.calls if c[1] == "/v1/responses")
    assert body["metadata"] == {"harness_id": HARNESS, "metao_execution_id": "exec-1"}
    assert body["background"] is True and body["stream"] is False
    assert body["model"] == "claude-sonnet-4.6"
    assert body["timeout_seconds"] == 300
    assert body["input"].startswith("Summarise README.md")
    assert '"subject":"x"' in body["input"]


def test_incomplete_is_not_success() -> None:
    fake = FakeUhp(polls=[{"id": "resp_1", "status": "incomplete",
                           "incomplete_details": {"reason": "max_step"}, "metadata": {}}])
    result = _adapter(fake).execute(_request())
    assert result.status is ExecutionStatus.FAILED
    assert "max_step" in result.error


def test_failed_task_carries_error_message() -> None:
    fake = FakeUhp(polls=[{"id": "resp_1", "status": "failed",
                           "error": {"type": "harness_error", "code": "harness_error",
                                     "message": "harness crashed"}, "metadata": {}}])
    result = _adapter(fake).execute(_request())
    assert result.status is ExecutionStatus.FAILED
    assert result.error == "harness crashed"


def test_model_substitution_fails_closed_by_default() -> None:
    fake = FakeUhp(polls=[_completed(model_fallback=True, requested_model="gpt-x")])
    result = _adapter(fake).execute(_request())
    assert result.status is ExecutionStatus.FAILED
    assert "substituted" in result.error


def test_model_substitution_allowed_is_reported_not_hidden() -> None:
    fake = FakeUhp(polls=[_completed(model_fallback=True, requested_model="gpt-x")])
    result = _adapter(fake, allow_model_fallback=True).execute(_request())
    assert result.status is ExecutionStatus.SUCCEEDED
    assert result.output["model_fallback"] is True


def test_ignored_fields_are_surfaced() -> None:
    fake = FakeUhp(polls=[_completed(ignored_fields=["tools"])])
    result = _adapter(fake).execute(_request())
    assert result.output["ignored_fields"] == ["tools"]


def test_missing_response_id_fails_without_polling() -> None:
    fake = FakeUhp(create={"status": "in_progress"})
    result = _adapter(fake).execute(_request())
    assert result.status is ExecutionStatus.FAILED
    assert fake.paths("GET") == []


@pytest.mark.parametrize(
    ("status", "expected"),
    [
        (401, CapacityStatus.AUTHENTICATION_FAILURE),
        (429, CapacityStatus.TEMPORARILY_RATE_LIMITED),
        (503, CapacityStatus.PROVIDER_UNAVAILABLE),
        (418, CapacityStatus.UNKNOWN),
    ],
)
def test_http_errors_map_to_capacity(status: int, expected: CapacityStatus) -> None:
    err = HarnessRouterHttpError(status, {"error": {"code": "x", "message": "m"}})
    fake = FakeUhp(create=err)
    result = _adapter(fake).execute(_request())
    assert result.status is ExecutionStatus.FAILED
    assert result.capacity_observation is not None
    assert result.capacity_observation.capacity_status is expected


def test_retry_after_becomes_recovery_time() -> None:
    err = HarnessRouterHttpError(429, {}, headers={"Retry-After": "30"})
    adapter = _adapter(FakeUhp(create=err), )
    result = adapter.execute(_request(created_at_epoch=1000.0))
    recovery = result.capacity_observation.recovery
    assert recovery is not None and recovery.recover_at_epoch == 1030.0


def test_client_error_is_not_a_capacity_signal() -> None:
    fake = FakeUhp(create=HarnessRouterHttpError(422, {"error": {"code": "model_unavailable"}}))
    result = _adapter(fake).execute(_request())
    assert result.status is ExecutionStatus.FAILED
    assert result.capacity_observation is None
    assert result.output["error_code"] == "model_unavailable"


def test_error_text_never_contains_token() -> None:
    fake = FakeUhp(create=HarnessRouterHttpError(401, {"error": {"message": "bad"}}))
    result = _adapter(fake).execute(_request())
    assert "secret-token" not in result.error


def test_transport_error_is_contained() -> None:
    fake = FakeUhp(create=OSError("connection refused"))
    result = _adapter(fake).execute(_request())
    assert result.status is ExecutionStatus.FAILED
    assert "OSError" in result.error
    assert "connection refused" not in result.error


def test_malformed_response_is_protocol_violation() -> None:
    fake = FakeUhp(polls=["not-an-object"])
    result = _adapter(fake).execute(_request())
    assert result.status is ExecutionStatus.FAILED
    assert "protocol violation" in result.error


def test_deadline_cancels_upstream_and_fails() -> None:
    now = [0.0]

    def clock() -> float:
        now[0] += 100.0
        return now[0]

    fake = FakeUhp(polls=[{"id": "resp_1", "status": "in_progress"}])
    result = _adapter(fake, clock=clock, max_wait_s=50.0).execute(_request())
    assert result.status is ExecutionStatus.FAILED
    assert "no terminal state" in result.error
    assert "/v1/responses/resp_1/cancel" in fake.paths("POST")


def test_cancel_before_dispatch_skips_upstream() -> None:
    fake = FakeUhp()
    adapter = _adapter(fake)
    adapter.cancel("exec-1")
    result = adapter.execute(_request())
    assert result.status is ExecutionStatus.CANCELLED
    assert fake.paths("POST") == []


def test_cancel_during_flight_reaches_upstream() -> None:
    fake = FakeUhp(polls=[{"id": "resp_1", "status": "in_progress"}])
    adapter = _adapter(fake)
    calls = {"n": 0}

    def sleep_then_cancel(_s: float) -> None:
        calls["n"] += 1
        if calls["n"] == 1:
            adapter.cancel("exec-1")
        elif calls["n"] == 2:
            fake.polls = [{"id": "resp_1", "status": "cancelled", "metadata": {}}]

    adapter._sleep = sleep_then_cancel
    result = adapter.execute(_request())
    assert "/v1/responses/resp_1/cancel" in fake.paths("POST")
    assert result.status is ExecutionStatus.CANCELLED


def test_health_unconfigured_token_is_unhealthy() -> None:
    adapter = HarnessRouterUhpAdapter(base_url="https://hr.example", harness_id=HARNESS)
    assert adapter.health().status is HealthStatus.UNHEALTHY


def test_health_missing_harness_is_unhealthy() -> None:
    def transport(method, path, body):
        if path == "/v1/uhp":
            return {}
        raise HarnessRouterHttpError(404, {"error": {"code": "harness_not_found"}})

    adapter = HarnessRouterUhpAdapter(base_url="https://hr.example", harness_id=HARNESS,
                                      api_token="t", transport=transport)
    assert adapter.health().status is HealthStatus.UNHEALTHY


def test_health_healthy_when_reachable_and_present() -> None:
    assert _adapter(FakeUhp()).health().status is HealthStatus.HEALTHY


def test_health_unreachable_is_unhealthy() -> None:
    def transport(method, path, body):
        raise OSError("down")

    adapter = HarnessRouterUhpAdapter(base_url="https://hr.example", harness_id=HARNESS,
                                      api_token="t", transport=transport)
    assert adapter.health().status is HealthStatus.UNHEALTHY


@pytest.mark.parametrize(
    "kwargs",
    [
        {"base_url": " ", "harness_id": HARNESS},
        {"base_url": "https://x", "harness_id": " "},
        {"base_url": "https://x", "harness_id": HARNESS, "model": " "},
        {"base_url": "https://x", "harness_id": HARNESS, "poll_interval_s": 0},
    ],
)
def test_invalid_configuration_is_rejected(kwargs: dict) -> None:
    with pytest.raises(ValueError):
        HarnessRouterUhpAdapter(**kwargs)
