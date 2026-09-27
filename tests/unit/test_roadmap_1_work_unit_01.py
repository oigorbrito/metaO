from __future__ import annotations

import inspect
import unittest

import metao.core as core_module
from metao.acceptance import AcceptanceContext, AcceptanceDecision, EvidenceEnvelope
from metao.control_plane import MissionStatus, execute_mission, execute_mission_once
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


class FakeOrchestrator:
    def __init__(self, orchestrator_id: str, *, succeeds: bool = True) -> None:
        self.calls = 0
        self.succeeds = succeeds
        self._descriptor = OrchestratorDescriptor(orchestrator_id, "1.0", frozenset({"workflow"}))

    @property
    def descriptor(self) -> OrchestratorDescriptor:
        return self._descriptor

    def health(self) -> HealthReport:
        return HealthReport(HealthStatus.HEALTHY)

    def execute(self, request: ExecutionRequest) -> ExecutionResult:
        self.calls += 1
        if not self.succeeds:
            return ExecutionResult(
                request.execution_id,
                self.descriptor.orchestrator_id,
                ExecutionStatus.FAILED,
                error="runtime failure",
            )
        return ExecutionResult(
            request.execution_id,
            self.descriptor.orchestrator_id,
            ExecutionStatus.SUCCEEDED,
            output={"result": request.mission.objective},
        )

    def cancel(self, execution_id: str) -> None:
        pass


def pool(orchestrator_id: str, *, preferred: bool = False, capabilities: frozenset[str] = frozenset({"workflow"})):
    return OrchestratorPoolState(
        orchestrator_id,
        OrchestratorStatus.HEALTHY,
        capabilities,
        0.99 if preferred else 0.80,
        0.99 if preferred else 0.80,
        0.99 if preferred else 0.80,
        10.0 if preferred else 20.0,
        0.01 if preferred else 0.02,
    )


def context() -> AcceptanceContext:
    return AcceptanceContext(
        "subject",
        "state",
        "verify",
        "policy",
        frozenset({"execution_result"}),
    )


def budget(**overrides) -> AcceptanceBudget:
    values = dict(
        money_limit=10.0,
        token_limit=1000,
        wall_time_limit_s=60.0,
        verifier_attempt_limit=3,
    )
    values.update(overrides)
    return AcceptanceBudget(**values)


def normalizer(*, passed: bool = True):
    def normalize(*, request, orchestrator_id, adapter_version, output, attempt_id):
        return EvidenceEnvelope(
            evidence_id=f"{request.execution_id}:{attempt_id}",
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
            payload_digest="digest",
            provenance_root="local-test",
            authority_id=request.context["authority_id"],
            passed=passed,
            created_at_epoch=request.context["created_at_epoch"],
        )
    return normalize


def registry_with(*items: FakeOrchestrator) -> OrchestratorRegistry:
    registry = OrchestratorRegistry()
    for item in items:
        registry.register(item)
    return registry


