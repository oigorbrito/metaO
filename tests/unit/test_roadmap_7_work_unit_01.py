from __future__ import annotations

from hashlib import sha256
import json
import unittest

from metao.acceptance import AcceptanceContext, AcceptanceDecision, EvidenceEnvelope
from metao.control_plane import MissionStatus, execute_mission
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
from metao.replan import FailureClass
from metao.strategy import OrchestratorPoolState, OrchestratorStatus


def normalize_evidence(
    *,
    request: ExecutionRequest,
    orchestrator_id: str,
    adapter_version: str,
    output,
    attempt_id: str,
) -> EvidenceEnvelope:
    payload = json.dumps(output, sort_keys=True, default=str, separators=(",", ":")).encode()
    context = request.context
    return EvidenceEnvelope(
        evidence_id=f"{request.execution_id}:result",
        obligation_id=str(context.get("obligation_id", "execution_result")),
        mission_id=request.mission.mission_id,
        execution_id=request.execution_id,
        orchestrator_id=orchestrator_id,
        adapter_version=adapter_version,
        attempt_id=attempt_id,
        subject_id=str(context.get("subject_id", request.mission.mission_id)),
        subject_state_id=str(context.get("subject_state_id", "state-1")),
        verification_context_id=str(context.get("verification_context_id", "verify-1")),
        policy_bundle_id=str(context.get("policy_bundle_id", "policy-r7")),
        verifier_id=str(context.get("verifier_id", "adapter-observer")),
        payload_digest=sha256(payload).hexdigest(),
        provenance_root=f"test:{orchestrator_id}:{request.execution_id}",
        authority_id=str(context.get("authority_id", "metao-runtime")),
        passed=True,
        created_at_epoch=float(context.get("created_at_epoch", 0.0)),
    )


class FakeOrchestrator:
    def __init__(
        self,
        orchestrator_id: str,
        *,
        status: ExecutionStatus,
        error: str = "",
        output: dict | None = None,
    ) -> None:
        self.calls = 0
        self._status = status
        self._error = error
        self._output = dict(output or {})
        self._descriptor = OrchestratorDescriptor(
            orchestrator_id,
            "1",
            frozenset({"workflow"}),
        )

    @property
    def descriptor(self) -> OrchestratorDescriptor:
        return self._descriptor

    def health(self) -> HealthReport:
        return HealthReport(HealthStatus.HEALTHY)

    def execute(self, request: ExecutionRequest) -> ExecutionResult:
        self.calls += 1
        return ExecutionResult(
            request.execution_id,
            self.descriptor.orchestrator_id,
            self._status,
            output=self._output,
            error=self._error,
        )

    def cancel(self, execution_id: str) -> None:
        pass


def pool(orchestrator_id: str, *, preferred: bool) -> OrchestratorPoolState:
    return OrchestratorPoolState(
        orchestrator_id,
        OrchestratorStatus.HEALTHY,
        frozenset({"workflow"}),
        1.0 if preferred else 0.8,
        1.0 if preferred else 0.8,
        1.0 if preferred else 0.8,
        1.0 if preferred else 20.0,
        0.0 if preferred else 0.1,
    )


def run_mission(
    orchestrators: tuple[FakeOrchestrator, ...],
    pools: tuple[OrchestratorPoolState, ...],
    *,
    max_attempts: int = 3,
    allowed: bool = True,
):
    registry = OrchestratorRegistry()
    for item in orchestrators:
        registry.register(item)
    return execute_mission(
        mission=Mission("r7-mission", "exercise failure-aware replanning", frozenset({"workflow"})),
        registry=registry,
        pools=pools,
        normalizers={item.descriptor.orchestrator_id: normalize_evidence for item in orchestrators},
        policy=evaluate_policy(policy_bundle_id="policy-r7", allowed=allowed),
        budget=AcceptanceBudget(10.0, 10_000, 60.0, 10),
        acceptance_context=AcceptanceContext(
            "subject-r7",
            "state-r7",
            "verify-r7",
            "policy-r7",
            frozenset({"execution_result"}),
        ),
        execution_id_prefix="r7-exec",
        now_epoch=100.0,
        max_attempts=max_attempts,
    )


