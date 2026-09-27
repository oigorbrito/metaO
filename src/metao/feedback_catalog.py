"""Catalog overlay applying durable deterministic runtime feedback."""

from __future__ import annotations

from dataclasses import replace

from .runtime_feedback import RuntimeFeedbackStorePort
from .strategy import OrchestratorPoolState


class HistoricalFeedbackCatalog:
    """Replace routing metrics with observed EMA only after evidence exists.

    Health/disposition and capabilities are inherited unchanged from the wrapped
    catalog, so quarantine and live health remain authoritative over selection.
    Reliability is intentionally left as configured metadata because the current
    deterministic scorer does not consume it and WU05 has no independent
    reliability observation signal.
    """

    def __init__(self, catalog, feedback: RuntimeFeedbackStorePort) -> None:
        self._catalog = catalog
        self._feedback = feedback

    def entries(self):
        result = []
        for entry in self._catalog.entries():
            history = self._feedback.score(entry.orchestrator_id)
            if history.samples == 0:
                result.append(entry)
                continue
            result.append(
                replace(
                    entry,
                    success_rate=history.outcome_ema,
                    quality=history.quality_ema,
                    latency_ms=history.latency_ema_ms,
                    cost=history.cost_ema,
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

    def normalizers(self):
        return self._catalog.normalizers()


__all__ = ["HistoricalFeedbackCatalog"]
