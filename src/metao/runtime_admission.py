"""Framework-neutral runtime admission gate.

A runtime is admitted to the operational registry/catalog only after an active
conformance probe succeeds. Optional durable certification is recorded before
any operational mutation, so audit persistence can fail closed without leaving a
partially admitted runtime.
"""

from __future__ import annotations

from dataclasses import dataclass

from .catalog import OrchestratorCatalog
from .control_plane import EvidenceNormalizer
from .core import ExecutionRequest, OrchestratorContract, OrchestratorRegistry
from .runtime_certification import (
    RuntimeCertification,
    RuntimeCertificationStorePort,
    record_report,
)
from .runtime_conformance import RuntimeConformanceReport, evaluate_runtime_conformance


@dataclass(frozen=True, slots=True)
class RuntimeAdmissionRecord:
    orchestrator_id: str
    conformance: RuntimeConformanceReport
    certification: RuntimeCertification | None = None


class RuntimeAdmissionError(RuntimeError):
    def __init__(self, report: RuntimeConformanceReport) -> None:
        self.report = report
        failed = ", ".join(report.failed_checks) or "unknown"
        super().__init__(f"runtime admission blocked: {failed}")


def _runtime_version(orchestrator: OrchestratorContract) -> str:
    try:
        version = orchestrator.descriptor.version
    except Exception:
        return "<unknown>"
    return str(version) if version else "<unknown>"


class RuntimeAdmissionGate:
    """Admit conformant runtimes into an existing neutral registry/catalog.

    Current health is not an admission criterion. The conformance harness checks
    that a valid ``HealthReport`` is exposed; the catalog remains responsible for
    projecting HEALTHY/DEGRADED/UNHEALTHY at selection time.
    """

    def __init__(
        self,
        registry: OrchestratorRegistry,
        catalog: OrchestratorCatalog,
        certifications: RuntimeCertificationStorePort | None = None,
    ) -> None:
        self._registry = registry
        self._catalog = catalog
        self._certifications = certifications

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
        """Probe, optionally certify, then atomically register operational state."""

        report = evaluate_runtime_conformance(orchestrator, normalizer, probe_request)
        certification = None
        if self._certifications is not None:
            certification = record_report(
                self._certifications,
                report,
                runtime_version=_runtime_version(orchestrator),
                probe_execution_id=probe_request.execution_id,
            )

        if not report.passed:
            raise RuntimeAdmissionError(report)

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

        return RuntimeAdmissionRecord(orchestrator_id, report, certification)


__all__ = [
    "RuntimeAdmissionRecord",
    "RuntimeAdmissionError",
    "RuntimeAdmissionGate",
]
