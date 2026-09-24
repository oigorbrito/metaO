from __future__ import annotations

import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest


class ReadmeQuickstartE2ETests(unittest.TestCase):
    def run_metao(self, cwd: Path, env: dict[str, str], *args: str) -> object:
        python_dir = Path(sys.executable).parent
        script_dirs = [python_dir]
        if sys.platform == "win32":
            script_dirs.append(python_dir / "Scripts")
        executable = next(
            (
                candidate
                for scripts_dir in script_dirs
                for candidate in (
                    shutil.which("metao", path=str(scripts_dir)),
                    shutil.which("metao.exe", path=str(scripts_dir)),
                )
                if candidate is not None
            ),
            None,
        )
        self.assertIsNotNone(
            executable,
            f"installed metao console script is required near interpreter: {python_dir}",
        )
        completed = subprocess.run(
            [executable, *args],
            cwd=cwd,
            env=env,
            text=True,
            capture_output=True,
            check=False,
        )
        self.assertEqual(
            completed.returncode,
            0,
            f"metao {' '.join(args)} failed\nexecutable={executable}\nstdout={completed.stdout}\nstderr={completed.stderr}",
        )
        self.assertEqual(completed.stderr, "")
        return json.loads(completed.stdout)

    def test_committed_readme_quickstart_reaches_accepted_mission(self) -> None:
        repo_root = Path(__file__).resolve().parents[2]
        catalog_path = repo_root / "examples" / "runtime-catalog-quickstart.json"
        mission_path = repo_root / "examples" / "mission-quickstart-accepted.json"
        self.assertTrue(catalog_path.is_file())
        self.assertTrue(mission_path.is_file())

        with tempfile.TemporaryDirectory() as temp:
            state_root = Path(temp)
            mission_db = state_root / "metao.db"
            control_db = state_root / "runtime-control.db"
            certification_db = state_root / "runtime-certification.db"
            revocation_db = state_root / "runtime-certification-revocation.db"

            env = os.environ.copy()
            env["METAO_OPERATOR_FACTORY"] = "metao.runtime_factory:create_operator"
            env["METAO_RUNTIME_CATALOG"] = str(catalog_path)
            env["METAO_RUNTIME_CONTROL_DB"] = str(control_db)
            env["METAO_RUNTIME_CERTIFICATION_DB"] = str(certification_db)
            env["METAO_RUNTIME_CERTIFICATION_REVOCATION_DB"] = str(revocation_db)

            doctor = self.run_metao(
                repo_root,
                env,
                "--db",
                str(mission_db),
                "doctor",
            )
            self.assertEqual(doctor["overall_status"], "PASS")
            checks = {item["name"]: item for item in doctor["checks"]}
            self.assertEqual(checks["FACTORY_CONFIG"]["status"], "PASS")
            self.assertEqual(checks["FACTORY_IMPORT"]["status"], "PASS")
            self.assertEqual(checks["OPERATOR_CONSTRUCTION"]["status"], "PASS")
            self.assertEqual(checks["RUNTIME_CATALOG"]["status"], "PASS")
            self.assertEqual(checks["RUNTIME_CATALOG"]["details"], "count=1")
            self.assertFalse(mission_db.exists(), "doctor must not create mission persistence")

            runtimes = self.run_metao(
                repo_root,
                env,
                "--db",
                str(mission_db),
                "runtimes",
            )
            self.assertEqual(len(runtimes), 1)
            self.assertEqual(runtimes[0]["orchestrator_id"], "quickstart-local")
            self.assertEqual(runtimes[0]["health"], "healthy")

            certificates = self.run_metao(
                repo_root,
                env,
                "--db",
                str(mission_db),
                "runtime-certificates",
                "quickstart-local",
            )
            self.assertGreaterEqual(len(certificates), 1)
            self.assertTrue(certificates[-1]["passed"])
            self.assertEqual(
                certificates[-1]["probe_execution_id"],
                "quickstart-certification",
            )

            run_result = self.run_metao(
                repo_root,
                env,
                "--db",
                str(mission_db),
                "run",
                str(mission_path),
            )
            self.assertEqual(run_result["mission_id"], "quickstart-accepted")
            self.assertEqual(run_result["status"], "ACCEPTED")
            self.assertEqual(run_result["acceptance_decision"], "ACCEPT")
            self.assertEqual(run_result["orchestrator_id"], "quickstart-local")
            self.assertEqual(run_result["attempted_orchestrators"], ["quickstart-local"])
            self.assertTrue(mission_db.exists())

            status = self.run_metao(
                repo_root,
                env,
                "--db",
                str(mission_db),
                "status",
                "quickstart-accepted",
            )
            self.assertEqual(status["mission_id"], "quickstart-accepted")
            self.assertEqual(status["status"], "ACCEPTED")

            inspected = self.run_metao(
                repo_root,
                env,
                "--db",
                str(mission_db),
                "inspect",
                "quickstart-accepted",
            )
            self.assertEqual(inspected["status"], "ACCEPTED")
            self.assertEqual(inspected["execution"]["status"], "SUCCEEDED")
            self.assertEqual(
                inspected["execution"]["output"]["result"],
                "quickstart:quickstart mission",
            )
            self.assertEqual(inspected["acceptance"]["decision"], "ACCEPT")
            self.assertIsNotNone(inspected["acceptance"]["proof"])


if __name__ == "__main__":
    unittest.main(verbosity=2)
