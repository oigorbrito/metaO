"""Framework-neutral runtime/adapter conformance harness.

The harness certifies boundary behavior, not business quality. It deliberately
knows nothing about LangGraph, CrewAI, or any other orchestrator SDK.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from .acceptance import EvidenceEnvelope
from .control_plane import EvidenceNormalizer
from .core import (
    ExecutionRequest,
    ExecutionResult,
    HealthReport,
    OrchestratorContract,
)


@dataclass(frozen=True, slots=True)
class ConformanceCheck:
    name: str
    passed: bool
    detail: str = ""


@dataclass(frozen=True, slots=True)
class RuntimeConformanceReport:
    orchestrator_id: str
    checks: tuple[ConformanceCheck, ...]

    @property
    def passed(self) -> bool:
        return bool(self.checks) and all(item.passed for item in self.checks)

    @property
    def failed_checks(self) -> tuple[str, ...]:
        return tuple(item.name for item in self.checks if not item.passed)


class RuntimeConformanceError(RuntimeError):
    def __init__(self, report: RuntimeConformanceReport) -> None:
        self.report = report
        failed = ", ".join(report.failed_checks) or "unknown"
        super().__init__(f"runtime conformance failed: {failed}")


def _check(name: str, condition: bool, detail: str = "") -> ConformanceCheck:
    return ConformanceCheck(name=name, passed=bool(condition), detail=detail)


def evaluate_runtime_conformance(
    orchestrator: OrchestratorContract,
    normalizer: EvidenceNormalizer,
    request: ExecutionRequest,
) -> RuntimeConformanceReport:
    """Execute one explicit probe and validate neutral boundary invariants.

    This is an active test harness: ``execute`` is called exactly once. Callers
    must provide a probe mission safe for the target runtime.
    """

    checks: list[ConformanceCheck] = []
    orchestrator_id = "<unknown>"

    contract_ok = isinstance(orchestrator, OrchestratorContract)
    checks.append(_check("orchestrator_contract", contract_ok))
    if not contract_ok:
        return RuntimeConformanceReport(orchestrator_id, tuple(checks))

    try:
        descriptor = orchestrator.descriptor
        orchestrator_id = descriptor.orchestrator_id
        descriptor_ok = bool(
            descriptor.orchestrator_id
            and descriptor.version
            and descriptor.capabilities
        )
        checks.append(_check("descriptor", descriptor_ok))
    except Exception as exc:
        checks.append(_check("descriptor", False, type(exc).__name__))
        return RuntimeConformanceReport(orchestrator_id, tuple(checks))

    try:
        health = orchestrator.health()
        checks.append(_check("health_report", isinstance(health, HealthReport)))
    except Exception as exc:
        checks.append(_check("health_report", False, type(exc).__name__))

    try:
        result = orchestrator.execute(request)
    except Exception as exc:
        checks.append(_check("execute_returns_result", False, type(exc).__name__))
        return RuntimeConformanceReport(orchestrator_id, tuple(checks))

    result_ok = isinstance(result, ExecutionResult)
    checks.append(_check("execute_returns_result", result_ok))
    if not result_ok:
        return RuntimeConformanceReport(orchestrator_id, tuple(checks))

    checks.append(
        _check(
            "execution_id_binding",
            result.execution_id == request.execution_id,
            f"expected={request.execution_id} actual={result.execution_id}",
        )
    )
    checks.append(
        _check(
            "orchestrator_id_binding",
            result.orchestrator_id == descriptor.orchestrator_id,
            f"expected={descriptor.orchestrator_id} actual={result.orchestrator_id}",
        )
    )

    if not callable(normalizer):
        checks.append(_check("evidence_normalizer_callable", False))
        return RuntimeConformanceReport(orchestrator_id, tuple(checks))
    checks.append(_check("evidence_normalizer_callable", True))

    try:
        evidence: Any = normalizer(
            request=request,
            orchestrator_id=descriptor.orchestrator_id,
            adapter_version=descriptor.version,
            output=result.output,
            attempt_id="conformance-attempt",
        )
    except Exception as exc:
        checks.append(_check("evidence_normalizer_output", False, type(exc).__name__))
        return RuntimeConformanceReport(orchestrator_id, tuple(checks))

    evidence_ok = isinstance(evidence, EvidenceEnvelope)
    checks.append(_check("evidence_normalizer_output", evidence_ok))
    if not evidence_ok:
        return RuntimeConformanceReport(orchestrator_id, tuple(checks))

    binding_ok = (
        evidence.mission_id == request.mission.mission_id
        and evidence.execution_id == request.execution_id
        and evidence.orchestrator_id == descriptor.orchestrator_id
        and evidence.adapter_version == descriptor.version
        and evidence.attempt_id == "conformance-attempt"
    )
    checks.append(_check("evidence_binding", binding_ok))

    required_evidence_fields_ok = all(
        (
            evidence.evidence_id,
            evidence.obligation_id,
            evidence.payload_digest,
            evidence.provenance_root,
            evidence.authority_id,
            evidence.verifier_id,
        )
    )
    checks.append(_check("evidence_required_fields", required_evidence_fields_ok))

    return RuntimeConformanceReport(orchestrator_id, tuple(checks))


def assert_runtime_conformant(
    orchestrator: OrchestratorContract,
    normalizer: EvidenceNormalizer,
    request: ExecutionRequest,
) -> RuntimeConformanceReport:
    report = evaluate_runtime_conformance(orchestrator, normalizer, request)
    if not report.passed:
        raise RuntimeConformanceError(report)
    return report


__all__ = [
    "ConformanceCheck",
    "RuntimeConformanceReport",
    "RuntimeConformanceError",
    "evaluate_runtime_conformance",
    "assert_runtime_conformant",
]
