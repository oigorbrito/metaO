from metao.adapters.crewai import CrewAIOrchestratorAdapter
from metao.adapters.langgraph import LangGraphOrchestratorAdapter


class _Crew:
    def kickoff(self, *, inputs):
        return {"ok": True}


class _Graph:
    def invoke(self, payload):
        return {"ok": True}


def test_two_runtime_adapters_report_security_isolation_unsupported_consistently():
    adapters = (
        CrewAIOrchestratorAdapter(_Crew(), orchestrator_id="crewai-a", version="1"),
        LangGraphOrchestratorAdapter(_Graph(), orchestrator_id="langgraph-a", version="1"),
    )

    for adapter in adapters:
        assert adapter.descriptor.metadata["security_isolation"] == "unsupported"


def test_unsupported_security_isolation_does_not_mint_enforcement_capability():
    crew = CrewAIOrchestratorAdapter(_Crew(), orchestrator_id="crewai-a", version="1")
    graph = LangGraphOrchestratorAdapter(_Graph(), orchestrator_id="langgraph-a", version="1")

    for adapter in (crew, graph):
        assert "security_isolation" not in adapter.descriptor.capabilities
        assert adapter.descriptor.metadata["security_isolation"] == "unsupported"
        assert adapter.descriptor.metadata["workload_identity"] == "unsupported"
