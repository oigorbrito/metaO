from __future__ import annotations

import json
import os
from pathlib import Path
import sqlite3
import subprocess
import sys
import tempfile
import unittest

from metao.project_effects import (
    ProjectEffectAmbiguous,
    ProjectEffectKey,
    ProjectEffectReconciliation,
    ProjectEffectState,
    ReconciledWorkUnitRunner,
)
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
from metao.project_supervision_state import (
    SQLiteProjectActionFence,
    SQLiteProjectSupervisionStateStore,
)


class _EffectRunner:
    def __init__(self) -> None:
        self.calls: list[str] = []

    def run_with_idempotency_key(
        self,
        objective,
        unit,
        target,
        checkpoint,
        *,
        idempotency_key,
    ):
        self.calls.append(idempotency_key)
        return WorkExecutionResult(
            unit.work_unit_id,
            target.executor_id,
            target.provider_id,
            WorkExecutionStatus.SUCCEEDED,
            "effect-state",
            "effect:ticket",
            "effect-evidence",
        )


class _Reconciliation:
    def __init__(self, state: ProjectEffectState, execution=None) -> None:
        self.state = state
        self.execution = execution
        self.keys: list[str] = []

    def reconcile(self, objective, unit, target, checkpoint, key):
        self.keys.append(key.value)
        return ProjectEffectReconciliation(
            key,
            self.state,
            self.execution,
            "authority:test",
        )


class _ImmediateFence:
    """Unit-test-only fence; continuity evidence uses SQLiteProjectActionFence."""

    def execute(self, action):
        return action()


