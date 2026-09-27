from __future__ import annotations

import unittest

from metao.acceptance import AcceptanceContext, EvidenceEnvelope
from metao.control_plane import execute_mission, execute_mission_once
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


class CaptureOrchestrator:
    def __init__(self, orchestrator_id: str, *, succeeds: bool = True) -> None:
        self.requests: list[ExecutionRequest] = []
        self.succeeds = succeeds
        self._descriptor = OrchestratorDescriptor(orchestrator_id, "1.0", frozenset({"workflow"}))

    @property
    def descriptor(self) -> OrchestratorDescriptor:
        return self._descriptor

    def health(self) -> HealthReport:
        return HealthReport(HealthStatus.HEALTHY)

    def execute(self, request: ExecutionRequest) -> ExecutionResult:
        self.requests.append(request)
        return ExecutionResult(
            request.execution_id,
            self.descriptor.orchestrator_id,
            ExecutionStatus.SUCCEEDED if self.succeeds else ExecutionStatus.FAILED,
            output={"result": "ok"} if self.succeeds else {},
            error=None if self.succeeds else "runtime failure",
        )

    def cancel(self, execution_id: str) -> None:
        pass


def pool(orchestrator_id: str, *, score: float = 0.99) -> OrchestratorPoolState:
    return OrchestratorPoolState(
        orchestrator_id,
        OrchestratorStatus.HEALTHY,
        frozenset({"workflow"}),
        score,
        score,
        score,
        10.0,
        0.01,
    )


def acceptance_context() -> AcceptanceContext:
    return AcceptanceContext(
        "subject",
        "state",
        "verify",
        "policy",
        frozenset({"execution_result"}),
    )


def budget() -> AcceptanceBudget:
    return AcceptanceBudget(10.0, 1000, 60.0, 3)


def normalizer(*, request, orchestrator_id, adapter_version, output, attempt_id):
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
        provenance_root="issue-511-test",
        authority_id=request.context["authority_id"],
        passed=True,
        created_at_epoch=request.context["created_at_epoch"],
    )


class ProjectExecutionContextTests(unittest.TestCase):
    def setUp(self) -> None:
        self.mission = Mission("mission-511", "execute project work", frozenset({"workflow"}))
        self.policy = evaluate_policy(policy_bundle_id="policy", allowed=True)
        self.acceptance = acceptance_context()
        self.project_context = {
            "project_id": "project-360",
            "work_unit_id": "wu-1",
            "checkpoint_id": "checkpoint-1",
            "repository_id": "repo-metao",
            "repository_state_id": "bedf5badea284132be71d3d34d512529c13c40a1",
            "artifact_ref": "git:bedf5badea284132be71d3d34d512529c13c40a1",
        }

    def _registry(self, *runtimes: CaptureOrchestrator) -> OrchestratorRegistry:
        registry = OrchestratorRegistry()
        for runtime in runtimes:
            registry.register(runtime)
        return registry

    def test_execute_mission_once_carries_external_context_to_exact_request(self):
        runtime = CaptureOrchestrator("primary")
        execute_mission_once(
            mission=self.mission,
            registry=self._registry(runtime),
            pools=(pool("primary"),),
            normalizers={"primary": normalizer},
            policy=self.policy,
            budget=budget(),
            acceptance_context=self.acceptance,
            execution_id="issue-511-1",
            execution_context=self.project_context,
            now_epoch=100.0,
        )

        self.assertEqual(len(runtime.requests), 1)
        request = runtime.requests[0]
        for key, value in self.project_context.items():
            self.assertEqual(request.context[key], value)

    def test_reserved_context_collision_fails_closed_before_dispatch(self):
        runtime = CaptureOrchestrator("primary")
        with self.assertRaisesRegex(ValueError, "reserved execution context"):
            execute_mission_once(
                mission=self.mission,
                registry=self._registry(runtime),
                pools=(pool("primary"),),
                normalizers={"primary": normalizer},
                policy=self.policy,
                budget=budget(),
                acceptance_context=self.acceptance,
                execution_id="issue-511-collision",
                execution_context={"project_id": "project-360", "authority_id": "caller"},
            )
        self.assertEqual(runtime.requests, [])

    def test_replans_preserve_identical_external_context(self):
        first = CaptureOrchestrator("first", succeeds=False)
        second = CaptureOrchestrator("second", succeeds=True)
        execute_mission(
            mission=self.mission,
            registry=self._registry(first, second),
            pools=(pool("first", score=0.99), pool("second", score=0.90)),
            normalizers={"first": normalizer, "second": normalizer},
            policy=self.policy,
            budget=budget(),
            acceptance_context=self.acceptance,
            execution_id_prefix="issue-511-replan",
            execution_context=self.project_context,
            max_attempts=2,
            now_epoch=100.0,
        )

        self.assertEqual(len(first.requests), 1)
        self.assertEqual(len(second.requests), 1)
        first_external = {key: first.requests[0].context[key] for key in self.project_context}
        second_external = {key: second.requests[0].context[key] for key in self.project_context}
        self.assertEqual(first_external, self.project_context)
        self.assertEqual(second_external, self.project_context)


if __name__ == "__main__":
    unittest.main()
