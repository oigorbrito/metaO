from __future__ import annotations

import unittest

from metao.acceptance import AcceptanceContext, AcceptanceDecision
from metao.control_plane import MissionAttempt, execute_mission_once
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
from metao.governance import AcceptanceBudget, PolicyDecision, PolicyEffect
from metao.strategy import OrchestratorPoolState, OrchestratorStatus


class TinyRuntime:
    def __init__(self) -> None:
        self.calls = 0
        self._descriptor = OrchestratorDescriptor("tiny", "v1", frozenset({"cap"}))

    @property
    def descriptor(self) -> OrchestratorDescriptor:
        return self._descriptor

    def health(self) -> HealthReport:
        return HealthReport(HealthStatus.HEALTHY)

    def execute(self, request: ExecutionRequest) -> ExecutionResult:
        self.calls += 1
        return ExecutionResult(request.execution_id, "tiny", ExecutionStatus.FAILED, error="probe")

    def cancel(self, execution_id: str) -> None:
        return None


def budget() -> AcceptanceBudget:
    return AcceptanceBudget(10.0, 100, 30.0, 3)


def context() -> AcceptanceContext:
    return AcceptanceContext(
        "subject",
        "state",
        "verification",
        "policy",
        frozenset({"obligation"}),
    )


def allowed() -> PolicyDecision:
    return PolicyDecision(PolicyEffect.ALLOW, "policy")


def runtime_inputs():
    runtime = TinyRuntime()
    registry = OrchestratorRegistry()
    registry.register(runtime)
    pools = (
        OrchestratorPoolState(
            "tiny",
            OrchestratorStatus.HEALTHY,
            capabilities=frozenset({"cap"}),
        ),
    )
    return runtime, registry, pools


class ControlPlaneNonFiniteClockTests(unittest.TestCase):
    def test_non_finite_now_epoch_is_rejected_before_policy_or_selection(self) -> None:
        mission = Mission("m", "clock", frozenset({"cap"}))
        for value in (float("nan"), float("inf"), float("-inf")):
            with self.subTest(value=value):
                with self.assertRaisesRegex(ValueError, "mission current time must be finite"):
                    execute_mission_once(
                        mission=mission,
                        registry=OrchestratorRegistry(),
                        pools=(),
                        normalizers={},
                        policy=PolicyDecision(PolicyEffect.DENY, "policy"),
                        budget=budget(),
                        acceptance_context=context(),
                        execution_id="exec",
                        now_epoch=value,
                    )

    def test_non_finite_attempt_start_is_rejected_before_dispatch(self) -> None:
        mission = Mission("m", "clock", frozenset({"cap"}))
        for value in (float("nan"), float("inf"), float("-inf")):
            runtime, registry, pools = runtime_inputs()
            started = []
            with self.subTest(value=value):
                with self.assertRaisesRegex(ValueError, "mission attempt start timestamp must be finite"):
                    execute_mission_once(
                        mission=mission,
                        registry=registry,
                        pools=pools,
                        normalizers={"tiny": lambda **kwargs: None},
                        policy=allowed(),
                        budget=budget(),
                        acceptance_context=context(),
                        execution_id="exec",
                        now_epoch=0.0,
                        attempt_clock=lambda: value,
                        on_attempt_started=started.append,
                    )
                self.assertEqual(runtime.calls, 0)
                self.assertEqual(started, [])

    def test_non_finite_attempt_end_is_rejected_before_completion_callback(self) -> None:
        mission = Mission("m", "clock", frozenset({"cap"}))
        for value in (float("nan"), float("inf"), float("-inf")):
            runtime, registry, pools = runtime_inputs()
            readings = iter((10.0, value))
            finished = []
            with self.subTest(value=value):
                with self.assertRaisesRegex(ValueError, "mission attempt end timestamp must be finite"):
                    execute_mission_once(
                        mission=mission,
                        registry=registry,
                        pools=pools,
                        normalizers={"tiny": lambda **kwargs: None},
                        policy=allowed(),
                        budget=budget(),
                        acceptance_context=context(),
                        execution_id="exec",
                        now_epoch=0.0,
                        attempt_clock=lambda: next(readings),
                        on_attempt_finished=lambda *args: finished.append(args),
                    )
                self.assertEqual(runtime.calls, 1)
                self.assertEqual(finished, [])

    def test_reversed_attempt_clock_is_rejected(self) -> None:
        mission = Mission("m", "clock", frozenset({"cap"}))
        runtime, registry, pools = runtime_inputs()
        readings = iter((10.0, 9.0))
        with self.assertRaisesRegex(ValueError, "mission attempt end timestamp cannot precede start"):
            execute_mission_once(
                mission=mission,
                registry=registry,
                pools=pools,
                normalizers={"tiny": lambda **kwargs: None},
                policy=allowed(),
                budget=budget(),
                acceptance_context=context(),
                execution_id="exec",
                now_epoch=0.0,
                attempt_clock=lambda: next(readings),
            )
        self.assertEqual(runtime.calls, 1)

    def test_mission_attempt_rejects_non_finite_timestamp_and_cost(self) -> None:
        base = dict(
            attempt_number=1,
            execution_id="exec",
            orchestrator_id="tiny",
            execution_status=ExecutionStatus.FAILED,
            acceptance_decision=AcceptanceDecision.NOT_DONE,
        )
        for value in (float("nan"), float("inf"), float("-inf")):
            with self.subTest(field="start", value=value):
                with self.assertRaisesRegex(ValueError, "mission attempt start timestamp must be finite"):
                    MissionAttempt(**base, started_at_epoch=value)
            with self.subTest(field="end", value=value):
                with self.assertRaisesRegex(ValueError, "mission attempt end timestamp must be finite"):
                    MissionAttempt(**base, ended_at_epoch=value)
            with self.subTest(field="cost", value=value):
                with self.assertRaisesRegex(ValueError, "mission attempt cost must be finite"):
                    MissionAttempt(**base, cost=value)

    def test_finite_attempt_clock_is_preserved(self) -> None:
        mission = Mission("m", "clock", frozenset({"cap"}))
        runtime, registry, pools = runtime_inputs()
        readings = iter((10.0, 11.0))
        outcome = execute_mission_once(
            mission=mission,
            registry=registry,
            pools=pools,
            normalizers={"tiny": lambda **kwargs: None},
            policy=allowed(),
            budget=budget(),
            acceptance_context=context(),
            execution_id="exec",
            now_epoch=1.0,
            attempt_clock=lambda: next(readings),
        )
        self.assertEqual(runtime.calls, 1)
        self.assertIsNotNone(outcome.state)
        attempt = outcome.state.attempts[-1]
        self.assertEqual(attempt.started_at_epoch, 10.0)
        self.assertEqual(attempt.ended_at_epoch, 11.0)


if __name__ == "__main__":
    unittest.main(verbosity=2)
