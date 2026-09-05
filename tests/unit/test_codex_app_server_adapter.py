import sys
import textwrap
import unittest

from metao.adapters.codex_app_server import (
    CodexAppServerOrchestratorAdapter,
    CodexAppServerRpcError,
    normalize_evidence,
)
from metao.adapters.codex_app_server_stdio import CodexAppServerStdioTransport
from metao.capacity import CapacityStatus
from metao.core import ExecutionRequest, ExecutionStatus, Mission


class _ScriptedRpc:
    def __init__(self, calls, notifications=()):
        self.expected = list(calls)
        self.notifications = list(notifications)
        self.calls = []
        self.notifies = []

    def request(self, method, params=None):
        self.calls.append((method, params))
        if not self.expected:
            raise AssertionError(f"unexpected Codex RPC call: {method}")
        expected_method, result = self.expected.pop(0)
        if method != expected_method:
            raise AssertionError(f"expected {expected_method}, got {method}")
        if isinstance(result, Exception):
            raise result
        return result

    def notify(self, method, params=None):
        self.notifies.append((method, params))

    def read_notification(self):
        if not self.notifications:
            raise AssertionError("unexpected Codex notification read")
        return self.notifications.pop(0)

    def assert_complete(self):
        if self.expected:
            raise AssertionError(f"unconsumed Codex calls: {self.expected!r}")
        if self.notifications:
            raise AssertionError(
                f"unconsumed Codex notifications: {self.notifications!r}"
            )


def _request(execution_id="codex-exec"):
    return ExecutionRequest(
        execution_id,
        Mission("codex-mission", "review and repair the repository", frozenset({"coding"})),
        {
            "obligation_id": "execution_result",
            "subject_id": "subject-codex",
            "subject_state_id": "state-codex",
            "verification_context_id": "verify-codex",
            "policy_bundle_id": "policy-codex",
            "verifier_id": "adapter-observer",
            "authority_id": "metao-runtime",
            "created_at_epoch": 100.0,
            "a": "one",
            "z": 2,
        },
    )


def _thread_result(thread_id="thr-1"):
    return {"thread": {"id": thread_id, "status": "idle"}}


def _turn(turn_id="turn-1", status="inProgress", *, items=None, error=None):
    value = {"id": turn_id, "status": status, "items": list(items or [])}
    if error is not None:
        value["error"] = error
    return value


def _completed_notification(turn):
    return {"method": "turn/completed", "params": {"turn": turn}}


def _adapter(rpc, **kwargs):
    return CodexAppServerOrchestratorAdapter(
        request_fn=rpc.request,
        notify_fn=rpc.notify,
        read_notification_fn=rpc.read_notification,
        max_notifications=16,
        **kwargs,
    )


