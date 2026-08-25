from __future__ import annotations

import json
from pathlib import Path
import sys
import tempfile
from types import ModuleType
import unittest

from metao.adapters.langgraph import normalize_evidence
from metao.core import (
    ExecutionRequest,
    ExecutionResult,
    ExecutionStatus,
    HealthReport,
    HealthStatus,
    OrchestratorDescriptor,
)
from metao.mission_store import InMemoryMissionStore
from metao.runtime_certification import (
    InMemoryRuntimeCertificationStore,
    RuntimeCertification,
    certificate_identity,
    latest_certificate,
)
from metao.runtime_certification_revocation import (
    InMemoryRuntimeCertificationRevocationStore,
    revoke_certificate,
)
from metao.runtime_factory import RuntimeCatalogConfigError, RuntimePlugin, create_operator_from_catalog


class ProbeRuntime:
    def __init__(self, *, wrong_execution_id: bool = False) -> None:
        self._descriptor = OrchestratorDescriptor("runtime-a", "v1", frozenset({"workflow"}))
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


def manifest_entry(factory: str, *, reuse: bool, max_age: float | None = 60.0) -> dict:
    certification = {
        "mode": "required",
        "reuse_passed": reuse,
        "probe": {
            "execution_id": "probe-v1",
            "objective": "certify latest verdict authority",
            "required_capabilities": ["workflow"],
        },
    }
    if max_age is not None:
        certification["max_age_seconds"] = max_age
    return {
        "factory": factory,
        "cost": 0.1,
        "latency_ms": 10.0,
        "success_rate": 0.8,
        "quality": 0.8,
        "reliability": 0.8,
        "certification": certification,
    }


def cert(epoch: float, *, passed: bool, version: str = "v1", probe: str = "probe-v1") -> RuntimeCertification:
    return RuntimeCertification(
        certificate_id=certificate_identity(
            "runtime-a", version, probe, certified_at_epoch=epoch
        ),
        orchestrator_id="runtime-a",
        runtime_version=version,
        probe_execution_id=probe,
        passed=passed,
        failed_checks=() if passed else ("execution_id_binding",),
        checks_digest=("a" if passed else "b") * 64,
        total_checks=8,
        certified_at_epoch=epoch,
    )


