"""Typed project-to-executor scheduling authority.

This adapter bridges project work units to the existing framework-neutral runtime
routing model without deriving provider identity from free-form metadata and
without introducing a second scoring engine.
"""

from __future__ import annotations

from dataclasses import dataclass

from .project_supervision import ExecutorTarget, WorkUnit
from .strategy import OrchestratorPoolState, select_orchestrator


@dataclass(frozen=True, slots=True)
class WorkUnitSchedulingRequirements:
    work_unit_id: str
    required_capabilities: frozenset[str]

    def __post_init__(self) -> None:
        if not self.work_unit_id or not self.work_unit_id.strip():
            raise ValueError("work_unit_id must be non-empty")
        if not self.required_capabilities:
            raise ValueError("required_capabilities must be non-empty")
        if any(not value or not value.strip() for value in self.required_capabilities):
            raise ValueError("required_capabilities cannot contain blank values")


@dataclass(frozen=True, slots=True)
class ExecutorProviderRegistration:
    executor_id: str
    provider_id: str

    def __post_init__(self) -> None:
        if not self.executor_id or not self.executor_id.strip():
            raise ValueError("executor_id must be non-empty")
        if not self.provider_id or not self.provider_id.strip():
            raise ValueError("provider_id must be non-empty")


class CanonicalProjectExecutorScheduler:
    """Project scheduler backed by canonical work requirements and provider ids.

    The scheduler reuses ``select_orchestrator`` for health/capacity/cost routing.
    It owns no acceptance, retry, failover execution, or budget mutation authority.
    """

    def __init__(
        self,
        *,
        pools: tuple[OrchestratorPoolState, ...],
        requirements: tuple[WorkUnitSchedulingRequirements, ...],
        registrations: tuple[ExecutorProviderRegistration, ...],
        now_epoch: float = 0.0,
        provider_diverse_failover: bool = False,
    ) -> None:
        self._pools = pools
        self._now_epoch = now_epoch
        self._provider_diverse_failover = provider_diverse_failover
        self._requirements = self._unique_requirements(requirements)
        self._providers = self._unique_registrations(registrations)

        pool_ids = {pool.orchestrator_id for pool in pools}
        if not pool_ids:
            raise ValueError("project scheduler requires executor pools")
        missing = pool_ids - self._providers.keys()
        if missing:
            raise ValueError(
                f"missing provider registration for executor: {sorted(missing)[0]}"
            )

    @staticmethod
    def _unique_requirements(
        values: tuple[WorkUnitSchedulingRequirements, ...],
    ) -> dict[str, WorkUnitSchedulingRequirements]:
        result: dict[str, WorkUnitSchedulingRequirements] = {}
        for value in values:
            if value.work_unit_id in result:
                raise ValueError(
                    f"duplicate work-unit scheduling requirements: {value.work_unit_id}"
                )
            result[value.work_unit_id] = value
        return result

    @staticmethod
    def _unique_registrations(
        values: tuple[ExecutorProviderRegistration, ...],
    ) -> dict[str, str]:
        result: dict[str, str] = {}
        for value in values:
            if value.executor_id in result:
                raise ValueError(
                    f"duplicate executor provider registration: {value.executor_id}"
                )
            result[value.executor_id] = value.provider_id
        return result

    def select(
        self,
        unit: WorkUnit,
        *,
        excluded_executor_ids: frozenset[str],
    ) -> ExecutorTarget | None:
        requirements = self._requirements.get(unit.work_unit_id)
        if requirements is None:
            raise ValueError(
                f"missing scheduling requirements for work unit: {unit.work_unit_id}"
            )

        excluded_provider_ids = (
            frozenset(
                self._providers[executor_id]
                for executor_id in excluded_executor_ids
                if executor_id in self._providers
            )
            if self._provider_diverse_failover and excluded_executor_ids
            else frozenset()
        )

        eligible = tuple(
            pool
            for pool in self._pools
            if pool.orchestrator_id not in excluded_executor_ids
            and self._providers[pool.orchestrator_id] not in excluded_provider_ids
            and requirements.required_capabilities <= pool.capabilities
        )
        selected = select_orchestrator(eligible, now_epoch=self._now_epoch)
        if selected is None:
            return None

        provider_id = self._providers.get(selected)
        if provider_id is None:
            raise ValueError(f"missing provider registration for executor: {selected}")
        return ExecutorTarget(selected, provider_id)


__all__ = [
    "WorkUnitSchedulingRequirements",
    "ExecutorProviderRegistration",
    "CanonicalProjectExecutorScheduler",
]
