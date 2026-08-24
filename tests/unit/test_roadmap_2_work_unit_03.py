from __future__ import annotations

from pathlib import Path
import tempfile
import unittest

from metao.acceptance import AcceptanceContext
from metao.adapters.langgraph import normalize_evidence
from metao.catalog import OrchestratorCatalog
from metao.control_plane import MissionStatus
from metao.core import (
    ExecutionRequest,
    ExecutionResult,
    ExecutionStatus,
    HealthReport,
    HealthStatus,
    Mission,
    OrchestratorDescriptor,
    OrchestratorRegistry,
)
from metao.governance import AcceptanceBudget, evaluate_policy
from metao.governed_catalog import GovernedOrchestratorCatalog
from metao.mission_store import InMemoryMissionStore
from metao.operator import MissionOperator
from metao.runtime_control import (
    InMemoryRuntimeControlStore,
    RuntimeControlStorePort,
    RuntimeDisposition,
    quarantine,
    restore,
)
from metao.sqlite_runtime_control import SQLiteRuntimeControlStore
from metao.strategy import OrchestratorStatus


class Runtime:
    def __init__(self, orchestrator_id: str, health: HealthStatus = HealthStatus.HEALTHY):
        self._descriptor = OrchestratorDescriptor(
            orchestrator_id,
            "v1",
            frozenset({"workflow"}),
        )
        self.health_status = health
        self.calls = 0

    @property
    def descriptor(self):
        return self._descriptor

    def health(self):
        return HealthReport(self.health_status)

    def execute(self, request: ExecutionRequest):
        self.calls += 1
        return ExecutionResult(
            request.execution_id,
            self.descriptor.orchestrator_id,
            ExecutionStatus.SUCCEEDED,
            {"result": self.descriptor.orchestrator_id},
        )

    def cancel(self, execution_id: str) -> None:
        pass


def configured_operator(primary: Runtime, fallback: Runtime, controls):
    registry = OrchestratorRegistry()
    registry.register(primary)
    registry.register(fallback)
    base = OrchestratorCatalog(registry)
    base.register(
        primary.descriptor.orchestrator_id,
        normalizer=normalize_evidence,
        cost=0.01,
        latency_ms=10.0,
        success_rate=0.99,
        quality=0.99,
        reliability=0.99,
    )
    base.register(
        fallback.descriptor.orchestrator_id,
        normalizer=normalize_evidence,
        cost=5.0,
        latency_ms=5000.0,
        success_rate=0.2,
        quality=0.2,
        reliability=0.2,
    )
    governed = GovernedOrchestratorCatalog(base, controls)
    return MissionOperator(
        registry=registry,
        catalog=governed,
        store=InMemoryMissionStore(),
    ), governed


