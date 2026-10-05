from __future__ import annotations

from dataclasses import replace
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

from metao.project_supervision import (
    ProjectTraceEvent,
    ProjectTraceKind,
    ProjectTraceabilityRecord,
    RepositoryCheckpoint,
    WorkExecutionResult,
    WorkExecutionStatus,
    WorkUnit,
)
from metao.project_supervision_state import (
    ProjectSupervisionSnapshot,
    ProjectSupervisionStateConflict,
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

    def test_real_process_takeover_increments_fence_and_stale_owner_is_rejected(self):
        with tempfile.TemporaryDirectory() as directory:
            db = Path(directory) / "project.db"
            first_store = SQLiteProjectSupervisionStateStore(db)
            first = first_store.create(_snapshot(), holder_id="process-a")

            child = """
from pathlib import Path
import sys
from metao.project_supervision_state import SQLiteProjectSupervisionStateStore

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


if __name__ == "__main__":
    unittest.main(verbosity=2)