class CodexAppServerAdapterTests(unittest.TestCase):
    def test_completed_turn_uses_thread_turn_boundary_and_binds_evidence(self):
        final = _turn(
            status="completed",
            items=[{"type": "agentMessage", "id": "item-1", "text": "codex-ok"}],
        )
        rpc = _ScriptedRpc(
            [
                ("initialize", {"userAgent": "codex-test"}),
                ("thread/start", _thread_result()),
                ("turn/start", {"turn": _turn()}),
            ],
            [_completed_notification(final)],
        )
        adapter = _adapter(rpc, cwd="/repo")
        request = _request()

        result = adapter.execute(request)

        self.assertIs(result.status, ExecutionStatus.SUCCEEDED)
        self.assertEqual(result.output["result"], "codex-ok")
        self.assertEqual(result.output["thread_id"], "thr-1")
        self.assertEqual(rpc.notifies, [("initialized", {})])
        thread_params = rpc.calls[1][1]
        self.assertEqual(thread_params["cwd"], "/repo")
        self.assertEqual(thread_params["approvalPolicy"], "on-request")
        self.assertEqual(thread_params["sandbox"], "workspace-write")
        turn_params = rpc.calls[2][1]
        self.assertEqual(turn_params["threadId"], "thr-1")
        self.assertIn('"a":"one"', turn_params["input"][0]["text"])
        self.assertIn('"z":2', turn_params["input"][0]["text"])

        first = normalize_evidence(
            request=request,
            orchestrator_id=adapter.descriptor.orchestrator_id,
            adapter_version=adapter.descriptor.version,
            output=result.output,
        )
        second = adapter.normalize_evidence(request, result.output)
        self.assertEqual(first, second)
        self.assertTrue(first.payload_digest)
        self.assertEqual(
            first.provenance_root,
            "codex-app-server:codex-app-server:codex-exec",
        )
        rpc.assert_complete()

    def test_interrupted_turn_is_cancelled_not_success(self):
        rpc = _ScriptedRpc(
            [
                ("initialize", {}),
                ("thread/start", _thread_result()),
                ("turn/start", {"turn": _turn()}),
            ],
            [_completed_notification(_turn(status="interrupted"))],
        )

        result = _adapter(rpc).execute(_request())

        self.assertIs(result.status, ExecutionStatus.CANCELLED)
        rpc.assert_complete()

    def test_rate_limit_is_temporary_without_invented_recovery(self):
        error = {"message": "rate limited", "codexErrorInfo": "rateLimitExceeded"}
        rpc = _ScriptedRpc(
            [
                ("initialize", {}),
                ("thread/start", _thread_result()),
                ("turn/start", {"turn": _turn()}),
            ],
            [_completed_notification(_turn(status="failed", error=error))],
        )

        result = _adapter(rpc).execute(_request())

        self.assertIs(result.status, ExecutionStatus.FAILED)
        self.assertIs(
            result.capacity_observation.capacity_status,
            CapacityStatus.TEMPORARILY_RATE_LIMITED,
        )
        self.assertIsNone(result.capacity_observation.recovery)
        rpc.assert_complete()

    def test_usage_limit_is_unknown_because_codex_collapses_distinct_causes(self):
        error = {"message": "usage limit", "codexErrorInfo": "usageLimitExceeded"}
        rpc = _ScriptedRpc(
            [
                ("initialize", {}),
                ("thread/start", _thread_result()),
                ("turn/start", {"turn": _turn()}),
            ],
            [_completed_notification(_turn(status="failed", error=error))],
        )

        result = _adapter(rpc).execute(_request())

        self.assertIs(result.capacity_observation.capacity_status, CapacityStatus.UNKNOWN)
        self.assertIsNone(result.capacity_observation.recovery)
        rpc.assert_complete()

    def test_model_overload_is_unknown_not_provider_wide_outage(self):
        error = {"message": "model at capacity", "codexErrorInfo": "serverOverloaded"}
        rpc = _ScriptedRpc(
            [
                ("initialize", {}),
                ("thread/start", _thread_result()),
                ("turn/start", {"turn": _turn()}),
            ],
            [_completed_notification(_turn(status="failed", error=error))],
        )

        result = _adapter(rpc).execute(_request())

        self.assertIs(result.capacity_observation.capacity_status, CapacityStatus.UNKNOWN)
        rpc.assert_complete()

    def test_internal_server_error_is_provider_unavailable(self):
        error = {"message": "upstream error", "codexErrorInfo": "internalServerError"}
        rpc = _ScriptedRpc(
            [
                ("initialize", {}),
                ("thread/start", _thread_result()),
                ("turn/start", {"turn": _turn()}),
            ],
            [_completed_notification(_turn(status="failed", error=error))],
        )

        result = _adapter(rpc).execute(_request())

        self.assertIs(
            result.capacity_observation.capacity_status,
            CapacityStatus.PROVIDER_UNAVAILABLE,
        )
        rpc.assert_complete()

    def test_structured_401_on_connection_failure_is_authentication_failure(self):
        error = {
            "message": "connection failed",
            "codexErrorInfo": {"httpConnectionFailed": {"httpStatusCode": 401}},
        }
        rpc = _ScriptedRpc(
            [
                ("initialize", {}),
                ("thread/start", _thread_result()),
                ("turn/start", {"turn": _turn()}),
            ],
            [_completed_notification(_turn(status="failed", error=error))],
        )

        result = _adapter(rpc).execute(_request())

        self.assertIs(
            result.capacity_observation.capacity_status,
            CapacityStatus.AUTHENTICATION_FAILURE,
        )
        rpc.assert_complete()

    def test_session_budget_failure_does_not_fabricate_capacity(self):
        error = {"message": "session budget", "codexErrorInfo": "sessionBudgetExceeded"}
        rpc = _ScriptedRpc(
            [
                ("initialize", {}),
                ("thread/start", _thread_result()),
                ("turn/start", {"turn": _turn()}),
            ],
            [_completed_notification(_turn(status="failed", error=error))],
        )

        result = _adapter(rpc).execute(_request())

        self.assertIs(result.status, ExecutionStatus.FAILED)
        self.assertIsNone(result.capacity_observation)
        rpc.assert_complete()

    def test_app_server_ingress_overload_is_unknown_not_provider_rate_limit(self):
        rpc = _ScriptedRpc(
            [
                (
                    "initialize",
                    CodexAppServerRpcError(-32001, "Server overloaded; retry later."),
                )
            ]
        )

        result = _adapter(rpc).execute(_request())

        self.assertIs(result.status, ExecutionStatus.FAILED)
        self.assertIs(result.capacity_observation.capacity_status, CapacityStatus.UNKNOWN)
        rpc.assert_complete()

    def test_cancel_before_dispatch_prevents_any_provider_call(self):
        rpc = _ScriptedRpc([])
        adapter = _adapter(rpc)
        self.assertTrue(adapter.cancel("cancel-me"))

        result = adapter.execute(_request(execution_id="cancel-me"))

        self.assertIs(result.status, ExecutionStatus.CANCELLED)
        self.assertEqual(rpc.calls, [])

    def test_real_stdio_framing_with_fake_app_server_subprocess(self):
        fake_server = textwrap.dedent(
            r'''
            import json
            import sys

            def send(value):
                sys.stdout.write(json.dumps(value, separators=(",", ":")) + "\n")
                sys.stdout.flush()

            for line in sys.stdin:
                message = json.loads(line)
                method = message.get("method")
                request_id = message.get("id")
                if method == "initialize" and request_id is not None:
                    send({"id": request_id, "result": {"userAgent": "fake-codex"}})
                elif method == "initialized":
                    pass
                elif method == "thread/start":
                    send({"id": request_id, "result": {"thread": {"id": "thr-sub", "status": "idle"}}})
                elif method == "turn/start":
                    send({"id": request_id, "result": {"turn": {"id": "turn-sub", "status": "inProgress", "items": []}}})
                    send({"method": "turn/completed", "params": {"turn": {"id": "turn-sub", "status": "completed", "items": [{"type": "agentMessage", "id": "a1", "text": "stdio-ok"}]}}})
                elif method == "turn/interrupt":
                    send({"id": request_id, "result": {}})
            '''
        )
        command = (sys.executable, "-u", "-c", fake_server)

        with CodexAppServerStdioTransport(command) as transport:
            adapter = CodexAppServerOrchestratorAdapter(
                request_fn=transport.request,
                notify_fn=transport.notify,
                read_notification_fn=transport.read_notification,
                max_notifications=16,
            )
            result = adapter.execute(_request())

        self.assertIs(result.status, ExecutionStatus.SUCCEEDED)
        self.assertEqual(result.output["result"], "stdio-ok")
        self.assertEqual(result.output["thread_id"], "thr-sub")


if __name__ == "__main__":
    unittest.main()
