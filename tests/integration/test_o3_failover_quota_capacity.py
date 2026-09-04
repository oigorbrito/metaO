from __future__ import annotations

import unittest

from metao.acceptance import AcceptanceContext, AcceptanceDecision, EvidenceEnvelope
from metao.control_plane import execute_mission
from metao.core import (
    ExecutionRequest,
    ExecutionResult,
    ExecutionStatus,
    HealthReport,
    HealthStatus,
    Mission,
    OrchestratorDescriptor,
    OrchestratorRegistry,
)
from metao.governance import AcceptanceBudget, evaluate_policy
from metao.strategy import CapacityStatus, OrchestratorPoolState, OrchestratorStatus


class PrimaryOrchestrator:
    def __init__(self) -> None:
        self.calls = 0
        self._descriptor = OrchestratorDescriptor("primary", "1", frozenset({"workflow"}))

    @property
    def descriptor(self):
        return self._descriptor

    def health(self):
        return HealthReport(HealthStatus.HEALTHY)

    def execute(self, request: ExecutionRequest):
        self.calls += 1
        return ExecutionResult(
            request.execution_id,
            "primary",
            ExecutionStatus.SUCCEEDED,
            output={"result": "primary"},
        )

    def cancel(self, execution_id: str) -> None:
        pass


class FreeFallbackOrchestrator:
    def __init__(self) -> None:
        self.calls = 0
        self._descriptor = OrchestratorDescriptor("fallback", "1", frozenset({"workflow"}))

    @property
    def descriptor(self):
        return self._descriptor

    def health(self):
        return HealthReport(HealthStatus.HEALTHY)

    def execute(self, request: ExecutionRequest):
        self.calls += 1
        return ExecutionResult(
            request.execution_id,
            "fallback",
            ExecutionStatus.SUCCEEDED,
            output={"result": f"fallback:{request.mission.objective}"},
        )

    def cancel(self, execution_id: str) -> None:
        pass


def normalize_evidence(*, request, orchestrator_id, adapter_version, output, attempt_id):
    return EvidenceEnvelope(
        evidence_id=f"{request.execution_id}:result",
        obligation_id=str(request.context["obligation_id"]),
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
        payload_digest=f"digest:{output['result']}",
        provenance_root=f"provenance:{orchestrator_id}",
        authority_id=request.context["authority_id"],
        passed=True,
    )


class O3FailoverQuotaCapacity(unittest.TestCase):
    def _run(self, pools):
        primary = PrimaryOrchestrator()
        fallback = FreeFallbackOrchestrator()
        registry = OrchestratorRegistry()
        registry.register(primary)
        registry.register(fallback)

        outcome = execute_mission(
            mission=Mission("o3-quota-mission", "recover with free fallback", frozenset({"workflow"})),
            registry=registry,
            pools=pools,
            normalizers={"primary": normalize_evidence, "fallback": normalize_evidence},
            policy=evaluate_policy(policy_bundle_id="policy-o3", allowed=True),
            budget=AcceptanceBudget(1.0, 1000, 60.0, 3),
            acceptance_context=AcceptanceContext(
                "subject-o3",
                "state-o3",
                "verify-o3",
                "policy-o3",
                frozenset({"execution_result"}),
            ),
            execution_id_prefix="o3-quota-exec",
            now_epoch=100.0,
            max_attempts=2,
        )
        return primary, fallback, outcome

    def test_baseline_primary_wins_when_both_healthy_and_no_capacity_signal(self):
        primary, fallback, outcome = self._run(
            (
                OrchestratorPoolState(
                    "primary",
                    OrchestratorStatus.HEALTHY,
                    CapacityStatus.AVAILABLE,
                    frozenset({"workflow"}),
                    1.0,
                    1.0,
                    1.0,
                    1.0,
                    0.0,
                ),
                OrchestratorPoolState(
                    "fallback",
                    OrchestratorStatus.HEALTHY,
                    CapacityStatus.AVAILABLE,
                    frozenset({"workflow"}),
                    0.8,
                    0.8,
                    0.8,
                    20.0,
                    0.02,
                ),
            )
        )

        self.assertEqual(primary.calls, 1)
        self.assertEqual(fallback.calls, 0)
        self.assertEqual(outcome.orchestrator_id, "primary")
        self.assertEqual(outcome.attempted_orchestrators, ("primary",))
        self.assertEqual(outcome.execution.output["result"], "primary")
        self.assertEqual(outcome.acceptance.decision, AcceptanceDecision.ACCEPT)

    def test_quota_exhaustion_does_not_fail_task_when_free_alternative_exists(self):
        primary, fallback, outcome = self._run(
            (
                OrchestratorPoolState(
                    "primary",
                    OrchestratorStatus.HEALTHY,
                    CapacityStatus.TEMPORARILY_QUOTA_EXHAUSTED,
                    frozenset({"workflow"}),
                    1.0,
                    1.0,
                    1.0,
                    1.0,
                    0.0,
                ),
                OrchestratorPoolState(
                    "fallback",
                    OrchestratorStatus.HEALTHY,
                    CapacityStatus.AVAILABLE,
                    frozenset({"workflow"}),
                    0.8,
                    0.8,
                    0.8,
                    20.0,
                    0.02,
                ),
            )
        )

        self.assertEqual(primary.calls, 0)
        self.assertEqual(fallback.calls, 1)
        self.assertEqual(outcome.attempted_orchestrators, ("fallback",))
        self.assertEqual(outcome.orchestrator_id, "fallback")
        self.assertEqual(outcome.execution.output["result"], "fallback:recover with free fallback")
        self.assertEqual(outcome.acceptance.decision, AcceptanceDecision.ACCEPT)


if __name__ == "__main__":
    unittest.main(verbosity=2)
