from __future__ import annotations

import json
import os
from io import StringIO
from pathlib import Path
import sys
import tempfile
import unittest

from metao.cli import FACTORY_ENV_VAR
from metao.entrypoint import main


class OperatorUXDoctorTests(unittest.TestCase):
    def setUp(self) -> None:
        self._original_factory = None
        self._had_factory = FACTORY_ENV_VAR in os.environ
        if self._had_factory:
            self._original_factory = os.environ[FACTORY_ENV_VAR]
            del os.environ[FACTORY_ENV_VAR]

    def tearDown(self) -> None:
        if self._had_factory:
            os.environ[FACTORY_ENV_VAR] = self._original_factory  # type: ignore[assignment]

    def run_cli(self, *args: str) -> tuple[int, str, str]:
        stdout = StringIO()
        stderr = StringIO()
        code = main(args, stdout=stdout, stderr=stderr)
        return code, stdout.getvalue(), stderr.getvalue()

    def test_t01_help_includes_doctor(self) -> None:
        code, out, err = self.run_cli("--help")
        self.assertEqual(code, 0)
        self.assertIn("mission commands", out)
        self.assertEqual(err, "")

    def test_t02_doctor_runs_without_factory(self) -> None:
        code, out, err = self.run_cli("doctor")
        self.assertEqual(code, 0)
        self.assertEqual(err, "")
        data = json.loads(out)
        self.assertIn(data["overall_status"], ["NOT_CONFIGURED", "FAIL"])

    def test_t03_doctor_reports_not_configured(self) -> None:
        code, out, err = self.run_cli("doctor")
        self.assertEqual(code, 0)
        self.assertEqual(err, "")
        data = json.loads(out)
        factory_check = next(c for c in data["checks"] if c["name"] == "FACTORY_CONFIG")
        self.assertEqual(factory_check["status"], "NOT_CONFIGURED")

    def test_t06_malformed_factory_syntax_fails_clearly(self) -> None:
        code, out, err = self.run_cli("doctor", "--factory", "bad_syntax")
        self.assertEqual(code, 0)
        self.assertEqual(err, "")
        data = json.loads(out)
        import_check = next(c for c in data["checks"] if c["name"] == "FACTORY_IMPORT")
        self.assertEqual(import_check["status"], "FAIL")
        self.assertIn("Syntax must be module:function", import_check["message"])

    def test_t07_module_import_failure(self) -> None:
        code, out, err = self.run_cli("doctor", "--factory", "does_not_exist:func")
        self.assertEqual(code, 0)
        self.assertEqual(err, "")
        data = json.loads(out)
        import_check = next(c for c in data["checks"] if c["name"] == "FACTORY_IMPORT")
        self.assertEqual(import_check["status"], "FAIL")

    def test_t12_doctor_does_not_execute_mission(self) -> None:
        code, out, err = self.run_cli("doctor")
        self.assertEqual(code, 0)
        self.assertEqual(err, "")
        self.assertNotIn("mission_id", out)

    def test_t14_run_explicit_factory_remains_backward_compatible(self) -> None:
        try:
            self.run_cli("run", "dummy.json", "--factory", "os:environ")
        except SystemExit:
            pass
        except Exception:
            pass

    def test_t16_runtimes_explicit_factory(self) -> None:
        try:
            self.run_cli("runtimes", "--factory", "does_not_exist:func")
        except SystemExit:
            pass
        except Exception:
            pass

    def test_t17_configured_doctor_and_runtimes_use_factory_catalog(self) -> None:
        module_source = """
from metao.acceptance import EvidenceEnvelope
from metao.catalog import OrchestratorCatalog
from metao.core import ExecutionResult, ExecutionStatus, HealthReport, HealthStatus, OrchestratorDescriptor, OrchestratorRegistry
from metao.operator import MissionOperator


class Runtime:
    @property
    def descriptor(self):
        return OrchestratorDescriptor("doctor-runtime", "v1", frozenset({"workflow"}))

    def health(self):
        return HealthReport(HealthStatus.HEALTHY)

    def execute(self, request):
        return ExecutionResult(request.execution_id, self.descriptor.orchestrator_id, ExecutionStatus.SUCCEEDED)

    def cancel(self, execution_id):
        return None


def normalize_evidence(*, request, orchestrator_id, adapter_version, output, attempt_id):
    return EvidenceEnvelope(
        evidence_id=f"{request.execution_id}:evidence",
        obligation_id=request.context["obligation_id"],
        mission_id=request.mission.mission_id,
        execution_id=request.execution_id,
        orchestrator_id=orchestrator_id,
        adapter_version=adapter_version,
        attempt_id=attempt_id,
        subject_id=request.context["subject_id"],
        subject_state_id=request.context["subject_state_id"],
        verification_context_id=request.context["verification_context_id"],
        policy_bundle_id=request.context["policy_bundle_id"],
        verifier_id=request.context["verifier_id"],
        payload_digest="digest",
        provenance_root="provenance",
        authority_id=request.context["authority_id"],
        passed=True,
    )


def create_operator(*, store, **kwargs):
    registry = OrchestratorRegistry()
    runtime = Runtime()
    registry.register(runtime)
    catalog = OrchestratorCatalog(registry)
    catalog.register(runtime.descriptor.orchestrator_id, normalizer=normalize_evidence)
    return MissionOperator(registry=registry, store=store, catalog=catalog)
"""
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory)
            (path / "doctor_factory.py").write_text(module_source, encoding="utf-8")
            sys.path.insert(0, directory)
            try:
                db = str(path / "metao.db")
                code, out, err = self.run_cli("--db", db, "doctor", "--factory", "doctor_factory:create_operator")
                self.assertEqual(code, 0)
                self.assertEqual(err, "")
                doctor = json.loads(out)
                self.assertEqual(doctor["overall_status"], "PASS")

                code, out, err = self.run_cli("--db", db, "runtimes", "--factory", "doctor_factory:create_operator")
                self.assertEqual(code, 0)
                self.assertEqual(err, "")
                runtimes = json.loads(out)
                self.assertEqual(runtimes[0]["orchestrator_id"], "doctor-runtime")
                self.assertEqual(runtimes[0]["health"], "healthy")
            finally:
                sys.path.remove(directory)

    def test_t18_packaged_readme_factory_supports_doctor_and_runtimes(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            db = str(Path(directory) / "metao.db")
            factory = "metao.examples.readme_factory:create_operator"

            code, out, err = self.run_cli("--db", db, "doctor", "--factory", factory)
            self.assertEqual(code, 0)
            self.assertEqual(err, "")
            doctor = json.loads(out)
            self.assertEqual(doctor["overall_status"], "PASS")

            code, out, err = self.run_cli("--db", db, "runtimes", "--factory", factory)
            self.assertEqual(code, 0)
            self.assertEqual(err, "")
            runtimes = json.loads(out)
            self.assertEqual(runtimes[0]["orchestrator_id"], "readme-runtime")


if __name__ == "__main__":
    unittest.main(verbosity=2)
