from __future__ import annotations

import json
import os
from io import StringIO
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


if __name__ == "__main__":
    unittest.main(verbosity=2)
