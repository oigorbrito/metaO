"""Public operator facades for durable executions and metaO missions.

The module-level functions preserve the existing DurableExecutionPort API.
MissionOperator is the product-facing, framework-neutral facade over the
control-plane plus a MissionStorePort.
"""

from __future__ import annotations

from typing import Mapping

from metao.acceptance import AcceptanceContext
from metao.catalog import OrchestratorCatalog
from metao.control_plane import EvidenceNormalizer, MissionOutcome, MissionStatus, execute_mission
from metao.core import Mission, OrchestratorRegistry
from metao.durable import DurableExecutionPort, DurableExecutionSpec, DurableExecutionState
from metao.governance import AcceptanceBudget, PolicyDecision
from metao.mission_store import MissionAlreadyExists, MissionRecord, MissionStorePort
from metao.strategy import OrchestratorPoolState


def run(port: DurableExecutionPort, spec: DurableExecutionSpec) -> str:
    return port.start(spec)


def status(port: DurableExecutionPort, execution_id: str) -> DurableExecutionState:
    return port.state(execution_id)


def inspect(port: DurableExecutionPort, execution_id: str) -> DurableExecutionState:
    """Return the current authoritative durable execution state."""
    return port.state(execution_id)


def cancel(port: DurableExecutionPort, execution_id: str) -> None:
    port.cancel(execution_id)


def resume(port: DurableExecutionPort, execution_id: str) -> None:
    port.resume(execution_id)


class MissionOperator:
    """Configured synchronous mission facade backed by a MissionStorePort.

    Prefer ``catalog=`` for product usage. ``pools`` + ``normalizers`` remain
    supported as the lower-level compatibility path proven by earlier blocks.

    Cancellation/resume are intentionally not exposed here yet. A synchronous
    control-plane run has no truthful in-flight execution handle to cancel, and
    approval resume requires the explicit approval workflow planned later.
    """

    def __init__(
        self,
        *,
        registry: OrchestratorRegistry,
        store: MissionStorePort,
        catalog: OrchestratorCatalog | None = None,
        pools: tuple[OrchestratorPoolState, ...] = (),
        normalizers: Mapping[str, EvidenceNormalizer] | None = None,
    ) -> None:
        if catalog is not None and (pools or normalizers is not None):
            raise ValueError("configure MissionOperator with catalog or pools/normalizers, not both")
        if catalog is None and normalizers is None:
            raise ValueError("MissionOperator requires catalog or normalizers")

        self._registry = registry
        self._catalog = catalog
        self._pools = tuple(pools)
        self._normalizers = dict(normalizers or {})
        self._store = store

    def _routing_inputs(self) -> tuple[tuple[OrchestratorPoolState, ...], Mapping[str, EvidenceNormalizer]]:
        if self._catalog is not None:
            return self._catalog.pools(), self._catalog.normalizers()
        return self._pools, self._normalizers

    def run(
        self,
        mission: Mission,
        *,
        policy: PolicyDecision,
        budget: AcceptanceBudget,
        acceptance_context: AcceptanceContext,
        execution_id_prefix: str | None = None,
        now_epoch: float = 0.0,
        max_attempts: int = 2,
    ) -> MissionOutcome:
        """Execute and atomically register one canonical mission outcome."""
        if self._store.contains(mission.mission_id):
            raise MissionAlreadyExists(mission.mission_id)

        pools, normalizers = self._routing_inputs()
        outcome = execute_mission(
            mission=mission,
            registry=self._registry,
            pools=pools,
            normalizers=normalizers,
            policy=policy,
            budget=budget,
            acceptance_context=acceptance_context,
            execution_id_prefix=execution_id_prefix or f"{mission.mission_id}-exec",
            now_epoch=now_epoch,
            max_attempts=max_attempts,
        )
        self._store.create(MissionRecord(mission, outcome))
        return outcome

    def status(self, mission_id: str) -> MissionStatus:
        return self._store.get(mission_id).status

    def inspect(self, mission_id: str) -> MissionRecord:
        return self._store.get(mission_id)

    def list(self) -> tuple[MissionRecord, ...]:
        return self._store.list()


__all__ = ["run", "status", "inspect", "cancel", "resume", "MissionOperator"]
