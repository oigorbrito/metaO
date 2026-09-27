from __future__ import annotations

from pathlib import Path
import tempfile
import unittest

from metao.benchmark_evidence import (
    BenchmarkEvidence,
    BenchmarkEvidenceSource,
    BenchmarkMetric,
)
from metao.benchmark_routing import BenchmarkRoutingPolicy
from metao.benchmark_store import SQLiteBenchmarkEvidenceStore
from metao.routing_decision import SQLiteRoutingDecisionStore
from metao.strategy import OrchestratorPoolState, OrchestratorStatus, SelectionContext
from metao.task_family_selection import (
    MissingTaskFamilyPolicy,
    TaskFamilyBenchmarkSelectionPolicy,
    TaskFamilyRoutingPolicy,
)


def evidence(
    executor_id: str,
    *,
    evidence_id: str,
    task_set: str,
    score: float,
) -> BenchmarkEvidence:
    return BenchmarkEvidence(
        evidence_id=evidence_id,
        benchmark_id="executor-matrix",
        benchmark_version="v1",
        task_set=task_set,
        executor_id=executor_id,
        executor_version="1.0",
        harness_id="harness",
        harness_version="1.0",
        model_id="model",
        provider_id="provider",
        model_version="2026-09",
        runtime_config_digest=f"runtime-{executor_id}",
        tool_policy_digest="tool-policy",
        environment_id="test",
        observed_at_epoch=100.0,
        source=BenchmarkEvidenceSource.METAO_REPRODUCED,
        raw_result_ref=f"artifact://{evidence_id}",
        metrics=(BenchmarkMetric("success_rate", score, "ratio"),),
    )


def family_policy(task_set: str) -> BenchmarkRoutingPolicy:
    return BenchmarkRoutingPolicy(
        benchmark_id="executor-matrix",
        benchmark_version="v1",
        task_set=task_set,
        metric_name="success_rate",
        base_weight=0.1,
        benchmark_weight=0.9,
        max_age_seconds=60.0,
    )


class TaskFamilyBenchmarkSelectionTests(unittest.TestCase):
    def test_task_family_changes_ranking_without_changing_candidates(self):
        candidates = (
            OrchestratorPoolState(
                "alpha",
                OrchestratorStatus.HEALTHY,
                frozenset({"workflow"}),
                success_rate=0.8,
                quality=0.8,
            ),
            OrchestratorPoolState(
                "beta",
                OrchestratorStatus.HEALTHY,
                frozenset({"workflow"}),
                success_rate=0.8,
                quality=0.8,
            ),
        )
        with tempfile.TemporaryDirectory() as temp:
            db = Path(temp) / "routing.db"
            store = SQLiteBenchmarkEvidenceStore(db)
            decisions = SQLiteRoutingDecisionStore(db)
            for item in (
                evidence("alpha", evidence_id="alpha-code", task_set="coding", score=0.95),
                evidence("beta", evidence_id="beta-code", task_set="coding", score=0.20),
                evidence("alpha", evidence_id="alpha-terminal", task_set="terminal", score=0.10),
                evidence("beta", evidence_id="beta-terminal", task_set="terminal", score=0.90),
            ):
                store.record(item)

            policy = TaskFamilyBenchmarkSelectionPolicy(
                store,
                TaskFamilyRoutingPolicy(
                    {
                        "coding": family_policy("coding"),
                        "terminal": family_policy("terminal"),
                    }
                ),
                decision_store=decisions,
            )

            coding = policy.select_with_context(
                candidates,
                120.0,
                SelectionContext("mission-code", "exec-code", 1, "coding"),
            )
            terminal = policy.select_with_context(
                candidates,
                120.0,
                SelectionContext("mission-terminal", "exec-terminal", 1, "terminal"),
            )

            self.assertEqual(coding, "alpha")
            self.assertEqual(terminal, "beta")
            self.assertEqual(
                decisions.history("mission-code")[0].candidates[0].evidence_id,
                "alpha-code",
            )
            self.assertEqual(
                decisions.history("mission-terminal")[0].candidates[0].evidence_id,
                "beta-terminal",
            )
            self.assertNotEqual(
                decisions.history("mission-code")[0].policy_digest,
                decisions.history("mission-terminal")[0].policy_digest,
            )

    def test_unknown_family_fail_closed_is_explicit(self):
        with tempfile.TemporaryDirectory() as temp:
            store = SQLiteBenchmarkEvidenceStore(Path(temp) / "routing.db")
            policy = TaskFamilyBenchmarkSelectionPolicy(
                store,
                TaskFamilyRoutingPolicy(
                    {"coding": family_policy("coding")},
                    missing_family=MissingTaskFamilyPolicy.FAIL_CLOSED,
                ),
            )
            selected = policy.select_with_context(
                (
                    OrchestratorPoolState(
                        "alpha",
                        OrchestratorStatus.HEALTHY,
                        frozenset({"workflow"}),
                    ),
                ),
                120.0,
                SelectionContext("mission", "exec", 1, "unknown"),
            )
            self.assertIsNone(selected)

    def test_unknown_family_base_only_uses_only_supplied_candidates_and_records_reason(self):
        with tempfile.TemporaryDirectory() as temp:
            db = Path(temp) / "routing.db"
            store = SQLiteBenchmarkEvidenceStore(db)
            decisions = SQLiteRoutingDecisionStore(db)
            store.record(
                evidence(
                    "outside",
                    evidence_id="outside-high",
                    task_set="coding",
                    score=1.0,
                )
            )
            candidates = (
                OrchestratorPoolState(
                    "alpha",
                    OrchestratorStatus.HEALTHY,
                    frozenset({"workflow"}),
                    success_rate=0.9,
                    quality=0.9,
                ),
                OrchestratorPoolState(
                    "beta",
                    OrchestratorStatus.HEALTHY,
                    frozenset({"workflow"}),
                    success_rate=0.1,
                    quality=0.1,
                ),
            )
            policy = TaskFamilyBenchmarkSelectionPolicy(
                store,
                TaskFamilyRoutingPolicy(
                    {"coding": family_policy("coding")},
                    missing_family=MissingTaskFamilyPolicy.BASE_ONLY,
                ),
                decision_store=decisions,
            )
            selected = policy.select_with_context(
                candidates,
                120.0,
                SelectionContext("mission", "exec", 1, "unknown"),
            )
            self.assertEqual(selected, "alpha")
            receipt = decisions.history("mission")[0]
            self.assertEqual(
                tuple(item.executor_id for item in receipt.candidates),
                ("alpha", "beta"),
            )
            self.assertTrue(
                all(item.reason == "missing_task_family_base_only" for item in receipt.candidates)
            )
            self.assertNotIn("outside", {item.executor_id for item in receipt.candidates})


if __name__ == "__main__":
    unittest.main(verbosity=2)
