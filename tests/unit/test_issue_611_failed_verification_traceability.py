from __future__ import annotations

import unittest

from metao.project_supervision import (
    ExecutorTarget,
    ProjectObjective,
    ProjectVerdict,
    RepositoryCheckpoint,
    WorkExecutionResult,
    WorkExecutionStatus,
    WorkGraph,
    WorkUnit,
    WorkVerificationResult,
    supervise_project,
)


class Planner:
    def __init__(self) -> None:
        self.original = WorkUnit("prepare", "prepare artifact")
        self.corrective = WorkUnit(
            "repair-prepare",
            "repair artifact",
            dependencies=("prepare",),
            corrective=True,
            corrects_work_unit_id="prepare",
        )

    def plan(self, objective: ProjectObjective) -> WorkGraph:
        del objective
        return WorkGraph("metao", (self.original,))

    def corrective_work(self, objective, failed_unit, verification, graph):
        del objective, verification, graph
        if failed_unit.work_unit_id == self.original.work_unit_id:
            return self.corrective
        return None


class Scheduler:
    def select(self, unit: WorkUnit, *, excluded_executor_ids: frozenset[str]):
        del excluded_executor_ids
        if unit.corrective:
            return ExecutorTarget("executor-c", "provider-y")
        return ExecutorTarget("executor-a", "provider-x")


class Runner:
    def run(self, objective, unit, target, checkpoint):
        del objective, checkpoint
        state = "b" * 40 if unit.corrective else "a" * 40
        return WorkExecutionResult(
            unit.work_unit_id,
            target.executor_id,
            target.provider_id,
            WorkExecutionStatus.SUCCEEDED,
            state,
            f"git://repo/{state}",
        )


class Repository:
    def __init__(self) -> None:
        self.checkpoint = RepositoryCheckpoint(
            "initial",
            "repo",
            "0" * 40,
            f"git://repo/{'0' * 40}",
        )

    def initial(self, objective):
        del objective
        return self.checkpoint

    def capture(self, objective, unit, execution):
        del objective, unit
        self.checkpoint = RepositoryCheckpoint(
            f"cp-{execution.work_unit_id}",
            "repo",
            execution.repository_state_id,
            execution.artifact_ref or "",
        )
        return self.checkpoint

    def handoff(self, checkpoint, *, from_executor_id, to_executor_id):
        del from_executor_id, to_executor_id
        return checkpoint


class Verifier:
    def __init__(self, *, corrective_accepts: bool) -> None:
        self.corrective_accepts = corrective_accepts

    def verify(self, objective, unit, execution, checkpoint):
        del objective, execution, checkpoint
        if unit.corrective:
            return WorkVerificationResult(
                self.corrective_accepts,
                "independent-verifier",
                "evidence://repair",
                "test://repair",
                "repair verdict",
            )
        return WorkVerificationResult(
            False,
            "independent-verifier",
            "evidence://prepare-failed",
            "test://prepare",
            "prepare failed verification",
        )


class FailedVerificationTraceabilityTests(unittest.TestCase):
    def _run(self, *, corrective_accepts: bool):
        return supervise_project(
            objective=ProjectObjective("project-360", "req-360", "deliver"),
            planner=Planner(),
            scheduler=Scheduler(),
            runner=Runner(),
            repository=Repository(),
            verifier=Verifier(corrective_accepts=corrective_accepts),
        )

    def test_failed_verification_is_preserved_before_corrected_pass(self):
        result = self._run(corrective_accepts=True)

        self.assertEqual(result.verdict, ProjectVerdict.PROJECT_ACCEPTED)
        self.assertEqual(
            [(record.work_unit_id, record.test_ref, record.verdict) for record in result.traceability],
            [
                ("prepare", "test://prepare", "FAIL"),
                ("repair-prepare", "test://repair", "PASS"),
                ("prepare", "test://repair", "CORRECTED_PASS"),
            ],
        )
        self.assertEqual(result.traceability[0].artifact_ref, f"git://repo/{'a' * 40}")
        self.assertEqual(result.traceability[2].artifact_ref, f"git://repo/{'b' * 40}")

    def test_failed_corrective_verification_is_recorded_before_project_blocked(self):
        result = self._run(corrective_accepts=False)

        self.assertEqual(result.verdict, ProjectVerdict.PROJECT_BLOCKED)
        self.assertEqual(
            [(record.work_unit_id, record.test_ref, record.verdict) for record in result.traceability],
            [
                ("prepare", "test://prepare", "FAIL"),
                ("repair-prepare", "test://repair", "FAIL"),
            ],
        )
        self.assertIn("corrective work failed verification", result.reason)


if __name__ == "__main__":
    unittest.main()
