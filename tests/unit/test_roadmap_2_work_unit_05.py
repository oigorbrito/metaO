from __future__ import annotations

from io import StringIO
import json
import os
from pathlib import Path
import sys
import tempfile
from types import ModuleType
import unittest
from unittest.mock import patch

from metao.acceptance import AcceptanceContext, AcceptanceDecision
from metao.adapters.langgraph import normalize_evidence
from metao.core import (
    ExecutionRequest,
    ExecutionResult,
    ExecutionStatus,
    HealthReport,
    HealthStatus,
    Mission,
    OrchestratorDescriptor,
)
from metao.entrypoint import main as cli_main
from metao.governance import AcceptanceBudget, evaluate_policy
from metao.mission_store import InMemoryMissionStore
from metao.runtime_control import InMemoryRuntimeControlStore, quarantine
from metao.runtime_factory import (
    RUNTIME_CATALOG_ENV,
    RuntimePlugin,
    create_operator_from_catalog,
)
from metao.runtime_feedback import (
    InMemoryRuntimeFeedbackStore,
    RuntimeFeedbackConflict,
    RuntimeObservation,
    RuntimeFeedbackStorePort,
)
from metao.sqlite_runtime_feedback import SQLiteRuntimeFeedbackStore
from metao.strategy import OrchestratorStatus


class Runtime:
    def __init__(self, orchestrator_id: str, *, fail_first: bool = False):
        self._descriptor = OrchestratorDescriptor(
            orchestrator_id,
            "v1",
            frozenset({"workflow"}),
        )
        self.fail_first = fail_first
        self.calls = 0

    @property
    def descriptor(self):
        return self._descriptor

    def health(self):
        return HealthReport(HealthStatus.HEALTHY)

    def execute(self, request: ExecutionRequest):
        self.calls += 1
        failed = self.fail_first and self.calls == 1
        return ExecutionResult(
            request.execution_id,
            self.descriptor.orchestrator_id,
            ExecutionStatus.FAILED if failed else ExecutionStatus.SUCCEEDED,
            {"result": self.descriptor.orchestrator_id},
            error="runtime failure" if failed else "",
        )

    def cancel(self, execution_id: str) -> None:
        pass


def catalog_entry(factory: str, *, preferred: bool) -> dict:
    return {
        "factory": factory,
        "cost": 0.01 if preferred else 5.0,
        "latency_ms": 10.0 if preferred else 5000.0,
        "success_rate": 0.99 if preferred else 0.20,
        "quality": 0.99 if preferred else 0.20,
        "reliability": 0.99 if preferred else 0.20,
        "trust_profile": "local-test",
    }


def observation(
    observation_id: str,
    orchestrator_id: str,
    *,
    outcome: float,
    latency_ms: float,
    cost: float,
    observed_at: float,
) -> RuntimeObservation:
    return RuntimeObservation(
        observation_id=observation_id,
        mission_id=observation_id.split(":", 1)[0],
        execution_id=observation_id,
        orchestrator_id=orchestrator_id,
        outcome=outcome,
        quality=outcome,
        latency_ms=latency_ms,
        cost=cost,
        observed_at_epoch=observed_at,
    )


class FailingRecordFeedback:
    def __init__(self) -> None:
        self.record_calls = 0

    def record(self, item):
        self.record_calls += 1
        raise RuntimeError("feedback unavailable")

    def history(self, orchestrator_id):
        return ()

    def score(self, orchestrator_id, *, alpha=0.2):
        from metao.strategy import HistoricalScore
        return HistoricalScore()


