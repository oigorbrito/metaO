from __future__ import annotations

from dataclasses import replace
from pathlib import Path
import subprocess
import sys
import tempfile
import threading
import time
import unittest

from metao.project_supervision import (
    ExecutorTarget,
    ProjectObjective,
    ProjectTraceEvent,
    ProjectTraceKind,
    ProjectTraceabilityRecord,
    RepositoryCheckpoint,
    WorkExecutionResult,
    WorkExecutionStatus,
    WorkGraph,
    WorkUnit,
    WorkVerificationResult,
    supervise_project,
)
from metao.project_supervision_state import (
    ProjectSupervisionSnapshot,
    ProjectSupervisionStateConflict,
    SQLiteProjectActionFence,
    SQLiteProjectSupervisionStateStore,
    StaleProjectOwner,
)


def _snapshot(*, accepted: bool = True) -> ProjectSupervisionSnapshot:
    units = (
        WorkUnit("first", "first work"),
        WorkUnit("second", "second work", ("first",)),
    )
    accepted_ids = frozenset({"first"}) if accepted else frozenset()
    accepted_results = (
        (
            WorkExecutionResult(
                "first",
                "executor-a",
                "provider-a",
                WorkExecutionStatus.SUCCEEDED,
                "state-first",
                "artifact:first",
                "evidence:first",
            ),
        )
        if accepted
        else ()
    )
    traceability = (
        (
            ProjectTraceabilityRecord(
                "req-753",
                "first",
                "artifact:first",
                "test:first",
                "evidence:first",
                "PASS",
            ),
        )
        if accepted
        else ()
    )
    return ProjectSupervisionSnapshot(
        "project-753",
        "req-753",
        "resume project after process crash",
        "metao",
        units,
        frozenset({"first"}) if accepted else frozenset(),
        accepted_ids,
        accepted_results,
        (),
        (ProjectTraceEvent(ProjectTraceKind.PLANNED),),
        traceability,
        frozenset({"executor-a"}) if accepted else frozenset(),
        frozenset({"provider-a"}) if accepted else frozenset(),
        RepositoryCheckpoint(
            "checkpoint-first" if accepted else "checkpoint-root",
            "repo-753",
            "state-first" if accepted else "root",
            "artifact:first" if accepted else "artifact:root",
        ),
        "executor-a" if accepted else None,
        0,
    )


