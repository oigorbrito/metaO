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
from metao.runtime_certification import InMemoryRuntimeCertificationStore
from metao.runtime_control import InMemoryRuntimeControlStore, quarantine
from metao.runtime_factory import (
    RuntimeCatalogConfigError,
    RuntimePlugin,
    create_operator_from_catalog,
)
from metao.runtime_feedback import InMemoryRuntimeFeedbackStore, RuntimeObservation
from metao.strategy import OrchestratorStatus


class ProbeRuntime:
    def __init__(self, orchestrator_id: str = "runtime-a", *, wrong_execution_id: bool = False):
        self._descriptor = OrchestratorDescriptor(
            orchestrator_id,
            "v1",
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
            "wrong-execution" if self.wrong_execution_id else request.execution_id,
            self.descriptor.orchestrator_id,
            ExecutionStatus.SUCCEEDED,
            {"result": "probe-ok"},
        )

    def cancel(self, execution_id: str) -> None:
        pass


def certified_entry(factory: str) -> dict:
    return {
        "factory": factory,
        "cost": 0.25,
        "latency_ms": 25.0,
        "success_rate": 0.8,
        "quality": 0.8,
        "reliability": 0.8,
        "trust_profile": "local-test",
        "certification": {
            "mode": "required",
            "probe": {
                "execution_id": "r4-probe-exec",
                "mission_id": "r4-probe-mission",
                "objective": "certify runtime boundary",
                "required_capabilities": ["workflow"],
                "context": {
                    "obligation_id": "execution_result",
                    "subject_id": "r4-subject",
                    "subject_state_id": "r4-state",
                    "verification_context_id": "r4-verify",
                    "policy_bundle_id": "r4-policy",
                    "verifier_id": "adapter-observer",
                    "authority_id": "metao-runtime",
                },
            },
        },
    }