class DurableRuntimeQuarantineV1Tests(unittest.TestCase):
    def setUp(self) -> None:
        self.policy = evaluate_policy(policy_bundle_id="policy-wu03", allowed=True)
        self.budget = AcceptanceBudget(10.0, 10_000, 60.0, 4)
        self.context = AcceptanceContext(
            "subject-wu03",
            "state-wu03",
            "verify-wu03",
            "policy-wu03",
            frozenset({"execution_result"}),
        )

    def run(self, operator: MissionOperator, mission_id: str):
        return operator.run(
            Mission(mission_id, "govern runtime availability", frozenset({"workflow"})),
            policy=self.policy,
            budget=self.budget,
            acceptance_context=self.context,
            max_attempts=2,
        )

    def test_in_memory_control_is_revisioned_and_auditable(self):
        store = InMemoryRuntimeControlStore()
        self.assertIsInstance(store, RuntimeControlStorePort)
        first = quarantine(
            store,
            "runtime-a",
            reason="operator investigation",
            actor_id="operator-1",
            updated_at_epoch=10.0,
        )
        second = restore(
            store,
            "runtime-a",
            reason="investigation cleared",
            actor_id="operator-2",
            updated_at_epoch=20.0,
        )
        self.assertEqual((first.revision, second.revision), (1, 2))
        self.assertEqual(first.disposition, RuntimeDisposition.QUARANTINED)
        self.assertEqual(second.disposition, RuntimeDisposition.ACTIVE)
        self.assertEqual(store.current("runtime-a"), second)
        self.assertEqual(store.history("runtime-a"), (first, second))

    def test_sqlite_quarantine_and_restore_survive_restart(self):
        with tempfile.TemporaryDirectory() as temp:
            path = Path(temp) / "metao.db"
            first_store = SQLiteRuntimeControlStore(path)
            quarantined = quarantine(
                first_store,
                "runtime-a",
                reason="failure spike",
                actor_id="operator-1",
                updated_at_epoch=100.0,
            )
            restarted = SQLiteRuntimeControlStore(path)
            self.assertEqual(restarted.current("runtime-a"), quarantined)
            restored = restore(
                restarted,
                "runtime-a",
                reason="health verified",
                actor_id="operator-2",
                updated_at_epoch=200.0,
            )
            final = SQLiteRuntimeControlStore(path)
            self.assertEqual(final.current("runtime-a"), restored)
            self.assertEqual(
                [item.disposition for item in final.history("runtime-a")],
                [RuntimeDisposition.QUARANTINED, RuntimeDisposition.ACTIVE],
            )

    def test_quarantined_preferred_runtime_is_never_selected_or_executed(self):
        primary, fallback = Runtime("primary"), Runtime("fallback")
        controls = InMemoryRuntimeControlStore()
        quarantine(
            controls,
            "primary",
            reason="manual isolation",
            actor_id="operator",
            updated_at_epoch=10.0,
        )
        operator, governed = configured_operator(primary, fallback, controls)
        outcome = self.run(operator, "wu03-quarantine")
        self.assertEqual(outcome.state.status, MissionStatus.ACCEPTED)
        self.assertEqual(outcome.orchestrator_id, "fallback")
        self.assertEqual(primary.calls, 0)
        self.assertEqual(fallback.calls, 1)
        self.assertEqual(governed.entries()[1].health, OrchestratorStatus.QUARANTINED)

    def test_all_quarantined_runtimes_fail_closed_without_execution(self):
        primary, fallback = Runtime("primary"), Runtime("fallback")
        controls = InMemoryRuntimeControlStore()
        for runtime_id in ("primary", "fallback"):
            quarantine(
                controls,
                runtime_id,
                reason="fleet isolation",
                actor_id="operator",
                updated_at_epoch=10.0,
            )
        operator, _ = configured_operator(primary, fallback, controls)
        outcome = self.run(operator, "wu03-all-quarantined")
        self.assertEqual(outcome.state.status, MissionStatus.FAILED)
        self.assertIn("no_eligible_orchestrator", outcome.acceptance.reasons)
        self.assertEqual((primary.calls, fallback.calls), (0, 0))

    def test_restore_reenables_preferred_runtime_without_score_mutation(self):
        primary, fallback = Runtime("primary"), Runtime("fallback")
        controls = InMemoryRuntimeControlStore()
        quarantine(
            controls,
            "primary",
            reason="temporary isolation",
            actor_id="operator",
            updated_at_epoch=10.0,
        )
        restore(
            controls,
            "primary",
            reason="verified healthy",
            actor_id="operator",
            updated_at_epoch=20.0,
        )
        operator, governed = configured_operator(primary, fallback, controls)
        primary_entry = next(e for e in governed.entries() if e.orchestrator_id == "primary")
        self.assertEqual(primary_entry.health, OrchestratorStatus.HEALTHY)
        self.assertEqual(primary_entry.quality, 0.99)
        self.assertEqual(primary_entry.cost, 0.01)
        outcome = self.run(operator, "wu03-restored")
        self.assertEqual(outcome.orchestrator_id, "primary")
        self.assertEqual((primary.calls, fallback.calls), (1, 0))

    def test_active_control_never_overrides_unhealthy_runtime_health(self):
        primary = Runtime("primary", HealthStatus.UNHEALTHY)
        fallback = Runtime("fallback")
        controls = InMemoryRuntimeControlStore()
        restore(
            controls,
            "primary",
            reason="manual block removed",
            actor_id="operator",
            updated_at_epoch=10.0,
        )
        operator, governed = configured_operator(primary, fallback, controls)
        primary_entry = next(e for e in governed.entries() if e.orchestrator_id == "primary")
        self.assertEqual(primary_entry.health, OrchestratorStatus.UNHEALTHY)
        outcome = self.run(operator, "wu03-unhealthy")
        self.assertEqual(outcome.orchestrator_id, "fallback")
        self.assertEqual(primary.calls, 0)

    def test_quarantine_overrides_live_healthy_state_until_explicit_restore(self):
        primary, fallback = Runtime("primary"), Runtime("fallback")
        controls = InMemoryRuntimeControlStore()
        operator, governed = configured_operator(primary, fallback, controls)
        self.assertEqual(
            next(e for e in governed.entries() if e.orchestrator_id == "primary").health,
            OrchestratorStatus.HEALTHY,
        )
        quarantine(
            controls,
            "primary",
            reason="operator hold",
            actor_id="operator",
            updated_at_epoch=10.0,
        )
        self.assertEqual(
            next(e for e in governed.entries() if e.orchestrator_id == "primary").health,
            OrchestratorStatus.QUARANTINED,
        )

    def test_runtime_control_validation_fails_closed(self):
        store = InMemoryRuntimeControlStore()
        with self.assertRaises(ValueError):
            quarantine(store, "runtime", reason="", actor_id="operator", updated_at_epoch=1.0)
        with self.assertRaises(ValueError):
            quarantine(store, "runtime", reason="reason", actor_id="", updated_at_epoch=1.0)
        with self.assertRaises(ValueError):
            quarantine(store, "runtime", reason="reason", actor_id="operator", updated_at_epoch=-1.0)

    def test_quarantine_modules_remain_orchestrator_sdk_neutral(self):
        root = Path(__file__).resolve().parents[2]
        for relative in (
            "src/metao/runtime_control.py",
            "src/metao/sqlite_runtime_control.py",
            "src/metao/governed_catalog.py",
            "src/metao/runtime_factory.py",
        ):
            source = (root / relative).read_text(encoding="utf-8").lower()
            for forbidden in ("import langgraph", "from langgraph", "import crewai", "from crewai"):
                self.assertNotIn(forbidden, source)


if __name__ == "__main__":
    unittest.main(verbosity=2)
