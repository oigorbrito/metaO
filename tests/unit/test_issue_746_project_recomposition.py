from __future__ import annotations

import unittest

from metao.project_supervision import (
    ExecutorTarget,
    ProjectCompositionResult,
    ProjectObjective,
    ProjectTraceKind,
    ProjectVerificationResult,
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
                WorkUnit("left", "produce A"),
                WorkUnit("right", "produce right fragment", ("left",)),
            ),
        )

    def corrective_work(self, objective, failed_unit, verification, graph):
        return None


class _Scheduler:
    def select(self, unit, *, excluded_executor_ids):
        if "executor-a" in excluded_executor_ids:
            return None
        return ExecutorTarget("executor-a", "provider-a")


class _Runner:
    def __init__(self, right_fragment: str) -> None:
        self.fragments = {"left": "A", "right": right_fragment}

    def run(self, objective, unit, target, checkpoint):
        fragment = self.fragments[unit.work_unit_id]
        return WorkExecutionResult(
            unit.work_unit_id,
            target.executor_id,
            target.provider_id,
            WorkExecutionStatus.SUCCEEDED,
            f"state-{unit.work_unit_id}-{fragment}",
            artifact_ref=f"fragment:{fragment}",
            evidence_ref=f"execution:{unit.work_unit_id}",
        )


class _Repository:
    def initial(self, objective):
        return RepositoryCheckpoint("root", "repo", "root", "artifact:root")

    def capture(self, objective, unit, execution):
        return RepositoryCheckpoint(
            f"checkpoint-{unit.work_unit_id}",
            "repo",
            execution.repository_state_id,
            execution.artifact_ref,
        )

    def handoff(self, checkpoint, *, from_executor_id, to_executor_id):
        return checkpoint


class _LocalVerifier:
    def verify(self, objective, unit, execution, checkpoint):
        return WorkVerificationResult(
            True,
            "local-independent-verifier",
            f"local-evidence:{unit.work_unit_id}",
            f"local-test:{unit.work_unit_id}",
        )


class _Recomposer:
    def recompose(self, objective, graph, accepted_work, checkpoint):
        fragments = [execution.artifact_ref.split(":", 1)[1] for execution in accepted_work]
        composite = "".join(fragments)
        return ProjectCompositionResult(
            objective.project_id,
            f"composite:{composite}",
            f"recomposition:{composite}",
        )


class _ProjectVerifier:
    def __init__(self, verifier_id: str = "project-independent-verifier") -> None:
        self.verifier_id = verifier_id

    def verify(self, objective, composition, graph, traceability, checkpoint):
        accepted = composition.artifact_ref == "composite:AB"
        return ProjectVerificationResult(
            accepted,
            self.verifier_id,
            f"project-verification:{composition.artifact_ref}",
            "original-spec:AB",
            "" if accepted else "recomposed result does not satisfy original specification",
        )


class Issue746ProjectRecompositionTests(unittest.TestCase):
    def _run(self, right_fragment: str, *, project_verifier=None):
        return supervise_project(
            objective=ProjectObjective(
                "project-746",
                "req-746",
                "Produce exactly AB from the accepted work products.",
            ),
            planner=_Planner(),
            scheduler=_Scheduler(),
            runner=_Runner(right_fragment),
            repository=_Repository(),
            verifier=_LocalVerifier(),
            project_recomposer=_Recomposer(),
            project_verifier=project_verifier or _ProjectVerifier(),
            max_executor_attempts_per_unit=1,
            max_corrective_units=0,
        )

    def test_valid_recomposition_is_verified_before_project_acceptance(self):
        result = self._run("B")

        self.assertEqual(result.verdict, ProjectVerdict.PROJECT_ACCEPTED)
        self.assertEqual(result.project_artifact_ref, "composite:AB")
        self.assertIsNotNone(result.project_verification)
        self.assertTrue(result.project_verification.accepted)
        kinds = [event.kind for event in result.trace]
        self.assertLess(kinds.index(ProjectTraceKind.RECOMPOSED), kinds.index(ProjectTraceKind.PROJECT_VERIFICATION_PASSED))
        self.assertLess(kinds.index(ProjectTraceKind.PROJECT_VERIFICATION_PASSED), kinds.index(ProjectTraceKind.PROJECT_ACCEPTED))

    def test_local_pass_global_spec_fail_blocks_project_acceptance(self):
        result = self._run("X")

        self.assertEqual(result.verdict, ProjectVerdict.PROJECT_BLOCKED)
        self.assertEqual(result.project_artifact_ref, "composite:AX")
        self.assertIsNotNone(result.project_verification)
        self.assertFalse(result.project_verification.accepted)
        kinds = [event.kind for event in result.trace]
        self.assertIn(ProjectTraceKind.RECOMPOSED, kinds)
        self.assertIn(ProjectTraceKind.PROJECT_VERIFICATION_FAILED, kinds)
        self.assertNotIn(ProjectTraceKind.PROJECT_ACCEPTED, kinds)
        self.assertIn("original-spec", result.reason)

    def test_recomposer_and_project_verifier_must_be_configured_together(self):
        with self.assertRaisesRegex(ValueError, "configured together"):
            supervise_project(
                objective=ProjectObjective("project", "req", "objective"),
                planner=_Planner(),
                scheduler=_Scheduler(),
                runner=_Runner("B"),
                repository=_Repository(),
                verifier=_LocalVerifier(),
                project_recomposer=_Recomposer(),
            )

    def test_project_verifier_cannot_be_an_executor_used_by_the_project(self):
        result = self._run("B", project_verifier=_ProjectVerifier("executor-a"))

        self.assertEqual(result.verdict, ProjectVerdict.PROJECT_BLOCKED)
        self.assertIn("not independent", result.reason)
        self.assertNotIn(
            ProjectTraceKind.PROJECT_ACCEPTED,
            [event.kind for event in result.trace],
        )


if __name__ == "__main__":
    unittest.main(verbosity=2)
