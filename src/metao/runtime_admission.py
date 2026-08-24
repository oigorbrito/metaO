"""Framework-neutral runtime admission gate.

A runtime is admitted to the operational registry/catalog only after either an
active conformance probe succeeds or an explicitly reused persisted PASS
certificate is strictly bound to the same runtime identity/version/probe id.
Optional freshness policy additionally requires the reused certificate to remain
inside its deterministic validity window.
"""

from __future__ import annotations

from dataclasses import dataclass

from .catalog import OrchestratorCatalog
from .control_plane import EvidenceNormalizer
from .core import ExecutionRequest, OrchestratorContract, OrchestratorRegistry
from .runtime_certification import (
    RuntimeCertification,
    RuntimeCertificationStorePort,
    is_certificate_fresh,
    record_report,
)
from .runtime_conformance import RuntimeConformanceReport, evaluate_runtime_conformance


@dataclass(frozen=True, slots=True)
class RuntimeAdmissionRecord:
    orchestrator_id: str
    conformance: RuntimeConformanceReport
    certification: RuntimeCertification | None = None


@dataclass(frozen=True, slots=True)
class RuntimeCertificateAdmissionRecord:
    orchestrator_id: str
    certification: RuntimeCertification


class RuntimeAdmissionError(RuntimeError):
    def __init__(self, report: RuntimeConformanceReport) -> None:
        self.report = report
        failed = ", ".join(report.failed_checks) or "unknown"
        super().__init__(f"runtime admission blocked: {failed}")


class RuntimeCertificateAdmissionError(RuntimeError):
    pass


def _runtime_version(orchestrator: OrchestratorContract) -> str:
    try:
        version = orchestrator.descriptor.version
    except Exception:
        return "<unknown>"
    return str(version) if version else "<unknown>"


class RuntimeAdmissionGate:
    """Admit conformant or strictly pre-certified runtimes atomically."""

    def __init__(
        self,
        registry: OrchestratorRegistry,
        catalog: OrchestratorCatalog,
        certifications: RuntimeCertificationStorePort | None = None,
    ) -> None:
        self._registry = registry
        self._catalog = catalog
        self._certifications = certifications

    def _register(
        self,
        orchestrator: OrchestratorContract,
        normalizer: EvidenceNormalizer,
        *,
        cost: float,
        latency_ms: float,
        trust_profile: str,
        success_rate: float,
        quality: float,
        reliability: float,
    ) -> str:
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
            self._registry.unregister(orchestrator_id)
            raise
        return orchestrator_id

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
        certified_at_epoch: float = 0.0,
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
                certified_at_epoch=certified_at_epoch,
            )
        if not report.passed:
            raise RuntimeAdmissionError(report)
        orchestrator_id = self._register(
            orchestrator,
            normalizer,
            cost=cost,
            latency_ms=latency_ms,
            trust_profile=trust_profile,
            success_rate=success_rate,
            quality=quality,
            reliability=reliability,
        )
        return RuntimeAdmissionRecord(orchestrator_id, report, certification)

    def admit_certified(
        self,
        orchestrator: OrchestratorContract,
        normalizer: EvidenceNormalizer,
        certificate: RuntimeCertification,
        *,
        expected_probe_execution_id: str,
        cost: float = 0.0,
        latency_ms: float = 1000.0,
        trust_profile: str = "local",
        success_rate: float = 0.5,
        quality: float = 0.5,
        reliability: float = 0.5,
        now_epoch: float | None = None,
        max_age_seconds: float | None = None,
    ) -> RuntimeCertificateAdmissionRecord:
        """Admit without probing only from an exact persisted, optionally fresh PASS."""

        if self._certifications is None:
            raise RuntimeCertificateAdmissionError("certification store is required for reuse")
        orchestrator_id = orchestrator.descriptor.orchestrator_id
        runtime_version = _runtime_version(orchestrator)
        if not certificate.passed:
            raise RuntimeCertificateAdmissionError("failed certificate cannot be reused")
        if certificate.orchestrator_id != orchestrator_id:
            raise RuntimeCertificateAdmissionError("certificate orchestrator binding mismatch")
        if certificate.runtime_version != runtime_version:
            raise RuntimeCertificateAdmissionError("certificate runtime version mismatch")
        if certificate.probe_execution_id != expected_probe_execution_id:
            raise RuntimeCertificateAdmissionError("certificate probe binding mismatch")
        if (now_epoch is None) != (max_age_seconds is None):
            raise RuntimeCertificateAdmissionError(
                "certificate freshness requires both now_epoch and max_age_seconds"
            )
        if now_epoch is not None and max_age_seconds is not None:
            try:
                fresh = is_certificate_fresh(
                    certificate,
                    now_epoch=now_epoch,
                    max_age_seconds=max_age_seconds,
                )
            except ValueError as exc:
                raise RuntimeCertificateAdmissionError("invalid certificate freshness policy") from exc
            if not fresh:
                raise RuntimeCertificateAdmissionError("certificate is stale")
        persisted = self._certifications.get(certificate.certificate_id)
        if persisted is None:
            raise RuntimeCertificateAdmissionError("certificate is not durably persisted")
        if persisted != certificate:
            raise RuntimeCertificateAdmissionError(
                "persisted certificate conflicts with supplied certificate"
            )
        admitted_id = self._register(
            orchestrator,
            normalizer,
            cost=cost,
            latency_ms=latency_ms,
            trust_profile=trust_profile,
            success_rate=success_rate,
            quality=quality,
            reliability=reliability,
        )
        return RuntimeCertificateAdmissionRecord(admitted_id, certificate)


__all__ = [
    "RuntimeAdmissionRecord",
    "RuntimeCertificateAdmissionRecord",
    "RuntimeAdmissionError",
    "RuntimeCertificateAdmissionError",
    "RuntimeAdmissionGate",
]