class MissionLifecycleControlPlaneV1Tests(unittest.TestCase):
    def setUp(self) -> None:
        self.mission = Mission("mission-r1", "finish work unit", frozenset({"workflow"}))
        self.policy = evaluate_policy(policy_bundle_id="policy", allowed=True)
        self.context = context()

    def test_happy_path_records_lifecycle(self):
        runtime = FakeOrchestrator("primary")
        outcome = execute_mission(
            mission=self.mission,
            registry=registry_with(runtime),
            pools=(pool("primary", preferred=True),),
            normalizers={"primary": normalizer()},
            policy=self.policy,
            budget=budget(),
            acceptance_context=self.context,
            execution_id_prefix="r1",
            now_epoch=100.0,
        )
        self.assertEqual(outcome.state.status, MissionStatus.ACCEPTED)
        self.assertEqual(
            outcome.state.history,
            (
                MissionStatus.CREATED,
                MissionStatus.PLANNING,
                MissionStatus.SELECTING,
                MissionStatus.RUNNING,
                MissionStatus.VERIFYING,
                MissionStatus.ACCEPTED,
            ),
        )
        self.assertEqual(len(outcome.state.attempts), 1)

    def test_no_eligible_orchestrator(self):
        runtime = FakeOrchestrator("primary")
        outcome = execute_mission(
            mission=self.mission,
            registry=registry_with(runtime),
            pools=(pool("primary", capabilities=frozenset({"other"})),),
            normalizers={"primary": normalizer()},
            policy=self.policy,
            budget=budget(),
            acceptance_context=self.context,
            execution_id_prefix="r1",
        )
        self.assertEqual(outcome.state.status, MissionStatus.FAILED)
        self.assertIn("no_eligible_orchestrator", outcome.acceptance.reasons)
        self.assertEqual(runtime.calls, 0)

    def test_policy_deny_blocks_before_runtime(self):
        runtime = FakeOrchestrator("primary")
        outcome = execute_mission_once(
            mission=self.mission,
            registry=registry_with(runtime),
            pools=(pool("primary"),),
            normalizers={"primary": normalizer()},
            policy=evaluate_policy(policy_bundle_id="policy", allowed=False),
            budget=budget(),
            acceptance_context=self.context,
            execution_id="r1-1",
        )
        self.assertEqual(outcome.state.status, MissionStatus.BLOCKED)
        self.assertEqual(outcome.acceptance.decision, AcceptanceDecision.BLOCK)
        self.assertEqual(runtime.calls, 0)

    def test_budget_exhausted_blocks_before_runtime(self):
        runtime = FakeOrchestrator("primary")
        outcome = execute_mission_once(
            mission=self.mission,
            registry=registry_with(runtime),
            pools=(pool("primary"),),
            normalizers={"primary": normalizer()},
            policy=self.policy,
            budget=budget(money_used=10.0),
            acceptance_context=self.context,
            execution_id="r1-1",
        )
        self.assertEqual(outcome.state.status, MissionStatus.BLOCKED)
        self.assertIn("budget_exhausted", outcome.acceptance.reasons)
        self.assertEqual(runtime.calls, 0)

    def test_selection_policy_can_reorder_only_routable_candidates(self):
        primary = FakeOrchestrator("primary")
        fallback = FakeOrchestrator("fallback")
        seen = []

        def choose_fallback(candidates, now_epoch):
            seen.append((tuple(item.orchestrator_id for item in candidates), now_epoch))
            return "fallback"

        outcome = execute_mission_once(
            mission=self.mission,
            registry=registry_with(primary, fallback),
            pools=(pool("primary", preferred=True), pool("fallback")),
            normalizers={"primary": normalizer(), "fallback": normalizer()},
            policy=self.policy,
            budget=budget(),
            acceptance_context=self.context,
            execution_id="r1-policy-1",
            now_epoch=100.0,
            selection_policy=choose_fallback,
        )

        self.assertEqual(outcome.orchestrator_id, "fallback")
        self.assertEqual(primary.calls, 0)
        self.assertEqual(fallback.calls, 1)
        self.assertEqual(seen, [(("primary", "fallback"), 100.0)])

    def test_selection_policy_cannot_reintroduce_quarantined_runtime(self):
        healthy = FakeOrchestrator("healthy")
        quarantined = FakeOrchestrator("quarantined")
        quarantined_pool = OrchestratorPoolState(
            "quarantined",
            OrchestratorStatus.QUARANTINED,
            frozenset({"workflow"}),
            1.0,
            1.0,
            1.0,
            1.0,
            0.0,
        )

        def choose_quarantined(candidates, now_epoch):
            self.assertEqual(
                tuple(item.orchestrator_id for item in candidates),
                ("healthy",),
            )
            return "quarantined"

        with self.assertRaisesRegex(ValueError, "non-routable orchestrator"):
            execute_mission_once(
                mission=self.mission,
                registry=registry_with(healthy, quarantined),
                pools=(pool("healthy"), quarantined_pool),
                normalizers={"healthy": normalizer(), "quarantined": normalizer()},
                policy=self.policy,
                budget=budget(),
                acceptance_context=self.context,
                execution_id="r1-policy-2",
                now_epoch=100.0,
                selection_policy=choose_quarantined,
            )

        self.assertEqual(healthy.calls, 0)
        self.assertEqual(quarantined.calls, 0)

    def test_runtime_failure_replans_to_fallback(self):
        primary = FakeOrchestrator("primary", succeeds=False)
        fallback = FakeOrchestrator("fallback")
        outcome = execute_mission(
            mission=self.mission,
            registry=registry_with(primary, fallback),
            pools=(pool("primary", preferred=True), pool("fallback")),
            normalizers={"primary": normalizer(), "fallback": normalizer()},
            policy=self.policy,
            budget=budget(),
            acceptance_context=self.context,
            execution_id_prefix="r1",
            now_epoch=100.0,
            max_attempts=2,
        )
        self.assertEqual(outcome.state.status, MissionStatus.ACCEPTED)
        self.assertEqual(outcome.attempted_orchestrators, ("primary", "fallback"))
        self.assertIn(MissionStatus.REPLANNING, outcome.state.history)
        self.assertEqual([a.execution_status for a in outcome.state.attempts], [ExecutionStatus.FAILED, ExecutionStatus.SUCCEEDED])

    def test_runtime_success_cannot_force_acceptance(self):
        runtime = FakeOrchestrator("primary")
        outcome = execute_mission(
            mission=self.mission,
            registry=registry_with(runtime),
            pools=(pool("primary"),),
            normalizers={"primary": normalizer(passed=False)},
            policy=self.policy,
            budget=budget(),
            acceptance_context=self.context,
            execution_id_prefix="r1",
            now_epoch=100.0,
            max_attempts=1,
        )
        self.assertEqual(outcome.execution.status, ExecutionStatus.SUCCEEDED)
        self.assertNotEqual(outcome.acceptance.decision, AcceptanceDecision.ACCEPT)
        self.assertEqual(outcome.state.status, MissionStatus.BLOCKED)

    def test_acceptance_success_is_final_authority(self):
        runtime = FakeOrchestrator("primary")
        outcome = execute_mission_once(
            mission=self.mission,
            registry=registry_with(runtime),
            pools=(pool("primary"),),
            normalizers={"primary": normalizer()},
            policy=self.policy,
            budget=budget(),
            acceptance_context=self.context,
            execution_id="r1-1",
            now_epoch=100.0,
        )
        self.assertEqual(outcome.acceptance.decision, AcceptanceDecision.ACCEPT)
        self.assertEqual(outcome.state.status, MissionStatus.ACCEPTED)
        self.assertEqual(outcome.budget.verifier_attempts_used, 1)

    def test_replan_limit_reached_is_auditable(self):
        primary = FakeOrchestrator("primary", succeeds=False)
        fallback = FakeOrchestrator("fallback")
        outcome = execute_mission(
            mission=self.mission,
            registry=registry_with(primary, fallback),
            pools=(pool("primary", preferred=True), pool("fallback")),
            normalizers={"primary": normalizer(), "fallback": normalizer()},
            policy=self.policy,
            budget=budget(),
            acceptance_context=self.context,
            execution_id_prefix="r1",
            max_attempts=1,
        )
        self.assertEqual(outcome.state.status, MissionStatus.FAILED)
        self.assertIn("replan_limit_reached", outcome.acceptance.reasons)
        self.assertEqual(primary.calls, 1)
        self.assertEqual(fallback.calls, 0)

    def test_attempted_runtimes_and_attempt_ids_are_recorded(self):
        primary = FakeOrchestrator("primary", succeeds=False)
        fallback = FakeOrchestrator("fallback")
        outcome = execute_mission(
            mission=self.mission,
            registry=registry_with(primary, fallback),
            pools=(pool("primary", preferred=True), pool("fallback")),
            normalizers={"primary": normalizer(), "fallback": normalizer()},
            policy=self.policy,
            budget=budget(),
            acceptance_context=self.context,
            execution_id_prefix="ledger",
            now_epoch=100.0,
            max_attempts=2,
        )
        self.assertEqual(outcome.attempted_orchestrators, ("primary", "fallback"))
        self.assertEqual([a.attempt_number for a in outcome.state.attempts], [1, 2])
        self.assertEqual([a.execution_id for a in outcome.state.attempts], ["ledger-1", "ledger-2"])

    def test_core_remains_framework_sdk_neutral(self):
        source = inspect.getsource(core_module).lower()
        self.assertNotIn("langgraph", source)
        self.assertNotIn("crewai", source)
        self.assertNotIn("openai", source)


if __name__ == "__main__":
    unittest.main(verbosity=2)