class Issue754ProjectEffectContractTests(unittest.TestCase):
    def test_ambiguous_effect_fails_closed_without_reissue(self):
        effect = _EffectRunner()
        runner = ReconciledWorkUnitRunner(
            runner=effect,
            reconciliation=_Reconciliation(ProjectEffectState.AMBIGUOUS),
        )
        result = runner.run(
            ProjectObjective("project", "req", "objective"),
            WorkUnit("effect", "create ticket"),
            ExecutorTarget("executor-a", "provider-a"),
            RepositoryCheckpoint("cp", "repo", "state", "artifact"),
        )
        self.assertEqual(result.status, WorkExecutionStatus.FAILED)
        self.assertIn("ambiguous-effect:", result.evidence_ref)
        self.assertEqual(effect.calls, [])


    def test_ambiguous_effect_blocks_supervision_and_persists_terminal_state(self):
        class Planner:
            def plan(self, objective):
                return WorkGraph("metao", (WorkUnit("effect", "create ticket"),))
            def corrective_work(self, objective, failed_unit, verification, graph):
                return None

        class Scheduler:
            def select(self, unit, *, excluded_executor_ids):
                return ExecutorTarget("executor-a", "provider-a")

        class Repository:
            def initial(self, objective):
                return RepositoryCheckpoint("root", "repo", "root", "artifact:root")
            def capture(self, objective, unit, execution):
                raise AssertionError("FAILED ambiguous effect must not be captured")
            def handoff(self, checkpoint, *, from_executor_id, to_executor_id):
                return checkpoint

        class Verifier:
            def verify(self, objective, unit, execution, checkpoint):
                raise AssertionError("FAILED ambiguous effect must not be verified")

        persisted = []
        result = supervise_project(
            objective=ProjectObjective("project", "req", "objective"),
            planner=Planner(),
            scheduler=Scheduler(),
            runner=ReconciledWorkUnitRunner(
                runner=_EffectRunner(),
                reconciliation=_Reconciliation(ProjectEffectState.AMBIGUOUS),
            ),
            repository=Repository(),
            verifier=Verifier(),
            persist_resume_state=persisted.append,
            action_fence=_ImmediateFence(),
            max_executor_attempts_per_unit=1,
            max_corrective_units=0,
        )
        self.assertEqual(result.verdict, ProjectVerdict.PROJECT_BLOCKED)
        self.assertEqual(
            persisted[-1].trace[-1].kind.value,
            "PROJECT_BLOCKED",
        )

    def test_not_applied_uses_stable_logical_effect_key(self):
        effect = _EffectRunner()
        reconciliation = _Reconciliation(ProjectEffectState.NOT_APPLIED)
        runner = ReconciledWorkUnitRunner(
            runner=effect,
            reconciliation=reconciliation,
        )
        objective = ProjectObjective("project", "req", "objective")
        unit = WorkUnit("effect", "create ticket")
        target = ExecutorTarget("executor-a", "provider-a")
        checkpoint = RepositoryCheckpoint("cp", "repo", "state", "artifact")

        result = runner.run(objective, unit, target, checkpoint)
        self.assertEqual(result.status, WorkExecutionStatus.SUCCEEDED)
        expected_key = ProjectEffectKey(
            "project",
            "effect",
            "primary-work-unit-effect",
        ).value
        self.assertEqual(effect.calls, [expected_key])
        self.assertEqual(effect.calls, reconciliation.keys)


    def test_runner_cannot_choose_or_rotate_effect_identity(self):
        effect = _EffectRunner()
        reconciliation = _Reconciliation(ProjectEffectState.NOT_APPLIED)
        runner = ReconciledWorkUnitRunner(
            runner=effect,
            reconciliation=reconciliation,
        )
        objective = ProjectObjective("project", "req", "objective")
        unit = WorkUnit("effect", "create ticket")
        target = ExecutorTarget("executor-a", "provider-a")
        checkpoint = RepositoryCheckpoint("cp", "repo", "state", "artifact")

        runner.run(objective, unit, target, checkpoint)
        runner.run(objective, unit, target, checkpoint)

        expected = ProjectEffectKey(
            "project",
            "effect",
            "primary-work-unit-effect",
        ).value
        self.assertEqual(effect.calls, [expected, expected])
        self.assertEqual(reconciliation.keys, [expected, expected])

    def test_effect_key_canonicalization_avoids_delimiter_collisions(self):
        first = ProjectEffectKey("a:b", "c", "d").value
        second = ProjectEffectKey("a", "b:c", "d").value
        self.assertNotEqual(first, second)
        self.assertEqual(
            first,
            ProjectEffectKey("a:b", "c", "d").value,
        )
        self.assertTrue(first.startswith("metao-project-effect-v1:"))

    def test_applied_reconciliation_reuses_authoritative_execution(self):
        execution = WorkExecutionResult(
            "effect",
            "executor-a",
            "provider-a",
            WorkExecutionStatus.SUCCEEDED,
            "effect-state",
            "effect:ticket",
            "effect-evidence",
        )
        effect = _EffectRunner()
        runner = ReconciledWorkUnitRunner(
            runner=effect,
            reconciliation=_Reconciliation(
                ProjectEffectState.APPLIED,
                execution,
            ),
        )
        result = runner.run(
            ProjectObjective("project", "req", "objective"),
            WorkUnit("effect", "create ticket"),
            ExecutorTarget("executor-a", "provider-a"),
            RepositoryCheckpoint("cp", "repo", "state", "artifact"),
        )
        self.assertEqual(result, execution)
        self.assertEqual(effect.calls, [])


