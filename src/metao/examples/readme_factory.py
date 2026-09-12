from __future__ import annotations

from metao.acceptance import EvidenceEnvelope
from metao.catalog import OrchestratorCatalog
from metao.core import (
    ExecutionResult,
    ExecutionStatus,
    HealthReport,
    HealthStatus,
    OrchestratorDescriptor,
    OrchestratorRegistry,
)
from metao.operator import MissionOperator


class ReadmeRuntime:
    @property
    def descriptor(self) -> OrchestratorDescriptor:
        return OrchestratorDescriptor(
            "readme-runtime",
            "readme-v1",
            frozenset({"workflow"}),
        )

    def health(self) -> HealthReport:
        return HealthReport(HealthStatus.HEALTHY)

    def execute(self, request):
        return ExecutionResult(
            request.execution_id,
            self.descriptor.orchestrator_id,
            ExecutionStatus.SUCCEEDED,
            {"result": "readme quickstart fixture"},
        )

    def cancel(self, execution_id: str) -> None:
        return None


def normalize_evidence(*, request, orchestrator_id, adapter_version, output, attempt_id):
    return EvidenceEnvelope(
        evidence_id=f"{request.execution_id}:evidence",
        obligation_id=request.context["obligation_id"],
        mission_id=request.mission.mission_id,
        execution_id=request.execution_id,
        orchestrator_id=orchestrator_id,
        adapter_version=adapter_version,
        attempt_id=attempt_id,
        subject_id=request.context["subject_id"],
        subject_state_id=request.context["subject_state_id"],
        verification_context_id=request.context["verification_context_id"],
        policy_bundle_id=request.context["policy_bundle_id"],
        verifier_id=request.context["verifier_id"],
        payload_digest="readme-digest",
        provenance_root="readme-provenance",
        authority_id=request.context["authority_id"],
        passed=True,
        created_at_epoch=request.context["created_at_epoch"],
    )


def create_operator(*, store, **kwargs) -> MissionOperator:
    registry = OrchestratorRegistry()
    runtime = ReadmeRuntime()
    registry.register(runtime)
    catalog = OrchestratorCatalog(registry)
    catalog.register(runtime.descriptor.orchestrator_id, normalizer=normalize_evidence)
    return MissionOperator(registry=registry, store=store, catalog=catalog)
