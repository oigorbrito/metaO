import unittest

from metao.adapters.openai_agents import OpenAIAgentsOrchestratorAdapter
from metao.capacity import CapacityStatus
from metao.core import ExecutionRequest, ExecutionStatus, Mission


class _ServiceUnavailableError(RuntimeError):
    status_code = 503


class _Runner:
    def run_sync(self, agent, payload):
        raise _ServiceUnavailableError("service unavailable")


class ProviderUnavailableAdapterRedTests(unittest.TestCase):
    def test_http_503_emits_provider_unavailable_without_invented_recovery(self):
        adapter = OpenAIAgentsOrchestratorAdapter(_Runner(), object())
        request = ExecutionRequest(
            execution_id="execution-provider-unavailable",
            mission=Mission("mission-provider-unavailable", "test provider outage"),
            context={"created_at_epoch": 100.0},
        )

        result = adapter.execute(request)

        self.assertIs(result.status, ExecutionStatus.FAILED)
        observation = result.capacity_observation
        self.assertIsNotNone(
            observation,
            "verified HTTP 503 must be represented as structured provider capacity state",
        )
        self.assertIs(observation.capacity_status, CapacityStatus.PROVIDER_UNAVAILABLE)
        self.assertIsNone(
            observation.recovery,
            "provider unavailability must not gain a recovery deadline without explicit recovery evidence",
        )


if __name__ == "__main__":
    unittest.main()
