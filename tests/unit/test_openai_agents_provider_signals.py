import unittest

from metao.adapters.openai_agents import OpenAIAgentsOrchestratorAdapter
from metao.capacity import CapacityStatus
from metao.core import ExecutionRequest, ExecutionStatus, Mission
from metao.strategy import OrchestratorPoolState, OrchestratorStatus, select_orchestrator
from metao.supervision import apply_capacity_observation


class _ProviderError(RuntimeError):
    def __init__(self, message: str, *, status_code: int, headers=None):
        super().__init__(message)
        self.status_code = status_code
        self.headers = headers


class _Runner:
    def __init__(self, error: Exception):
        self.error = error

    def run_sync(self, agent, payload):
        raise self.error


def _request() -> ExecutionRequest:
    return ExecutionRequest(
        execution_id="provider-signal-exec",
        mission=Mission("provider-signal-mission", "normalize provider signal"),
        context={"created_at_epoch": 100.0},
    )


def _execute(error: Exception):
    return OpenAIAgentsOrchestratorAdapter(_Runner(error), object()).execute(_request())


class OpenAIAgentsProviderSignalsTests(unittest.TestCase):
    def test_http_401_emits_authentication_failure_without_recovery(self):
        result = _execute(_ProviderError("authentication failed", status_code=401))

        self.assertIs(result.status, ExecutionStatus.FAILED)
        self.assertIsNotNone(result.capacity_observation)
        self.assertIs(
            result.capacity_observation.capacity_status,
            CapacityStatus.AUTHENTICATION_FAILURE,
        )
        self.assertIsNone(result.capacity_observation.recovery)

    def test_http_429_without_retry_after_does_not_invent_recovery(self):
        result = _execute(_ProviderError("rate limited", status_code=429, headers={}))

        self.assertIs(result.status, ExecutionStatus.FAILED)
        self.assertIsNotNone(result.capacity_observation)
        self.assertIs(
            result.capacity_observation.capacity_status,
            CapacityStatus.TEMPORARILY_RATE_LIMITED,
        )
        self.assertIsNone(result.capacity_observation.recovery)

    def test_unrecognized_http_provider_state_is_unknown_and_fails_closed(self):
        result = _execute(_ProviderError("permission denied", status_code=403))

        observation = result.capacity_observation
        self.assertIsNotNone(observation)
        self.assertIs(observation.capacity_status, CapacityStatus.UNKNOWN)
        self.assertIsNone(observation.recovery)

        pools = (
            OrchestratorPoolState(
                "openai-agents",
                OrchestratorStatus.HEALTHY,
                frozenset({"workflow", "agent"}),
            ),
        )
        supervised = apply_capacity_observation(
            pools,
            orchestrator_id="openai-agents",
            observation=observation,
        )
        self.assertIsNone(select_orchestrator(supervised, now_epoch=100.0))

    def test_plain_runtime_failure_does_not_invent_provider_capacity_state(self):
        result = _execute(RuntimeError("task code failed"))

        self.assertIs(result.status, ExecutionStatus.FAILED)
        self.assertIsNone(result.capacity_observation)


if __name__ == "__main__":
    unittest.main()
