import unittest

from metao.adapters.gemini_interactions import (
    GeminiHttpError,
    GeminiInteractionsOrchestratorAdapter,
)
from metao.capacity import CapacityStatus
from metao.core import ExecutionRequest, ExecutionStatus, Mission


class _FailingTransport:
    def __init__(self, error):
        self.error = error
        self.calls = 0

    def __call__(self, method, path, body):
        self.calls += 1
        self.method = method
        self.path = path
        self.body = body
        raise self.error


def _request():
    return ExecutionRequest(
        "gemini-api-key-invalid",
        Mission("gemini-auth-mission", "validate auth normalization", frozenset({"agent"})),
        {},
    )


def _result_for(body):
    transport = _FailingTransport(GeminiHttpError(400, body))
    adapter = GeminiInteractionsOrchestratorAdapter(
        transport=transport,
        max_polls=1,
        poll_interval_s=0.0,
        sleep_fn=lambda _: None,
    )
    result = adapter.execute(_request())
    if transport.calls != 1 or transport.method != "POST" or transport.path != "/interactions":
        raise AssertionError("unexpected Gemini transport interaction")
    return result


def _observed_invalid_key_body(*, reason="API_KEY_INVALID", domain="googleapis.com", type_name="type.googleapis.com/google.rpc.ErrorInfo"):
    return [
        {
            "error": {
                "code": 400,
                "status": "INVALID_ARGUMENT",
                "message": "message content must not drive classification",
                "details": [
                    {
                        "@type": type_name,
                        "reason": reason,
                        "domain": domain,
                        "metadata": {"service": "generativelanguage.googleapis.com"},
                    }
                ],
            }
        }
    ]


class GeminiApiKeyInvalidEvidenceTests(unittest.TestCase):
    def test_observed_google_error_info_api_key_invalid_is_authentication_failure(self):
        result = _result_for(_observed_invalid_key_body())

        self.assertIs(result.status, ExecutionStatus.FAILED)
        self.assertIsNotNone(result.capacity_observation)
        self.assertIs(
            result.capacity_observation.capacity_status,
            CapacityStatus.AUTHENTICATION_FAILURE,
        )
        self.assertIsNone(result.capacity_observation.recovery)

    def test_generic_invalid_argument_without_api_key_reason_is_not_authentication(self):
        result = _result_for(
            [{"error": {"code": 400, "status": "INVALID_ARGUMENT", "details": []}}]
        )

        self.assertIs(result.status, ExecutionStatus.FAILED)
        self.assertIsNone(result.capacity_observation)

    def test_api_key_invalid_in_wrong_domain_is_not_authentication(self):
        result = _result_for(_observed_invalid_key_body(domain="example.invalid"))

        self.assertIs(result.status, ExecutionStatus.FAILED)
        self.assertIsNone(result.capacity_observation)

    def test_free_form_api_key_invalid_message_is_not_authentication(self):
        result = _result_for(
            [
                {
                    "error": {
                        "code": 400,
                        "status": "INVALID_ARGUMENT",
                        "message": "API_KEY_INVALID",
                    }
                }
            ]
        )

        self.assertIs(result.status, ExecutionStatus.FAILED)
        self.assertIsNone(result.capacity_observation)

    def test_reason_requires_google_rpc_error_info_type(self):
        result = _result_for(
            _observed_invalid_key_body(type_name="type.googleapis.com/example.NotErrorInfo")
        )

        self.assertIs(result.status, ExecutionStatus.FAILED)
        self.assertIsNone(result.capacity_observation)


if __name__ == "__main__":
    unittest.main()
