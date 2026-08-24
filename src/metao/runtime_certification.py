"""Deterministic, framework-neutral runtime conformance certificates.

A certificate records the result of one explicit conformance probe. It is not an
operational-admission record: a runtime may be conformant yet later fail catalog
registration because of invalid routing metadata.

Roadmap 5 adds optional issuance time. Legacy certificates keep the original
stable identity and ``certified_at_epoch=0``. Timestamped certificates form
append-only generations so an expired PASS can be deterministically re-certified
without mutating prior evidence.
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
    certified_at_epoch: float = 0.0

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
        if self.certified_at_epoch < 0:
            raise ValueError("runtime certification time must be non-negative")
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
                    key=lambda item: (item.certified_at_epoch, item.certificate_id),
                )
            )


def _epoch_token(certified_at_epoch: float) -> str:
    return f"{certified_at_epoch:.6f}"


def certificate_identity(
    orchestrator_id: str,
    runtime_version: str,
    probe_execution_id: str,
    *,
    certified_at_epoch: float = 0.0,
) -> str:
    if certified_at_epoch < 0:
        raise ValueError("runtime certification time must be non-negative")
    base = f"{orchestrator_id}:{runtime_version}:{probe_execution_id}"
    if certified_at_epoch == 0.0:
        return base
    return f"{base}:{_epoch_token(certified_at_epoch)}"


def is_certificate_fresh(
    certificate: RuntimeCertification,
    *,
    now_epoch: float,
    max_age_seconds: float,
) -> bool:
    """Return whether a timestamped certificate is reusable at ``now_epoch``.

    Legacy certificates with ``certified_at_epoch=0`` are intentionally stale
    when a freshness policy is enabled. Clock reversal also fails closed.
    """

    if now_epoch < 0:
        raise ValueError("current certification time must be non-negative")
    if max_age_seconds <= 0:
        raise ValueError("certificate max age must be positive")
    if certificate.certified_at_epoch <= 0:
        return False
    if now_epoch < certificate.certified_at_epoch:
        return False
    return (now_epoch - certificate.certified_at_epoch) <= max_age_seconds


def latest_passing_certificate(
    store: RuntimeCertificationStorePort,
    *,
    orchestrator_id: str,
    runtime_version: str,
    probe_execution_id: str,
    now_epoch: float | None = None,
    max_age_seconds: float | None = None,
) -> RuntimeCertification | None:
    """Find the newest exact PASS generation, optionally enforcing freshness."""

    if (now_epoch is None) != (max_age_seconds is None):
        raise ValueError("freshness lookup requires both now_epoch and max_age_seconds")
    matches = [
        item
        for item in store.history(orchestrator_id)
        if item.passed
        and item.runtime_version == runtime_version
        and item.probe_execution_id == probe_execution_id
    ]
    if now_epoch is not None and max_age_seconds is not None:
        matches = [
            item
            for item in matches
            if is_certificate_fresh(
                item,
                now_epoch=now_epoch,
                max_age_seconds=max_age_seconds,
            )
        ]
    if not matches:
        return None
    return max(matches, key=lambda item: (item.certified_at_epoch, item.certificate_id))


def certification_from_report(
    report: RuntimeConformanceReport,
    *,
    runtime_version: str,
    probe_execution_id: str,
    certified_at_epoch: float = 0.0,
) -> RuntimeCertification:
    if not runtime_version or not probe_execution_id:
        raise ValueError("runtime version and probe execution id are required")
    if certified_at_epoch < 0:
        raise ValueError("runtime certification time must be non-negative")
    checks_payload = [
        {"name": item.name, "passed": item.passed, "detail": item.detail}
        for item in report.checks
    ]
    digest = sha256(
        json.dumps(checks_payload, sort_keys=True, separators=(",", ":")).encode()
    ).hexdigest()
    return RuntimeCertification(
        certificate_id=certificate_identity(
            report.orchestrator_id,
            runtime_version,
            probe_execution_id,
            certified_at_epoch=certified_at_epoch,
        ),
        orchestrator_id=report.orchestrator_id,
        runtime_version=runtime_version,
        probe_execution_id=probe_execution_id,
        passed=report.passed,
        failed_checks=report.failed_checks,
        checks_digest=digest,
        total_checks=len(report.checks),
        certified_at_epoch=certified_at_epoch,
    )


def record_report(
    store: RuntimeCertificationStorePort,
    report: RuntimeConformanceReport,
    *,
    runtime_version: str,
    probe_execution_id: str,
    certified_at_epoch: float = 0.0,
) -> RuntimeCertification:
    return store.record(
        certification_from_report(
            report,
            runtime_version=runtime_version,
            probe_execution_id=probe_execution_id,
            certified_at_epoch=certified_at_epoch,
        )
    )


__all__ = [
    "RuntimeCertificationConflict",
    "RuntimeCertification",
    "RuntimeCertificationStorePort",
    "InMemoryRuntimeCertificationStore",
    "certificate_identity",
    "is_certificate_fresh",
    "latest_passing_certificate",
    "certification_from_report",
    "record_report",
]
