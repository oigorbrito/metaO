from __future__ import annotations

import unittest

from metao.adapters.crewai import normalize_evidence as normalize_crewai
from metao.adapters.langgraph import normalize_evidence as normalize_langgraph
from metao.adapters.openai_agents import normalize_evidence as normalize_openai_agents
from metao.core import ExecutionRequest, Mission
from metao.evidence import EvidenceEnvelope


class Roadmap8A12CrossOrchestratorEvidenceTests(unittest.TestCase):
    def setUp(self) -> None:
        self.request = ExecutionRequest(
            "exec-a12",
            Mission("mission-a12", "prove cross-orchestrator evidence", frozenset({"workflow"})),
            context={
                "obligation_id": "result",
                "subject_id": "subject-a12",
                "subject_state_id": "state-a12",
                "verification_context_id": "verify-a12",
                "policy_bundle_id": "policy-a12",
                "verifier_id": "verifier-a12",
                "authority_id": "authority-a12",
                "created_at_epoch": 10.0,
            },
        )

    def _items(self) -> tuple[EvidenceEnvelope, ...]:
        output = {"answer": "same-logical-result"}
        return (
            normalize_langgraph(
                request=self.request,
                orchestrator_id="langgraph",
                adapter_version="1",
                output=output,
            ),
            normalize_crewai(
                request=self.request,
                orchestrator_id="crewai",
                adapter_version="1",
                output=output,
            ),
            normalize_openai_agents(
                request=self.request,
                orchestrator_id="openai-agents",
                adapter_version="1",
                output=output,
            ),
        )

    def test_all_runtimes_emit_exact_canonical_class(self) -> None:
        for item in self._items():
            self.assertIs(type(item), EvidenceEnvelope)

    def test_acceptance_bindings_are_runtime_independent(self) -> None:
        invariant_fields = (
            "mission_id",
            "execution_id",
            "obligation_id",
            "subject_id",
            "subject_state_id",
            "verification_context_id",
            "policy_bundle_id",
            "verifier_id",
            "authority_id",
        )
        items = self._items()
        expected = tuple(getattr(items[0], name) for name in invariant_fields)
        for item in items[1:]:
            self.assertEqual(
                tuple(getattr(item, name) for name in invariant_fields),
                expected,
            )

    def test_runtime_identity_varies_without_changing_core_contract(self) -> None:
        items = self._items()
        self.assertEqual(
            {item.orchestrator_id for item in items},
            {"langgraph", "crewai", "openai-agents"},
        )
        self.assertEqual(
            {item.adapter_id for item in items},
            {"langgraph", "crewai", "openai-agents"},
        )
        self.assertTrue(all(item.adapter_version == "1" for item in items))

    def test_envelope_contains_no_framework_specific_runtime_object(self) -> None:
        forbidden_module_roots = {"langgraph", "crewai", "agents", "openai"}
        for item in self._items():
            for value in item.__dict__.values():
                module_root = type(value).__module__.split(".", 1)[0]
                self.assertNotIn(module_root, forbidden_module_roots)

    def test_normalization_does_not_encode_final_metao_acceptance(self) -> None:
        for item in self._items():
            self.assertFalse(hasattr(item, "acceptance_decision"))
            self.assertFalse(hasattr(item, "metao_accepted"))


if __name__ == "__main__":
    unittest.main(verbosity=2)
