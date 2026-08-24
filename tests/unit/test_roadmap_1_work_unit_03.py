from __future__ import annotations

from pathlib import Path
import unittest

from metao.acceptance import AcceptanceContext, AcceptanceDecision
from metao.adapters.langgraph import normalize_evidence
from metao.catalog import CatalogEntryAlreadyExists, OrchestratorCatalog
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
from metao.mission_store import InMemoryMissionStore
from metao.operator import MissionOperator
from metao.strategy import OrchestratorStatus


class Runtime:
    def __init__(self, orchestrator_id: str, *, health: HealthStatus = HealthStatus.HEALTHY) -> None:
        self._descriptor = OrchestratorDescriptor(orchestrator_id, "v1", frozenset({"workflow"}))
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
            {"result": f"done:{self.descriptor.orchestrator_id}"},
        )

    def cancel(self, execution_id: str) -> None:
        pass


class OrchestratorCatalogSelectionV1Tests(unittest.TestCase):
    def setUp(self) -> None:
        self.registry = OrchestratorRegistry()
        self.primary = Runtime("primary")
        self.fallback = Runtime("fallback")
        self.registry.register(self.primary)
        self.registry.register(self.fallback)
        self.catalog = OrchestratorCatalog(self.registry)
        self.context = AcceptanceContext(
            "subject-1",
            "state-1",
            "verify-1",
            "policy-1",
            frozenset({"execution_result"}),
        )
        self.budget = AcceptanceBudget(1.0, 1000, 60.0, 3)
        self.allow = evaluate_policy(policy_bundle_id="policy-1", allowed=True)

    def _register_primary(self) -> None:
        self.catalog.register(
            "primary",
            normalizer=normalize_evidence,
            cost=0.01,
            latency_ms=10.0,
            trust_profile="local-trusted",
            success_rate=0.99,
            quality=0.99,
            reliability=0.99,
        )

    def _register_fallback(self) -> None:
        self.catalog.register(
            "fallback",
            normalizer=normalize_evidence,
            cost=5.0,
            latency_ms=5000.0,
            trust_profile="sandbox",
            success_rate=0.2,
            quality=0.2,
            reliability=0.2,
        )

    def test_catalog_descriptor_combines_core_identity_and_operational_profile(self):
        self._register_primary()
        entry = self.catalog.entries()[0]

        self.assertEqual(entry.orchestrator_id, "primary")
        self.assertEqual(entry.version, "v1")
        self.assertEqual(entry.capabilities, frozenset({"workflow"}))
        self.assertEqual(entry.health, OrchestratorStatus.HEALTHY)
        self.assertEqual(entry.cost, 0.01)
        self.assertEqual(entry.latency_ms, 10.0)
        self.assertEqual(entry.trust_profile, "local-trusted")

    def test_catalog_observes_live_runtime_health(self):
        self._register_primary()
        self.assertEqual(self.catalog.entries()[0].health, OrchestratorStatus.HEALTHY)

        self.primary.health_status = HealthStatus.DEGRADED
        self.assertEqual(self.catalog.entries()[0].health, OrchestratorStatus.DEGRADED)

        self.primary.health_status = HealthStatus.UNHEALTHY
        self.assertEqual(self.catalog.entries()[0].health, OrchestratorStatus.UNHEALTHY)

    def test_duplicate_and_unknown_catalog_registration_fail_closed(self):
        self._register_primary()
        with self.assertRaises(CatalogEntryAlreadyExists):
            self._register_primary()
        with self.assertRaises(KeyError):
            self.catalog.register("missing", normalizer=normalize_evidence)

    def test_invalid_operational_profiles_are_rejected(self):
        with self.assertRaises(ValueError):
            self.catalog.register("primary", normalizer=normalize_evidence, cost=-1.0)
        with self.assertRaises(ValueError):
            self.catalog.register("primary", normalizer=normalize_evidence, success_rate=1.1)
        with self.assertRaises(ValueError):
            self.catalog.register("primary", normalizer=normalize_evidence, trust_profile="")

    def test_mission_operator_selects_from_catalog_without_manual_pools(self):
        self._register_primary()
        self._register_fallback()
        operator = MissionOperator(
            registry=self.registry,
            catalog=self.catalog,
            store=InMemoryMissionStore(),
        )

        outcome = operator.run(
            Mission("mission-catalog", "select catalog runtime", frozenset({"workflow"})),
            policy=self.allow,
            budget=self.budget,
            acceptance_context=self.context,
            now_epoch=100.0,
        )

        self.assertEqual(outcome.acceptance.decision, AcceptanceDecision.ACCEPT)
        self.assertEqual(outcome.orchestrator_id, "primary")
        self.assertEqual(self.primary.calls, 1)
        self.assertEqual(self.fallback.calls, 0)

    def test_unhealthy_preferred_runtime_is_excluded_by_live_catalog_snapshot(self):
        self._register_primary()
        self._register_fallback()
        self.primary.health_status = HealthStatus.UNHEALTHY
        operator = MissionOperator(
            registry=self.registry,
            catalog=self.catalog,
            store=InMemoryMissionStore(),
        )

        outcome = operator.run(
            Mission("mission-fallback", "select healthy runtime", frozenset({"workflow"})),
            policy=self.allow,
            budget=self.budget,
            acceptance_context=self.context,
            now_epoch=100.0,
        )

        self.assertEqual(outcome.orchestrator_id, "fallback")
        self.assertEqual(self.primary.calls, 0)
        self.assertEqual(self.fallback.calls, 1)

    def test_operator_rejects_ambiguous_catalog_and_manual_routing_configuration(self):
        self._register_primary()
        with self.assertRaises(ValueError):
            MissionOperator(
                registry=self.registry,
                catalog=self.catalog,
                pools=self.catalog.pools(),
                normalizers=self.catalog.normalizers(),
                store=InMemoryMissionStore(),
            )

    def test_catalog_and_core_remain_framework_sdk_neutral(self):
        root = Path(__file__).resolve().parents[2]
        for relative in ("src/metao/core.py", "src/metao/catalog.py"):
            source = (root / relative).read_text(encoding="utf-8").lower()
            for forbidden in ("import langgraph", "from langgraph", "import crewai", "from crewai"):
                self.assertNotIn(forbidden, source)


if __name__ == "__main__":
    unittest.main(verbosity=2)
