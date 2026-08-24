from __future__ import annotations

import unittest

from metao.acceptance import AcceptanceContext, AcceptanceDecision, EvidenceEnvelope
from metao.control_plane import execute_mission_once
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
from metao.strategy import OrchestratorPoolState, OrchestratorStatus


class CountingOrchestrator:
    def __init__(self) -> None:
        self.calls = 0
        self._descriptor = OrchestratorDescriptor("sandbox", "1", frozenset({"workflow"}))

    @property
    def descriptor(self):
        return self._descriptor

    def health(self):
        return HealthReport(HealthStatus.HEALTHY)

    def execute(self, request: ExecutionRequest):
        self.calls += 1
        return ExecutionResult(request.execution_id, "sandbox", ExecutionStatus.SUCCEEDED, output={"result": "ok"})

    def cancel(self, execution_id: str) -> None:
        pass


def bad_state_normalizer(*, request, orchestrator_id, adapter_version, output, attempt_id):
    return EvidenceEnvelope(
        evidence_id=request.execution_id + ":result",
        obligation_id=request.context["obligation_id"],
        mission_id=request.mission.mission_id,
        execution_id=request.execution_id,
        orchestrator_id=orchestrator_id,
        adapter_version=adapter_version,
        attempt_id=attempt_id,
        subject_id=request.context["subject_id"],
        subject_state_id="tampered-state",
        verification_context_id=request.context["verification_context_id"],
        policy_bundle_id=request.context["policy_bundle_id"],
        verifier_id=request.context["verifier_id"],
        payload_digest="digest-present",
        provenance_root="sandbox:proof",
        authority_id=request.context["authority_id"],
        passed=True,
        created_at_epoch=request.context["created_at_epoch"],
    )


class O4GovernanceGates(unittest.TestCase):
    def setUp(self):
        self.runtime = CountingOrchestrator()
        self.registry = OrchestratorRegistry()
        self.registry.register(self.runtime)
        self.mission = Mission("o4-mission", "governed sandbox", frozenset({"workflow"}))
        self.context = AcceptanceContext("subject-o4", "state-o4", "verify-o4", "policy-o4", frozenset({"execution_result"}))
        self.pools = (OrchestratorPoolState("sandbox", OrchestratorStatus.HEALTHY, frozenset({"workflow"})),)

    def call(self, *, policy, budget):
        return execute_mission_once(
            mission=self.mission,
            registry=self.registry,
            pools=self.pools,
            normalizers={"sandbox": bad_state_normalizer},
            policy=policy,
            budget=budget,
            acceptance_context=self.context,
            execution_id="o4-exec",
            now_epoch=100.0,
        )

    def test_policy_denial_blocks_before_runtime(self):
        outcome = self.call(
            policy=evaluate_policy(policy_bundle_id="policy-o4", allowed=False),
            budget=AcceptanceBudget(1.0, 1000, 60.0, 2),
        )
        self.assertEqual(self.runtime.calls, 0)
        self.assertEqual(outcome.acceptance.decision, AcceptanceDecision.BLOCK)
        self.assertIn("policy:deny", outcome.acceptance.reasons)

    def test_exhausted_budget_blocks_before_runtime(self):
        outcome = self.call(
            policy=evaluate_policy(policy_bundle_id="policy-o4", allowed=True),
            budget=AcceptanceBudget(0.0, 1000, 60.0, 2),
        )
        self.assertEqual(self.runtime.calls, 0)
        self.assertEqual(outcome.acceptance.decision, AcceptanceDecision.BLOCK)
        self.assertIn("budget_exhausted", outcome.acceptance.reasons)

    def test_successful_runtime_cannot_override_independent_acceptance(self):
        outcome = self.call(
            policy=evaluate_policy(policy_bundle_id="policy-o4", allowed=True),
            budget=AcceptanceBudget(1.0, 1000, 60.0, 2),
        )
        self.assertEqual(self.runtime.calls, 1)
        self.assertEqual(outcome.execution.status, ExecutionStatus.SUCCEEDED)
        self.assertEqual(outcome.acceptance.decision, AcceptanceDecision.STALE)
        self.assertIn("subject_state_mismatch", outcome.acceptance.reasons)


if __name__ == "__main__":
    unittest.main(verbosity=2)
