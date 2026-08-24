import inspect
import unittest

from metao.acceptance import EvidenceEnvelope
from metao.adapters.crewai import CrewAIOrchestratorAdapter, normalize_evidence as normalize_crewai
from metao.adapters.langgraph import LangGraphOrchestratorAdapter, normalize_evidence as normalize_langgraph
from metao.core import ExecutionRequest, ExecutionStatus, Mission, OrchestratorContract
import metao.core as core


class FakeLangGraph:
    def __init__(self):
        self.calls = []

    def invoke(self, payload):
        self.calls.append(payload)
        return {"answer": "langgraph-ok"}


class FakeCrew:
    def __init__(self):
        self.calls = []

    def kickoff(self, *, inputs):
        self.calls.append(inputs)
        return {"answer": "crewai-ok"}


class BlockLMultiOrchestratorAcceptance(unittest.TestCase):
    def setUp(self):
        self.request = ExecutionRequest(
            execution_id="exec-1",
            mission=Mission("mission-1", "solve task", frozenset({"workflow"})),
            context={
                "subject_id": "subject-1",
                "subject_state_id": "state-1",
                "verification_context_id": "verify-1",
                "policy_bundle_id": "policy-1",
                "verifier_id": "verifier-1",
                "authority_id": "authority-1",
                "created_at_epoch": 10.0,
                "obligation_id": "result",
            },
        )

    def test_langgraph_adapter_executes_native_invoke_shape(self):
        graph = FakeLangGraph()
        adapter = LangGraphOrchestratorAdapter(graph)
        result = adapter.execute(self.request)
        self.assertEqual(result.status, ExecutionStatus.SUCCEEDED)
        self.assertEqual(result.output["answer"], "langgraph-ok")
        self.assertEqual(len(graph.calls), 1)
        self.assertIsInstance(adapter, OrchestratorContract)

    def test_crewai_adapter_executes_native_kickoff_shape(self):
        crew = FakeCrew()
        adapter = CrewAIOrchestratorAdapter(crew)
        result = adapter.execute(self.request)
        self.assertEqual(result.status, ExecutionStatus.SUCCEEDED)
        self.assertEqual(result.output["answer"], "crewai-ok")
        self.assertEqual(len(crew.calls), 1)
        self.assertIsInstance(adapter, OrchestratorContract)

    def test_both_adapters_share_orchestrator_contract(self):
        graph_adapter = LangGraphOrchestratorAdapter(FakeLangGraph())
        crew_adapter = CrewAIOrchestratorAdapter(FakeCrew())
        for adapter in (graph_adapter, crew_adapter):
            self.assertIsInstance(adapter, OrchestratorContract)
            self.assertTrue(adapter.health().status.value == "HEALTHY")
            self.assertIn("workflow", adapter.descriptor.capabilities)

    def test_both_normalize_to_same_acceptance_envelope_contract(self):
        output = {"answer": "same"}
        lg = normalize_langgraph(
            request=self.request,
            orchestrator_id="lg",
            adapter_version="1",
            output=output,
        )
        crew = normalize_crewai(
            request=self.request,
            orchestrator_id="crew",
            adapter_version="1",
            output=output,
        )
        self.assertIsInstance(lg, EvidenceEnvelope)
        self.assertIsInstance(crew, EvidenceEnvelope)
        for field in (
            "mission_id",
            "execution_id",
            "subject_id",
            "subject_state_id",
            "verification_context_id",
            "policy_bundle_id",
            "verifier_id",
            "authority_id",
            "payload_digest",
        ):
            self.assertEqual(getattr(lg, field), getattr(crew, field))

    def test_core_remains_free_of_framework_specific_sdk_types(self):
        source = inspect.getsource(core).lower()
        self.assertNotIn("langgraph", source)
        self.assertNotIn("crewai", source)


if __name__ == "__main__":
    unittest.main()
