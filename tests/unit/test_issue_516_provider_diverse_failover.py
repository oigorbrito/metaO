from __future__ import annotations

import unittest

from metao.capacity import CapacityStatus
from metao.project_scheduler import (
    CanonicalProjectExecutorScheduler,
    ExecutorProviderRegistration,
    WorkUnitSchedulingRequirements,
)
from metao.project_supervision import WorkUnit
from metao.strategy import OrchestratorPoolState, OrchestratorStatus


class Issue516ProviderDiverseFailoverTests(unittest.TestCase):
    def _pools(self):
        return (
            OrchestratorPoolState(
                "executor-a",
                OrchestratorStatus.HEALTHY,
                frozenset({"code"}),
                quality=0.99,
                reliability=0.99,
                capacity_status=CapacityStatus.AVAILABLE,
            ),
            OrchestratorPoolState(
                "executor-b",
                OrchestratorStatus.HEALTHY,
                frozenset({"code"}),
                quality=0.95,
                reliability=0.95,
                capacity_status=CapacityStatus.AVAILABLE,
            ),
            OrchestratorPoolState(
                "executor-c",
                OrchestratorStatus.HEALTHY,
                frozenset({"code"}),
                quality=0.80,
                reliability=0.80,
                capacity_status=CapacityStatus.AVAILABLE,
            ),
        )

    def _scheduler(self, *, provider_diverse_failover: bool):
        return CanonicalProjectExecutorScheduler(
            pools=self._pools(),
            requirements=(
                WorkUnitSchedulingRequirements("implement", frozenset({"code"})),
            ),
            registrations=(
                ExecutorProviderRegistration("executor-a", "provider-x"),
                ExecutorProviderRegistration("executor-b", "provider-x"),
                ExecutorProviderRegistration("executor-c", "provider-y"),
            ),
            provider_diverse_failover=provider_diverse_failover,
            now_epoch=100.0,
        )

    def test_provider_diverse_failover_skips_same_provider_alternate(self):
        scheduler = self._scheduler(provider_diverse_failover=True)
        target = scheduler.select(
            WorkUnit("implement", "implement"),
            excluded_executor_ids=frozenset({"executor-a"}),
        )
        self.assertIsNotNone(target)
        self.assertEqual(target.executor_id, "executor-c")
        self.assertEqual(target.provider_id, "provider-y")

    def test_ordinary_failover_may_use_same_provider_alternate(self):
        scheduler = self._scheduler(provider_diverse_failover=False)
        target = scheduler.select(
            WorkUnit("implement", "implement"),
            excluded_executor_ids=frozenset({"executor-a"}),
        )
        self.assertIsNotNone(target)
        self.assertEqual(target.executor_id, "executor-b")
        self.assertEqual(target.provider_id, "provider-x")

    def test_provider_diverse_mode_returns_none_without_other_provider(self):
        scheduler = CanonicalProjectExecutorScheduler(
            pools=self._pools()[:2],
            requirements=(
                WorkUnitSchedulingRequirements("implement", frozenset({"code"})),
            ),
            registrations=(
                ExecutorProviderRegistration("executor-a", "provider-x"),
                ExecutorProviderRegistration("executor-b", "provider-x"),
            ),
            provider_diverse_failover=True,
        )
        target = scheduler.select(
            WorkUnit("implement", "implement"),
            excluded_executor_ids=frozenset({"executor-a"}),
        )
        self.assertIsNone(target)

    def test_capability_filter_still_applies_after_provider_filter(self):
        pools = self._pools() + (
            OrchestratorPoolState(
                "executor-d",
                OrchestratorStatus.HEALTHY,
                frozenset({"docs"}),
                quality=1.0,
                reliability=1.0,
                capacity_status=CapacityStatus.AVAILABLE,
            ),
        )
        scheduler = CanonicalProjectExecutorScheduler(
            pools=pools,
            requirements=(
                WorkUnitSchedulingRequirements("implement", frozenset({"code"})),
            ),
            registrations=(
                ExecutorProviderRegistration("executor-a", "provider-x"),
                ExecutorProviderRegistration("executor-b", "provider-x"),
                ExecutorProviderRegistration("executor-c", "provider-y"),
                ExecutorProviderRegistration("executor-d", "provider-z"),
            ),
            provider_diverse_failover=True,
        )
        target = scheduler.select(
            WorkUnit("implement", "implement"),
            excluded_executor_ids=frozenset({"executor-a"}),
        )
        self.assertEqual(target.executor_id, "executor-c")


if __name__ == "__main__":
    unittest.main(verbosity=2)
