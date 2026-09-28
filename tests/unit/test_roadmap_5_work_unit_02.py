from __future__ import annotations

from dataclasses import replace
import json
from pathlib import Path
import sys
import tempfile
from types import ModuleType
import unittest

from metao.adapters.langgraph import normalize_evidence
from metao.catalog import OrchestratorCatalog
from metao.core import (
    ExecutionRequest,
    ExecutionResult,
    ExecutionStatus,
    HealthReport,
    HealthStatus,
    OrchestratorDescriptor,
    OrchestratorRegistry,
)
from metao.mission_store import InMemoryMissionStore
from metao.runtime_admission import RuntimeAdmissionGate, RuntimeCertificateAdmissionError
from metao.runtime_certification import (
    InMemoryRuntimeCertificationStore,
    RuntimeCertification,
    certificate_identity,
)
from metao.runtime_certification_revocation import (
    InMemoryRuntimeCertificationRevocationStore,
    RuntimeCertificationRevocation,
    RuntimeCertificationRevocationConflict,
    UnknownRuntimeCertification,
    is_certificate_revoked,
    revoke_certificate,
)
from metao.runtime_factory import RuntimePlugin, create_operator_from_catalog
from metao.sqlite_runtime_certification import SQLiteRuntimeCertificationStore
from metao.sqlite_runtime_certification_revocation import (
    SQLiteRuntimeCertificationRevocationStore,
)


class ProbeRuntime:
    def __init__(self, *, version: str = "v1") -> None:
        self._descriptor = OrchestratorDescriptor("runtime-a", version, frozenset({"workflow"}))
        self.calls = 0

    @property
    def descriptor(self):
        return self._descriptor

    def health(self):
        return HealthReport(HealthStatus.HEALTHY)

    def execute(self, request: ExecutionRequest):
        self.calls += 1
        return ExecutionResult(
            request.execution_id,
            self.descriptor.orchestrator_id,
            ExecutionStatus.SUCCEEDED,
            {"result": "ok"},
        )

    def cancel(self, execution_id: str) -> None:
        pass


def manifest_entry(factory: str) -> dict:
    return {
        "factory": factory,
        "cost": 0.1,
        "latency_ms": 10.0,
        "success_rate": 0.8,
        "quality": 0.8,
        "reliability": 0.8,
        "certification": {
            "mode": "required",
            "reuse_passed": True,
            "probe": {
                "execution_id": "probe-v1",
                "objective": "certify revocation runtime",
                "required_capabilities": ["workflow"],
            },
        },
    }


def passing_certificate(epoch: float = 100.0) -> RuntimeCertification:
    return RuntimeCertification(
        certificate_id=certificate_identity(
            "runtime-a", "v1", "probe-v1", certified_at_epoch=epoch
        ),
        orchestrator_id="runtime-a",
        runtime_version="v1",
        probe_execution_id="probe-v1",
        passed=True,
        failed_checks=(),
        checks_digest="a" * 64,
        total_checks=8,
        certified_at_epoch=epoch,
    )


