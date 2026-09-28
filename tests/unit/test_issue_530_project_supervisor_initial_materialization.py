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


class Planner:
    def plan(self, objective):
        return WorkGraph("metao", (WorkUnit("wu-1", "do work"),))

    def corrective_work(self, objective, failed_unit, verification, graph):
        return None


class Scheduler:
    def select(self, unit, *, excluded_executor_ids):
        return ExecutorTarget("executor-a", "provider-a")


class Repository:
    def initial(self, objective):
        return RepositoryCheckpoint("cp-0", "repo", "state-0", "artifact-0")

    def capture(self, objective, unit, execution):
        return RepositoryCheckpoint("cp-1", "repo", execution.repository_state_id, execution.artifact_ref)

    def handoff(self, checkpoint, *, from_executor_id, to_executor_id):
        raise AssertionError("handoff is not expected")


class Materializer:
    def __init__(self, *, mutate=False):
        self.calls = []
        self.ready = False
        self.mutate = mutate

    def materialize(self, checkpoint, *, to_executor_id):
        self.calls.append((checkpoint, to_executor_id))
        self.ready = True
        if self.mutate:
            return RepositoryCheckpoint("changed", checkpoint.repository_id, checkpoint.state_id, checkpoint.artifact_ref)
        return checkpoint


class Runner:
    def __init__(self, materializer):
        self.materializer = materializer
        self.calls = 0

    def run(self, objective, unit, target, checkpoint):
        self.calls += 1
        if not self.materializer.ready:
            raise AssertionError("runner observed dispatch before initial checkpoint materialization")
        return WorkExecutionResult(
            unit.work_unit_id,
            target.executor_id,
            target.provider_id,
            WorkExecutionStatus.SUCCEEDED,
            "state-1",
            "artifact-1",
            "exec-evidence",
        )


class Verifier:
    def verify(self, objective, unit, execution, checkpoint):
        return WorkVerificationResult(True, "verifier", "verify-evidence", "test-ref")


class InitialMaterializationSupervisorTests(unittest.TestCase):
    def test_materialization_occurs_before_first_dispatch(self):
        materializer = Materializer()
        runner = Runner(materializer)

        result = supervise_project(
            objective=ProjectObjective("project-360", "req-360", "deliver"),
            planner=Planner(),
            scheduler=Scheduler(),
            runner=runner,
            repository=Repository(),
            verifier=Verifier(),
            initial_checkpoint_materializer=materializer,
        )

        self.assertEqual(result.verdict, ProjectVerdict.PROJECT_ACCEPTED)
        self.assertEqual(len(materializer.calls), 1)
        self.assertEqual(materializer.calls[0][1], "executor-a")
        self.assertEqual(runner.calls, 1)
        kinds = tuple(event.kind for event in result.trace)
        self.assertLess(kinds.index(ProjectTraceKind.MATERIALIZED), kinds.index(ProjectTraceKind.DISPATCHED))

    def test_changed_checkpoint_blocks_before_runner_dispatch(self):
        materializer = Materializer(mutate=True)
        runner = Runner(materializer)

        result = supervise_project(
            objective=ProjectObjective("project-360", "req-360", "deliver"),
            planner=Planner(),
            scheduler=Scheduler(),
            runner=runner,
            repository=Repository(),
            verifier=Verifier(),
            initial_checkpoint_materializer=materializer,
        )

        self.assertEqual(result.verdict, ProjectVerdict.PROJECT_BLOCKED)
        self.assertEqual(result.reason, "repository checkpoint changed during initial materialization")
        self.assertEqual(runner.calls, 0)
        self.assertNotIn(ProjectTraceKind.DISPATCHED, tuple(event.kind for event in result.trace))


if __name__ == "__main__":
    unittest.main()
