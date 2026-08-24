"""Framework-neutral runtime admission gate.

A runtime is admitted to the operational registry/catalog only after an active
conformance probe succeeds. Admission is atomic with respect to registry/catalog
mutation: conformance or catalog-registration failure leaves no newly registered
runtime behind.
"""

from __future__ import annotations

from dataclasses import dataclass

from .catalog import OrchestratorCatalog
from .control_plane import EvidenceNormalizer
from .core import ExecutionRequest, OrchestratorContract, OrchestratorRegistry
from .runtime_conformance import (
    RuntimeConformanceError,
    RuntimeConformanceReport,
    assert_runtime_conformant,
)


@dataclass(frozen=True, slots=True)
class RuntimeAdmissionRecord:
    orchestrator_id: str
    conformance: RuntimeConformanceReport


class RuntimeAdmissionError(RuntimeError):
    def __init__(self, report: RuntimeConformanceReport) -> None:
        self.report = report
        failed = ", ".join(report.failed_checks) or "unknown"
        super().__init__(f"runtime admission blocked: {failed}")


class RuntimeAdmissionGate:
    """Admit conformant runtimes into an existing neutral registry/catalog.

    Current health is not an admission criterion. The conformance harness checks
    that a valid ``HealthReport`` is exposed; the catalog remains responsible for
    projecting HEALTHY/DEGRADED/UNHEALTHY at selection time.
    """

    def __init__(self, registry: OrchestratorRegistry, catalog: OrchestratorCatalog) -> None:
        self._registry = registry
        self._catalog = catalog

    def admit(
        self,
        orchestrator: OrchestratorContract,
        normalizer: EvidenceNormalizer,
        probe_request: ExecutionRequest,
        *,
        cost: float = 0.0,
        latency_ms: float = 1000.0,
        trust_profile: str = "local",
        success_rate: float = 0.5,
        quality: float = 0.5,
        reliability: float = 0.5,
    ) -> RuntimeAdmissionRecord:
        """Probe first, then atomically register runtime and routing metadata."""

        try:
            report = assert_runtime_conformant(orchestrator, normalizer, probe_request)
        except RuntimeConformanceError as exc:
            raise RuntimeAdmissionError(exc.report) from exc

        orchestrator_id = orchestrator.descriptor.orchestrator_id
        self._registry.register(orchestrator)
        try:
            self._catalog.register(
                orchestrator_id,
                normalizer=normalizer,
                cost=cost,
                latency_ms=latency_ms,
                trust_profile=trust_profile,
                success_rate=success_rate,
                quality=quality,
                reliability=reliability,
            )
        except Exception:
            # Catalog validation/registration must not leave a half-admitted runtime.
            self._registry.unregister(orchestrator_id)
            raise

        return RuntimeAdmissionRecord(orchestrator_id, report)


__all__ = [
    "RuntimeAdmissionRecord",
    "RuntimeAdmissionError",
    "RuntimeAdmissionGate",
]