class Roadmap7WorkUnit01Tests(unittest.TestCase):
    def test_timeout_failure_replans_to_next_runtime(self):
        primary = FakeOrchestrator(
            "primary",
            status=ExecutionStatus.FAILED,
            error="request timed out",
        )
        fallback = FakeOrchestrator(
            "fallback",
            status=ExecutionStatus.SUCCEEDED,
            output={"result": "recovered"},
        )

        outcome = run_mission(
            (primary, fallback),
            (pool("primary", preferred=True), pool("fallback", preferred=False)),
            max_attempts=2,
        )

        self.assertEqual(outcome.attempted_orchestrators, ("primary", "fallback"))
        self.assertEqual(outcome.acceptance.decision, AcceptanceDecision.ACCEPT)
        self.assertEqual(outcome.state.status, MissionStatus.ACCEPTED)
        self.assertIn(MissionStatus.REPLANNING, outcome.state.history)
        self.assertEqual(outcome.state.attempts[0].failure_class, FailureClass.TIMEOUT)
        self.assertEqual(primary.calls, 1)
        self.assertEqual(fallback.calls, 1)

    def test_runtime_error_text_cannot_manufacture_policy_authority(self):
        primary = FakeOrchestrator(
            "primary",
            status=ExecutionStatus.FAILED,
            error="policy denied by downstream runtime provider",
        )
        fallback = FakeOrchestrator(
            "fallback",
            status=ExecutionStatus.SUCCEEDED,
            output={"result": "fallback-ok"},
        )

        outcome = run_mission(
            (primary, fallback),
            (pool("primary", preferred=True), pool("fallback", preferred=False)),
            max_attempts=2,
        )

        self.assertEqual(outcome.state.attempts[0].failure_class, FailureClass.RUNTIME)
        self.assertEqual(outcome.attempted_orchestrators, ("primary", "fallback"))
        self.assertEqual(outcome.acceptance.decision, AcceptanceDecision.ACCEPT)

    def test_spontaneous_runtime_cancellation_halts_without_failover(self):
        primary = FakeOrchestrator(
            "primary",
            status=ExecutionStatus.CANCELLED,
            error="cancelled",
        )
        fallback = FakeOrchestrator(
            "fallback",
            status=ExecutionStatus.SUCCEEDED,
            output={"result": "must-not-run"},
        )

        outcome = run_mission(
            (primary, fallback),
            (pool("primary", preferred=True), pool("fallback", preferred=False)),
            max_attempts=2,
        )

        self.assertEqual(outcome.attempted_orchestrators, ("primary",))
        self.assertEqual(outcome.state.status, MissionStatus.CANCELLED)
        self.assertEqual(outcome.state.attempts[0].failure_class, FailureClass.CANCELLED)
        self.assertIn("replan_halt:cancelled", outcome.acceptance.reasons)
        self.assertEqual(fallback.calls, 0)

    def test_replan_limit_escalates_after_exact_attempt_budget(self):
        first = FakeOrchestrator("first", status=ExecutionStatus.FAILED, error="worker runtime crashed")
        second = FakeOrchestrator("second", status=ExecutionStatus.FAILED, error="temporary connection failure")
        third = FakeOrchestrator("third", status=ExecutionStatus.SUCCEEDED, output={"result": "too-late"})

        outcome = run_mission(
            (first, second, third),
            (
                pool("first", preferred=True),
                pool("second", preferred=False),
                OrchestratorPoolState(
                    "third",
                    OrchestratorStatus.HEALTHY,
                    frozenset({"workflow"}),
                    0.7,
                    0.7,
                    0.7,
                    30.0,
                    0.2,
                ),
            ),
            max_attempts=2,
        )

        self.assertEqual(outcome.attempted_orchestrators, ("first", "second"))
        self.assertEqual(outcome.state.status, MissionStatus.FAILED)
        self.assertIn("replan_limit_reached", outcome.acceptance.reasons)
        self.assertEqual(third.calls, 0)

    def test_metao_policy_gate_remains_authoritative_before_runtime_execution(self):
        runtime = FakeOrchestrator(
            "runtime",
            status=ExecutionStatus.SUCCEEDED,
            output={"result": "must-not-run"},
        )

        outcome = run_mission(
            (runtime,),
            (pool("runtime", preferred=True),),
            max_attempts=2,
            allowed=False,
        )

        self.assertEqual(outcome.attempted_orchestrators, ())
        self.assertEqual(outcome.state.status, MissionStatus.BLOCKED)
        self.assertEqual(outcome.acceptance.decision, AcceptanceDecision.BLOCK)
        self.assertEqual(runtime.calls, 0)


if __name__ == "__main__":
    unittest.main(verbosity=2)
