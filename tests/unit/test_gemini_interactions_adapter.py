import unittest

from metao.adapters.gemini_interactions import (
    GeminiHttpError,
    GeminiInteractionsOrchestratorAdapter,
    normalize_evidence,
)
from metao.capacity import CapacityStatus, RecoveryEvidenceBasis
from metao.core import ExecutionRequest, ExecutionStatus, Mission


class _ScriptedTransport:
    def __init__(self, steps):
        self.steps = list(steps)
        self.calls = []

    def __call__(self, method, path, body):
        self.calls.append((method, path, body))
        if not self.steps:
            raise AssertionError(f"unexpected Gemini call: {method} {path}")
        expected_method, expected_path, result = self.steps.pop(0)
        if (method, path) != (expected_method, expected_path):
            raise AssertionError(
                f"expected {expected_method} {expected_path}, got {method} {path}"
            )
        if isinstance(result, Exception):
            raise result
        return result

    def assert_complete(self):
        if self.steps:
            raise AssertionError(f"unconsumed Gemini transport steps: {self.steps!r}")


def _request(*, execution_id="gemini-exec", created_at_epoch=1768507200.0):
    context = {
        "obligation_id": "execution_result",
        "subject_id": "subject-gemini",
        "subject_state_id": "state-gemini",
        "verification_context_id": "verify-gemini",
        "policy_bundle_id": "policy-gemini",
        "verifier_id": "adapter-observer",
        "authority_id": "metao-runtime",
        "a": "one",
        "z": 2,
    }
    if created_at_epoch is not None:
        context["created_at_epoch"] = created_at_epoch
    return ExecutionRequest(
        execution_id,
        Mission("gemini-mission", "review the repository change", frozenset({"agent"})),
        context,
    )


def _interaction(*, interaction_id="int-1", status="completed", text="gemini-ok"):
    value = {"id": interaction_id, "status": status}
    if text is not None:
        value["steps"] = [
            {
                "type": "model_output",
                "content": [{"type": "text", "text": text}],
            }
        ]
    return value


def _error(code, *, status=429, headers=None):
    return GeminiHttpError(
        status,
        {"error": {"type": "provider_error", "code": code, "message": code}},
        headers=headers,
    )


def _adapter(transport, **kwargs):
    return GeminiInteractionsOrchestratorAdapter(
        transport=transport,
        max_polls=4,
        poll_interval_s=0.0,
        sleep_fn=lambda _: None,
        **kwargs,
    )


