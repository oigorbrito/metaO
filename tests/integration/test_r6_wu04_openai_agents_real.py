from __future__ import annotations

from importlib.metadata import version as package_version
import unittest

from agents import Agent, Runner, set_tracing_disabled

from _openai_agents_model import ScriptedModel, assistant_message
from metao.adapters.openai_agents import (
    OpenAIAgentsOrchestratorAdapter,
    normalize_evidence,
)
from metao.core import ExecutionRequest, ExecutionStatus, HealthStatus, Mission
from metao.runtime_conformance import assert_runtime_conformant


OPENAI_AGENTS_VERSION = "0.20.0"


def probe_request(execution_id: str = "r6-openai-agents-conformance") -> ExecutionRequest:
    return ExecutionRequest(
        execution_id,
        Mission(
            "r6-openai-agents-certification",
            "prove the OpenAI Agents SDK neutral runtime boundary",
            frozenset({"workflow"}),
        ),
        {
            "obligation_id": "runtime_conformance",
            "subject_id": "openai-agents-runtime",
            "subject_state_id": "openai-agents-0.20.0",
            "verification_context_id": "roadmap6-wu04",
            "policy_bundle_id": "runtime-certification-v1",
            "verifier_id": "metao-runtime-conformance",
            "authority_id": "metao-runtime",
        },
    )


def build_adapter(response: str = "openai-agents-certified-ok"):
    model = ScriptedModel([[assistant_message(response)]])
    agent = Agent(
        name="metaO OpenAI Agents certification worker",
        instructions="Return the deterministic scripted certification result.",
        model=model,
    )
    adapter = OpenAIAgentsOrchestratorAdapter(
        Runner,
        agent,
        orchestrator_id="openai-agents-real",
        version=OPENAI_AGENTS_VERSION,
    )
    return adapter, model


class OpenAIAgentsRealRuntimeV1Tests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        # The deterministic test boundary must never export traces or contact a
        # provider even if credentials exist in the surrounding environment.
        set_tracing_disabled(True)

    def test_01_pinned_real_runtime_version(self):
        self.assertEqual(package_version("openai-agents"), OPENAI_AGENTS_VERSION)

    def test_02_real_sdk_scripted_model_executes_without_provider(self):
        adapter, model = build_adapter()

        health = adapter.health()
        result = adapter.execute(probe_request("r6-openai-agents-direct"))

        self.assertIs(health.status, HealthStatus.HEALTHY)
        self.assertIs(result.status, ExecutionStatus.SUCCEEDED)
        self.assertEqual(result.output, {"result": "openai-agents-certified-ok"})
        self.assertEqual(len(model.calls), 1)
        model.assert_complete()

    def test_03_existing_neutral_conformance_harness_accepts_real_sdk_runtime(self):
        adapter, model = build_adapter("openai-agents-conformance-ok")

        report = assert_runtime_conformant(
            adapter,
            normalize_evidence,
            probe_request(),
        )

        self.assertTrue(report.passed)
        self.assertEqual(report.orchestrator_id, "openai-agents-real")
        self.assertEqual(report.failed_checks, ())
        self.assertEqual(len(model.calls), 1)
        model.assert_complete()

    def test_04_pre_dispatch_cancel_stays_metaO_owned(self):
        adapter, model = build_adapter()
        probe = probe_request("r6-openai-agents-cancelled")

        adapter.cancel(probe.execution_id)
        result = adapter.execute(probe)

        self.assertIs(result.status, ExecutionStatus.CANCELLED)
        self.assertEqual(len(model.calls), 0)
        # The model step intentionally remains unconsumed because the SDK was
        # never dispatched. That is the behavior under test.
        self.assertEqual(model.remaining_steps, 1)


if __name__ == "__main__":
    unittest.main(verbosity=2)