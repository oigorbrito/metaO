from metao.adapters.crewai import CrewAIOrchestratorAdapter
from metao.adapters.langgraph import LangGraphOrchestratorAdapter


class _Crew:
    def kickoff(self, *, inputs):
        return {"ok": True}


class _Graph:
    def invoke(self, payload):
        return {"ok": True}


def test_two_runtime_adapters_report_workload_identity_unsupported_consistently():
    adapters = (
        CrewAIOrchestratorAdapter(_Crew(), orchestrator_id="crewai-a", version="1"),
        LangGraphOrchestratorAdapter(_Graph(), orchestrator_id="langgraph-a", version="1"),
    )

    for adapter in adapters:
        assert adapter.descriptor.metadata["workload_identity"] == "unsupported"


def test_unsupported_identity_metadata_does_not_change_orchestrator_contract():
    crew = CrewAIOrchestratorAdapter(_Crew(), orchestrator_id="crewai-a", version="1")
    graph = LangGraphOrchestratorAdapter(_Graph(), orchestrator_id="langgraph-a", version="1")

    assert crew.descriptor.orchestrator_id == "crewai-a"
    assert graph.descriptor.orchestrator_id == "langgraph-a"
    assert crew.descriptor.metadata["adapter"] == "crewai"
    assert graph.descriptor.metadata["adapter"] == "langgraph"
