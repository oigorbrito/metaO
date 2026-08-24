"""Runtime catalog overlay for explicit operator quarantine controls."""

from __future__ import annotations

from dataclasses import replace

from .catalog import OrchestratorCatalog, OrchestratorCatalogEntry
from .runtime_control import RuntimeControlStorePort, RuntimeDisposition
from .strategy import OrchestratorPoolState, OrchestratorStatus


class GovernedOrchestratorCatalog:
    """Projects durable operator controls over live runtime catalog health.

    QUARANTINED always wins over live health. ACTIVE means "no manual block" and
    therefore restores the catalog's actual health status rather than forcing a
    runtime healthy.
    """

    def __init__(
        self,
        catalog: OrchestratorCatalog,
        controls: RuntimeControlStorePort,
    ) -> None:
        self._catalog = catalog
        self._controls = controls

    def entries(self) -> tuple[OrchestratorCatalogEntry, ...]:
        result: list[OrchestratorCatalogEntry] = []
        for entry in self._catalog.entries():
            control = self._controls.current(entry.orchestrator_id)
            if control is not None and control.disposition is RuntimeDisposition.QUARANTINED:
                result.append(replace(entry, health=OrchestratorStatus.QUARANTINED))
            else:
                result.append(entry)
        return tuple(result)

    def pools(self) -> tuple[OrchestratorPoolState, ...]:
        return tuple(
            OrchestratorPoolState(
                orchestrator_id=entry.orchestrator_id,
                status=entry.health,
                capabilities=entry.capabilities,
                success_rate=entry.success_rate,
                quality=entry.quality,
                reliability=entry.reliability,
                latency_ms=entry.latency_ms,
                cost=entry.cost,
            )
            for entry in self.entries()
        )

    def normalizers(self):
        return self._catalog.normalizers()


__all__ = ["GovernedOrchestratorCatalog"]
