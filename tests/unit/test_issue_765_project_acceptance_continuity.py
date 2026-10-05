from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from metao.project_supervision import (
    ExecutorTarget,
    ProjectCompositionResult,
    ProjectObjective,
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
from metao.project_supervision_state import (
    SQLiteProjectActionFence,
    SQLiteProjectSupervisionStateStore,
)


class _CrashAfterCorrection(RuntimeError):
    pass


class _Planner:
    def plan(self, objective):
        return WorkGraph("metao", (WorkUnit("original", "produce original"),))

    def corrective_work(self, objective, failed_unit, verification, graph):
        return WorkUnit(
            "repair",
            "repair original",
            ("original",),
            True,
            "original",
        )


class _Scheduler:
    def select(self, unit, *, excluded_executor_ids):
        return ExecutorTarget("executor-a", "provider-a")


class _Runner:
    def __init__(self):
        self.calls: list[str] = []

    def run(self, objective, unit, target, checkpoint):
        self.calls.append(unit.work_unit_id)
        fragment = "X" if unit.work_unit_id == "original" else "A"
        return WorkExecutionResult(
            unit.work_unit_id,
            target.executor_id,
            target.provider_id,
            WorkExecutionStatus.SUCCEEDED,
            f"state-{unit.work_unit_id}",
            f"fragment:{fragment}",
            f"execution:{unit.work_unit_id}",
        )


class _Repository:
    def initial(self, objective):
        return RepositoryCheckpoint("root", "repo-765", "root", "artifact:root")

    def capture(self, objective, unit, execution):
        return RepositoryCheckpoint(
            f"checkpoint-{unit.work_unit_id}",
            "repo-765",
            execution.repository_state_id,
            execution.artifact_ref or "artifact:missing",
        )

    def handoff(self, checkpoint, *, from_executor_id, to_executor_id):
        return checkpoint


class _LocalVerifier:
    def verify(self, objective, unit, execution, checkpoint):
        accepted = unit.work_unit_id == "repair"
        return WorkVerificationResult(
            accepted,
            "local-independent-verifier",
            f"local-evidence:{unit.work_unit_id}",
            f"local-test:{unit.work_unit_id}",
            "" if accepted else "original requires correction",
        )


class _Recomposer:
    def __init__(self):
        self.accepted_work_ids: list[str] = []

    def recompose(self, objective, graph, accepted_work, checkpoint):
        self.accepted_work_ids = [item.work_unit_id for item in accepted_work]
        fragments = [item.artifact_ref.split(":", 1)[1] for item in accepted_work]
        return ProjectCompositionResult(
            objective.project_id,
            "composite:" + "".join(fragments),
            "recomposition:resume",
        )


class _ProjectVerifier:
    def verify(self, objective, composition, graph, traceability, checkpoint):
        accepted = composition.artifact_ref == "composite:A"
        return ProjectVerificationResult(
            accepted,
            "project-independent-verifier",
            "project-evidence:resume",
            "original-spec:A",
            "" if accepted else "unexpected recomposed result",
        )


class Issue765AcceptanceContinuityIntegrationTests(unittest.TestCase):
    def test_corrective_result_binding_survives_resume_and_recomposition(self):
        with tempfile.TemporaryDirectory() as directory:
            db = Path(directory) / "project.db"
            store = SQLiteProjectSupervisionStateStore(db)
            record_box = [None]
            runner = _Runner()
            objective = ProjectObjective(
                "project-765",
                "req-765",
                "Produce exactly A after any required correction.",
            )

            def persist_a(state):
                if record_box[0] is None:
                    record_box[0] = store.create(state, holder_id="process-a")
                else:
                    record_box[0] = store.replace(
                        state,
                        owner=record_box[0].owner,
                        expected_revision=record_box[0].revision,
                    )
                if state.accepted_work_unit_ids == frozenset({"original", "repair"}):
                    raise _CrashAfterCorrection()

            with self.assertRaises(_CrashAfterCorrection):
                supervise_project(
                    objective=objective,
                    planner=_Planner(),
                    scheduler=_Scheduler(),
                    runner=runner,
                    repository=_Repository(),
                    verifier=_LocalVerifier(),
                    persist_resume_state=persist_a,
                    action_fence=SQLiteProjectActionFence(
                        store,
                        lambda: record_box[0].owner,
                    ),
                    project_recomposer=_Recomposer(),
                    project_verifier=_ProjectVerifier(),
                    max_executor_attempts_per_unit=1,
                    max_corrective_units=1,
                )

            crashed = store.load("project-765")
            bindings = dict(crashed.snapshot.accepted_result_bindings)
            self.assertEqual(bindings["original"].work_unit_id, "repair")
            self.assertEqual(bindings["repair"].work_unit_id, "repair")

            acquired = store.acquire("project-765", holder_id="process-b")
            record_box[0] = acquired

            def persist_b(state):
                record_box[0] = store.replace(
                    state,
                    owner=record_box[0].owner,
                    expected_revision=record_box[0].revision,
                )

            recomposer = _Recomposer()
            result = supervise_project(
                objective=objective,
                planner=_Planner(),
                scheduler=_Scheduler(),
                runner=runner,
                repository=_Repository(),
                verifier=_LocalVerifier(),
                resume_state=acquired.snapshot,
                persist_resume_state=persist_b,
                action_fence=SQLiteProjectActionFence(
                    store,
                    lambda: record_box[0].owner,
                ),
                project_recomposer=recomposer,
                project_verifier=_ProjectVerifier(),
                max_executor_attempts_per_unit=1,
                max_corrective_units=1,
            )

            self.assertEqual(runner.calls, ["original", "repair"])
            self.assertEqual(recomposer.accepted_work_ids, ["repair"])
            self.assertEqual(result.verdict, ProjectVerdict.PROJECT_ACCEPTED)
            self.assertEqual(result.project_artifact_ref, "composite:A")
            self.assertIsNotNone(result.project_verification)
            self.assertTrue(result.project_verification.accepted)


if __name__ == "__main__":
    unittest.main(verbosity=2)