class Issue753ProjectSupervisionStateTests(unittest.TestCase):
    def test_sqlite_roundtrip_preserves_project_plane_progress(self):
        with tempfile.TemporaryDirectory() as directory:
            db = Path(directory) / "project.db"
            store = SQLiteProjectSupervisionStateStore(db)
            created = store.create(_snapshot(), holder_id="process-a")
            loaded = SQLiteProjectSupervisionStateStore(db).load("project-753")

            self.assertEqual(created, loaded)
            self.assertEqual(loaded.snapshot.accepted_work_unit_ids, frozenset({"first"}))
            self.assertEqual(loaded.snapshot.checkpoint.state_id, "state-first")
            self.assertEqual(loaded.owner.generation, 1)
            self.assertEqual(loaded.revision, 1)

    def test_roundtrip_preserves_logical_result_binding_after_correction(self):
        with tempfile.TemporaryDirectory() as directory:
            db = Path(directory) / "project.db"
            store = SQLiteProjectSupervisionStateStore(db)

            base = _snapshot(accepted=False)
            corrective = WorkUnit(
                "repair-first",
                "repair first work",
                ("first",),
                True,
                "first",
            )
            result = WorkExecutionResult(
                "repair-first",
                "executor-b",
                "provider-b",
                WorkExecutionStatus.SUCCEEDED,
                "state-repair",
                "artifact:repair",
                "evidence:repair",
            )
            snapshot = replace(
                base,
                units=base.units + (corrective,),
                executed_work_unit_ids=frozenset({"first", "repair-first"}),
                accepted_work_unit_ids=frozenset({"first", "repair-first"}),
                accepted_results=(result,),
                checkpoint=RepositoryCheckpoint(
                    "checkpoint-repair",
                    "repo-753",
                    "state-repair",
                    "artifact:repair",
                ),
                checkpoint_holder_executor_id="executor-b",
                accepted_result_bindings=(
                    ("first", result),
                    ("repair-first", result),
                ),
            )

            created = store.create(snapshot, holder_id="process-a")
            loaded = SQLiteProjectSupervisionStateStore(db).load("project-753")

            self.assertEqual(created, loaded)
            bindings = dict(loaded.snapshot.accepted_result_bindings)
            self.assertEqual(bindings["first"].work_unit_id, "repair-first")
            self.assertEqual(bindings["repair-first"].artifact_ref, "artifact:repair")

    def test_real_process_takeover_increments_fence_and_stale_owner_is_rejected(self):
        with tempfile.TemporaryDirectory() as directory:
            db = Path(directory) / "project.db"
            first_store = SQLiteProjectSupervisionStateStore(db)
            first = first_store.create(_snapshot(), holder_id="process-a")

            child = """
from pathlib import Path
import sys
from metao.project_supervision_state import (
    SQLiteProjectActionFence,
    SQLiteProjectSupervisionStateStore,
)

record = SQLiteProjectSupervisionStateStore(Path(sys.argv[1])).acquire(
    "project-753",
    holder_id="process-b",
)
print(f"{record.owner.holder_id}:{record.owner.generation}:{record.revision}")
"""
            completed = subprocess.run(
                [sys.executable, "-c", child, str(db)],
                check=True,
                capture_output=True,
                text=True,
            )
            self.assertEqual(completed.stdout.strip(), "process-b:2:2")

            resumed = SQLiteProjectSupervisionStateStore(db).load("project-753")
            self.assertEqual(resumed.owner.holder_id, "process-b")
            self.assertEqual(resumed.owner.generation, 2)

            with self.assertRaises(StaleProjectOwner):
                first_store.replace(
                    replace(first.snapshot, corrective_count=1),
                    owner=first.owner,
                    expected_revision=first.revision,
                )

            updated = SQLiteProjectSupervisionStateStore(db).replace(
                replace(resumed.snapshot, corrective_count=1),
                owner=resumed.owner,
                expected_revision=resumed.revision,
            )
            self.assertEqual(updated.revision, 3)
            self.assertEqual(updated.snapshot.corrective_count, 1)


    def test_stale_owner_is_rejected_before_runner_dispatch(self):
        with tempfile.TemporaryDirectory() as directory:
            db = Path(directory) / "project.db"
            store = SQLiteProjectSupervisionStateStore(db)
            stale = store.create(_snapshot(accepted=False), holder_id="process-a")
            store.acquire("project-753", holder_id="process-b")

            class Planner:
                def plan(self, objective):
                    raise AssertionError("resume state must provide graph")
                def corrective_work(self, objective, failed_unit, verification, graph):
                    return None

            class Scheduler:
                def select(self, unit, *, excluded_executor_ids):
                    return ExecutorTarget("executor-a", "provider-a")

            class Runner:
                calls = 0
                def run(self, objective, unit, target, checkpoint):
                    self.calls += 1
                    raise AssertionError("stale owner must be fenced before dispatch")

            class Repository:
                def initial(self, objective):
                    raise AssertionError("resume path must not request initial checkpoint")
                def capture(self, objective, unit, execution):
                    raise AssertionError("stale owner must not capture")
                def handoff(self, checkpoint, *, from_executor_id, to_executor_id):
                    return checkpoint

            class Verifier:
                def verify(self, objective, unit, execution, checkpoint):
                    return WorkVerificationResult(
                        True,
                        "independent-verifier",
                        "evidence",
                        "test",
                    )

            runner = Runner()
            with self.assertRaises(StaleProjectOwner):
                supervise_project(
                    objective=ProjectObjective(
                        "project-753",
                        "req-753",
                        "resume project after process crash",
                    ),
                    planner=Planner(),
                    scheduler=Scheduler(),
                    runner=runner,
                    repository=Repository(),
                    verifier=Verifier(),
                    resume_state=stale.snapshot,
                    persist_resume_state=lambda state: None,
                    action_fence=SQLiteProjectActionFence(
                        store,
                        lambda: stale.owner,
                    ),
                    max_executor_attempts_per_unit=1,
                    max_corrective_units=0,
                )
            self.assertEqual(runner.calls, 0)


    def test_stale_owner_atomic_action_is_rejected_before_effect(self):
        with tempfile.TemporaryDirectory() as directory:
            db = Path(directory) / "project.db"
            store = SQLiteProjectSupervisionStateStore(db)
            first = store.create(_snapshot(accepted=False), holder_id="process-a")
            store.acquire("project-753", holder_id="process-b")

            effects: list[str] = []
            with self.assertRaises(StaleProjectOwner):
                store.execute_if_owner(
                    first.owner,
                    lambda: effects.append("stale-effect"),
                )
            self.assertEqual(effects, [])

    def test_takeover_waits_for_current_atomic_action_boundary(self):
        with tempfile.TemporaryDirectory() as directory:
            db = Path(directory) / "project.db"
            store = SQLiteProjectSupervisionStateStore(db)
            first = store.create(_snapshot(accepted=False), holder_id="process-a")

            entered = threading.Event()
            release = threading.Event()
            action_done = threading.Event()
            takeover_done = threading.Event()
            takeover_records = []

            def action():
                entered.set()
                if not release.wait(timeout=2):
                    raise AssertionError("test did not release fenced action")
                action_done.set()
                return "done"

            action_thread = threading.Thread(
                target=lambda: store.execute_if_owner(first.owner, action),
                daemon=True,
            )
            action_thread.start()
            self.assertTrue(entered.wait(timeout=2))

            def takeover():
                takeover_records.append(
                    SQLiteProjectSupervisionStateStore(db).acquire(
                        "project-753",
                        holder_id="process-b",
                    )
                )
                takeover_done.set()

            takeover_thread = threading.Thread(target=takeover, daemon=True)
            takeover_thread.start()
            time.sleep(0.1)
            self.assertFalse(takeover_done.is_set())

            release.set()
            action_thread.join(timeout=2)
            takeover_thread.join(timeout=2)

            self.assertTrue(action_done.is_set())
            self.assertTrue(takeover_done.is_set())
            self.assertEqual(takeover_records[0].owner.holder_id, "process-b")
            self.assertEqual(takeover_records[0].owner.generation, 2)

    def test_resume_requires_durable_persistence_and_owner_fencing(self):
        class Planner:
            def plan(self, objective):
                raise AssertionError("resume state must provide graph")
            def corrective_work(self, objective, failed_unit, verification, graph):
                return None

        class Scheduler:
            def select(self, unit, *, excluded_executor_ids):
                return ExecutorTarget("executor-a", "provider-a")

        class Runner:
            def run(self, objective, unit, target, checkpoint):
                raise AssertionError("invalid resume configuration must fail before dispatch")

        class Repository:
            def initial(self, objective):
                raise AssertionError("resume path must not request initial checkpoint")
            def capture(self, objective, unit, execution):
                raise AssertionError("invalid resume configuration must fail before capture")
            def handoff(self, checkpoint, *, from_executor_id, to_executor_id):
                return checkpoint

        class Verifier:
            def verify(self, objective, unit, execution, checkpoint):
                raise AssertionError("invalid resume configuration must fail before verification")

        objective = ProjectObjective(
            "project-753",
            "req-753",
            "resume project after process crash",
        )
        state = _snapshot(accepted=False)

        with self.assertRaisesRegex(ValueError, "requires durable persistence"):
            supervise_project(
                objective=objective,
                planner=Planner(),
                scheduler=Scheduler(),
                runner=Runner(),
                repository=Repository(),
                verifier=Verifier(),
                resume_state=state,
                assert_resume_owner=lambda: None,
                max_executor_attempts_per_unit=1,
                max_corrective_units=0,
            )

        with self.assertRaisesRegex(ValueError, "requires atomic action fencing"):
            supervise_project(
                objective=objective,
                planner=Planner(),
                scheduler=Scheduler(),
                runner=Runner(),
                repository=Repository(),
                verifier=Verifier(),
                resume_state=state,
                persist_resume_state=lambda state: None,
                max_executor_attempts_per_unit=1,
                max_corrective_units=0,
            )

    def test_fresh_durable_supervision_requires_owner_fencing(self):
        class Planner:
            def plan(self, objective):
                return WorkGraph("metao", (WorkUnit("first", "first"),))
            def corrective_work(self, objective, failed_unit, verification, graph):
                return None

        class Scheduler:
            def select(self, unit, *, excluded_executor_ids):
                return ExecutorTarget("executor-a", "provider-a")

        class Runner:
            def run(self, objective, unit, target, checkpoint):
                raise AssertionError("invalid durable configuration must fail before dispatch")

        class Repository:
            def initial(self, objective):
                return RepositoryCheckpoint("root", "repo-753", "root", "artifact:root")
            def capture(self, objective, unit, execution):
                raise AssertionError("invalid durable configuration must fail before capture")
            def handoff(self, checkpoint, *, from_executor_id, to_executor_id):
                return checkpoint

        class Verifier:
            def verify(self, objective, unit, execution, checkpoint):
                raise AssertionError("invalid durable configuration must fail before verification")

        with self.assertRaisesRegex(ValueError, "requires atomic action fencing"):
            supervise_project(
                objective=ProjectObjective(
                    "project-753",
                    "req-753",
                    "resume project after process crash",
                ),
                planner=Planner(),
                scheduler=Scheduler(),
                runner=Runner(),
                repository=Repository(),
                verifier=Verifier(),
                persist_resume_state=lambda state: None,
                max_executor_attempts_per_unit=1,
                max_corrective_units=0,
            )

    def test_revision_compare_and_swap_rejects_lost_update(self):
        with tempfile.TemporaryDirectory() as directory:
            db = Path(directory) / "project.db"
            store = SQLiteProjectSupervisionStateStore(db)
            record = store.create(_snapshot(), holder_id="process-a")
            updated = store.replace(
                replace(record.snapshot, corrective_count=1),
                owner=record.owner,
                expected_revision=record.revision,
            )
            self.assertEqual(updated.revision, 2)

            with self.assertRaises(ProjectSupervisionStateConflict):
                store.replace(
                    replace(record.snapshot, corrective_count=2),
                    owner=record.owner,
                    expected_revision=record.revision,
                )

    def test_same_owner_reacquire_does_not_mint_new_generation(self):
        with tempfile.TemporaryDirectory() as directory:
            db = Path(directory) / "project.db"
            store = SQLiteProjectSupervisionStateStore(db)
            created = store.create(_snapshot(), holder_id="process-a")
            reacquired = SQLiteProjectSupervisionStateStore(db).acquire(
                "project-753",
                holder_id="process-a",
            )
            self.assertEqual(reacquired.owner, created.owner)
            self.assertEqual(reacquired.revision, created.revision)