class Issue754DuplicateEffectCrashWindowTests(unittest.TestCase):
    def test_applied_effect_is_reconciled_after_crash_without_second_application(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            project_db = root / "project.db"
            effect_db = root / "effects.db"

            service = r"""
import json
from pathlib import Path
import sqlite3
import sys

db = Path(sys.argv[1])
command = sys.argv[2]
key = sys.argv[3]
connection = sqlite3.connect(db)
with connection:
    connection.execute(
        '''
        CREATE TABLE IF NOT EXISTS effects (
            idempotency_key TEXT PRIMARY KEY,
            application_count INTEGER NOT NULL,
            execution_json TEXT NOT NULL
        )
        '''
    )
    row = connection.execute(
        "SELECT application_count, execution_json FROM effects WHERE idempotency_key=?",
        (key,),
    ).fetchone()
    if command == "query":
        if row is None:
            print(json.dumps({"state": "NOT_APPLIED"}))
        else:
            print(json.dumps({
                "state": "APPLIED",
                "application_count": row[0],
                "execution": json.loads(row[1]),
            }))
    elif command == "apply":
        if row is not None:
            print(json.dumps({
                "state": "APPLIED",
                "application_count": row[0],
                "execution": json.loads(row[1]),
                "deduplicated": True,
            }))
        else:
            execution = {
                "work_unit_id": "effect",
                "executor_id": "executor-a",
                "provider_id": "provider-a",
                "status": "SUCCEEDED",
                "repository_state_id": "state-effect",
                "artifact_ref": "effect:ticket-1",
                "evidence_ref": "effect-service:ticket-1",
            }
            connection.execute(
                "INSERT INTO effects(idempotency_key,application_count,execution_json) VALUES(?,?,?)",
                (key, 1, json.dumps(execution, sort_keys=True)),
            )
            print(json.dumps({
                "state": "APPLIED",
                "application_count": 1,
                "execution": execution,
                "deduplicated": False,
            }))
    else:
        raise SystemExit(2)
"""

            worker = r"""
from __future__ import annotations

import json
import os
from pathlib import Path
import subprocess
import sys

from metao.project_effects import (
    ProjectEffectKey,
    ProjectEffectReconciliation,
    ProjectEffectState,
    ReconciledWorkUnitRunner,
)
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
from metao.project_supervision_state import (
    SQLiteProjectActionFence,
    SQLiteProjectSupervisionStateStore,
)

project_db = Path(sys.argv[1])
effect_db = Path(sys.argv[2])
mode = sys.argv[3]
service_code = sys.argv[4]


def service(command, key):
    completed = subprocess.run(
        [sys.executable, "-c", service_code, str(effect_db), command, key],
        check=True,
        capture_output=True,
        text=True,
    )
    return json.loads(completed.stdout)


def execution_from(data):
    return WorkExecutionResult(
        data["work_unit_id"],
        data["executor_id"],
        data["provider_id"],
        WorkExecutionStatus(data["status"]),
        data["repository_state_id"],
        data["artifact_ref"],
        data["evidence_ref"],
    )


class Planner:
    def plan(self, objective):
        return WorkGraph("metao", (WorkUnit("effect", "create ticket"),))
    def corrective_work(self, objective, failed_unit, verification, graph):
        return None


class Scheduler:
    def select(self, unit, *, excluded_executor_ids):
        return ExecutorTarget("executor-a", "provider-a")


class EffectRunner:
    def run_with_idempotency_key(
        self,
        objective,
        unit,
        target,
        checkpoint,
        *,
        idempotency_key,
    ):
        response = service("apply", idempotency_key)
        execution = execution_from(response["execution"])
        if mode == "a":
            # Critical window: the external effect is durable, but the
            # supervisor has not yet captured/verified/persisted this unit.
            os._exit(37)
        return execution


class Reconciliation:
    def reconcile(self, objective, unit, target, checkpoint, key):
        response = service("query", key.value)
        if response["state"] == "NOT_APPLIED":
            return ProjectEffectReconciliation(
                key,
                ProjectEffectState.NOT_APPLIED,
                authority_ref="effect-service:query",
            )
        return ProjectEffectReconciliation(
            key,
            ProjectEffectState.APPLIED,
            execution_from(response["execution"]),
            "effect-service:query",
        )


class Repository:
    def initial(self, objective):
        if mode == "b":
            raise AssertionError("resume must reuse durable checkpoint")
        return RepositoryCheckpoint("root", "repo", "root", "artifact:root")

    def capture(self, objective, unit, execution):
        return RepositoryCheckpoint(
            "checkpoint-effect",
            "repo",
            execution.repository_state_id,
            execution.artifact_ref,
        )

    def handoff(self, checkpoint, *, from_executor_id, to_executor_id):
        return checkpoint


class Verifier:
    def verify(self, objective, unit, execution, checkpoint):
        return WorkVerificationResult(
            True,
            "independent-verifier",
            "verification:effect",
            "test:effect",
        )


store = SQLiteProjectSupervisionStateStore(project_db)
box = [None]

if mode == "a":
    def persist(state):
        if box[0] is None:
            box[0] = store.create(state, holder_id="process-a")
        else:
            box[0] = store.replace(
                state,
                owner=box[0].owner,
                expected_revision=box[0].revision,
            )

    supervise_project(
        objective=ProjectObjective("project-754", "req-754", "create one logical ticket"),
        planner=Planner(),
        scheduler=Scheduler(),
        runner=ReconciledWorkUnitRunner(
            runner=EffectRunner(),
            reconciliation=Reconciliation(),
        ),
        repository=Repository(),
        verifier=Verifier(),
        persist_resume_state=persist,
        action_fence=SQLiteProjectActionFence(
            store,
            lambda: box[0].owner,
        ),
        max_executor_attempts_per_unit=1,
        max_corrective_units=0,
    )
    raise AssertionError("process A should die in the effect crash window")
else:
    acquired = store.acquire("project-754", holder_id="process-b")
    box[0] = acquired

    def persist(state):
        box[0] = store.replace(
            state,
            owner=box[0].owner,
            expected_revision=box[0].revision,
        )

    result = supervise_project(
        objective=ProjectObjective("project-754", "req-754", "create one logical ticket"),
        planner=Planner(),
        scheduler=Scheduler(),
        runner=ReconciledWorkUnitRunner(
            runner=EffectRunner(),
            reconciliation=Reconciliation(),
        ),
        repository=Repository(),
        verifier=Verifier(),
        resume_state=acquired.snapshot,
        persist_resume_state=persist,
        action_fence=SQLiteProjectActionFence(
            store,
            lambda: box[0].owner,
        ),
        max_executor_attempts_per_unit=1,
        max_corrective_units=0,
    )
    if result.verdict is not ProjectVerdict.PROJECT_ACCEPTED:
        raise SystemExit(92)
    print("ACCEPTED")
"""

            first = subprocess.run(
                [
                    sys.executable,
                    "-c",
                    worker,
                    str(project_db),
                    str(effect_db),
                    "a",
                    service,
                ],
                capture_output=True,
                text=True,
            )
            self.assertEqual(first.returncode, 37)

            store = SQLiteProjectSupervisionStateStore(project_db)
            before_resume = store.load("project-754")
            self.assertEqual(before_resume.snapshot.accepted_work_unit_ids, frozenset())

            second = subprocess.run(
                [
                    sys.executable,
                    "-c",
                    worker,
                    str(project_db),
                    str(effect_db),
                    "b",
                    service,
                ],
                check=True,
                capture_output=True,
                text=True,
            )
            self.assertEqual(second.stdout.strip(), "ACCEPTED")

            key = ProjectEffectKey(
                "project-754",
                "effect",
                "primary-work-unit-effect",
            ).value
            with sqlite3.connect(effect_db) as connection:
                row = connection.execute(
                    "SELECT application_count FROM effects WHERE idempotency_key=?",
                    (key,),
                ).fetchone()
            self.assertEqual(row, (1,))

            final = store.load("project-754")
            self.assertEqual(
                final.snapshot.accepted_work_unit_ids,
                frozenset({"effect"}),
            )
            self.assertEqual(final.owner.holder_id, "process-b")
            self.assertEqual(final.owner.generation, 2)
            self.assertEqual(
                final.snapshot.trace[-1].kind.value,
                "PROJECT_ACCEPTED",
            )


if __name__ == "__main__":
    unittest.main(verbosity=2)
