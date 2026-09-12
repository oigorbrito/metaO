from __future__ import annotations

from contextlib import closing
from pathlib import Path
import sqlite3
import tempfile
import unittest

from metao.core import ExecutionStatus
from metao.runtime_health import RuntimeHealthHistoryCorrupt, RuntimeHealthTracker
from metao.sqlite_runtime_health import SQLiteRuntimeHealthStore


class DurableRuntimeHealthIntegrityTests(unittest.TestCase):
    def test_raw_string_status_is_not_accepted_as_execution_status(self):
        tracker = RuntimeHealthTracker(
            runtime_id="runtime",
            runtime_version="1",
            config_id="cfg",
        )
        with self.assertRaises(ValueError):
            tracker.record_execution("SUCCEEDED", execution_id="raw-string")  # type: ignore[arg-type]

        with tempfile.TemporaryDirectory() as temp:
            store = SQLiteRuntimeHealthStore(Path(temp) / "runtime.db")
            with self.assertRaises(ValueError):
                store.record(
                    runtime_id="runtime",
                    runtime_version="1",
                    config_id="cfg",
                    execution_id="raw-store-string",
                    status="FAILED",  # type: ignore[arg-type]
                )

    def test_sequence_gap_in_durable_history_fails_closed(self):
        with tempfile.TemporaryDirectory() as temp:
            path = Path(temp) / "runtime.db"
            SQLiteRuntimeHealthStore(path)
            with closing(sqlite3.connect(path)) as connection, connection:
                connection.execute(
                    """
                    INSERT INTO runtime_health_execution_facts(
                        runtime_id,runtime_version,config_id,execution_id,status,sequence
                    ) VALUES(?,?,?,?,?,?)
                    """,
                    (
                        "runtime",
                        "1",
                        "cfg",
                        "missing-predecessor",
                        ExecutionStatus.FAILED.value,
                        2,
                    ),
                )

            tracker = RuntimeHealthTracker(
                runtime_id="runtime",
                runtime_version="1",
                config_id="cfg",
                store=SQLiteRuntimeHealthStore(path),
            )
            with self.assertRaises(RuntimeHealthHistoryCorrupt):
                tracker.facts()


if __name__ == "__main__":
    unittest.main(verbosity=2)
