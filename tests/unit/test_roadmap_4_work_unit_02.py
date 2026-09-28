from __future__ import annotations

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
)
from metao.runtime_factory import (
    RuntimeCatalogConfigError,
    RuntimePlugin,
    create_operator_from_catalog,
)
from metao.sqlite_runtime_certification import SQLiteRuntimeCertificationStore


class ProbeRuntime:
    def __init__(self, *, version: str = "v1", wrong_execution_id: bool = False):
        self._descriptor = OrchestratorDescriptor(
            "runtime-a",
            version,
            frozenset({"workflow"}),
        )
        self.wrong_execution_id = wrong_execution_id
        self.calls = 0

    @property
    def descriptor(self):
        return self._descriptor

    def health(self):
        return HealthReport(HealthStatus.HEALTHY)

    def execute(self, request: ExecutionRequest):
        self.calls += 1
        return ExecutionResult(
            "wrong" if self.wrong_execution_id else request.execution_id,
            self.descriptor.orchestrator_id,
            ExecutionStatus.SUCCEEDED,
            {"result": "ok"},
        )

    def cancel(self, execution_id: str) -> None:
        pass


def entry(factory: str, *, execution_id: str = "probe-v1", reuse=True) -> dict:
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
            "probe": {
                "execution_id": execution_id,
                "objective": "certify reusable runtime",
                "required_capabilities": ["workflow"],
            },
        },
    }


