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


class _Planner:
    def plan(self, objective):
        return WorkGraph(
            "metao",
            (
                WorkUnit("upstream", "produce upstream artifact"),
                WorkUnit("downstream", "consume accepted upstream", ("upstream",)),
            ),
        )

    def corrective_work(self, objective, failed_unit, verification, graph):
        return WorkUnit(
            "repair-upstream",
            "repair rejected upstream artifact",
            (failed_unit.work_unit_id,),
            corrective=True,
            corrects_work_unit_id=failed_unit.work_unit_id,
        )


class _Scheduler:
    def select(self, unit, *, excluded_executor_ids):
        return ExecutorTarget("executor-a", "provider-a")


class _Runner:
    def __init__(self):
        self.calls: list[str] = []

    def run(self, objective, unit, target, checkpoint):
        self.calls.append(unit.work_unit_id)
        state = f"state-{unit.work_unit_id}"
        return WorkExecutionResult(
            unit.work_unit_id,
            target.executor_id,
            target.provider_id,
            WorkExecutionStatus.SUCCEEDED,
            state,
            artifact_ref=state,
            evidence_ref=f"execution://{unit.work_unit_id}",
        )


class _Repository:
    def initial(self, objective):
        return RepositoryCheckpoint("checkpoint-root", "repo-509", "root", "artifact-root")

    def capture(self, objective, unit, execution):
        return RepositoryCheckpoint(
            f"checkpoint-{unit.work_unit_id}",
            "repo-509",
            execution.repository_state_id,
            execution.artifact_ref,
        )

    def handoff(self, checkpoint, *, from_executor_id, to_executor_id):
        return checkpoint


class _Verifier:
    def __init__(self, *, correction_passes: bool = True):
        self.correction_passes = correction_passes

    def verify(self, objective, unit, execution, checkpoint):
        accepted = unit.work_unit_id != "upstream"
        if unit.work_unit_id == "repair-upstream":
            accepted = self.correction_passes
        return WorkVerificationResult(
            accepted,
            "independent-verifier",
            f"verification://{unit.work_unit_id}",
            f"test://{unit.work_unit_id}",
            "rejected" if not accepted else "",
        )


class Issue509DependencyAcceptanceTests(unittest.TestCase):
    def test_downstream_waits_for_corrective_acceptance(self):
        runner = _Runner()
        result = supervise_project(
            objective=ProjectObjective("project-509", "req-509", "deliver accepted dependency chain"),
            planner=_Planner(),
            scheduler=_Scheduler(),
            runner=runner,
            repository=_Repository(),
            verifier=_Verifier(),
        )

        self.assertEqual(result.verdict, ProjectVerdict.PROJECT_ACCEPTED)
        self.assertEqual(runner.calls, ["upstream", "repair-upstream", "downstream"])
        records = {record.work_unit_id: record.verdict for record in result.traceability}
        self.assertEqual(records["upstream"], "CORRECTED_PASS")
        self.assertEqual(records["repair-upstream"], "PASS")
        self.assertEqual(records["downstream"], "PASS")

    def test_rejected_correction_never_releases_downstream(self):
        runner = _Runner()
        result = supervise_project(
            objective=ProjectObjective("project-509", "req-509", "deliver accepted dependency chain"),
            planner=_Planner(),
            scheduler=_Scheduler(),
            runner=runner,
            repository=_Repository(),
            verifier=_Verifier(correction_passes=False),
        )

        self.assertEqual(result.verdict, ProjectVerdict.PROJECT_BLOCKED)
        self.assertEqual(runner.calls, ["upstream", "repair-upstream"])
        self.assertNotIn("downstream", runner.calls)
        self.assertIn("corrective work failed verification", result.reason)


if __name__ == "__main__":
    unittest.main(verbosity=2)
