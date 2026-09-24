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


class Issue514ProjectSchedulerAuthorityTests(unittest.TestCase):
    def _scheduler(self):
        pools = (
            OrchestratorPoolState(
                "executor-code",
                OrchestratorStatus.HEALTHY,
                frozenset({"code", "git"}),
                quality=0.9,
                reliability=0.9,
                capacity_status=CapacityStatus.AVAILABLE,
            ),
            OrchestratorPoolState(
                "executor-docs",
                OrchestratorStatus.HEALTHY,
                frozenset({"docs"}),
                quality=0.8,
                reliability=0.8,
                capacity_status=CapacityStatus.AVAILABLE,
            ),
        )
        return CanonicalProjectExecutorScheduler(
            pools=pools,
            requirements=(
                WorkUnitSchedulingRequirements("implement", frozenset({"code", "git"})),
                WorkUnitSchedulingRequirements("document", frozenset({"docs"})),
            ),
            registrations=(
                ExecutorProviderRegistration("executor-code", "provider-a"),
                ExecutorProviderRegistration("executor-docs", "provider-b"),
            ),
            now_epoch=100.0,
        )

    def test_capability_incompatible_executor_is_not_selected(self):
        scheduler = self._scheduler()
        target = scheduler.select(
            WorkUnit("implement", "implement feature"),
            excluded_executor_ids=frozenset(),
        )
        self.assertIsNotNone(target)
        self.assertEqual(target.executor_id, "executor-code")
        self.assertEqual(target.provider_id, "provider-a")

    def test_excluded_executor_is_not_returned(self):
        scheduler = self._scheduler()
        target = scheduler.select(
            WorkUnit("implement", "implement feature"),
            excluded_executor_ids=frozenset({"executor-code"}),
        )
        self.assertIsNone(target)

    def test_provider_identity_is_exact_configured_registration(self):
        scheduler = self._scheduler()
        target = scheduler.select(
            WorkUnit("document", "write docs"),
            excluded_executor_ids=frozenset(),
        )
        self.assertEqual(target.executor_id, "executor-docs")
        self.assertEqual(target.provider_id, "provider-b")

    def test_missing_work_unit_requirements_fails_closed(self):
        scheduler = self._scheduler()
        with self.assertRaisesRegex(ValueError, "missing scheduling requirements"):
            scheduler.select(
                WorkUnit("unknown", "unknown work"),
                excluded_executor_ids=frozenset(),
            )

    def test_missing_provider_registration_fails_closed_at_construction(self):
        pools = (
            OrchestratorPoolState(
                "executor-a",
                OrchestratorStatus.HEALTHY,
                frozenset({"code"}),
                capacity_status=CapacityStatus.AVAILABLE,
            ),
        )
        with self.assertRaisesRegex(ValueError, "missing provider registration"):
            CanonicalProjectExecutorScheduler(
                pools=pools,
                requirements=(
                    WorkUnitSchedulingRequirements("implement", frozenset({"code"})),
                ),
                registrations=(),
            )

    def test_duplicate_authority_bindings_are_rejected(self):
        pools = (
            OrchestratorPoolState(
                "executor-a",
                OrchestratorStatus.HEALTHY,
                frozenset({"code"}),
                capacity_status=CapacityStatus.AVAILABLE,
            ),
        )
        with self.assertRaisesRegex(ValueError, "duplicate work-unit"):
            CanonicalProjectExecutorScheduler(
                pools=pools,
                requirements=(
                    WorkUnitSchedulingRequirements("implement", frozenset({"code"})),
                    WorkUnitSchedulingRequirements("implement", frozenset({"code"})),
                ),
                registrations=(
                    ExecutorProviderRegistration("executor-a", "provider-a"),
                ),
            )


if __name__ == "__main__":
    unittest.main(verbosity=2)
