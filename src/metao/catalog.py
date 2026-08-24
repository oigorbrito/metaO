"""Framework-neutral orchestrator catalog and live routing snapshots."""

from __future__ import annotations

from dataclasses import dataclass

from .control_plane import EvidenceNormalizer
from .core import HealthStatus, OrchestratorRegistry
from .strategy import OrchestratorPoolState, OrchestratorStatus


class CatalogEntryAlreadyExists(RuntimeError):
    pass


@dataclass(frozen=True)
class OrchestratorCatalogEntry:
    orchestrator_id: str
    version: str
    capabilities: frozenset[str]
    health: OrchestratorStatus
    cost: float
    latency_ms: float
    trust_profile: str
    success_rate: float
    quality: float
    reliability: float


@dataclass(frozen=True)
class _CatalogProfile:
    orchestrator_id: str
    normalizer: EvidenceNormalizer
    cost: float
    latency_ms: float
    trust_profile: str
    success_rate: float
    quality: float
    reliability: float


class OrchestratorCatalog:
    """Operational metadata for orchestrators already registered in Core.

    Core owns the stable orchestrator contract. The catalog owns mutable-ish
    product routing metadata and observes live health through that contract.
    """

    def __init__(self, registry: OrchestratorRegistry) -> None:
        self._registry = registry
        self._profiles: dict[str, _CatalogProfile] = {}

    @staticmethod
    def _validate_unit_interval(name: str, value: float) -> None:
        if not 0.0 <= value <= 1.0:
            raise ValueError(f"{name} must be within [0, 1]")

    def register(
        self,
        orchestrator_id: str,
        *,
        normalizer: EvidenceNormalizer,
        cost: float = 0.0,
        latency_ms: float = 1000.0,
        trust_profile: str = "local",
        success_rate: float = 0.5,
        quality: float = 0.5,
        reliability: float = 0.5,
    ) -> None:
        if orchestrator_id in self._profiles:
            raise CatalogEntryAlreadyExists(orchestrator_id)
        if cost < 0 or latency_ms < 0:
            raise ValueError("catalog cost and latency must be non-negative")
        if not trust_profile:
            raise ValueError("trust_profile is required")
        for name, value in (
            ("success_rate", success_rate),
            ("quality", quality),
            ("reliability", reliability),
        ):
            self._validate_unit_interval(name, value)

        # Fail immediately if the catalog references a runtime not owned by Core.
        self._registry.get(orchestrator_id)
        self._profiles[orchestrator_id] = _CatalogProfile(
            orchestrator_id,
            normalizer,
            cost,
            latency_ms,
            trust_profile,
            success_rate,
            quality,
            reliability,
        )

    @staticmethod
    def _map_health(status: HealthStatus) -> OrchestratorStatus:
        if status is HealthStatus.HEALTHY:
            return OrchestratorStatus.HEALTHY
        if status is HealthStatus.DEGRADED:
            return OrchestratorStatus.DEGRADED
        return OrchestratorStatus.UNHEALTHY

    def entries(self) -> tuple[OrchestratorCatalogEntry, ...]:
        result: list[OrchestratorCatalogEntry] = []
        for orchestrator_id in sorted(self._profiles):
            profile = self._profiles[orchestrator_id]
            orchestrator = self._registry.get(orchestrator_id)
            descriptor = orchestrator.descriptor
            result.append(
                OrchestratorCatalogEntry(
                    orchestrator_id=orchestrator_id,
                    version=descriptor.version,
                    capabilities=descriptor.capabilities,
                    health=self._map_health(orchestrator.health().status),
                    cost=profile.cost,
                    latency_ms=profile.latency_ms,
                    trust_profile=profile.trust_profile,
                    success_rate=profile.success_rate,
                    quality=profile.quality,
                    reliability=profile.reliability,
                )
            )
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

    def normalizers(self) -> dict[str, EvidenceNormalizer]:
        return {key: self._profiles[key].normalizer for key in sorted(self._profiles)}


__all__ = [
    "CatalogEntryAlreadyExists",
    "OrchestratorCatalogEntry",
    "OrchestratorCatalog",
]
