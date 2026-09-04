from __future__ import annotations

import unittest

from metao.acceptance import AcceptanceContext, EvidenceEnvelope
from metao.capacity import (
    CapacityObservation,
    CapacityRecovery,
    CapacityStatus,
    RecoveryEvidenceBasis,
)
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
from metao.strategy import OrchestratorPoolState, OrchestratorStatus
from metao.supervision import apply_capacity_observation


class _RateLimitedPrimary:
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
        recovery = CapacityRecovery(
            recover_at_epoch=110.0,
            evidence_basis=RecoveryEvidenceBasis.ADAPTER_VERIFIED,
            evidence_ref="synthetic:429:retry-after=10",
        )
        return ExecutionResult(
            request.execution_id,
            "primary",
            ExecutionStatus.FAILED,
            error="rate limited",
            capacity_observation=CapacityObservation(
                capacity_status=CapacityStatus.TEMPORARILY_RATE_LIMITED,
                recovery=recovery,
            ),
        )

    def cancel(self, execution_id: str) -> None:
        pass


class _SuccessfulFallback:
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
            output={"result": "fallback-ok"},
        )

    def cancel(self, execution_id: str) -> None:
        pass


def _normalizer(**kwargs):
    request = kwargs["request"]
    return EvidenceEnvelope(
        evidence_id=f"{request.execution_id}:result",
        obligation_id=str(request.context["obligation_id"]),
        mission_id=request.mission.mission_id,
        execution_id=request.execution_id,
        orchestrator_id=kwargs["orchestrator_id"],
        adapter_version=kwargs["adapter_version"],
        attempt_id=kwargs["attempt_id"],
        subject_id=str(request.context["subject_id"]),
        subject_state_id=str(request.context["subject_state_id"]),
        verification_context_id=str(request.context["verification_context_id"]),
        policy_bundle_id=str(request.context["policy_bundle_id"]),
        verifier_id=str(request.context["verifier_id"]),
        payload_digest="fixture-digest",
        provenance_root="fixture:wave5",
        authority_id=str(request.context["authority_id"]),
        passed=True,
        created_at_epoch=float(request.context["created_at_epoch"]),
    )


class CapacitySupervisionRedTests(unittest.TestCase):
    def test_evidenced_rate_limit_updates_explicit_supervision_until_recovery(self):
        primary = _RateLimitedPrimary()
        fallback = _SuccessfulFallback()
        registry = OrchestratorRegistry()
        registry.register(primary)
        registry.register(fallback)

        pools = (
            OrchestratorPoolState(
                "primary", OrchestratorStatus.HEALTHY, frozenset({"workflow"}),
                1.0, 1.0, 1.0, 1.0, 0.0,
            ),
            OrchestratorPoolState(
                "fallback", OrchestratorStatus.HEALTHY, frozenset({"workflow"}),
                0.8, 0.8, 0.8, 20.0, 0.02,
            ),
        )
        mission = Mission("wave5", "prove capacity supervision", frozenset({"workflow"}))
        policy = evaluate_policy(policy_bundle_id="policy-wave5", allowed=True)
        context = AcceptanceContext(
            "subject-wave5", "state-wave5", "verify-wave5", "policy-wave5",
            frozenset({"execution_result"}),
        )
        budget = AcceptanceBudget(10.0, 10_000, 600.0, 10)

        supervised_pools = pools

        def on_attempt_finished(attempt_context, execution, ended_at_epoch):
            nonlocal supervised_pools
            supervised_pools = apply_capacity_observation(
                supervised_pools,
                orchestrator_id=attempt_context.orchestrator_id,
                observation=execution.capacity_observation,
            )

        first = execute_mission(
            mission=mission,
            registry=registry,
            pools=pools,
            normalizers={"primary": _normalizer, "fallback": _normalizer},
            policy=policy,
            budget=budget,
            acceptance_context=context,
            execution_id_prefix="wave5-first",
            now_epoch=100.0,
            max_attempts=2,
            on_attempt_finished=on_attempt_finished,
        )
        self.assertEqual(first.attempted_orchestrators[:2], ("primary", "fallback"))
        self.assertEqual(primary.calls, 1)

        primary_state = next(pool for pool in supervised_pools if pool.orchestrator_id == "primary")
        self.assertEqual(primary_state.capacity_status, CapacityStatus.TEMPORARILY_RATE_LIMITED)
        self.assertEqual(primary_state.recovery.recover_at_epoch, 110.0)

        second = execute_mission(
            mission=mission,
            registry=registry,
            pools=supervised_pools,
            normalizers={"primary": _normalizer, "fallback": _normalizer},
            policy=policy,
            budget=budget,
            acceptance_context=context,
            execution_id_prefix="wave5-second",
            now_epoch=105.0,
            max_attempts=1,
        )

        self.assertEqual(primary.calls, 1)
        self.assertEqual(second.orchestrator_id, "fallback")

        third = execute_mission(
            mission=mission,
            registry=registry,
            pools=supervised_pools,
            normalizers={"primary": _normalizer, "fallback": _normalizer},
            policy=policy,
            budget=budget,
            acceptance_context=context,
            execution_id_prefix="wave5-third",
            now_epoch=110.0,
            max_attempts=1,
        )

        self.assertEqual(third.orchestrator_id, "primary")
        self.assertEqual(primary.calls, 2)


if __name__ == "__main__":
    unittest.main()
