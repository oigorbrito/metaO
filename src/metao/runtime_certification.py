"""Deterministic, framework-neutral runtime conformance certificates.

A certificate records the result of one explicit conformance probe. It is not an
operational-admission record: a runtime may be conformant yet later fail catalog
registration because of invalid routing metadata.
"""

from __future__ import annotations

from dataclasses import dataclass
from hashlib import sha256
import json
from threading import RLock
from typing import Protocol, runtime_checkable

from .runtime_conformance import RuntimeConformanceReport


class RuntimeCertificationConflict(RuntimeError):
    pass


@dataclass(frozen=True, slots=True)
class RuntimeCertification:
    certificate_id: str
    orchestrator_id: str
    runtime_version: str
    probe_execution_id: str
    passed: bool
    failed_checks: tuple[str, ...]
    checks_digest: str
    total_checks: int

    def __post_init__(self) -> None:
        if not all(
            (
                self.certificate_id,
                self.orchestrator_id,
                self.runtime_version,
                self.probe_execution_id,
                self.checks_digest,
            )
        ):
            raise ValueError("runtime certification requires stable identities and digest")
        if self.total_checks < 1:
            raise ValueError("runtime certification requires at least one check")
        if self.passed and self.failed_checks:
            raise ValueError("passing runtime certification cannot contain failed checks")
        if not self.passed and not self.failed_checks:
            raise ValueError("failed runtime certification requires failed checks")


@runtime_checkable
class RuntimeCertificationStorePort(Protocol):
    def record(self, certificate: RuntimeCertification) -> RuntimeCertification: ...
    def get(self, certificate_id: str) -> RuntimeCertification | None: ...
    def history(self, orchestrator_id: str) -> tuple[RuntimeCertification, ...]: ...


class InMemoryRuntimeCertificationStore:
    def __init__(self) -> None:
        self._by_id: dict[str, RuntimeCertification] = {}
        self._lock = RLock()

    def record(self, certificate: RuntimeCertification) -> RuntimeCertification:
        with self._lock:
            existing = self._by_id.get(certificate.certificate_id)
            if existing is not None:
                if existing != certificate:
                    raise RuntimeCertificationConflict(certificate.certificate_id)
                return existing
            self._by_id[certificate.certificate_id] = certificate
            return certificate

    def get(self, certificate_id: str) -> RuntimeCertification | None:
        with self._lock:
            return self._by_id.get(certificate_id)

    def history(self, orchestrator_id: str) -> tuple[RuntimeCertification, ...]:
        with self._lock:
            return tuple(
                sorted(
                    (
                        item
                        for item in self._by_id.values()
                        if item.orchestrator_id == orchestrator_id
                    ),
                    key=lambda item: item.certificate_id,
                )
            )


def certification_from_report(
    report: RuntimeConformanceReport,
    *,
    runtime_version: str,
    probe_execution_id: str,
) -> RuntimeCertification:
    if not runtime_version or not probe_execution_id:
        raise ValueError("runtime version and probe execution id are required")
    checks_payload = [
        {"name": item.name, "passed": item.passed, "detail": item.detail}
        for item in report.checks
    ]
    digest = sha256(
        json.dumps(checks_payload, sort_keys=True, separators=(",", ":")).encode()
    ).hexdigest()
    certificate_id = f"{report.orchestrator_id}:{runtime_version}:{probe_execution_id}"
    return RuntimeCertification(
        certificate_id=certificate_id,
        orchestrator_id=report.orchestrator_id,
        runtime_version=runtime_version,
        probe_execution_id=probe_execution_id,
        passed=report.passed,
        failed_checks=report.failed_checks,
        checks_digest=digest,
        total_checks=len(report.checks),
    )


def record_report(
    store: RuntimeCertificationStorePort,
    report: RuntimeConformanceReport,
    *,
    runtime_version: str,
    probe_execution_id: str,
) -> RuntimeCertification:
    return store.record(
        certification_from_report(
            report,
            runtime_version=runtime_version,
            probe_execution_id=probe_execution_id,
        )
    )


__all__ = [
    "RuntimeCertificationConflict",
    "RuntimeCertification",
    "RuntimeCertificationStorePort",
    "InMemoryRuntimeCertificationStore",
    "certification_from_report",
    "record_report",
]