class LatestCertificationVerdictAuthorityV1Tests(unittest.TestCase):
    def setUp(self) -> None:
        self.module_name = "metao_r5_wu05_plugins"
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

    def test_latest_certificate_returns_newest_exact_generation_even_when_it_failed(self):
        store = InMemoryRuntimeCertificationStore()
        store.record(cert(100.0, passed=True))
        store.record(cert(120.0, passed=False))
        store.record(cert(200.0, passed=True, version="v2"))
        store.record(cert(210.0, passed=True, probe="probe-v2"))
        current = latest_certificate(
            store,
            orchestrator_id="runtime-a",
            runtime_version="v1",
            probe_execution_id="probe-v1",
        )
        self.assertIsNotNone(current)
        self.assertEqual(current.certified_at_epoch, 120.0)
        self.assertFalse(current.passed)

    def test_newer_failed_probe_blocks_fallback_to_older_still_fresh_pass(self):
        certifications = InMemoryRuntimeCertificationStore()
        first_runtime = ProbeRuntime()
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            first_path = self.write_manifest(
                root / "first.json",
                manifest_entry(self.bind(first_runtime), reuse=True),
            )
            create_operator_from_catalog(
                first_path,
                store=InMemoryMissionStore(),
                certifications=certifications,
                certification_now_epoch=100.0,
            )

            failing_runtime = ProbeRuntime(wrong_execution_id=True)
            fail_path = self.write_manifest(
                root / "fail.json",
                manifest_entry(self.bind(failing_runtime), reuse=False),
            )
            with self.assertRaises(RuntimeCatalogConfigError):
                create_operator_from_catalog(
                    fail_path,
                    store=InMemoryMissionStore(),
                    certifications=certifications,
                    certification_now_epoch=120.0,
                )
            self.assertEqual(failing_runtime.calls, 1)

            recovering_runtime = ProbeRuntime()
            recover_path = self.write_manifest(
                root / "recover.json",
                manifest_entry(self.bind(recovering_runtime), reuse=True),
            )
            create_operator_from_catalog(
                recover_path,
                store=InMemoryMissionStore(),
                certifications=certifications,
                certification_now_epoch=130.0,
            )
        self.assertEqual(recovering_runtime.calls, 1)
        history = certifications.history("runtime-a")
        self.assertEqual([item.certified_at_epoch for item in history], [100.0, 120.0, 130.0])
        self.assertEqual([item.passed for item in history], [True, False, True])

    def test_revoked_latest_pass_blocks_fallback_to_older_unrevoked_fresh_pass(self):
        certifications = InMemoryRuntimeCertificationStore()
        revocations = InMemoryRuntimeCertificationRevocationStore()
        certifications.record(cert(100.0, passed=True))
        certifications.record(cert(120.0, passed=True))
        revoke_certificate(
            certifications,
            revocations,
            cert(120.0, passed=True).certificate_id,
            reason="latest generation revoked",
            actor_id="operator-a",
            revoked_at_epoch=125.0,
        )
        runtime = ProbeRuntime()
        with tempfile.TemporaryDirectory() as temp:
            path = self.write_manifest(
                Path(temp) / "runtimes.json",
                manifest_entry(self.bind(runtime), reuse=True),
            )
            create_operator_from_catalog(
                path,
                store=InMemoryMissionStore(),
                certifications=certifications,
                certification_revocations=revocations,
                certification_now_epoch=130.0,
            )
        self.assertEqual(runtime.calls, 1)
        history = certifications.history("runtime-a")
        self.assertEqual([item.certified_at_epoch for item in history], [100.0, 120.0, 130.0])

    def test_newest_recovery_pass_is_reused_after_a_failed_verdict(self):
        certifications = InMemoryRuntimeCertificationStore()
        certifications.record(cert(100.0, passed=True))
        certifications.record(cert(120.0, passed=False))
        certifications.record(cert(130.0, passed=True))
        runtime = ProbeRuntime()
        with tempfile.TemporaryDirectory() as temp:
            path = self.write_manifest(
                Path(temp) / "runtimes.json",
                manifest_entry(self.bind(runtime), reuse=True),
            )
            operator = create_operator_from_catalog(
                path,
                store=InMemoryMissionStore(),
                certifications=certifications,
                certification_now_epoch=140.0,
            )
        self.assertEqual(runtime.calls, 0)
        self.assertEqual(operator.runtime_entries()[0].orchestrator_id, "runtime-a")
        self.assertEqual(len(certifications.history("runtime-a")), 3)

    def test_timestamped_history_stays_generational_after_ttl_is_removed(self):
        certifications = InMemoryRuntimeCertificationStore()
        certifications.record(cert(100.0, passed=False))
        runtime = ProbeRuntime()
        with tempfile.TemporaryDirectory() as temp:
            path = self.write_manifest(
                Path(temp) / "runtimes.json",
                manifest_entry(self.bind(runtime), reuse=False, max_age=None),
            )
            create_operator_from_catalog(
                path,
                store=InMemoryMissionStore(),
                certifications=certifications,
                certification_now_epoch=130.0,
            )
        self.assertEqual(runtime.calls, 1)
        history = certifications.history("runtime-a")
        self.assertEqual([item.certified_at_epoch for item in history], [100.0, 130.0])
        self.assertTrue(history[-1].passed)

    def test_latest_verdict_implementation_remains_sdk_neutral(self):
        root = Path(__file__).resolve().parents[2]
        for relative in (
            "src/metao/runtime_certification.py",
            "src/metao/runtime_factory.py",
        ):
            source = (root / relative).read_text(encoding="utf-8").lower()
            self.assertNotIn("import crewai", source)
            self.assertNotIn("from crewai", source)
            self.assertNotIn("import langgraph", source)
            self.assertNotIn("from langgraph", source)


if __name__ == "__main__":
    unittest.main()