class DeclarativeCertifiedRuntimeOnboardingV1Tests(unittest.TestCase):
    def setUp(self) -> None:
        self.module_name = "metao_r4_wu01_plugins"
        self.module = ModuleType(self.module_name)
        sys.modules[self.module_name] = self.module

    def tearDown(self) -> None:
        sys.modules.pop(self.module_name, None)

    def factory(self, runtime: ProbeRuntime, name: str = "runtime_factory") -> str:
        setattr(
            self.module,
            name,
            lambda runtime=runtime: RuntimePlugin(runtime, normalize_evidence),
        )
        return f"{self.module_name}:{name}"

    @staticmethod
    def manifest(path: Path, entries: list[dict]) -> Path:
        path.write_text(json.dumps({"runtimes": entries}), encoding="utf-8")
        return path

    def test_required_certification_probes_before_registering_and_records_certificate(self):
        runtime = ProbeRuntime()
        certifications = InMemoryRuntimeCertificationStore()
        with tempfile.TemporaryDirectory() as temp:
            path = self.manifest(
                Path(temp) / "runtimes.json",
                [certified_entry(self.factory(runtime))],
            )
            operator = create_operator_from_catalog(
                path,
                store=InMemoryMissionStore(),
                certifications=certifications,
            )
        self.assertEqual(runtime.calls, 1)
        self.assertEqual([item.orchestrator_id for item in operator.runtime_entries()], ["runtime-a"])
        history = certifications.history("runtime-a")
        self.assertEqual(len(history), 1)
        self.assertTrue(history[0].passed)
        self.assertEqual(history[0].probe_execution_id, "r4-probe-exec")

    def test_failed_certification_is_a_factory_error_and_runtime_is_not_admitted(self):
        runtime = ProbeRuntime(wrong_execution_id=True)
        certifications = InMemoryRuntimeCertificationStore()
        with tempfile.TemporaryDirectory() as temp:
            path = self.manifest(
                Path(temp) / "runtimes.json",
                [certified_entry(self.factory(runtime))],
            )
            with self.assertRaises(RuntimeCatalogConfigError) as raised:
                create_operator_from_catalog(
                    path,
                    store=InMemoryMissionStore(),
                    certifications=certifications,
                )
        self.assertIn("execution_id_binding", str(raised.exception))
        history = certifications.history("runtime-a")
        self.assertEqual(len(history), 1)
        self.assertFalse(history[0].passed)

    def test_required_certification_without_store_fails_closed_without_probe_execution(self):
        runtime = ProbeRuntime()
        with tempfile.TemporaryDirectory() as temp:
            path = self.manifest(
                Path(temp) / "runtimes.json",
                [certified_entry(self.factory(runtime))],
            )
            with self.assertRaisesRegex(RuntimeCatalogConfigError, "certification store"):
                create_operator_from_catalog(path, store=InMemoryMissionStore())
        self.assertEqual(runtime.calls, 0)

    def test_legacy_manifest_remains_backward_compatible_and_probe_free(self):
        runtime = ProbeRuntime()
        entry = certified_entry(self.factory(runtime))
        entry.pop("certification")
        with tempfile.TemporaryDirectory() as temp:
            path = self.manifest(Path(temp) / "runtimes.json", [entry])
            operator = create_operator_from_catalog(path, store=InMemoryMissionStore())
        self.assertEqual(runtime.calls, 0)
        self.assertEqual(operator.runtime_entries()[0].orchestrator_id, "runtime-a")

    def test_explicit_legacy_mode_does_not_run_probe(self):
        runtime = ProbeRuntime()
        entry = certified_entry(self.factory(runtime))
        entry["certification"] = {"mode": "legacy"}
        with tempfile.TemporaryDirectory() as temp:
            path = self.manifest(Path(temp) / "runtimes.json", [entry])
            operator = create_operator_from_catalog(path, store=InMemoryMissionStore())
        self.assertEqual(runtime.calls, 0)
        self.assertEqual(len(operator.runtime_entries()), 1)

    def test_feedback_overlays_certified_runtime_routing_metrics(self):
        runtime = ProbeRuntime()
        certifications = InMemoryRuntimeCertificationStore()
        feedback = InMemoryRuntimeFeedbackStore()
        feedback.record(
            RuntimeObservation(
                "prior:e1",
                "prior",
                "e1",
                "runtime-a",
                1.0,
                1.0,
                5.0,
                0.01,
                1.0,
            )
        )
        with tempfile.TemporaryDirectory() as temp:
            path = self.manifest(
                Path(temp) / "runtimes.json",
                [certified_entry(self.factory(runtime))],
            )
            operator = create_operator_from_catalog(
                path,
                store=InMemoryMissionStore(),
                certifications=certifications,
                feedback=feedback,
            )
        entry = operator.runtime_entries()[0]
        self.assertEqual(entry.success_rate, 1.0)
        self.assertEqual(entry.quality, 1.0)
        self.assertEqual(entry.latency_ms, 5.0)
        self.assertEqual(entry.cost, 0.01)

    def test_quarantine_remains_authoritative_over_certification_and_feedback(self):
        runtime = ProbeRuntime()
        certifications = InMemoryRuntimeCertificationStore()
        feedback = InMemoryRuntimeFeedbackStore()
        feedback.record(
            RuntimeObservation(
                "prior:e1",
                "prior",
                "e1",
                "runtime-a",
                1.0,
                1.0,
                1.0,
                0.0,
                1.0,
            )
        )
        controls = InMemoryRuntimeControlStore()
        quarantine(
            controls,
            "runtime-a",
            reason="operator hold",
            actor_id="operator",
            updated_at_epoch=2.0,
        )
        with tempfile.TemporaryDirectory() as temp:
            path = self.manifest(
                Path(temp) / "runtimes.json",
                [certified_entry(self.factory(runtime))],
            )
            operator = create_operator_from_catalog(
                path,
                store=InMemoryMissionStore(),
                controls=controls,
                feedback=feedback,
                certifications=certifications,
            )
        entry = operator.runtime_entries()[0]
        self.assertEqual(entry.health, OrchestratorStatus.QUARANTINED)
        self.assertEqual(entry.quality, 1.0)
        self.assertTrue(certifications.history("runtime-a")[0].passed)

    def test_malformed_probe_fails_before_runtime_execution(self):
        runtime = ProbeRuntime()
        entry = certified_entry(self.factory(runtime))
        del entry["certification"]["probe"]["objective"]
        with tempfile.TemporaryDirectory() as temp:
            path = self.manifest(Path(temp) / "runtimes.json", [entry])
            with self.assertRaises(RuntimeCatalogConfigError):
                create_operator_from_catalog(
                    path,
                    store=InMemoryMissionStore(),
                    certifications=InMemoryRuntimeCertificationStore(),
                )
        self.assertEqual(runtime.calls, 0)

    def test_composed_factory_remains_sdk_neutral_and_non_learned(self):
        root = Path(__file__).resolve().parents[2]
        for relative in (
            "src/metao/runtime_factory.py",
            "src/metao/runtime_feedback.py",
            "src/metao/sqlite_runtime_feedback.py",
            "src/metao/feedback_catalog.py",
            "src/metao/runtime_admission.py",
            "src/metao/runtime_certification.py",
        ):
            source = (root / relative).read_text(encoding="utf-8").lower()
            for forbidden in (
                "import langgraph",
                "from langgraph",
                "import crewai",
                "from crewai",
                "sklearn",
                "torch",
            ):
                self.assertNotIn(forbidden, source)


if __name__ == "__main__":
    unittest.main(verbosity=2)