class DurableCertificateRevocationV1Tests(unittest.TestCase):
    def setUp(self) -> None:
        self.module_name = "metao_r5_wu02_plugins"
        self.module = ModuleType(self.module_name)
        sys.modules[self.module_name] = self.module

    def tearDown(self) -> None:
        sys.modules.pop(self.module_name, None)

    def bind(self, runtime: ProbeRuntime) -> str:
        setattr(
            self.module,
            "make_runtime",
            lambda runtime=runtime: RuntimePlugin(runtime, normalize_evidence),
        )
        return f"{self.module_name}:make_runtime"

    @staticmethod
    def write_manifest(path: Path, item: dict) -> Path:
        path.write_text(json.dumps({"runtimes": [item]}), encoding="utf-8")
        return path

    def test_revocation_requires_an_existing_certificate(self):
        with self.assertRaises(UnknownRuntimeCertification):
            revoke_certificate(
                InMemoryRuntimeCertificationStore(),
                InMemoryRuntimeCertificationRevocationStore(),
                "missing",
                reason="operator distrust",
                actor_id="operator-a",
                revoked_at_epoch=100.0,
            )

    def test_in_memory_revocation_is_immutable_idempotent_and_conflicting_rewrite_fails(self):
        certifications = InMemoryRuntimeCertificationStore()
        revocations = InMemoryRuntimeCertificationRevocationStore()
        certificate = passing_certificate()
        certifications.record(certificate)
        first = revoke_certificate(
            certifications,
            revocations,
            certificate.certificate_id,
            reason="adapter regression",
            actor_id="operator-a",
            revoked_at_epoch=120.0,
        )
        self.assertEqual(revocations.record(first), first)
        self.assertTrue(is_certificate_revoked(revocations, certificate.certificate_id))
        with self.assertRaises(RuntimeCertificationRevocationConflict):
            revocations.record(replace(first, reason="rewrite attempt"))

    def test_sqlite_revocation_survives_restart(self):
        with tempfile.TemporaryDirectory() as temp:
            db = Path(temp) / "metao.db"
            certifications = SQLiteRuntimeCertificationStore(db)
            revocations = SQLiteRuntimeCertificationRevocationStore(db)
            certificate = passing_certificate()
            certifications.record(certificate)
            record = revoke_certificate(
                certifications,
                revocations,
                certificate.certificate_id,
                reason="manual revoke",
                actor_id="operator-a",
                revoked_at_epoch=130.0,
            )
            restarted = SQLiteRuntimeCertificationRevocationStore(db)
            self.assertEqual(restarted.get(certificate.certificate_id), record)
            self.assertEqual(restarted.history("runtime-a"), (record,))

    def test_admission_rejects_revoked_persisted_pass_before_registry_mutation(self):
        certifications = InMemoryRuntimeCertificationStore()
        revocations = InMemoryRuntimeCertificationRevocationStore()
        certificate = passing_certificate()
        certifications.record(certificate)
        revoke_certificate(
            certifications,
            revocations,
            certificate.certificate_id,
            reason="known bad generation",
            actor_id="operator-a",
            revoked_at_epoch=120.0,
        )
        registry = OrchestratorRegistry()
        catalog = OrchestratorCatalog(registry)
        gate = RuntimeAdmissionGate(registry, catalog, certifications, revocations)
        with self.assertRaisesRegex(RuntimeCertificateAdmissionError, "revoked"):
            gate.admit_certified(
                ProbeRuntime(),
                normalize_evidence,
                certificate,
                expected_probe_execution_id="probe-v1",
            )
        with self.assertRaises(KeyError):
            registry.get("runtime-a")
        self.assertEqual(catalog.entries(), ())

    def test_revoked_generation_forces_active_probe_and_new_generation(self):
        certifications = InMemoryRuntimeCertificationStore()
        revocations = InMemoryRuntimeCertificationRevocationStore()
        first_runtime = ProbeRuntime()
        with tempfile.TemporaryDirectory() as temp:
            path = self.write_manifest(
                Path(temp) / "runtimes.json",
                manifest_entry(self.bind(first_runtime)),
            )
            create_operator_from_catalog(
                path,
                store=InMemoryMissionStore(),
                certifications=certifications,
                certification_revocations=revocations,
                certification_now_epoch=100.0,
            )
            first = certifications.history("runtime-a")
            self.assertEqual(len(first), 1)
            revoke_certificate(
                certifications,
                revocations,
                first[0].certificate_id,
                reason="operator revoked first generation",
                actor_id="operator-a",
                revoked_at_epoch=110.0,
            )

            second_runtime = ProbeRuntime()
            self.bind(second_runtime)
            create_operator_from_catalog(
                path,
                store=InMemoryMissionStore(),
                certifications=certifications,
                certification_revocations=revocations,
                certification_now_epoch=120.0,
            )
        self.assertEqual(first_runtime.calls, 1)
        self.assertEqual(second_runtime.calls, 1)
        history = certifications.history("runtime-a")
        self.assertEqual([item.certified_at_epoch for item in history], [100.0, 120.0])
        self.assertTrue(is_certificate_revoked(revocations, history[0].certificate_id))
        self.assertFalse(is_certificate_revoked(revocations, history[1].certificate_id))

    def test_new_unrevoked_generation_is_reused_without_another_probe(self):
        certifications = InMemoryRuntimeCertificationStore()
        revocations = InMemoryRuntimeCertificationRevocationStore()
        first_runtime = ProbeRuntime()
        with tempfile.TemporaryDirectory() as temp:
            path = self.write_manifest(
                Path(temp) / "runtimes.json",
                manifest_entry(self.bind(first_runtime)),
            )
            create_operator_from_catalog(
                path,
                store=InMemoryMissionStore(),
                certifications=certifications,
                certification_revocations=revocations,
                certification_now_epoch=100.0,
            )
            old = certifications.history("runtime-a")[0]
            revoke_certificate(
                certifications,
                revocations,
                old.certificate_id,
                reason="rotate certificate",
                actor_id="operator-a",
                revoked_at_epoch=110.0,
            )
            second_runtime = ProbeRuntime()
            self.bind(second_runtime)
            create_operator_from_catalog(
                path,
                store=InMemoryMissionStore(),
                certifications=certifications,
                certification_revocations=revocations,
                certification_now_epoch=120.0,
            )
            third_runtime = ProbeRuntime()
            self.bind(third_runtime)
            operator = create_operator_from_catalog(
                path,
                store=InMemoryMissionStore(),
                certifications=certifications,
                certification_revocations=revocations,
                certification_now_epoch=130.0,
            )
        self.assertEqual((first_runtime.calls, second_runtime.calls, third_runtime.calls), (1, 1, 0))
        self.assertEqual(len(certifications.history("runtime-a")), 2)
        self.assertEqual(operator.runtime_entries()[0].orchestrator_id, "runtime-a")

    def test_active_probe_cannot_re_admit_same_revoked_generation_identity(self):
        certifications = InMemoryRuntimeCertificationStore()
        revocations = InMemoryRuntimeCertificationRevocationStore()
        certificate = passing_certificate(epoch=100.0)
        certifications.record(certificate)
        revoke_certificate(
            certifications,
            revocations,
            certificate.certificate_id,
            reason="generation revoked",
            actor_id="operator-a",
            revoked_at_epoch=110.0,
        )
        registry = OrchestratorRegistry()
        catalog = OrchestratorCatalog(registry)
        gate = RuntimeAdmissionGate(registry, catalog, certifications, revocations)
        request = ExecutionRequest(
            "probe-v1",
            __import__("metao.core", fromlist=["Mission"]).Mission(
                "certify-runtime-a", "probe", frozenset({"workflow"})
            ),
            {},
        )
        with self.assertRaisesRegex(RuntimeCertificateAdmissionError, "revoked"):
            gate.admit(
                ProbeRuntime(),
                normalize_evidence,
                request,
                certified_at_epoch=100.0,
            )
        self.assertEqual(catalog.entries(), ())

    def test_revocation_does_not_mutate_a_previously_admitted_catalog(self):
        certifications = InMemoryRuntimeCertificationStore()
        revocations = InMemoryRuntimeCertificationRevocationStore()
        runtime = ProbeRuntime()
        with tempfile.TemporaryDirectory() as temp:
            path = self.write_manifest(
                Path(temp) / "runtimes.json",
                manifest_entry(self.bind(runtime)),
            )
            operator = create_operator_from_catalog(
                path,
                store=InMemoryMissionStore(),
                certifications=certifications,
                certification_revocations=revocations,
                certification_now_epoch=100.0,
            )
            certificate = certifications.history("runtime-a")[0]
            revoke_certificate(
                certifications,
                revocations,
                certificate.certificate_id,
                reason="future onboarding revoke",
                actor_id="operator-a",
                revoked_at_epoch=110.0,
            )
        self.assertEqual(len(operator.runtime_entries()), 1)
        self.assertEqual(operator.runtime_entries()[0].orchestrator_id, "runtime-a")

    def test_revocation_modules_are_sdk_neutral(self):
        root = Path(__file__).resolve().parents[2]
        for relative in (
            "src/metao/runtime_certification_revocation.py",
            "src/metao/sqlite_runtime_certification_revocation.py",
            "src/metao/runtime_admission.py",
            "src/metao/runtime_factory.py",
        ):
            source = (root / relative).read_text(encoding="utf-8").lower()
            self.assertNotIn("import crewai", source)
            self.assertNotIn("from crewai", source)
            self.assertNotIn("import langgraph", source)
            self.assertNotIn("from langgraph", source)


if __name__ == "__main__":
    unittest.main()