class PassedCertificateReuseV1Tests(unittest.TestCase):
    def setUp(self) -> None:
        self.module_name = "metao_r4_wu02_plugins"
        self.module = ModuleType(self.module_name)
        sys.modules[self.module_name] = self.module

    def tearDown(self) -> None:
        sys.modules.pop(self.module_name, None)

    def bind(self, runtime: ProbeRuntime) -> str:
        setattr(self.module, "make_runtime", lambda runtime=runtime: RuntimePlugin(runtime, normalize_evidence))
        return f"{self.module_name}:make_runtime"

    @staticmethod
    def write_manifest(path: Path, item: dict) -> Path:
        path.write_text(json.dumps({"runtimes": [item]}), encoding="utf-8")
        return path

    def test_first_load_probes_and_second_load_reuses_persisted_pass_without_execute(self):
        store = InMemoryRuntimeCertificationStore()
        first_runtime = ProbeRuntime()
        with tempfile.TemporaryDirectory() as temp:
            path = self.write_manifest(Path(temp) / "runtimes.json", entry(self.bind(first_runtime)))
            first = create_operator_from_catalog(
                path,
                store=InMemoryMissionStore(),
                certifications=store,
            )
            self.assertEqual(first_runtime.calls, 1)
            self.assertEqual(len(first.runtime_entries()), 1)

            second_runtime = ProbeRuntime()
            self.bind(second_runtime)
            second = create_operator_from_catalog(
                path,
                store=InMemoryMissionStore(),
                certifications=store,
            )
        self.assertEqual(second_runtime.calls, 0)
        self.assertEqual(second.runtime_entries()[0].orchestrator_id, "runtime-a")
        self.assertEqual(len(store.history("runtime-a")), 1)

    def test_sqlite_restart_reuses_persisted_pass_without_runtime_execution(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            db = root / "metao.db"
            first_runtime = ProbeRuntime()
            path = self.write_manifest(root / "runtimes.json", entry(self.bind(first_runtime)))
            create_operator_from_catalog(
                path,
                store=InMemoryMissionStore(),
                certifications=SQLiteRuntimeCertificationStore(db),
            )
            self.assertEqual(first_runtime.calls, 1)

            second_runtime = ProbeRuntime()
            self.bind(second_runtime)
            operator = create_operator_from_catalog(
                path,
                store=InMemoryMissionStore(),
                certifications=SQLiteRuntimeCertificationStore(db),
            )
            self.assertEqual(second_runtime.calls, 0)
            self.assertEqual(len(operator.runtime_entries()), 1)
            self.assertEqual(len(SQLiteRuntimeCertificationStore(db).history("runtime-a")), 1)

    def test_runtime_version_change_invalidates_reuse_and_runs_new_probe(self):
        store = InMemoryRuntimeCertificationStore()
        first_runtime = ProbeRuntime(version="v1")
        with tempfile.TemporaryDirectory() as temp:
            path = self.write_manifest(Path(temp) / "runtimes.json", entry(self.bind(first_runtime)))
            create_operator_from_catalog(path, store=InMemoryMissionStore(), certifications=store)
            second_runtime = ProbeRuntime(version="v2")
            self.bind(second_runtime)
            create_operator_from_catalog(path, store=InMemoryMissionStore(), certifications=store)
        self.assertEqual(second_runtime.calls, 1)
        self.assertEqual(len(store.history("runtime-a")), 2)

    def test_probe_execution_id_change_invalidates_reuse(self):
        store = InMemoryRuntimeCertificationStore()
        first_runtime = ProbeRuntime()
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            first_path = self.write_manifest(root / "first.json", entry(self.bind(first_runtime), execution_id="probe-v1"))
            create_operator_from_catalog(first_path, store=InMemoryMissionStore(), certifications=store)
            second_runtime = ProbeRuntime()
            second_path = self.write_manifest(root / "second.json", entry(self.bind(second_runtime), execution_id="probe-v2"))
            create_operator_from_catalog(second_path, store=InMemoryMissionStore(), certifications=store)
        self.assertEqual(second_runtime.calls, 1)
        self.assertEqual(len(store.history("runtime-a")), 2)

    def test_failed_certificate_is_never_reused(self):
        store = InMemoryRuntimeCertificationStore()
        first_runtime = ProbeRuntime(wrong_execution_id=True)
        with tempfile.TemporaryDirectory() as temp:
            path = self.write_manifest(Path(temp) / "runtimes.json", entry(self.bind(first_runtime)))
            with self.assertRaises(RuntimeCatalogConfigError):
                create_operator_from_catalog(path, store=InMemoryMissionStore(), certifications=store)
            self.assertFalse(store.history("runtime-a")[0].passed)

            second_runtime = ProbeRuntime(wrong_execution_id=True)
            self.bind(second_runtime)
            with self.assertRaises(RuntimeCatalogConfigError):
                create_operator_from_catalog(path, store=InMemoryMissionStore(), certifications=store)
        self.assertEqual(second_runtime.calls, 1)

    def test_reuse_flag_must_be_boolean_and_fails_before_execute(self):
        runtime = ProbeRuntime()
        item = entry(self.bind(runtime), reuse="yes")
        with tempfile.TemporaryDirectory() as temp:
            path = self.write_manifest(Path(temp) / "runtimes.json", item)
            with self.assertRaisesRegex(RuntimeCatalogConfigError, "reuse_passed"):
                create_operator_from_catalog(
                    path,
                    store=InMemoryMissionStore(),
                    certifications=InMemoryRuntimeCertificationStore(),
                )
        self.assertEqual(runtime.calls, 0)

    def test_gate_rejects_unpersisted_or_misbound_certificate_without_execute(self):
        registry = OrchestratorRegistry()
        catalog = OrchestratorCatalog(registry)
        store = InMemoryRuntimeCertificationStore()
        gate = RuntimeAdmissionGate(registry, catalog, store)
        runtime = ProbeRuntime()
        certificate = RuntimeCertification(
            "runtime-a:v1:probe-v1",
            "runtime-a",
            "v1",
            "probe-v1",
            True,
            (),
            "0" * 64,
            1,
        )
        with self.assertRaisesRegex(RuntimeCertificateAdmissionError, "not durably persisted"):
            gate.admit_certified(
                runtime,
                normalize_evidence,
                certificate,
                expected_probe_execution_id="probe-v1",
            )
        self.assertEqual(runtime.calls, 0)
        store.record(certificate)
        runtime_v2 = ProbeRuntime(version="v2")
        with self.assertRaisesRegex(RuntimeCertificateAdmissionError, "version mismatch"):
            gate.admit_certified(
                runtime_v2,
                normalize_evidence,
                certificate,
                expected_probe_execution_id="probe-v1",
            )
        self.assertEqual(runtime_v2.calls, 0)

    def test_reuse_implementation_remains_sdk_neutral(self):
        root = Path(__file__).resolve().parents[2]
        for relative in ("src/metao/runtime_factory.py", "src/metao/runtime_admission.py"):
            source = (root / relative).read_text(encoding="utf-8").lower()
            for forbidden in ("import langgraph", "from langgraph", "import crewai", "from crewai"):
                self.assertNotIn(forbidden, source)


if __name__ == "__main__":
    unittest.main(verbosity=2)
