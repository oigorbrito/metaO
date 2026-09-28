from __future__ import annotations

import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import sysconfig
import tempfile
import unittest


class OperatorBootstrapNegativeE2ETests(unittest.TestCase):
    def metao_executable(self) -> str:
        scripts_dirs = (
            Path(sysconfig.get_path("scripts")),
            Path(sys.executable).resolve().parent,
        )
        executable = next(
            (
                str(candidate)
                for candidate in (
                    *(scripts_dir / "metao.exe" for scripts_dir in scripts_dirs),
                    *(scripts_dir / "metao" for scripts_dir in scripts_dirs),
                    *(scripts_dir / "Scripts" / "metao.exe" for scripts_dir in scripts_dirs),
                    *(scripts_dir / "Scripts" / "metao" for scripts_dir in scripts_dirs),
                )
                if candidate.is_file()
            ),
            None,
        ) or shutil.which("metao")
        self.assertIsNotNone(
            executable,
            f"installed metao console script is required in current interpreter scripts directories: {scripts_dirs}",
        )
        assert executable is not None
        return executable

    def run_metao(self, cwd: Path, env: dict[str, str], *args: str) -> subprocess.CompletedProcess[str]:
        return subprocess.run(
            [self.metao_executable(), *args],
            cwd=cwd,
            env=env,
            text=True,
            capture_output=True,
            check=False,
        )

    @staticmethod
    def clean_env() -> dict[str, str]:
        env = os.environ.copy()
        for name in (
            "METAO_OPERATOR_FACTORY",
            "METAO_RUNTIME_CATALOG",
            "METAO_RUNTIME_CONTROL_DB",
            "METAO_RUNTIME_FEEDBACK_DB",
            "METAO_RUNTIME_CERTIFICATION_DB",
            "METAO_RUNTIME_CERTIFICATION_REVOCATION_DB",
        ):
            env.pop(name, None)
        return env

    def test_installed_cli_negative_bootstrap_paths_fail_early_without_partial_state(self) -> None:
        repo_root = Path(__file__).resolve().parents[2]

        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            mission_db = root / "mission.db"
            env = self.clean_env()

            not_configured = self.run_metao(
                repo_root,
                env,
                "--db",
                str(mission_db),
                "doctor",
            )
            self.assertEqual(not_configured.returncode, 0, not_configured.stderr)
            self.assertEqual(not_configured.stderr, "")
            payload = json.loads(not_configured.stdout)
            self.assertEqual(payload["overall_status"], "NOT_CONFIGURED")
            checks = {item["name"]: item for item in payload["checks"]}
            self.assertEqual(checks["FACTORY_CONFIG"]["status"], "NOT_CONFIGURED")
            self.assertFalse(mission_db.exists(), "doctor must not create mission persistence")

            invalid_db = root / "directory-used-as-database"
            invalid_db.mkdir()
            bad_db_result = self.run_metao(
                repo_root,
                env,
                "--db",
                str(invalid_db),
                "doctor",
            )
            self.assertEqual(bad_db_result.returncode, 0, bad_db_result.stderr)
            self.assertEqual(bad_db_result.stderr, "")
            payload = json.loads(bad_db_result.stdout)
            checks = {item["name"]: item for item in payload["checks"]}
            self.assertEqual(payload["overall_status"], "FAIL")
            self.assertEqual(checks["DATABASE_PATH"]["status"], "FAIL")
            self.assertEqual(list(invalid_db.iterdir()), [])

            missing_mission = root / "missing-mission.json"
            bad_factory_env = env.copy()
            bad_factory_env["METAO_OPERATOR_FACTORY"] = "does_not_exist:factory"
            missing_result = self.run_metao(
                repo_root,
                bad_factory_env,
                "--db",
                str(mission_db),
                "run",
                str(missing_mission),
            )
            self.assertEqual(missing_result.returncode, 2)
            self.assertEqual(missing_result.stdout, "")
            error = json.loads(missing_result.stderr)
            self.assertEqual(error["error"], "CLIInputError")
            self.assertIn("cannot read mission file", error["message"])
            self.assertNotIn("does_not_exist", error["message"])
            self.assertFalse(mission_db.exists())

            invalid_mission = root / "invalid-mission.json"
            invalid_mission.write_text("{not-json", encoding="utf-8")
            invalid_result = self.run_metao(
                repo_root,
                bad_factory_env,
                "--db",
                str(mission_db),
                "run",
                str(invalid_mission),
            )
            self.assertEqual(invalid_result.returncode, 2)
            self.assertEqual(invalid_result.stdout, "")
            error = json.loads(invalid_result.stderr)
            self.assertEqual(error["error"], "CLIInputError")
            self.assertIn("invalid mission JSON", error["message"])
            self.assertNotIn("does_not_exist", error["message"])
            self.assertFalse(mission_db.exists())

            missing_catalog_env = env.copy()
            missing_catalog_env["METAO_OPERATOR_FACTORY"] = "metao.runtime_factory:create_operator"
            missing_catalog = self.run_metao(
                repo_root,
                missing_catalog_env,
                "--db",
                str(mission_db),
                "doctor",
            )
            self.assertEqual(missing_catalog.returncode, 0, missing_catalog.stderr)
            self.assertEqual(missing_catalog.stderr, "")
            payload = json.loads(missing_catalog.stdout)
            checks = {item["name"]: item for item in payload["checks"]}
            self.assertEqual(payload["overall_status"], "FAIL")
            self.assertEqual(checks["FACTORY_IMPORT"]["status"], "PASS")
            self.assertEqual(checks["OPERATOR_CONSTRUCTION"]["status"], "FAIL")
            self.assertIn("METAO_RUNTIME_CATALOG must point", checks["OPERATOR_CONSTRUCTION"]["message"])
            self.assertFalse(mission_db.exists())


if __name__ == "__main__":
    unittest.main(verbosity=2)