class GeminiInteractionsAdapterTests(unittest.TestCase):
    def test_model_interaction_completes_and_binds_deterministic_evidence(self):
        transport = _ScriptedTransport(
            [("POST", "/interactions", _interaction(text="model-ok"))]
        )
        adapter = _adapter(transport)
        request = _request()

        result = adapter.execute(request)

        self.assertIs(result.status, ExecutionStatus.SUCCEEDED)
        self.assertEqual(result.output["result"], "model-ok")
        payload = transport.calls[0][2]
        self.assertEqual(payload["model"], "gemini-3.8-flash")
        self.assertNotIn("agent", payload)
        self.assertNotIn("environment", payload)
        self.assertIn('"a":"one"', payload["input"])
        self.assertIn('"z":2', payload["input"])

        first = normalize_evidence(
            request=request,
            orchestrator_id=adapter.descriptor.orchestrator_id,
            adapter_version=adapter.descriptor.version,
            output=result.output,
        )
        second = normalize_evidence(
            request=request,
            orchestrator_id=adapter.descriptor.orchestrator_id,
            adapter_version=adapter.descriptor.version,
            output=result.output,
        )
        self.assertEqual(first, second)
        self.assertTrue(first.payload_digest)
        self.assertEqual(
            first.provenance_root,
            "gemini:gemini-interactions:gemini-exec",
        )
        transport.assert_complete()

    def test_antigravity_agent_uses_remote_environment_and_workflow_capability(self):
        transport = _ScriptedTransport(
            [("POST", "/interactions", _interaction(text="agent-ok"))]
        )
        adapter = _adapter(
            transport,
            target="antigravity-preview-05-2026",
            target_kind="agent",
        )

        result = adapter.execute(_request())

        self.assertIs(result.status, ExecutionStatus.SUCCEEDED)
        payload = transport.calls[0][2]
        self.assertEqual(payload["agent"], "antigravity-preview-05-2026")
        self.assertNotIn("model", payload)
        self.assertEqual(payload["environment"], "remote")
        self.assertIn("workflow", adapter.descriptor.capabilities)
        self.assertIn("agent", adapter.descriptor.capabilities)
        transport.assert_complete()

    def test_authentication_error_normalizes_without_recovery(self):
        transport = _ScriptedTransport(
            [("POST", "/interactions", _error("authentication", status=401))]
        )

        result = _adapter(transport).execute(_request())

        self.assertIs(result.status, ExecutionStatus.FAILED)
        self.assertIs(
            result.capacity_observation.capacity_status,
            CapacityStatus.AUTHENTICATION_FAILURE,
        )
        self.assertIsNone(result.capacity_observation.recovery)
        transport.assert_complete()

    def test_rate_limit_code_is_distinct_from_quota_and_does_not_invent_recovery(self):
        transport = _ScriptedTransport(
            [("POST", "/interactions", _error("rate_limit_exceeded"))]
        )

        result = _adapter(transport).execute(_request())

        self.assertIs(
            result.capacity_observation.capacity_status,
            CapacityStatus.TEMPORARILY_RATE_LIMITED,
        )
        self.assertIsNone(result.capacity_observation.recovery)
        transport.assert_complete()

    def test_quota_exceeded_uses_documented_next_midnight_pacific_reset(self):
        transport = _ScriptedTransport(
            [("POST", "/interactions", _error("quota_exceeded"))]
        )

        result = _adapter(transport).execute(
            _request(created_at_epoch=1768507200.0)
        )

        observation = result.capacity_observation
        self.assertIs(
            observation.capacity_status,
            CapacityStatus.TEMPORARILY_QUOTA_EXHAUSTED,
        )
        self.assertIsNotNone(observation.recovery)
        self.assertEqual(observation.recovery.recover_at_epoch, 1768550400.0)
        self.assertIs(
            observation.recovery.evidence_basis,
            RecoveryEvidenceBasis.PROVIDER_DOCUMENTATION,
        )
        self.assertEqual(
            observation.recovery.evidence_ref,
            "gemini:quota_exceeded:rpd-reset-midnight-pacific",
        )
        transport.assert_complete()

    def test_quota_exceeded_without_observation_time_stays_fail_closed_without_recovery(self):
        transport = _ScriptedTransport(
            [("POST", "/interactions", _error("quota_exceeded"))]
        )

        result = _adapter(transport).execute(_request(created_at_epoch=None))

        self.assertIs(
            result.capacity_observation.capacity_status,
            CapacityStatus.TEMPORARILY_QUOTA_EXHAUSTED,
        )
        self.assertIsNone(result.capacity_observation.recovery)
        transport.assert_complete()

    def test_quota_retry_after_overrides_documented_daily_reset_when_explicit(self):
        transport = _ScriptedTransport(
            [
                (
                    "POST",
                    "/interactions",
                    _error("quota_exceeded", headers={"Retry-After": "30"}),
                )
            ]
        )

        result = _adapter(transport).execute(_request(created_at_epoch=100.0))

        recovery = result.capacity_observation.recovery
        self.assertEqual(recovery.recover_at_epoch, 130.0)
        self.assertIs(recovery.evidence_basis, RecoveryEvidenceBasis.ADAPTER_VERIFIED)
        self.assertEqual(
            recovery.evidence_ref,
            "gemini:quota_exceeded:retry-after:30",
        )
        transport.assert_complete()

    def test_generic_http_429_without_machine_readable_code_is_unknown(self):
        transport = _ScriptedTransport(
            [("POST", "/interactions", GeminiHttpError(429, {"error": {"message": "limited"}}))]
        )

        result = _adapter(transport).execute(_request())

        self.assertIs(result.capacity_observation.capacity_status, CapacityStatus.UNKNOWN)
        self.assertIsNone(result.capacity_observation.recovery)
        transport.assert_complete()

    def test_service_unavailable_is_provider_unavailable_without_recovery(self):
        transport = _ScriptedTransport(
            [("POST", "/interactions", _error("service_unavailable", status=503))]
        )

        result = _adapter(transport).execute(_request())

        self.assertIs(
            result.capacity_observation.capacity_status,
            CapacityStatus.PROVIDER_UNAVAILABLE,
        )
        self.assertIsNone(result.capacity_observation.recovery)
        transport.assert_complete()

    def test_invalid_request_is_execution_failure_not_capacity(self):
        transport = _ScriptedTransport(
            [("POST", "/interactions", _error("invalid_request", status=400))]
        )

        result = _adapter(transport).execute(_request())

        self.assertIs(result.status, ExecutionStatus.FAILED)
        self.assertIsNone(result.capacity_observation)
        transport.assert_complete()

    def test_non_success_terminal_provider_statuses_do_not_imply_acceptance(self):
        for status in ("failed", "incomplete", "requires_action", "budget_exceeded"):
            with self.subTest(status=status):
                transport = _ScriptedTransport(
                    [("POST", "/interactions", _interaction(status=status, text=None))]
                )
                result = _adapter(transport).execute(_request())
                self.assertIs(result.status, ExecutionStatus.FAILED)
                self.assertIn(status, result.error)
                self.assertIsNone(result.capacity_observation)
                transport.assert_complete()

    def test_unknown_interaction_status_fails_closed(self):
        transport = _ScriptedTransport(
            [("POST", "/interactions", _interaction(status="new_status", text=None))]
        )

        result = _adapter(transport).execute(_request())

        self.assertIs(result.status, ExecutionStatus.FAILED)
        self.assertIn("unsupported Gemini interaction status", result.error)
        transport.assert_complete()

    def test_background_interaction_polls_until_completed(self):
        transport = _ScriptedTransport(
            [
                ("POST", "/interactions", _interaction(status="in_progress", text=None)),
                ("GET", "/interactions/int-1", _interaction(text="background-ok")),
            ]
        )
        adapter = _adapter(transport, background=True)

        result = adapter.execute(_request())

        self.assertIs(result.status, ExecutionStatus.SUCCEEDED)
        self.assertEqual(result.output["result"], "background-ok")
        self.assertTrue(transport.calls[0][2]["background"])
        transport.assert_complete()

    def test_pre_dispatch_cancel_never_calls_provider(self):
        transport = _ScriptedTransport([])
        adapter = _adapter(transport)
        adapter.cancel("gemini-exec")

        result = adapter.execute(_request())

        self.assertIs(result.status, ExecutionStatus.CANCELLED)
        self.assertEqual(transport.calls, [])
        transport.assert_complete()

    def test_inflight_cancel_delegates_provider_cancel_exactly_once(self):
        transport = _ScriptedTransport(
            [
                ("POST", "/interactions", _interaction(status="in_progress", text=None)),
                ("GET", "/interactions/int-1", _interaction(status="in_progress", text=None)),
                ("POST", "/interactions/int-1/cancel", _interaction(status="cancelled", text=None)),
            ]
        )
        holder = {}
        sleep_calls = {"count": 0}

        def cancel_after_first_poll(_):
            sleep_calls["count"] += 1
            if sleep_calls["count"] == 1:
                holder["adapter"].cancel("gemini-exec")

        adapter = GeminiInteractionsOrchestratorAdapter(
            transport=transport,
            background=True,
            max_polls=4,
            poll_interval_s=0.0,
            sleep_fn=cancel_after_first_poll,
        )
        holder["adapter"] = adapter

        result = adapter.execute(_request())

        self.assertIs(result.status, ExecutionStatus.CANCELLED)
        cancel_calls = [
            call for call in transport.calls if call[1] == "/interactions/int-1/cancel"
        ]
        self.assertEqual(len(cancel_calls), 1)
        transport.assert_complete()


if __name__ == "__main__":
    unittest.main()