class Issue753ProjectResumeAcrossCrashTests(unittest.TestCase):
    def test_process_b_resumes_only_pending_work_after_process_a_crash(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            db = root / "project.db"
            calls = root / "calls.log"

            worker = r"""
from __future__ import annotations

import os
from pathlib import Path
import sys

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
from metao.project_supervision_state import SQLiteProjectSupervisionStateStore

db = Path(sys.argv[1])
calls = Path(sys.argv[2])
mode = sys.argv[3]

class Planner:
    def plan(self, objective):
        return WorkGraph(
            "metao",
            (
                WorkUnit("first", "first"),
                WorkUnit("second", "second", ("first",)),
            ),
        )
    def corrective_work(self, objective, failed_unit, verification, graph):
        return None

class Scheduler:
    def select(self, unit, *, excluded_executor_ids):
        return ExecutorTarget("executor-a", "provider-a")

class Runner:
    def run(self, objective, unit, target, checkpoint):
        with calls.open("a", encoding="utf-8") as stream:
            stream.write(unit.work_unit_id + "\n")
        state = "state-" + unit.work_unit_id
        return WorkExecutionResult(
            unit.work_unit_id,
            target.executor_id,
            target.provider_id,
            WorkExecutionStatus.SUCCEEDED,
            state,
            artifact_ref="artifact:" + unit.work_unit_id,
            evidence_ref="execution:" + unit.work_unit_id,
        )

class Repository:
    def initial(self, objective):
        if mode == "b":
            raise AssertionError("resume path must not request a new initial checkpoint")
        return RepositoryCheckpoint("root", "repo-753", "root", "artifact:root")
    def capture(self, objective, unit, execution):
        return RepositoryCheckpoint(
            "checkpoint-" + unit.work_unit_id,
            "repo-753",
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
            "verification:" + unit.work_unit_id,
            "test:" + unit.work_unit_id,
        )

store = SQLiteProjectSupervisionStateStore(db)
record_box = [None]

if mode == "a":
    def persist(state):
        if record_box[0] is None:
            record_box[0] = store.create(state, holder_id="process-a")
        else:
            record_box[0] = store.replace(
                state,
                owner=record_box[0].owner,
                expected_revision=record_box[0].revision,
            )
        if state.accepted_work_unit_ids == frozenset({"first"}):
            os._exit(23)

    supervise_project(
        objective=ProjectObjective("project-753", "req-753", "resume project after process crash"),
        planner=Planner(),
        scheduler=Scheduler(),
        runner=Runner(),
        repository=Repository(),
        verifier=Verifier(),
        persist_resume_state=persist,
        action_fence=SQLiteProjectActionFence(
            store,
            lambda: record_box[0].owner,
        ),
        max_executor_attempts_per_unit=1,
        max_corrective_units=0,
    )
    raise AssertionError("process A should have crashed")
else:
    acquired = store.acquire("project-753", holder_id="process-b")
    record_box[0] = acquired

    def persist(state):
        record_box[0] = store.replace(
            state,
            owner=record_box[0].owner,
            expected_revision=record_box[0].revision,
        )

    result = supervise_project(
        objective=ProjectObjective("project-753", "req-753", "resume project after process crash"),
        planner=Planner(),
        scheduler=Scheduler(),
        runner=Runner(),
        repository=Repository(),
        verifier=Verifier(),
        resume_state=acquired.snapshot,
        persist_resume_state=persist,
        action_fence=SQLiteProjectActionFence(
            store,
            lambda: record_box[0].owner,
        ),
        max_executor_attempts_per_unit=1,
        max_corrective_units=0,
    )
    if result.verdict is not ProjectVerdict.PROJECT_UNVERIFIED:
        raise SystemExit(91)
    print("UNVERIFIED")
"""

            first = subprocess.run(
                [sys.executable, "-c", worker, str(db), str(calls), "a"],
                capture_output=True,
                text=True,
            )
            self.assertEqual(first.returncode, 23)

            after_crash = SQLiteProjectSupervisionStateStore(db).load("project-753")
            self.assertEqual(
                after_crash.snapshot.accepted_work_unit_ids,
                frozenset({"first"}),
            )
            self.assertEqual(after_crash.owner.holder_id, "process-a")

            second = subprocess.run(
                [sys.executable, "-c", worker, str(db), str(calls), "b"],
                check=True,
                capture_output=True,
                text=True,
            )
            self.assertEqual(second.stdout.strip(), "UNVERIFIED")

            self.assertEqual(
                calls.read_text(encoding="utf-8").splitlines(),
                ["first", "second"],
            )
            final = SQLiteProjectSupervisionStateStore(db).load("project-753")
            self.assertEqual(
                final.snapshot.accepted_work_unit_ids,
                frozenset({"first", "second"}),
            )
            self.assertEqual(final.owner.holder_id, "process-b")
            self.assertEqual(final.owner.generation, 2)
            self.assertEqual(
                final.snapshot.checkpoint.state_id,
                "state-second",
            )
            self.assertEqual(
                final.snapshot.trace[-1].kind,
                ProjectTraceKind.PROJECT_UNVERIFIED,
            )


if __name__ == "__main__":
    unittest.main(verbosity=2)
