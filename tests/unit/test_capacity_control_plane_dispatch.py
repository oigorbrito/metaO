import unittest

from metao.acceptance import AcceptanceContext
from metao.control_plane import execute_mission_once
from metao.core import (
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


class CountingRuntime:
    def __init__(self, orchestrator_id: str):
        self._descriptor = OrchestratorDescriptor(
            orchestrator_id,
            "1",
            frozenset({"workflow"}),
        )
        self.calls = []

    @property
    def descriptor(self):
        return self._descriptor

    def health(self):
        return HealthReport(HealthStatus.HEALTHY)

    def execute(self, request):
        self.calls.append(request)
        return ExecutionResult(
            request.execution_id,
            self.descriptor.orchestrator_id,
            ExecutionStatus.FAILED,
            error="controlled runtime failure after dispatch",
        )

    def cancel(self, execution_id: str):
        return None


class CapacityControlPlaneDispatchTests(unittest.TestCase):
    def setUp(self):
        self.primary = CountingRuntime("primary")
        self.fallback = CountingRuntime("fallback")
        self.registry = OrchestratorRegistry()
        self.registry.register(self.primary)
        self.registry.register(self.fallback)
        self.mission = Mission("mission-capacity", "exercise capacity dispatch", frozenset({"workflow"}))
        self.policy = evaluate_policy(policy_bundle_id="policy-1", allowed=True)
        self.budget = AcceptanceBudget(1.0, 1000, 60.0, 2)
        self.acceptance_context = AcceptanceContext(
            subject_id="subject-1",
            subject_state_id="state-1",
            verification_context_id="verify-1",
            policy_bundle_id="policy-1",
            required_obligations=frozenset({"result"}),
            trusted_verifiers=frozenset({"verifier-1"}),
            trusted_provenance_roots=frozenset({"root-1"}),
            authorized_authorities=frozenset({"authority-1"}),
        )
        self.normalizers = {
            "primary": lambda **_: None,
            "fallback": lambda **_: None,
        }

    def _pools(self):
        return (
            OrchestratorPoolState(
                "primary",
                OrchestratorStatus.HEALTHY,
                frozenset({"workflow"}),
                success_rate=1.0,
                quality=1.0,
                latency_ms=10,
                cost=0.0,
                capacity_status=CapacityStatus.TEMPORARILY_RATE_LIMITED,
                recover_at_epoch=200.0,
            ),
            OrchestratorPoolState(
                "fallback",
                OrchestratorStatus.HEALTHY,
                frozenset({"workflow"}),
                success_rate=0.6,
                quality=0.6,
                latency_ms=500,
                cost=0.2,
            ),
        )

    def _execute(self, now_epoch: float):
        return execute_mission_once(
            mission=self.mission,
            registry=self.registry,
            pools=self._pools(),
            normalizers=self.normalizers,
            policy=self.policy,
            budget=self.budget,
            acceptance_context=self.acceptance_context,
            execution_id=f"exec-{now_epoch}",
            now_epoch=now_epoch,
            attempt_clock=lambda: now_epoch,
        )

    def test_rate_limited_primary_is_not_dispatched_before_recovery_boundary(self):
        outcome = self._execute(199.999)

        self.assertEqual(outcome.orchestrator_id, "fallback")
        self.assertEqual(len(self.primary.calls), 0)
        self.assertEqual(len(self.fallback.calls), 1)
        self.assertEqual(self.fallback.calls[0].context["created_at_epoch"], 199.999)

    def test_primary_reenters_and_is_dispatched_at_exact_recovery_boundary(self):
        outcome = self._execute(200.0)

        self.assertEqual(outcome.orchestrator_id, "primary")
        self.assertEqual(len(self.primary.calls), 1)
        self.assertEqual(len(self.fallback.calls), 0)
        self.assertEqual(self.primary.calls[0].context["created_at_epoch"], 200.0)


if __name__ == "__main__":
    unittest.main()
