from __future__ import annotations

from dataclasses import replace
from hashlib import sha256
from pathlib import Path
import tempfile
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
from metao.runtime_certification import (
    InMemoryRuntimeCertificationStore,
    RuntimeCertificationConflict,
    certification_from_report,
)
from metao.runtime_conformance import evaluate_runtime_conformance
from metao.sqlite_runtime_certification import SQLiteRuntimeCertificationStore


class ProbeRuntime:
    def __init__(self, *, wrong_execution_id: bool = False) -> None:
        self._descriptor = OrchestratorDescriptor(
            "probe-runtime",
            "v1",
            frozenset({"workflow"}),
        )
        self._wrong_execution_id = wrong_execution_id
        self.calls = 0

    @property
    def descriptor(self):
        return self._descriptor

    def health(self):
        return HealthReport(HealthStatus.HEALTHY, "probe")

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
        Mission("probe-mission", "certify runtime admission", frozenset({"workflow"})),
    )


def build_gate(certifications=None):
    registry = OrchestratorRegistry()
    catalog = OrchestratorCatalog(registry)
    return registry, catalog, RuntimeAdmissionGate(registry, catalog, certifications)


class FailingCertificationStore:
    def record(self, certificate):
        raise RuntimeError("certification store unavailable")

    def get(self, certificate_id):
        return None

    def history(self, orchestrator_id):
        return ()


class DurableRuntimeCertificationV1Tests(unittest.TestCase):
    def test_in_memory_certificate_recording_is_idempotent_and_conflicts_fail_closed(self):
        report = evaluate_runtime_conformance(ProbeRuntime(), normalizer, probe_request())
        certificate = certification_from_report(
            report,
            runtime_version="v1",
            probe_execution_id="probe-execution",
        )
        store = InMemoryRuntimeCertificationStore()
        self.assertEqual(store.record(certificate), certificate)
        self.assertEqual(store.record(certificate), certificate)
        self.assertEqual(store.history("probe-runtime"), (certificate,))
        with self.assertRaises(RuntimeCertificationConflict):
            store.record(replace(certificate, checks_digest="0" * 64))

    def test_certificate_identity_and_digest_are_deterministic_for_same_probe_report(self):
        report = evaluate_runtime_conformance(ProbeRuntime(), normalizer, probe_request())
        first = certification_from_report(report, runtime_version="v1", probe_execution_id="probe-execution")
        second = certification_from_report(report, runtime_version="v1", probe_execution_id="probe-execution")
        self.assertEqual(first, second)
        self.assertEqual(first.certificate_id, "probe-runtime:v1:probe-execution")
        self.assertTrue(first.passed)
        self.assertEqual(first.failed_checks, ())
        self.assertEqual(len(first.checks_digest), 64)

    def test_sqlite_certification_survives_restart_without_duplicate_record(self):
        with tempfile.TemporaryDirectory() as temp:
            path = Path(temp) / "metao.db"
            report = evaluate_runtime_conformance(ProbeRuntime(), normalizer, probe_request())
            certificate = certification_from_report(
                report,
                runtime_version="v1",
                probe_execution_id="probe-execution",
            )
            first = SQLiteRuntimeCertificationStore(path)
            first.record(certificate)
            restarted = SQLiteRuntimeCertificationStore(path)
            self.assertEqual(restarted.record(certificate), certificate)
            self.assertEqual(restarted.get(certificate.certificate_id), certificate)
            self.assertEqual(restarted.history("probe-runtime"), (certificate,))

    def test_successful_admission_returns_and_persists_passing_certificate(self):
        store = InMemoryRuntimeCertificationStore()
        registry, catalog, gate = build_gate(store)
        runtime = ProbeRuntime()
        record = gate.admit(runtime, normalizer, probe_request())
        self.assertIsNotNone(record.certification)
        self.assertTrue(record.certification.passed)
        self.assertEqual(store.history("probe-runtime"), (record.certification,))
        self.assertIs(registry.get("probe-runtime"), runtime)
        self.assertEqual(len(catalog.entries()), 1)

    def test_failed_conformance_is_certified_but_not_operationally_admitted(self):
        store = InMemoryRuntimeCertificationStore()
        registry, catalog, gate = build_gate(store)
        with self.assertRaises(RuntimeAdmissionError):
            gate.admit(ProbeRuntime(wrong_execution_id=True), normalizer, probe_request())
        history = store.history("probe-runtime")
        self.assertEqual(len(history), 1)
        self.assertFalse(history[0].passed)
        self.assertIn("execution_id_binding", history[0].failed_checks)
        with self.assertRaises(KeyError):
            registry.get("probe-runtime")
        self.assertEqual(catalog.entries(), ())

    def test_certification_store_failure_blocks_admission_before_registry_mutation(self):
        registry, catalog, gate = build_gate(FailingCertificationStore())
        runtime = ProbeRuntime()
        with self.assertRaisesRegex(RuntimeError, "certification store unavailable"):
            gate.admit(runtime, normalizer, probe_request())
        self.assertEqual(runtime.calls, 1)
        with self.assertRaises(KeyError):
            registry.get("probe-runtime")
        self.assertEqual(catalog.entries(), ())

    def test_catalog_validation_failure_can_leave_conformance_certificate_but_no_admission(self):
        store = InMemoryRuntimeCertificationStore()
        registry, catalog, gate = build_gate(store)
        with self.assertRaises(ValueError):
            gate.admit(ProbeRuntime(), normalizer, probe_request(), cost=-1.0)
        history = store.history("probe-runtime")
        self.assertEqual(len(history), 1)
        self.assertTrue(history[0].passed)
        with self.assertRaises(KeyError):
            registry.get("probe-runtime")
        self.assertEqual(catalog.entries(), ())

    def test_same_probe_identity_with_changed_result_conflicts_before_admission(self):
        store = InMemoryRuntimeCertificationStore()
        passing = evaluate_runtime_conformance(ProbeRuntime(), normalizer, probe_request())
        store.record(
            certification_from_report(
                passing,
                runtime_version="v1",
                probe_execution_id="probe-execution",
            )
        )
        registry, catalog, gate = build_gate(store)
        with self.assertRaises(RuntimeCertificationConflict):
            gate.admit(ProbeRuntime(wrong_execution_id=True), normalizer, probe_request())
        with self.assertRaises(KeyError):
            registry.get("probe-runtime")
        self.assertEqual(catalog.entries(), ())

    def test_certification_modules_are_sdk_neutral_and_factory_independent(self):
        root = Path(__file__).resolve().parents[2]
        for relative in (
            "src/metao/runtime_certification.py",
            "src/metao/sqlite_runtime_certification.py",
            "src/metao/runtime_admission.py",
        ):
            source = (root / relative).read_text(encoding="utf-8").lower()
            for forbidden in (
                "import langgraph",
                "from langgraph",
                "import crewai",
                "from crewai",
                "sklearn",
                "torch",
                "from .runtime_factory",
                "import runtime_factory",
            ):
                self.assertNotIn(forbidden, source)


if __name__ == "__main__":
    unittest.main(verbosity=2)
