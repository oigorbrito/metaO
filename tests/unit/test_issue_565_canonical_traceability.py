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
    def plan(self, objective):
        return WorkGraph("metao", (WorkUnit("prepare", "prepare artifact"),))

    def corrective_work(self, objective, failed_unit, verification, graph):
        return WorkUnit(
            "repair-prepare",
            "repair preparation",
            dependencies=(failed_unit.work_unit_id,),
            corrective=True,
            corrects_work_unit_id=failed_unit.work_unit_id,
        )


class Scheduler:
    def select(self, unit, *, excluded_executor_ids):
        return ExecutorTarget("executor-a", "provider-a")


class Runner:
    def run(self, objective, unit, target, checkpoint):
        state = f"commit-{unit.work_unit_id}"
        return WorkExecutionResult(
            unit.work_unit_id,
            target.executor_id,
            target.provider_id,
            WorkExecutionStatus.SUCCEEDED,
            state,
            artifact_ref=state,
            evidence_ref="execution://provider-controlled-not-canonical",
        )


class Repository:
    def initial(self, objective):
        return RepositoryCheckpoint("root", "repo", "root", "repo://root")

    def capture(self, objective, unit, execution):
        return RepositoryCheckpoint(
            f"checkpoint-{unit.work_unit_id}",
            "repo",
            execution.repository_state_id,
            execution.artifact_ref,
        )

    def handoff(self, checkpoint, *, from_executor_id, to_executor_id):
        return checkpoint


class Verifier:
    def verify(self, objective, unit, execution, checkpoint):
        if unit.work_unit_id == "prepare":
            return WorkVerificationResult(
                False,
                "independent-verifier",
                "verification://prepare/rejected",
                "test://prepare/acceptance",
                "prepare needs correction",
            )
        return WorkVerificationResult(
            True,
            "independent-verifier",
            "verification://repair-prepare/accepted",
            "test://repair-prepare/acceptance",
        )


class Issue565CanonicalTraceabilityTests(unittest.TestCase):
    def test_failed_verification_is_historical_and_correction_can_accept_project(self):
        result = supervise_project(
            objective=ProjectObjective("project-565", "req-565", "traceable correction"),
            planner=Planner(),
            scheduler=Scheduler(),
            runner=Runner(),
            repository=Repository(),
            verifier=Verifier(),
        )

        self.assertEqual(ProjectVerdict.PROJECT_ACCEPTED, result.verdict)
        history = [
            (record.work_unit_id, record.verdict, record.evidence_ref)
            for record in result.traceability
        ]
        self.assertEqual(
            [
                ("prepare", "FAIL", "verification://prepare/rejected"),
                ("repair-prepare", "PASS", "verification://repair-prepare/accepted"),
                ("prepare", "CORRECTED_PASS", "verification://repair-prepare/accepted"),
            ],
            history,
        )

    def test_canonical_traceability_uses_verifier_evidence_not_execution_evidence(self):
        result = supervise_project(
            objective=ProjectObjective("project-565", "req-565", "traceable correction"),
            planner=Planner(),
            scheduler=Scheduler(),
            runner=Runner(),
            repository=Repository(),
            verifier=Verifier(),
        )

        self.assertTrue(result.traceability)
        self.assertTrue(
            all(
                record.evidence_ref.startswith("verification://")
                for record in result.traceability
            )
        )
        self.assertNotIn(
            "execution://provider-controlled-not-canonical",
            {record.evidence_ref for record in result.traceability},
        )


if __name__ == "__main__":
    unittest.main()
