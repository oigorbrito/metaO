import unittest

from metao.adapters.jules_http import (
    JulesHttpError,
    JulesHttpOrchestratorAdapter,
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
            raise AssertionError(f"unexpected Jules call: {method} {path}")
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
            raise AssertionError(f"unconsumed Jules transport steps: {self.steps!r}")


def _request(execution_id="jules-exec"):
    return ExecutionRequest(
        execution_id,
        Mission("jules-mission", "add deterministic tests", frozenset({"workflow"})),
        {
            "obligation_id": "execution_result",
            "subject_id": "subject-jules",
            "subject_state_id": "state-jules",
            "verification_context_id": "verify-jules",
            "policy_bundle_id": "policy-jules",
            "verifier_id": "adapter-observer",
            "authority_id": "metao-runtime",
            "created_at_epoch": 100.0,
        },
    )


def _adapter(transport, **kwargs):
    return JulesHttpOrchestratorAdapter(
        source="sources/github/oigorbrito/metaO",
        starting_branch="main",
        transport=transport,
        max_polls=3,
        poll_interval_s=0.0,
        sleep_fn=lambda _: None,
        **kwargs,
    )


class JulesHttpAdapterTests(unittest.TestCase):
    def test_completed_session_binds_outputs_activities_and_evidence(self):
        transport = _ScriptedTransport(
            [
                ("POST", "/sessions", {"name": "sessions/abc", "state": "QUEUED"}),
                (
                    "GET",
                    "/sessions/abc",
                    {
                        "name": "sessions/abc",
                        "state": "COMPLETED",
                        "outputs": [
                            {
                                "pullRequest": {
                                    "url": "https://github.com/oigorbrito/metaO/pull/999",
                                    "title": "result",
                                }
                            }
                        ],
                    },
                ),
                (
                    "GET",
                    "/sessions/abc/activities?pageSize=100",
                    {
                        "activities": [
                            {
                                "id": "act-1",
                                "artifacts": [
                                    {"changeSet": {"gitPatch": "diff --git a/a b/a"}}
                                ],
                            }
                        ]
                    },
                ),
            ]
        )
        adapter = _adapter(transport)
        request = _request()

        result = adapter.execute(request)

        self.assertIs(result.status, ExecutionStatus.SUCCEEDED)
        self.assertEqual(result.output["session"]["state"], "COMPLETED")
        self.assertEqual(result.output["activities"][0]["id"], "act-1")
        created_body = transport.calls[0][2]
        self.assertTrue(created_body["requirePlanApproval"])
        self.assertNotIn("automationMode", created_body)
        self.assertEqual(
            created_body["sourceContext"]["githubRepoContext"]["startingBranch"],
            "main",
        )

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
        self.assertEqual(first.provenance_root, "jules:jules:jules-exec")
        transport.assert_complete()

    def test_failed_session_is_execution_failure_not_acceptance(self):
        transport = _ScriptedTransport(
            [
                ("POST", "/sessions", {"name": "sessions/fail"}),
                (
                    "GET",
                    "/sessions/fail",
                    {"name": "sessions/fail", "state": "FAILED"},
                ),
            ]
        )

        result = _adapter(transport).execute(_request())

        self.assertIs(result.status, ExecutionStatus.FAILED)
        self.assertEqual(result.error, "Jules session failed")
        self.assertIsNone(result.capacity_observation)
        transport.assert_complete()

    def test_unknown_session_state_fails_closed(self):
        transport = _ScriptedTransport(
            [
                ("POST", "/sessions", {"name": "sessions/new-state"}),
                (
                    "GET",
                    "/sessions/new-state",
                    {"name": "sessions/new-state", "state": "NEW_PROVIDER_STATE"},
                ),
            ]
        )

        result = _adapter(transport).execute(_request())

        self.assertIs(result.status, ExecutionStatus.FAILED)
        self.assertIn("unsupported Jules session state", result.error)
        transport.assert_complete()

    def test_http_401_normalizes_authentication_failure(self):
        transport = _ScriptedTransport(
            [("POST", "/sessions", JulesHttpError(401, {"error": {"status": "UNAUTHENTICATED"}}))]
        )

        result = _adapter(transport).execute(_request())

        self.assertIs(result.status, ExecutionStatus.FAILED)
        self.assertIsNotNone(result.capacity_observation)
        self.assertIs(
            result.capacity_observation.capacity_status,
            CapacityStatus.AUTHENTICATION_FAILURE,
        )
        self.assertIsNone(result.capacity_observation.recovery)
        transport.assert_complete()

    def test_http_429_uses_retry_after_only_when_evidenced(self):
        transport = _ScriptedTransport(
            [
                (
                    "POST",
                    "/sessions",
                    JulesHttpError(
                        429,
                        {"error": {"status": "RESOURCE_EXHAUSTED"}},
                        headers={"Retry-After": "10"},
                    ),
                )
            ]
        )

        result = _adapter(transport).execute(_request())

        observation = result.capacity_observation
        self.assertIsNotNone(observation)
        self.assertIs(
            observation.capacity_status,
            CapacityStatus.TEMPORARILY_RATE_LIMITED,
        )
        self.assertEqual(observation.recovery.recover_at_epoch, 110.0)
        self.assertIs(
            observation.recovery.evidence_basis,
            RecoveryEvidenceBasis.ADAPTER_VERIFIED,
        )
        self.assertEqual(
            observation.recovery.evidence_ref,
            "jules:http:429:retry-after:10",
        )
        transport.assert_complete()

    def test_http_500_normalizes_provider_unavailable_without_recovery(self):
        transport = _ScriptedTransport(
            [("POST", "/sessions", JulesHttpError(500, {"error": {"status": "INTERNAL"}}))]
        )

        result = _adapter(transport).execute(_request())

        self.assertIsNotNone(result.capacity_observation)
        self.assertIs(
            result.capacity_observation.capacity_status,
            CapacityStatus.PROVIDER_UNAVAILABLE,
        )
        self.assertIsNone(result.capacity_observation.recovery)
        transport.assert_complete()

    def test_pre_dispatch_cancel_never_creates_provider_session(self):
        transport = _ScriptedTransport([])
        adapter = _adapter(transport)
        adapter.cancel("jules-exec")

        result = adapter.execute(_request())

        self.assertIs(result.status, ExecutionStatus.CANCELLED)
        self.assertEqual(transport.calls, [])
        transport.assert_complete()

    def test_plan_approval_message_and_cancel_are_explicit_interventions(self):
        transport = _ScriptedTransport(
            [
                ("POST", "/sessions", {"name": "sessions/intervene"}),
                ("POST", "/sessions/intervene:approvePlan", None),
                (
                    "POST",
                    "/sessions/intervene:sendMessage",
                    None,
                ),
                ("DELETE", "/sessions/intervene", None),
            ]
        )
        adapter = _adapter(transport)
        request = _request("jules-intervene")

        session_name = adapter.start_session(request)
        adapter.approve_plan(request.execution_id)
        adapter.send_message(request.execution_id, "use the verified checkpoint")
        adapter.cancel(request.execution_id)

        self.assertEqual(session_name, "sessions/intervene")
        self.assertEqual(
            transport.calls[2][2],
            {"prompt": "use the verified checkpoint"},
        )
        transport.assert_complete()


if __name__ == "__main__":
    unittest.main()
