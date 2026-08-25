from __future__ import annotations

from dataclasses import replace
from hashlib import sha256
from pathlib import Path
import unittest

from metao.acceptance import EvidenceEnvelope
from metao.core import (
    ExecutionRequest,
    ExecutionResult,
    ExecutionStatus,
    HealthReport,
    HealthStatus,
    Mission,
    OrchestratorDescriptor,
)
from metao.runtime_conformance import (
    RuntimeConformanceError,
    assert_runtime_conformant,
    evaluate_runtime_conformance,
)


class ProbeRuntime:
    def __init__(
        self,
        *,
        health: HealthStatus = HealthStatus.HEALTHY,
        wrong_execution_id: bool = False,
        wrong_orchestrator_id: bool = False,
        raise_on_execute: bool = False,
    ) -> None:
        self._descriptor = OrchestratorDescriptor(
            "probe-runtime",
            "v1",
            frozenset({"workflow"}),
        )
        self._health = health
        self._wrong_execution_id = wrong_execution_id
        self._wrong_orchestrator_id = wrong_orchestrator_id
        self._raise_on_execute = raise_on_execute
        self.calls = 0

    @property
    def descriptor(self):
        return self._descriptor

    def health(self):
        return HealthReport(self._health, "probe")

    def execute(self, request: ExecutionRequest):
        self.calls += 1
        if self._raise_on_execute:
            raise RuntimeError("probe execution failed")
        return ExecutionResult(
            "wrong-execution" if self._wrong_execution_id else request.execution_id,
            "wrong-runtime" if self._wrong_orchestrator_id else self.descriptor.orchestrator_id,
            ExecutionStatus.SUCCEEDED,
            {"result": "ok"},
        )

    def cancel(self, execution_id: str) -> None:
        pass


def normalizer(
    *,
    request: ExecutionRequest,
    orchestrator_id: str,
    adapter_version: str,
    output,
    attempt_id: str,
) -> EvidenceEnvelope:
    digest = sha256(repr(sorted(dict(output).items())).encode()).hexdigest()
    return EvidenceEnvelope(
        evidence_id=f"{request.execution_id}:result",
        obligation_id="execution_result",
        mission_id=request.mission.mission_id,
        execution_id=request.execution_id,
        orchestrator_id=orchestrator_id,
        adapter_version=adapter_version,
        attempt_id=attempt_id,
        subject_id="subject",
        subject_state_id="state",
        verification_context_id="verify",
        policy_bundle_id="policy",
        verifier_id="probe-verifier",
        payload_digest=digest,
        provenance_root=f"probe:{orchestrator_id}:{request.execution_id}",
        authority_id="metao-runtime",
        passed=True,
    )


def request() -> ExecutionRequest:
    return ExecutionRequest(
        "probe-execution",
        Mission("probe-mission", "certify neutral runtime boundary", frozenset({"workflow"})),
    )


class RuntimeConformanceHarnessV1Tests(unittest.TestCase):
    def test_conformant_runtime_passes_contract_execution_and_evidence_bindings(self):
        runtime = ProbeRuntime()
        report = evaluate_runtime_conformance(runtime, normalizer, request())
        self.assertTrue(report.passed, report.failed_checks)
        self.assertEqual(report.orchestrator_id, "probe-runtime")
        self.assertEqual(runtime.calls, 1)
        self.assertEqual(report.failed_checks, ())

    def test_health_state_is_observed_as_shape_not_confused_with_contract_compliance(self):
        runtime = ProbeRuntime(health=HealthStatus.UNHEALTHY)
        report = evaluate_runtime_conformance(runtime, normalizer, request())
        self.assertTrue(report.passed, report.failed_checks)

    def test_wrong_execution_binding_fails_closed(self):
        report = evaluate_runtime_conformance(
            ProbeRuntime(wrong_execution_id=True),
            normalizer,
            request(),
        )
        self.assertFalse(report.passed)
        self.assertIn("execution_id_binding", report.failed_checks)

    def test_wrong_orchestrator_binding_fails_closed(self):
        report = evaluate_runtime_conformance(
            ProbeRuntime(wrong_orchestrator_id=True),
            normalizer,
            request(),
        )
        self.assertFalse(report.passed)
        self.assertIn("orchestrator_id_binding", report.failed_checks)

    def test_non_evidence_normalizer_output_fails_closed(self):
        report = evaluate_runtime_conformance(
            ProbeRuntime(),
            lambda **kwargs: {"not": "evidence"},
            request(),
        )
        self.assertFalse(report.passed)
        self.assertIn("evidence_normalizer_output", report.failed_checks)

    def test_misbound_evidence_fails_closed(self):
        def misbound(**kwargs):
            return replace(normalizer(**kwargs), execution_id="other-execution")

        report = evaluate_runtime_conformance(ProbeRuntime(), misbound, request())
        self.assertFalse(report.passed)
        self.assertIn("evidence_binding", report.failed_checks)

    def test_execution_exception_becomes_deterministic_failed_report(self):
        report = evaluate_runtime_conformance(
            ProbeRuntime(raise_on_execute=True),
            normalizer,
            request(),
        )
        self.assertFalse(report.passed)
        self.assertIn("execute_returns_result", report.failed_checks)

    def test_assert_helper_raises_report_backed_error(self):
        with self.assertRaises(RuntimeConformanceError) as raised:
            assert_runtime_conformant(
                ProbeRuntime(wrong_execution_id=True),
                normalizer,
                request(),
            )
        self.assertIn("execution_id_binding", raised.exception.report.failed_checks)

    def test_harness_remains_sdk_neutral(self):
        root = Path(__file__).resolve().parents[2]
        source = (root / "src/metao/runtime_conformance.py").read_text(encoding="utf-8").lower()
        for forbidden in (
            "langgraph",
            "crewai",
            "openai_agents",
            "microsoft.agent",
            "sklearn",
            "torch",
        ):
            self.assertNotIn(f"import {forbidden}", source)
            self.assertNotIn(f"from {forbidden}", source)


if __name__ == "__main__":
    unittest.main(verbosity=2)
