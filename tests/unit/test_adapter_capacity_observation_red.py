import unittest

from metao.adapters.openai_agents import OpenAIAgentsOrchestratorAdapter
from metao.core import ExecutionRequest, ExecutionStatus, Mission
from metao.strategy import CapacityStatus, RecoveryEvidenceBasis


class _RateLimitError(RuntimeError):
    status_code = 429
    headers = {"retry-after": "10"}


class _Runner:
    def run_sync(self, agent, payload):
        raise _RateLimitError("rate limited")


class AdapterCapacityObservationRedTests(unittest.TestCase):
    def test_http_429_retry_after_emits_structured_capacity_observation(self):
        adapter = OpenAIAgentsOrchestratorAdapter(_Runner(), object())
        request = ExecutionRequest(
            execution_id="execution-1",
            mission=Mission("mission-1", "test mission"),
            context={"created_at_epoch": 100.0},
        )

        result = adapter.execute(request)

        self.assertIs(result.status, ExecutionStatus.FAILED)
        observation = result.capacity_observation
        self.assertIsNotNone(observation)
        self.assertIs(observation.capacity_status, CapacityStatus.TEMPORARILY_RATE_LIMITED)
        self.assertEqual(observation.recovery.recover_at_epoch, 110.0)
        self.assertIs(
            observation.recovery.evidence_basis,
            RecoveryEvidenceBasis.ADAPTER_VERIFIED,
        )
        self.assertTrue(observation.recovery.evidence_ref.strip())


if __name__ == "__main__":
    unittest.main()
