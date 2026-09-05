import unittest

from metao.adapters.deepseek_http import (
    DeepSeekHttpError,
    DeepSeekHttpOrchestratorAdapter,
    normalize_evidence,
)
from metao.capacity import CapacityStatus, RecoveryEvidenceBasis
from metao.core import ExecutionRequest, ExecutionStatus, Mission
from metao.strategy import OrchestratorPoolState, OrchestratorStatus, select_orchestrator
from metao.supervision import apply_capacity_observation


class _ScriptedTransport:
    def __init__(self, result):
        self.result = result
        self.calls = []

    def __call__(self, method, path, body):
        self.calls.append((method, path, body))
        if isinstance(self.result, Exception):
            raise self.result
        return self.result


def _request(execution_id="deepseek-exec"):
    return ExecutionRequest(
        execution_id,
        Mission("deepseek-mission", "review the patch", frozenset({"agent"})),
        {
            "subject_id": "subject-deepseek",
            "subject_state_id": "state-deepseek",
            "verification_context_id": "verify-deepseek",
            "policy_bundle_id": "policy-deepseek",
            "created_at_epoch": 100.0,
            "z": 2,
            "a": "one",
        },
    )


def _response(*, content="ok", finish_reason="stop"):
    return {
        "id": "chatcmpl-test",
        "object": "chat.completion",
        "model": "deepseek-v4-flash",
        "choices": [
            {
                "index": 0,
                "finish_reason": finish_reason,
                "message": {"role": "assistant", "content": content},
            }
        ],
        "usage": {"prompt_tokens": 1, "completion_tokens": 1, "total_tokens": 2},
    }


def _adapter(result):
    return DeepSeekHttpOrchestratorAdapter(transport=_ScriptedTransport(result))


class DeepSeekHttpAdapterTests(unittest.TestCase):
    def test_success_uses_stateless_chat_completion_and_binds_evidence(self):
        transport = _ScriptedTransport(_response(content="review-ok"))
        adapter = DeepSeekHttpOrchestratorAdapter(transport=transport)
        request = _request()

        result = adapter.execute(request)

        self.assertIs(result.status, ExecutionStatus.SUCCEEDED)
        self.assertEqual(result.output["result"], "review-ok")
        self.assertEqual(result.output["finish_reason"], "stop")
        self.assertEqual(transport.calls[0][0:2], ("POST", "/chat/completions"))
        payload = transport.calls[0][2]
        self.assertEqual(payload["model"], "deepseek-v4-flash")
        self.assertFalse(payload["stream"])
        self.assertEqual(payload["messages"][0]["role"], "user")
        self.assertIn('"a":"one"', payload["messages"][0]["content"])
        self.assertIn('"z":2', payload["messages"][0]["content"])

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
        self.assertEqual(first.provenance_root, "deepseek:deepseek:deepseek-exec")

    def test_http_401_is_authentication_failure(self):
        result = _adapter(DeepSeekHttpError(401)).execute(_request())

        self.assertIs(result.status, ExecutionStatus.FAILED)
        self.assertIs(
            result.capacity_observation.capacity_status,
            CapacityStatus.AUTHENTICATION_FAILURE,
        )
        self.assertIsNone(result.capacity_observation.recovery)

    def test_http_402_is_credit_exhausted_and_fails_future_dispatch_closed(self):
        result = _adapter(DeepSeekHttpError(402)).execute(_request())

        observation = result.capacity_observation
        self.assertIsNotNone(observation)
        self.assertIs(observation.capacity_status, CapacityStatus.CREDIT_EXHAUSTED)
        self.assertIsNone(observation.recovery)

        pools = (
            OrchestratorPoolState(
                "deepseek",
                OrchestratorStatus.HEALTHY,
                frozenset({"agent"}),
            ),
        )
        supervised = apply_capacity_observation(
            pools,
            orchestrator_id="deepseek",
            observation=observation,
        )
        self.assertIsNone(select_orchestrator(supervised, now_epoch=100.0))

    def test_http_429_without_retry_after_does_not_invent_recovery(self):
        result = _adapter(DeepSeekHttpError(429)).execute(_request())

        observation = result.capacity_observation
        self.assertIs(
            observation.capacity_status,
            CapacityStatus.TEMPORARILY_RATE_LIMITED,
        )
        self.assertIsNone(observation.recovery)

    def test_http_429_with_retry_after_has_evidenced_recovery(self):
        result = _adapter(
            DeepSeekHttpError(429, headers={"Retry-After": "12"})
        ).execute(_request())

        recovery = result.capacity_observation.recovery
        self.assertEqual(recovery.recover_at_epoch, 112.0)
        self.assertIs(recovery.evidence_basis, RecoveryEvidenceBasis.ADAPTER_VERIFIED)
        self.assertEqual(
            recovery.evidence_ref,
            "deepseek:http:429:retry-after:12",
        )

    def test_http_503_is_provider_unavailable_without_recovery(self):
        result = _adapter(DeepSeekHttpError(503)).execute(_request())

        self.assertIs(
            result.capacity_observation.capacity_status,
            CapacityStatus.PROVIDER_UNAVAILABLE,
        )
        self.assertIsNone(result.capacity_observation.recovery)

    def test_invalid_request_is_execution_failure_not_capacity(self):
        result = _adapter(DeepSeekHttpError(422)).execute(_request())

        self.assertIs(result.status, ExecutionStatus.FAILED)
        self.assertIsNone(result.capacity_observation)

    def test_unrecognized_http_state_is_unknown_and_fails_closed(self):
        result = _adapter(DeepSeekHttpError(418)).execute(_request())

        self.assertIs(
            result.capacity_observation.capacity_status,
            CapacityStatus.UNKNOWN,
        )
        self.assertIsNone(result.capacity_observation.recovery)

    def test_insufficient_system_resource_finish_reason_is_provider_unavailable(self):
        result = _adapter(
            _response(content="", finish_reason="insufficient_system_resource")
        ).execute(_request())

        self.assertIs(result.status, ExecutionStatus.FAILED)
        self.assertIs(
            result.capacity_observation.capacity_status,
            CapacityStatus.PROVIDER_UNAVAILABLE,
        )
        self.assertIsNone(result.capacity_observation.recovery)

    def test_unknown_finish_reason_fails_closed_without_fabricated_capacity(self):
        result = _adapter(_response(finish_reason="new_finish_reason")).execute(_request())

        self.assertIs(result.status, ExecutionStatus.FAILED)
        self.assertIn("unsupported DeepSeek finish reason", result.error)
        self.assertIsNone(result.capacity_observation)

    def test_pre_dispatch_cancel_does_not_call_provider(self):
        transport = _ScriptedTransport(_response())
        adapter = DeepSeekHttpOrchestratorAdapter(transport=transport)
        adapter.cancel("deepseek-exec")

        result = adapter.execute(_request())

        self.assertIs(result.status, ExecutionStatus.CANCELLED)
        self.assertEqual(transport.calls, [])


if __name__ == "__main__":
    unittest.main()
