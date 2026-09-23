"""SelectionPolicy adapter backed by durable benchmark evidence."""

from __future__ import annotations

from dataclasses import dataclass

from .benchmark_routing import BenchmarkRoutingPolicy, EvidenceWeightedRouter
from .benchmark_store import BenchmarkEvidenceStorePort
from .strategy import OrchestratorPoolState


@dataclass(frozen=True, slots=True)
class BenchmarkSelectionPolicy:
    store: BenchmarkEvidenceStorePort
    routing_policy: BenchmarkRoutingPolicy

    def __post_init__(self) -> None:
        object.__setattr__(self, "_router", EvidenceWeightedRouter(self.routing_policy))

    def __call__(
        self,
        candidates: tuple[OrchestratorPoolState, ...],
        now_epoch: float | None,
    ) -> str | None:
        if now_epoch is None:
            raise ValueError("benchmark selection requires explicit mission time")
        evidence_by_executor = {
            candidate.orchestrator_id: self.store.history(candidate.orchestrator_id)
            for candidate in candidates
        }
        return self._router.select(
            candidates,
            evidence_by_executor,
            now_epoch=now_epoch,
        )


__all__ = ["BenchmarkSelectionPolicy"]
