from __future__ import annotations

import json
from pathlib import Path
import unittest

from metao.adapters.openai_agents import (
    OpenAIAgentsOrchestratorAdapter,
    normalize_evidence,
)
from metao.core import (
    ExecutionRequest,
    ExecutionStatus,
    HealthStatus,
    Mission,
    OrchestratorContract,
)


class FakeRunResult:
    def __init__(self, final_output):
        self.final_output = final_output


class FakeRunner:
    def __init__(self, *, output="openai-agents-ok", error: Exception | None = None):
        self.output = output
        self.error = error
        self.calls: list[tuple[object, str]] = []

    def run_sync(self, agent, input_value):
        self.calls.append((agent, input_value))
        if self.error is not None:
            raise self.error
        return FakeRunResult(self.output)


class MissingRunner:
    pass


def request(*, execution_id: str = "r6-wu04-exec", context=None) -> ExecutionRequest:
    return ExecutionRequest(
        execution_id,
        Mission(
            "r6-wu04-mission",
            "prove the third runtime boundary",
            frozenset({"workflow"}),
        ),
        context or {},
    )


class Roadmap6WorkUnit04Tests(unittest.TestCase):
    def test_01_adapter_is_a_neutral_orchestrator_contract(self):
        adapter = OpenAIAgentsOrchestratorAdapter(
            FakeRunner(),
            object(),
            orchestrator_id="openai-agents-real",
            version="0.20.0",
        )

        self.assertIsInstance(adapter, OrchestratorContract)
        self.assertEqual(adapter.descriptor.orchestrator_id, "openai-agents-real")
        self.assertEqual(adapter.descriptor.version, "0.20.0")
        self.assertEqual(adapter.descriptor.capabilities, frozenset({"workflow", "agent"}))
        self.assertEqual(adapter.descriptor.metadata["adapter"], "openai-agents")

    def test_02_health_requires_sync_runner_and_configured_agent(self):
        healthy = OpenAIAgentsOrchestratorAdapter(FakeRunner(), object()).health()
        no_runner = OpenAIAgentsOrchestratorAdapter(MissingRunner(), object()).health()
        no_agent = OpenAIAgentsOrchestratorAdapter(FakeRunner(), None).health()

        self.assertIs(healthy.status, HealthStatus.HEALTHY)
        self.assertIs(no_runner.status, HealthStatus.UNHEALTHY)
        self.assertIs(no_agent.status, HealthStatus.UNHEALTHY)

    def test_03_execute_uses_deterministic_framework_neutral_input(self):
        runner = FakeRunner(output="sandbox-ok")
        agent = object()
        adapter = OpenAIAgentsOrchestratorAdapter(
            runner,
            agent,
            orchestrator_id="openai-agents-real",
            version="0.20.0",
        )
        probe = request(context={"z": 2, "a": "one"})

        result = adapter.execute(probe)

        self.assertIs(result.status, ExecutionStatus.SUCCEEDED)
        self.assertEqual(result.output, {"result": "sandbox-ok"})
        self.assertEqual(len(runner.calls), 1)
        called_agent, raw_input = runner.calls[0]
        self.assertIs(called_agent, agent)
        self.assertEqual(
            json.loads(raw_input),
            {
                "objective": "prove the third runtime boundary",
                "context": {"a": "one", "z": 2},
            },
        )
        self.assertEqual(
            raw_input,
            '{"context":{"a":"one","z":2},"objective":"prove the third runtime boundary"}',
        )

    def test_04_dict_final_output_is_preserved(self):
        adapter = OpenAIAgentsOrchestratorAdapter(
            FakeRunner(output={"answer": "ok", "count": 1}),
            object(),
        )

        result = adapter.execute(request())

        self.assertIs(result.status, ExecutionStatus.SUCCEEDED)
        self.assertEqual(result.output, {"answer": "ok", "count": 1})

    def test_05_runtime_exception_is_normalized_to_failed_result(self):
        adapter = OpenAIAgentsOrchestratorAdapter(
            FakeRunner(error=RuntimeError("scripted runtime failure")),
            object(),
            orchestrator_id="openai-agents-real",
        )

        result = adapter.execute(request())

        self.assertIs(result.status, ExecutionStatus.FAILED)
        self.assertEqual(result.orchestrator_id, "openai-agents-real")
        self.assertEqual(result.error, "scripted runtime failure")

    def test_06_cancel_before_dispatch_never_calls_sdk_runner(self):
        runner = FakeRunner()
        adapter = OpenAIAgentsOrchestratorAdapter(
            runner,
            object(),
            orchestrator_id="openai-agents-real",
        )
        probe = request(execution_id="cancel-me")

        adapter.cancel("cancel-me")
        result = adapter.execute(probe)

        self.assertIs(result.status, ExecutionStatus.CANCELLED)
        self.assertEqual(runner.calls, [])

    def test_07_evidence_normalization_is_deterministic_and_bound(self):
        probe = request(
            context={
                "obligation_id": "runtime_probe",
                "subject_id": "subject-7",
                "subject_state_id": "state-7",
                "verification_context_id": "verify-7",
                "policy_bundle_id": "policy-7",
                "verifier_id": "verifier-7",
                "authority_id": "authority-7",
                "created_at_epoch": 100.0,
                "expires_at_epoch": 200.0,
            }
        )
        output = {"result": "sandbox-ok", "nested": {"b": 2, "a": 1}}

        first = normalize_evidence(
            request=probe,
            orchestrator_id="openai-agents-real",
            adapter_version="0.20.0",
            output=output,
            attempt_id="attempt-7",
        )
        second = normalize_evidence(
            request=probe,
            orchestrator_id="openai-agents-real",
            adapter_version="0.20.0",
            output=output,
            attempt_id="attempt-7",
        )

        self.assertEqual(first, second)
        self.assertEqual(first.evidence_id, "r6-wu04-exec:result")
        self.assertEqual(first.obligation_id, "runtime_probe")
        self.assertEqual(first.mission_id, "r6-wu04-mission")
        self.assertEqual(first.execution_id, "r6-wu04-exec")
        self.assertEqual(first.orchestrator_id, "openai-agents-real")
        self.assertEqual(first.adapter_version, "0.20.0")
        self.assertEqual(first.attempt_id, "attempt-7")
        self.assertEqual(first.provenance_root, "openai-agents:openai-agents-real:r6-wu04-exec")
        self.assertTrue(first.payload_digest)
        self.assertTrue(first.passed)

    def test_08_production_adapter_has_no_openai_agents_sdk_import(self):
        source = Path("src/metao/adapters/openai_agents.py").read_text(encoding="utf-8")

        self.assertNotRegex(source, r"(?m)^\s*from\s+agents(?:\.|\s)")
        self.assertNotRegex(source, r"(?m)^\s*import\s+agents(?:\.|\s|$)")
        self.assertNotIn("from openai", source)
        self.assertNotIn("import openai", source)


if __name__ == "__main__":
    unittest.main(verbosity=2)
