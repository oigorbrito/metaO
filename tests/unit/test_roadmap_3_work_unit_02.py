from __future__ import annotations

from dataclasses import replace
from hashlib import sha256
from pathlib import Path
import unittest

from metao.acceptance import EvidenceEnvelope
from metao.catalog import OrchestratorCatalog
from metao.core import (
    ExecutionRequest,
    ExecutionResult,
    ExecutionStatus,
    HealthReport,
    HealthStatus,
    Mission,
    OrchestratorDescriptor,
    OrchestratorRegistry,
)
from metao.runtime_admission import RuntimeAdmissionError, RuntimeAdmissionGate
from metao.strategy import OrchestratorStatus


class ProbeRuntime:
    def __init__(
        self,
        orchestrator_id: str = "probe-runtime",
        *,
        health: HealthStatus = HealthStatus.HEALTHY,
        wrong_execution_id: bool = False,
    ) -> None:
        self._descriptor = OrchestratorDescriptor(
            orchestrator_id,
            "v1",
            frozenset({"workflow"}),
        )
        self._health = health
        self._wrong_execution_id = wrong_execution_id
        self.calls = 0

    @property
    def descriptor(self):
        return self._descriptor

    def health(self):
        return HealthReport(self._health, "probe")

    def execute(self, request: ExecutionRequest):
        self.calls += 1
        return ExecutionResult(
            "wrong-execution" if self._wrong_execution_id else request.execution_id,
            self.descriptor.orchestrator_id,
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


def probe_request() -> ExecutionRequest:
    return ExecutionRequest(
        "probe-execution",
        Mission("probe-mission", "admit neutral runtime", frozenset({"workflow"})),
    )


def build_gate():
    registry = OrchestratorRegistry()
    catalog = OrchestratorCatalog(registry)
    return registry, catalog, RuntimeAdmissionGate(registry, catalog)


class RuntimeAdmissionGateV1Tests(unittest.TestCase):
    def test_conformant_runtime_is_registered_only_after_probe(self):
        registry, catalog, gate = build_gate()
        runtime = ProbeRuntime()
        record = gate.admit(runtime, normalizer, probe_request(), cost=0.25)
        self.assertTrue(record.conformance.passed)
        self.assertEqual(record.orchestrator_id, "probe-runtime")
        self.assertIs(registry.get("probe-runtime"), runtime)
        self.assertEqual(runtime.calls, 1)
        self.assertEqual(catalog.entries()[0].cost, 0.25)

    def test_nonconformant_runtime_is_blocked_without_registry_or_catalog_mutation(self):
        registry, catalog, gate = build_gate()
        runtime = ProbeRuntime(wrong_execution_id=True)
        with self.assertRaises(RuntimeAdmissionError) as raised:
            gate.admit(runtime, normalizer, probe_request())
        self.assertIn("execution_id_binding", raised.exception.report.failed_checks)
        with self.assertRaises(KeyError):
            registry.get("probe-runtime")
        self.assertEqual(catalog.entries(), ())

    def test_misbound_evidence_blocks_admission_without_mutation(self):
        registry, catalog, gate = build_gate()

        def misbound(**kwargs):
            return replace(normalizer(**kwargs), orchestrator_id="other-runtime")

        with self.assertRaises(RuntimeAdmissionError) as raised:
            gate.admit(ProbeRuntime(), misbound, probe_request())
        self.assertIn("evidence_binding", raised.exception.report.failed_checks)
        with self.assertRaises(KeyError):
            registry.get("probe-runtime")
        self.assertEqual(catalog.entries(), ())

    def test_invalid_catalog_profile_rolls_back_new_registry_entry(self):
        registry, catalog, gate = build_gate()
        runtime = ProbeRuntime()
        with self.assertRaises(ValueError):
            gate.admit(runtime, normalizer, probe_request(), cost=-1.0)
        with self.assertRaises(KeyError):
            registry.get("probe-runtime")
        self.assertEqual(catalog.entries(), ())
        self.assertEqual(runtime.calls, 1)

    def test_duplicate_id_preserves_existing_admitted_runtime(self):
        registry, catalog, gate = build_gate()
        first = ProbeRuntime()
        second = ProbeRuntime()
        gate.admit(first, normalizer, probe_request())
        with self.assertRaises(ValueError):
            gate.admit(second, normalizer, probe_request())
        self.assertIs(registry.get("probe-runtime"), first)
        self.assertEqual(len(catalog.entries()), 1)
        self.assertEqual((first.calls, second.calls), (1, 1))

    def test_unhealthy_but_conformant_runtime_is_admitted_and_health_remains_live(self):
        registry, catalog, gate = build_gate()
        runtime = ProbeRuntime(health=HealthStatus.UNHEALTHY)
        record = gate.admit(runtime, normalizer, probe_request())
        self.assertTrue(record.conformance.passed)
        self.assertIs(registry.get("probe-runtime"), runtime)
        self.assertEqual(catalog.entries()[0].health, OrchestratorStatus.UNHEALTHY)

    def test_admission_preserves_normalizer_boundary(self):
        _, catalog, gate = build_gate()
        gate.admit(ProbeRuntime(), normalizer, probe_request())
        self.assertIs(catalog.normalizers()["probe-runtime"], normalizer)

    def test_conformance_failure_details_are_retained_by_admission_error(self):
        _, _, gate = build_gate()
        with self.assertRaises(RuntimeAdmissionError) as raised:
            gate.admit(ProbeRuntime(wrong_execution_id=True), normalizer, probe_request())
        self.assertEqual(raised.exception.report.orchestrator_id, "probe-runtime")
        self.assertFalse(raised.exception.report.passed)

    def test_admission_module_is_sdk_neutral_and_factory_independent(self):
        root = Path(__file__).resolve().parents[2]
        source = (root / "src/metao/runtime_admission.py").read_text(encoding="utf-8").lower()
        for forbidden in (
            "langgraph",
            "crewai",
            "openai_agents",
            "microsoft.agent",
            "sklearn",
            "torch",
            "runtime_factory",
        ):
            self.assertNotIn(f"import {forbidden}", source)
            self.assertNotIn(f"from {forbidden}", source)


if __name__ == "__main__":
    unittest.main(verbosity=2)
