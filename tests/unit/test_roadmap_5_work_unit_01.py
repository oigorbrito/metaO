from __future__ import annotations

from contextlib import closing
import json
from pathlib import Path
import sqlite3
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
    is_certificate_fresh,
    latest_passing_certificate,
)
from metao.runtime_factory import (
    RuntimeCatalogConfigError,
    RuntimePlugin,
    create_operator_from_catalog,
)
from metao.sqlite_runtime_certification import SQLiteRuntimeCertificationStore


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


def entry(factory: str, *, max_age_seconds: float = 60.0, reuse: bool = True) -> dict:
    return {
        "factory": factory,
        "cost": 0.1,
        "latency_ms": 10.0,
        "success_rate": 0.8,
        "quality": 0.8,
        "reliability": 0.8,
        "certification": {
            "mode": "required",
            "reuse_passed": reuse,
            "max_age_seconds": max_age_seconds,
            "probe": {
                "execution_id": "probe-v1",
                "objective": "certify freshness runtime",
                "required_capabilities": ["workflow"],
            },
        },
    }


class CertificateFreshnessV1Tests(unittest.TestCase):
    def setUp(self) -> None:
        self.module_name = "metao_r5_wu01_plugins"
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

    def test_legacy_identity_is_preserved_but_legacy_certificate_is_stale_under_freshness(self):
        certificate = RuntimeCertification(
            certificate_id="runtime-a:v1:probe-v1",
            orchestrator_id="runtime-a",
            runtime_version="v1",
            probe_execution_id="probe-v1",
            passed=True,
            failed_checks=(),
            checks_digest="a" * 64,
            total_checks=8,
        )
        self.assertEqual(
            certificate_identity("runtime-a", "v1", "probe-v1"),
            "runtime-a:v1:probe-v1",
        )
        self.assertEqual(certificate.certified_at_epoch, 0.0)
        self.assertFalse(is_certificate_fresh(certificate, now_epoch=100.0, max_age_seconds=60.0))

    def test_timestamped_generation_has_append_only_identity_and_boundary_is_inclusive(self):
        certificate = RuntimeCertification(
            certificate_id=certificate_identity(
                "runtime-a", "v1", "probe-v1", certified_at_epoch=100.0
            ),
            orchestrator_id="runtime-a",
            runtime_version="v1",
            probe_execution_id="probe-v1",
            passed=True,
            failed_checks=(),
            checks_digest="a" * 64,
            total_checks=8,
            certified_at_epoch=100.0,
        )
        self.assertEqual(certificate.certificate_id, "runtime-a:v1:probe-v1:100.000000")
        self.assertTrue(is_certificate_fresh(certificate, now_epoch=160.0, max_age_seconds=60.0))
        self.assertFalse(is_certificate_fresh(certificate, now_epoch=160.001, max_age_seconds=60.0))
        self.assertFalse(is_certificate_fresh(certificate, now_epoch=99.0, max_age_seconds=60.0))

    def test_first_load_certifies_and_restart_within_window_reuses_without_probe(self):
        certifications = InMemoryRuntimeCertificationStore()
        first_runtime = ProbeRuntime()
        with tempfile.TemporaryDirectory() as temp:
            path = self.write_manifest(Path(temp) / "runtimes.json", entry(self.bind(first_runtime)))
            create_operator_from_catalog(
                path,
                store=InMemoryMissionStore(),
                certifications=certifications,
                certification_now_epoch=100.0,
            )
            self.assertEqual(first_runtime.calls, 1)
            first = certifications.history("runtime-a")
            self.assertEqual(len(first), 1)
            self.assertEqual(first[0].certified_at_epoch, 100.0)

            second_runtime = ProbeRuntime()
            self.bind(second_runtime)
            operator = create_operator_from_catalog(
                path,
                store=InMemoryMissionStore(),
                certifications=certifications,
                certification_now_epoch=150.0,
            )
        self.assertEqual(second_runtime.calls, 0)
        self.assertEqual(len(operator.runtime_entries()), 1)
        self.assertEqual(len(certifications.history("runtime-a")), 1)

    def test_expired_pass_forces_probe_and_creates_new_generation(self):
        certifications = InMemoryRuntimeCertificationStore()
        first_runtime = ProbeRuntime()
        with tempfile.TemporaryDirectory() as temp:
            path = self.write_manifest(Path(temp) / "runtimes.json", entry(self.bind(first_runtime)))
            create_operator_from_catalog(
                path,
                store=InMemoryMissionStore(),
                certifications=certifications,
                certification_now_epoch=100.0,
            )
            second_runtime = ProbeRuntime()
            self.bind(second_runtime)
            create_operator_from_catalog(
                path,
                store=InMemoryMissionStore(),
                certifications=certifications,
                certification_now_epoch=161.0,
            )
        self.assertEqual(second_runtime.calls, 1)
        history = certifications.history("runtime-a")
        self.assertEqual(len(history), 2)
        self.assertEqual([item.certified_at_epoch for item in history], [100.0, 161.0])
        self.assertNotEqual(history[0].certificate_id, history[1].certificate_id)

    def test_latest_lookup_uses_newest_fresh_exact_generation_only(self):
        store = InMemoryRuntimeCertificationStore()
        for epoch in (100.0, 170.0):
            store.record(
                RuntimeCertification(
                    certificate_id=certificate_identity(
                        "runtime-a", "v1", "probe-v1", certified_at_epoch=epoch
                    ),
                    orchestrator_id="runtime-a",
                    runtime_version="v1",
                    probe_execution_id="probe-v1",
                    passed=True,
                    failed_checks=(),
                    checks_digest=str(int(epoch)) * 16,
                    total_checks=8,
                    certified_at_epoch=epoch,
                )
            )
        selected = latest_passing_certificate(
            store,
            orchestrator_id="runtime-a",
            runtime_version="v1",
            probe_execution_id="probe-v1",
            now_epoch=200.0,
            max_age_seconds=60.0,
        )
        self.assertIsNotNone(selected)
        self.assertEqual(selected.certified_at_epoch, 170.0)

    def test_admission_rejects_stale_certificate_even_if_passed_and_persisted(self):
        certificate = RuntimeCertification(
            certificate_id=certificate_identity(
                "runtime-a", "v1", "probe-v1", certified_at_epoch=100.0
            ),
            orchestrator_id="runtime-a",
            runtime_version="v1",
            probe_execution_id="probe-v1",
            passed=True,
            failed_checks=(),
            checks_digest="a" * 64,
            total_checks=8,
            certified_at_epoch=100.0,
        )
        store = InMemoryRuntimeCertificationStore()
        store.record(certificate)
        registry = OrchestratorRegistry()
        catalog = OrchestratorCatalog(registry)
        gate = RuntimeAdmissionGate(registry, catalog, store)
        with self.assertRaisesRegex(RuntimeCertificateAdmissionError, "stale"):
            gate.admit_certified(
                ProbeRuntime(),
                normalize_evidence,
                certificate,
                expected_probe_execution_id="probe-v1",
                now_epoch=161.0,
                max_age_seconds=60.0,
            )
        with self.assertRaises(KeyError):
            registry.get("runtime-a")
        self.assertEqual(catalog.entries(), ())

    def test_sqlite_migrates_legacy_schema_without_rewriting_old_certificate(self):
        with tempfile.TemporaryDirectory() as temp:
            path = Path(temp) / "legacy.db"
            with closing(sqlite3.connect(path)) as connection, connection:
                connection.execute(
                    """
                    CREATE TABLE runtime_certifications (
                        certificate_id TEXT PRIMARY KEY,
                        orchestrator_id TEXT NOT NULL,
                        runtime_version TEXT NOT NULL,
                        probe_execution_id TEXT NOT NULL,
                        passed INTEGER NOT NULL,
                        failed_checks_json TEXT NOT NULL,
                        checks_digest TEXT NOT NULL,
                        total_checks INTEGER NOT NULL
                    )
                    """
                )
                connection.execute(
                    "INSERT INTO runtime_certifications VALUES(?,?,?,?,?,?,?,?)",
                    (
                        "runtime-a:v1:probe-v1",
                        "runtime-a",
                        "v1",
                        "probe-v1",
                        1,
                        "[]",
                        "a" * 64,
                        8,
                    ),
                )
            store = SQLiteRuntimeCertificationStore(path)
            migrated = store.get("runtime-a:v1:probe-v1")
            self.assertIsNotNone(migrated)
            self.assertEqual(migrated.certified_at_epoch, 0.0)
            self.assertFalse(is_certificate_fresh(migrated, now_epoch=100.0, max_age_seconds=60.0))

    def test_sqlite_restart_preserves_multiple_recertification_generations(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            db = root / "metao.db"
            first_runtime = ProbeRuntime()
            manifest = self.write_manifest(root / "runtimes.json", entry(self.bind(first_runtime)))
            create_operator_from_catalog(
                manifest,
                store=InMemoryMissionStore(),
                certifications=SQLiteRuntimeCertificationStore(db),
                certification_now_epoch=100.0,
            )
            second_runtime = ProbeRuntime()
            self.bind(second_runtime)
            create_operator_from_catalog(
                manifest,
                store=InMemoryMissionStore(),
                certifications=SQLiteRuntimeCertificationStore(db),
                certification_now_epoch=161.0,
            )
            restarted = SQLiteRuntimeCertificationStore(db)
            history = restarted.history("runtime-a")
        self.assertEqual(second_runtime.calls, 1)
        self.assertEqual([item.certified_at_epoch for item in history], [100.0, 161.0])

    def test_invalid_freshness_window_fails_closed_before_probe(self):
        runtime = ProbeRuntime()
        with tempfile.TemporaryDirectory() as temp:
            path = self.write_manifest(
                Path(temp) / "runtimes.json",
                entry(self.bind(runtime), max_age_seconds=0.0),
            )
            with self.assertRaisesRegex(RuntimeCatalogConfigError, "max_age_seconds"):
                create_operator_from_catalog(
                    path,
                    store=InMemoryMissionStore(),
                    certifications=InMemoryRuntimeCertificationStore(),
                    certification_now_epoch=100.0,
                )
        self.assertEqual(runtime.calls, 0)

    def test_freshness_implementation_remains_sdk_neutral_and_learned_routing_free(self):
        root = Path(__file__).resolve().parents[2]
        for relative in (
            "src/metao/runtime_certification.py",
            "src/metao/sqlite_runtime_certification.py",
            "src/metao/runtime_admission.py",
            "src/metao/runtime_factory.py",
        ):
            source = (root / relative).read_text(encoding="utf-8").lower()
            self.assertNotIn("import crewai", source)
            self.assertNotIn("from crewai", source)
            self.assertNotIn("import langgraph", source)
            self.assertNotIn("from langgraph", source)
            self.assertNotIn("sklearn", source)
            self.assertNotIn("torch", source)


if __name__ == "__main__":
    unittest.main()
