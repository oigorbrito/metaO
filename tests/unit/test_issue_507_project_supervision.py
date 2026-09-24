from __future__ import annotations

import unittest

from metao.project_supervision import (
    ExecutorTarget,
    ProjectObjective,
    ProjectTraceKind,
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
    def plan(self, objective: ProjectObjective) -> WorkGraph:
        return WorkGraph(
            "metao",
            (
                WorkUnit("discover", "discover repository"),
                WorkUnit("implement", "implement change", ("discover",)),
                WorkUnit("verify", "verify implementation", ("implement",)),
            ),
        )

    def corrective_work(self, objective, failed_unit, verification, graph):
        return WorkUnit(
            "corrective-proof",
            "repair failed verification evidence",
            (failed_unit.work_unit_id,),
            corrective=True,
            corrects_work_unit_id=failed_unit.work_unit_id,
        )


class _Scheduler:
    def __init__(self) -> None:
        self.targets = (
            ExecutorTarget("executor-a", "provider-a"),
            ExecutorTarget("executor-b", "provider-b"),
        )

    def select(self, unit, *, excluded_executor_ids):
        for target in self.targets:
            if target.executor_id not in excluded_executor_ids:
                return target
        return None


class _Runner:
    def __init__(self) -> None:
        self.calls: list[tuple[str, str, str]] = []
        self.failed_capacity = False

    def run(self, objective, unit, target, checkpoint):
        self.calls.append((unit.work_unit_id, target.executor_id, checkpoint.state_id))
        if unit.work_unit_id == "implement" and target.executor_id == "executor-a" and not self.failed_capacity:
            self.failed_capacity = True
            return WorkExecutionResult(
                unit.work_unit_id,
                target.executor_id,
                target.provider_id,
                WorkExecutionStatus.CAPACITY_FAILED,
                checkpoint.state_id,
                evidence_ref="capacity://provider-a/quota",
            )
        state = f"commit-{unit.work_unit_id}"
        return WorkExecutionResult(
            unit.work_unit_id,
            target.executor_id,
            target.provider_id,
            WorkExecutionStatus.SUCCEEDED,
            state,
            artifact_ref=state,
            evidence_ref=f"execution://{unit.work_unit_id}/{target.executor_id}",
        )


class _Repository:
    def __init__(self, *, mutate_handoff: bool = False, mutate_capture_repository: bool = False) -> None:
        self.mutate_handoff = mutate_handoff
        self.mutate_capture_repository = mutate_capture_repository
        self.handoffs: list[tuple[str, str, str]] = []

    def initial(self, objective):
        return RepositoryCheckpoint("checkpoint-root", "repo-1", "root", "repo://root")

    def capture(self, objective, unit, execution):
        return RepositoryCheckpoint(
            f"checkpoint-{unit.work_unit_id}",
            "repo-other" if self.mutate_capture_repository else "repo-1",
            execution.repository_state_id,
            execution.artifact_ref,
        )

    def handoff(self, checkpoint, *, from_executor_id, to_executor_id):
        self.handoffs.append((from_executor_id, to_executor_id, checkpoint.state_id))
        if not self.mutate_handoff:
            return checkpoint
        return RepositoryCheckpoint(
            checkpoint.checkpoint_id,
            checkpoint.repository_id,
            "rewritten-state",
            checkpoint.artifact_ref,
        )


class _Verifier:
    def __init__(self, *, same_as_executor: bool = False) -> None:
        self.same_as_executor = same_as_executor

    def verify(self, objective, unit, execution, checkpoint):
        verifier_id = execution.executor_id if self.same_as_executor else "independent-verifier"
        if unit.work_unit_id == "verify":
            return WorkVerificationResult(
                False,
                verifier_id,
                "verification://missing-proof",
                "test://acceptance-proof",
                "missing proof",
            )
        return WorkVerificationResult(
            True,
            verifier_id,
            f"verification://{unit.work_unit_id}/pass",
            f"test://{unit.work_unit_id}/pass",
        )


class Issue507ProjectSupervisionTests(unittest.TestCase):
    def test_product_supervisor_decomposes_fails_over_corrects_and_accepts(self):
        repository = _Repository()
        runner = _Runner()
        result = supervise_project(
            objective=ProjectObjective(
                "project-507",
                "req-complete-project",
                "deliver a complete project from one objective",
            ),
            planner=_Planner(),
            scheduler=_Scheduler(),
            runner=runner,
            repository=repository,
            verifier=_Verifier(),
        )

        self.assertEqual(result.verdict, ProjectVerdict.PROJECT_ACCEPTED)
        self.assertEqual(result.graph.authority_id, "metao")
        self.assertGreater(len(result.graph.units), 1)
        self.assertTrue(any(unit.corrective for unit in result.graph.units))
        self.assertEqual(result.executors_used, frozenset({"executor-a", "executor-b"}))
        self.assertEqual(result.providers_used, frozenset({"provider-a", "provider-b"}))
        kinds = [event.kind for event in result.trace]
        self.assertIn(ProjectTraceKind.FAILED_CAPACITY, kinds)
        self.assertIn(ProjectTraceKind.HANDED_OFF, kinds)
        self.assertIn(ProjectTraceKind.VERIFICATION_FAILED, kinds)
        self.assertIn(ProjectTraceKind.CORRECTIVE_WORK_CREATED, kinds)
        self.assertIn(ProjectTraceKind.PROJECT_ACCEPTED, kinds)
        self.assertEqual(
    repository.handoffs,
    [
        ("executor-a", "executor-b", "commit-discover"),
        ("executor-b", "executor-a", "commit-implement"),
    ],
)
        implement_calls = [call for call in runner.calls if call[0] == "implement"]
        self.assertEqual(implement_calls[0][1], "executor-a")
        self.assertEqual(implement_calls[1][1], "executor-b")
        records = {record.work_unit_id: record for record in result.traceability}
        self.assertEqual(records["verify"].verdict, "CORRECTED_PASS")
        self.assertEqual(records["corrective-proof"].verdict, "PASS")
        self.assertTrue(all(record.requirement_id == "req-complete-project" for record in result.traceability))

    def test_handoff_cannot_rewrite_repository_checkpoint(self):
        result = supervise_project(
            objective=ProjectObjective("project", "req", "objective"),
            planner=_Planner(),
            scheduler=_Scheduler(),
            runner=_Runner(),
            repository=_Repository(mutate_handoff=True),
            verifier=_Verifier(),
        )
        self.assertEqual(result.verdict, ProjectVerdict.PROJECT_BLOCKED)
        self.assertIn("checkpoint changed", result.reason)

    def test_capture_cannot_switch_repository_identity(self):
        result = supervise_project(
            objective=ProjectObjective("project", "req", "objective"),
            planner=_Planner(),
            scheduler=_Scheduler(),
            runner=_Runner(),
            repository=_Repository(mutate_capture_repository=True),
            verifier=_Verifier(),
        )
        self.assertEqual(result.verdict, ProjectVerdict.PROJECT_BLOCKED)
        self.assertIn("repository identity", result.reason)

    def test_executor_cannot_independently_verify_its_own_work(self):
        result = supervise_project(
            objective=ProjectObjective("project", "req", "objective"),
            planner=_Planner(),
            scheduler=_Scheduler(),
            runner=_Runner(),
            repository=_Repository(),
            verifier=_Verifier(same_as_executor=True),
        )
        self.assertEqual(result.verdict, ProjectVerdict.PROJECT_BLOCKED)
        self.assertIn("not independent", result.reason)

    def test_corrective_work_must_depend_on_the_failed_unit(self):
        class UnboundCorrectionPlanner(_Planner):
            def corrective_work(self, objective, failed_unit, verification, graph):
                return WorkUnit(
                    "bad-correction",
                    "unbound correction",
                    (),
                    corrective=True,
                    corrects_work_unit_id=failed_unit.work_unit_id,
                )

        result = supervise_project(
            objective=ProjectObjective("project", "req", "objective"),
            planner=UnboundCorrectionPlanner(),
            scheduler=_Scheduler(),
            runner=_Runner(),
            repository=_Repository(),
            verifier=_Verifier(),
        )
        self.assertEqual(result.verdict, ProjectVerdict.PROJECT_BLOCKED)
        self.assertIn("does not depend", result.reason)

    def test_non_metao_decomposition_authority_fails_closed(self):
        class ExternalPlanner(_Planner):
            def plan(self, objective):
                return WorkGraph("executor-a", (WorkUnit("one", "do work"),))

        with self.assertRaisesRegex(ValueError, "authority must be metao"):
            supervise_project(
                objective=ProjectObjective("project", "req", "objective"),
                planner=ExternalPlanner(),
                scheduler=_Scheduler(),
                runner=_Runner(),
                repository=_Repository(),
                verifier=_Verifier(),
            )

    def test_dependency_cycle_is_rejected_before_dispatch(self):
        class CyclicPlanner(_Planner):
            def plan(self, objective):
                return WorkGraph(
                    "metao",
                    (
                        WorkUnit("a", "a", ("b",)),
                        WorkUnit("b", "b", ("a",)),
                    ),
                )

        with self.assertRaisesRegex(ValueError, "dependency cycle"):
            supervise_project(
                objective=ProjectObjective("project", "req", "objective"),
                planner=CyclicPlanner(),
                scheduler=_Scheduler(),
                runner=_Runner(),
                repository=_Repository(),
                verifier=_Verifier(),
            )


if __name__ == "__main__":
    unittest.main(verbosity=2)
