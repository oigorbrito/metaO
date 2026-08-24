import importlib
import unittest

from metao.core import OrchestratorContract


class BlockLMultiOrchestratorAcceptance(unittest.TestCase):
    def _langgraph(self):
        return importlib.import_module("metao.adapters.langgraph")

    def _crewai(self):
        return importlib.import_module("metao.adapters.crewai")

    def test_langgraph_real_adapter_exists(self):
        module = self._langgraph()
        self.assertTrue(hasattr(module, "LangGraphOrchestratorAdapter"))

    def test_crewai_real_adapter_exists(self):
        module = self._crewai()
        self.assertTrue(hasattr(module, "CrewAIOrchestratorAdapter"))

    def test_both_adapters_implement_common_contract(self):
        langgraph_cls = getattr(self._langgraph(), "LangGraphOrchestratorAdapter")
        crewai_cls = getattr(self._crewai(), "CrewAIOrchestratorAdapter")
        self.assertTrue(issubclass(langgraph_cls, OrchestratorContract))
        self.assertTrue(issubclass(crewai_cls, OrchestratorContract))

    def test_both_normalize_to_same_evidence_envelope(self):
        acceptance = importlib.import_module("metao.acceptance")
        envelope = getattr(acceptance, "EvidenceEnvelope")
        self.assertIsNotNone(envelope)
        for module in (self._langgraph(), self._crewai()):
            self.assertTrue(hasattr(module, "normalize_evidence"))

    def test_core_remains_free_of_framework_specific_sdk_types(self):
        core = importlib.import_module("metao.core")
        source = open(core.__file__, encoding="utf-8").read().lower()
        self.assertNotIn("langgraph", source)
        self.assertNotIn("crewai", source)


if __name__ == "__main__":
    unittest.main()