class DeterministicRuntimeFeedbackV1Tests(unittest.TestCase):
    def setUp(self) -> None:
        self.module_name = "metao_wu05_plugins"
        self.module = ModuleType(self.module_name)
        sys.modules[self.module_name] = self.module
        self.policy = evaluate_policy(policy_bundle_id="policy-wu05", allowed=True)
        self.budget = AcceptanceBudget(20.0, 10000, 60.0, 5)
        self.context = AcceptanceContext(
            "subject-wu05",
            "state-wu05",
            "verify-wu05",
            "policy-wu05",
            frozenset({"execution_result"}),
        )

    def tearDown(self) -> None:
        sys.modules.pop(self.module_name, None)

    def factory(self, name: str, runtime: Runtime) -> str:
        setattr(
            self.module,
            name,
            lambda runtime=runtime: RuntimePlugin(runtime, normalize_evidence),
        )
        return f"{self.module_name}:{name}"

    @staticmethod
    def write_manifest(path: Path, entries: list[dict]) -> Path:
        path.write_text(json.dumps({"runtimes": entries}), encoding="utf-8")
        return path

    def two_runtime_manifest(self, path: Path, primary: Runtime, fallback: Runtime) -> Path:
        return self.write_manifest(
            path,
            [
                catalog_entry(self.factory("primary", primary), preferred=True),
                catalog_entry(self.factory("fallback", fallback), preferred=False),
            ],
        )

    def run_mission(self, operator, mission_id: str):
        return operator.run(
            Mission(mission_id, "learn only from audited attempts", frozenset({"workflow"})),
            policy=self.policy,
            budget=self.budget,
            acceptance_context=self.context,
            max_attempts=2,
        )

    def test_in_memory_feedback_is_idempotent_and_conflicts_fail_closed(self):
        store = InMemoryRuntimeFeedbackStore()
        self.assertIsInstance(store, RuntimeFeedbackStorePort)
        item = observation("m1:e1", "runtime-a", outcome=1.0, latency_ms=10.0, cost=0.1, observed_at=1.0)
        self.assertEqual(store.record(item), item)
        self.assertEqual(store.record(item), item)
        self.assertEqual(store.history("runtime-a"), (item,))
        conflicting = RuntimeObservation(
            item.observation_id,
            item.mission_id,
            item.execution_id,
            item.orchestrator_id,
            0.0,
            0.0,
            item.latency_ms,
            item.cost,
            item.observed_at_epoch,
        )
        with self.assertRaises(RuntimeFeedbackConflict):
            store.record(conflicting)

    def test_historical_score_reuses_existing_deterministic_ema(self):
        store = InMemoryRuntimeFeedbackStore()
        store.record(observation("m1:e1", "runtime-a", outcome=0.0, latency_ms=100.0, cost=1.0, observed_at=1.0))
        store.record(observation("m2:e2", "runtime-a", outcome=1.0, latency_ms=300.0, cost=3.0, observed_at=2.0))
        score = store.score("runtime-a")
        self.assertEqual(score.samples, 2)
        self.assertAlmostEqual(score.outcome_ema, 0.2)
        self.assertAlmostEqual(score.quality_ema, 0.2)
        self.assertAlmostEqual(score.latency_ema_ms, 140.0)
        self.assertAlmostEqual(score.cost_ema, 1.4)

    def test_sqlite_feedback_survives_restart_without_duplicate_samples(self):
        with tempfile.TemporaryDirectory() as temp:
            path = Path(temp) / "metao.db"
            item = observation("m1:e1", "runtime-a", outcome=1.0, latency_ms=25.0, cost=0.5, observed_at=10.0)
            first = SQLiteRuntimeFeedbackStore(path)
            first.record(item)
            restarted = SQLiteRuntimeFeedbackStore(path)
            self.assertEqual(restarted.record(item), item)
            self.assertEqual(restarted.history("runtime-a"), (item,))
            self.assertEqual(restarted.score("runtime-a").samples, 1)

    def test_cold_start_preserves_manifest_routing_metrics(self):
        primary, fallback = Runtime("primary"), Runtime("fallback")
        feedback = InMemoryRuntimeFeedbackStore()
        with tempfile.TemporaryDirectory() as temp:
            manifest = self.two_runtime_manifest(Path(temp) / "runtimes.json", primary, fallback)
            operator = create_operator_from_catalog(
                manifest,
                store=InMemoryMissionStore(),
                feedback=feedback,
            )
            entries = {item.orchestrator_id: item for item in operator.runtime_entries()}
        self.assertEqual(entries["primary"].quality, 0.99)
        self.assertEqual(entries["primary"].cost, 0.01)
        self.assertEqual(entries["fallback"].quality, 0.20)

    def test_failed_preferred_runtime_feedback_changes_next_selection_deterministically(self):
        primary, fallback = Runtime("primary", fail_first=True), Runtime("fallback")
        feedback = InMemoryRuntimeFeedbackStore()
        with tempfile.TemporaryDirectory() as temp:
            manifest = self.two_runtime_manifest(Path(temp) / "runtimes.json", primary, fallback)
            operator = create_operator_from_catalog(
                manifest,
                store=InMemoryMissionStore(),
                feedback=feedback,
            )
            first = self.run_mission(operator, "wu05-first")
            second = self.run_mission(operator, "wu05-second")
        self.assertEqual(first.attempted_orchestrators, ("primary", "fallback"))
        self.assertEqual(first.acceptance.decision, AcceptanceDecision.ACCEPT)
        self.assertEqual(second.attempted_orchestrators, ("fallback",))
        self.assertEqual((primary.calls, fallback.calls), (1, 2))
        self.assertEqual(feedback.score("primary").outcome_ema, 0.0)
        self.assertEqual(feedback.score("fallback").outcome_ema, 1.0)

    def test_feedback_routing_survives_operator_restart(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            feedback_path = root / "feedback.db"
            primary1, fallback1 = Runtime("primary", fail_first=True), Runtime("fallback")
            manifest1 = self.two_runtime_manifest(root / "runtimes.json", primary1, fallback1)
            operator1 = create_operator_from_catalog(
                manifest1,
                store=InMemoryMissionStore(),
                feedback=SQLiteRuntimeFeedbackStore(feedback_path),
            )
            self.run_mission(operator1, "wu05-before-restart")

            primary2, fallback2 = Runtime("primary"), Runtime("fallback")
            self.factory("primary", primary2)
            self.factory("fallback", fallback2)
            operator2 = create_operator_from_catalog(
                manifest1,
                store=InMemoryMissionStore(),
                feedback=SQLiteRuntimeFeedbackStore(feedback_path),
            )
            outcome = self.run_mission(operator2, "wu05-after-restart")
        self.assertEqual(outcome.attempted_orchestrators, ("fallback",))
        self.assertEqual((primary2.calls, fallback2.calls), (0, 1))

    def test_quarantine_remains_authoritative_over_perfect_feedback(self):
        primary, fallback = Runtime("primary"), Runtime("fallback")
        feedback = InMemoryRuntimeFeedbackStore()
        feedback.record(observation("prior:e1", "primary", outcome=1.0, latency_ms=0.0, cost=0.0, observed_at=1.0))
        controls = InMemoryRuntimeControlStore()
        quarantine(
            controls,
            "primary",
            reason="operator hold",
            actor_id="operator",
            updated_at_epoch=2.0,
        )
        with tempfile.TemporaryDirectory() as temp:
            manifest = self.two_runtime_manifest(Path(temp) / "runtimes.json", primary, fallback)
            operator = create_operator_from_catalog(
                manifest,
                store=InMemoryMissionStore(),
                controls=controls,
                feedback=feedback,
            )
            entries = {item.orchestrator_id: item for item in operator.runtime_entries()}
            outcome = self.run_mission(operator, "wu05-quarantine")
        self.assertEqual(entries["primary"].health, OrchestratorStatus.QUARANTINED)
        self.assertEqual(outcome.orchestrator_id, "fallback")
        self.assertEqual(primary.calls, 0)

    def test_feedback_storage_failure_cannot_invalidate_committed_mission(self):
        runtime = Runtime("runtime-a")
        failing = FailingRecordFeedback()
        self.factory("single", runtime)
        with tempfile.TemporaryDirectory() as temp:
            manifest = self.write_manifest(
                Path(temp) / "runtimes.json",
                [catalog_entry(f"{self.module_name}:single", preferred=True)],
            )
            operator = create_operator_from_catalog(
                manifest,
                store=InMemoryMissionStore(),
                feedback=failing,
            )
            outcome = self.run_mission(operator, "wu05-feedback-down")
        self.assertEqual(outcome.acceptance.decision, AcceptanceDecision.ACCEPT)
        self.assertIsInstance(operator.feedback_error(), RuntimeError)
        self.assertEqual(failing.record_calls, 1)

    def test_installed_cli_reuses_same_sqlite_feedback_across_invocations(self):
        primary, fallback = Runtime("primary", fail_first=True), Runtime("fallback")
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            db = root / "metao.db"
            manifest = self.two_runtime_manifest(root / "runtimes.json", primary, fallback)

            def mission_file(mission_id: str) -> Path:
                path = root / f"{mission_id}.json"
                path.write_text(
                    json.dumps(
                        {
                            "mission": {
                                "mission_id": mission_id,
                                "objective": "cross invocation feedback",
                                "required_capabilities": ["workflow"],
                            },
                            "policy": {"policy_bundle_id": "policy-wu05", "allowed": True},
                            "budget": {
                                "money_limit": 20,
                                "token_limit": 10000,
                                "wall_time_limit_s": 60,
                                "verifier_attempt_limit": 5,
                            },
                            "acceptance_context": {
                                "subject_id": "subject-wu05",
                                "subject_state_id": "state-wu05",
                                "verification_context_id": "verify-wu05",
                                "policy_bundle_id": "policy-wu05",
                                "required_obligations": ["execution_result"],
                            },
                            "max_attempts": 2,
                        }
                    ),
                    encoding="utf-8",
                )
                return path

            with patch.dict(os.environ, {RUNTIME_CATALOG_ENV: str(manifest)}, clear=False):
                stdout, stderr = StringIO(), StringIO()
                first_code = cli_main(
                    [
                        "--db", str(db), "run", str(mission_file("wu05-cli-1")),
                        "--factory", "metao.runtime_factory:create_operator",
                    ],
                    stdout=stdout,
                    stderr=stderr,
                )
                self.assertEqual(first_code, 0, stderr.getvalue())
                self.assertEqual(json.loads(stdout.getvalue())["orchestrator_id"], "fallback")

                stdout, stderr = StringIO(), StringIO()
                second_code = cli_main(
                    [
                        "--db", str(db), "run", str(mission_file("wu05-cli-2")),
                        "--factory", "metao.runtime_factory:create_operator",
                    ],
                    stdout=stdout,
                    stderr=stderr,
                )
            self.assertEqual(second_code, 0, stderr.getvalue())
            second = json.loads(stdout.getvalue())
            persisted = SQLiteRuntimeFeedbackStore(db)
            primary_samples = persisted.score("primary").samples
            fallback_samples = persisted.score("fallback").samples
        self.assertEqual(second["orchestrator_id"], "fallback")
        self.assertEqual((primary.calls, fallback.calls), (1, 2))
        self.assertEqual(primary_samples, 1)
        self.assertEqual(fallback_samples, 2)

    def test_feedback_modules_remain_sdk_neutral_and_no_learned_router_is_added(self):
        root = Path(__file__).resolve().parents[2]
        for relative in (
            "src/metao/runtime_feedback.py",
            "src/metao/sqlite_runtime_feedback.py",
            "src/metao/feedback_catalog.py",
            "src/metao/runtime_factory.py",
        ):
            source = (root / relative).read_text(encoding="utf-8").lower()
            for forbidden in ("import langgraph", "from langgraph", "import crewai", "from crewai"):
                self.assertNotIn(forbidden, source)
            self.assertNotIn("sklearn", source)
            self.assertNotIn("torch", source)


if __name__ == "__main__":
    unittest.main(verbosity=2)
