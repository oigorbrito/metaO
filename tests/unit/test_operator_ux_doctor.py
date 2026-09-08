from __future__ import annotations

import json
import os
from io import StringIO
from pathlib import Path
import tempfile
import unittest

from metao.catalog import OrchestratorCatalog
from metao.cli import FACTORY_ENV_VAR
from metao.core import OrchestratorRegistry
from metao.entrypoint import main
from metao.runtime_factory import RuntimeCatalogOperator


def valid_operator_factory(*, store):
    registry = OrchestratorRegistry()
    catalog = OrchestratorCatalog(registry)
    return RuntimeCatalogOperator(registry=registry, catalog=catalog, store=store)


def failing_operator_factory(*, store):
    raise RuntimeError("factory-bootstrap-sentinel")


class NestedFactories:
    valid_operator_factory = staticmethod(valid_operator_factory)


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

    @staticmethod
    def checks_by_name(data: dict) -> dict[str, dict]:
        return {item["name"]: item for item in data["checks"]}

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
        self.assertEqual(data["overall_status"], "NOT_CONFIGURED")

    def test_t03_doctor_reports_not_configured(self) -> None:
        code, out, err = self.run_cli("doctor")
        self.assertEqual(code, 0)
        self.assertEqual(err, "")
        data = json.loads(out)
        factory_check = self.checks_by_name(data)["FACTORY_CONFIG"]
        self.assertEqual(factory_check["status"], "NOT_CONFIGURED")

    def test_t04_valid_factory_reaches_operator_and_catalog_readiness(self) -> None:
        factory_spec = f"{__name__}:valid_operator_factory"
        code, out, err = self.run_cli("doctor", "--factory", factory_spec)
        self.assertEqual(code, 0)
        self.assertEqual(err, "")
        data = json.loads(out)
        checks = self.checks_by_name(data)
        self.assertEqual(data["overall_status"], "PASS")
        self.assertEqual(checks["FACTORY_CONFIG"]["status"], "PASS")
        self.assertEqual(checks["FACTORY_IMPORT"]["status"], "PASS")
        self.assertEqual(checks["OPERATOR_CONSTRUCTION"]["status"], "PASS")
        self.assertEqual(checks["RUNTIME_CATALOG"]["status"], "PASS")
        self.assertEqual(checks["RUNTIME_CATALOG"]["details"], "count=0")

    def test_t05_factory_construction_failure_preserves_real_cause(self) -> None:
        factory_spec = f"{__name__}:failing_operator_factory"
        code, out, err = self.run_cli("doctor", "--factory", factory_spec)
        self.assertEqual(code, 0)
        self.assertEqual(err, "")
        data = json.loads(out)
        checks = self.checks_by_name(data)
        self.assertEqual(data["overall_status"], "FAIL")
        self.assertEqual(checks["FACTORY_IMPORT"]["status"], "PASS")
        self.assertEqual(checks["OPERATOR_CONSTRUCTION"]["status"], "FAIL")
        self.assertEqual(checks["OPERATOR_CONSTRUCTION"]["message"], "factory-bootstrap-sentinel")
        self.assertEqual(checks["RUNTIME_CATALOG"]["status"], "NOT_CHECKED")

    def test_t06_malformed_factory_syntax_fails_clearly(self) -> None:
        code, out, err = self.run_cli("doctor", "--factory", "bad_syntax")
        self.assertEqual(code, 0)
        self.assertEqual(err, "")
        data = json.loads(out)
        import_check = self.checks_by_name(data)["FACTORY_IMPORT"]
        self.assertEqual(import_check["status"], "FAIL")
        self.assertIn("factory must use module:function syntax", import_check["message"])

    def test_t07_module_import_failure(self) -> None:
        code, out, err = self.run_cli("doctor", "--factory", "does_not_exist:func")
        self.assertEqual(code, 0)
        self.assertEqual(err, "")
        data = json.loads(out)
        import_check = self.checks_by_name(data)["FACTORY_IMPORT"]
        self.assertEqual(import_check["status"], "FAIL")
        self.assertIn("does_not_exist", import_check["message"])

    def test_t08_nested_factory_path_is_identical_for_doctor(self) -> None:
        factory_spec = f"{__name__}:NestedFactories.valid_operator_factory"
        code, out, err = self.run_cli("doctor", "--factory", factory_spec)
        self.assertEqual(code, 0)
        self.assertEqual(err, "")
        data = json.loads(out)
        checks = self.checks_by_name(data)
        self.assertEqual(data["overall_status"], "PASS")
        self.assertEqual(checks["FACTORY_IMPORT"]["status"], "PASS")
        self.assertEqual(checks["OPERATOR_CONSTRUCTION"]["status"], "PASS")
        self.assertEqual(checks["RUNTIME_CATALOG"]["status"], "PASS")

    def test_t09_doctor_preflights_before_sqlite_persistence_wiring(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            db_path = Path(tmp) / "directory-used-as-db-path"
            db_path.mkdir()
            code, out, err = self.run_cli("--db", str(db_path), "doctor")
            self.assertEqual(code, 0)
            self.assertEqual(err, "")
            data = json.loads(out)
            self.assertEqual(data["overall_status"], "NOT_CONFIGURED")
            self.assertTrue(db_path.is_dir())
            self.assertEqual(list(db_path.iterdir()), [])

    def test_t12_doctor_does_not_execute_mission(self) -> None:
        factory_spec = f"{__name__}:valid_operator_factory"
        code, out, err = self.run_cli("doctor", "--factory", factory_spec)
        self.assertEqual(code, 0)
        self.assertEqual(err, "")
        self.assertNotIn("mission_id", out)

    def test_t14_run_explicit_factory_reports_invalid_target(self) -> None:
        code, out, err = self.run_cli("run", "dummy.json", "--factory", "os:environ")
        self.assertEqual(code, 2)
        self.assertEqual(out, "")
        error = json.loads(err)
        self.assertEqual(error["error"], "CLIInputError")
        self.assertEqual(error["message"], "factory target is not callable")

    def test_t15_run_accepts_nested_factory_path(self) -> None:
        factory_spec = f"{__name__}:NestedFactories.valid_operator_factory"
        mission = {
            "mission": {
                "mission_id": "nested-factory-run",
                "objective": "prove canonical nested factory loading",
                "required_capabilities": [],
            },
            "policy": {
                "policy_bundle_id": "policy-nested",
                "allowed": False,
                "require_human": False,
                "reason": "loader-probe-policy-block",
            },
            "budget": {
                "money_limit": 1,
                "token_limit": 1,
                "wall_time_limit_s": 1,
                "verifier_attempt_limit": 1,
            },
            "acceptance_context": {
                "subject_id": "subject",
                "subject_state_id": "state",
                "verification_context_id": "verification",
                "policy_bundle_id": "policy-nested",
                "required_obligations": [],
                "trusted_verifiers": [],
                "trusted_provenance_roots": [],
                "authorized_authorities": [],
            },
        }
        with tempfile.TemporaryDirectory() as tmp:
            mission_file = Path(tmp) / "mission.json"
            mission_file.write_text(json.dumps(mission), encoding="utf-8")
            db_path = Path(tmp) / "metao.db"
            code, out, err = self.run_cli(
                "--db",
                str(db_path),
                "run",
                str(mission_file),
                "--factory",
                factory_spec,
            )
            self.assertEqual(code, 0)
            self.assertEqual(err, "")
            result = json.loads(out)
            self.assertEqual(result["mission_id"], "nested-factory-run")
            self.assertEqual(result["status"], "BLOCKED")

    def test_t16_runtimes_explicit_factory_reports_import_failure(self) -> None:
        code, out, err = self.run_cli("runtimes", "--factory", "does_not_exist:func")
        self.assertEqual(code, 2)
        self.assertEqual(out, "")
        error = json.loads(err)
        self.assertIn(error["error"], {"ImportError", "ModuleNotFoundError"})
        self.assertIn("does_not_exist", error["message"])

    def test_t17_runtimes_accepts_nested_factory_path(self) -> None:
        factory_spec = f"{__name__}:NestedFactories.valid_operator_factory"
        with tempfile.TemporaryDirectory() as tmp:
            db_path = Path(tmp) / "metao.db"
            code, out, err = self.run_cli(
                "--db",
                str(db_path),
                "runtimes",
                "--factory",
                factory_spec,
            )
            self.assertEqual(code, 0)
            self.assertEqual(err, "")
            self.assertEqual(json.loads(out), [])


if __name__ == "__main__":
    unittest.main(verbosity=2)
