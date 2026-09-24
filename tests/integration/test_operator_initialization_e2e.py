from __future__ import annotations

import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest


class OperatorInitializationE2ETests(unittest.TestCase):
    def run_metao(self, root: Path, env: dict[str, str], *args: str) -> object:
        scripts_dirs = [Path(sys.executable).parent]
        if sys.platform == "win32":
            scripts_dirs.append(scripts_dirs[0] / "Scripts")
        executable = next(
            (
                shutil.which("metao", path=str(scripts_dir))
                for scripts_dir in scripts_dirs
                if scripts_dir.exists()
            ),
            None,
        )
        self.assertIsNotNone(
            executable,
            f"installed metao console script is required in current interpreter directories: {scripts_dirs}",
        )
        completed = subprocess.run(
            [executable, *args],
            cwd=root,
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

    def test_clean_bootstrap_to_certified_runtime_and_persisted_accepted_mission(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            plugin_path = root / "bootstrap_e2e_runtime.py"
            manifest_path = root / "runtimes.json"
            mission_path = root / "mission.json"
            mission_db = root / "metao.db"
            control_db = root / "runtime-control.db"
            certification_db = root / "runtime-certification.db"
            revocation_db = root / "runtime-certification-revocation.db"

            plugin_path.write_text(
                '''from typing_extensions import TypedDict\n'''
                '''from langgraph.graph import END, START, StateGraph\n'''
                '''from metao.adapters.langgraph import LangGraphOrchestratorAdapter, normalize_evidence\n'''
                '''from metao.runtime_factory import RuntimePlugin\n\n'''
                '''class State(TypedDict, total=False):\n'''
                '''    objective: str\n'''
                '''    result: str\n\n'''
                '''def create_plugin():\n'''
                '''    builder = StateGraph(State)\n'''
                '''    builder.add_node("step", lambda state: {"result": "boot:" + state["objective"]})\n'''
                '''    builder.add_edge(START, "step")\n'''
                '''    builder.add_edge("step", END)\n'''
                '''    graph = builder.compile()\n'''
                '''    adapter = LangGraphOrchestratorAdapter(\n'''
                '''        graph, orchestrator_id="bootstrap-e2e-langgraph", version="1.2.11"\n'''
                '''    )\n'''
                '''    return RuntimePlugin(adapter, normalize_evidence)\n''',
                encoding="utf-8",
            )

            manifest_path.write_text(
                json.dumps(
                    {
                        "runtimes": [
                            {
                                "factory": "bootstrap_e2e_runtime:create_plugin",
                                "cost": 0.01,
                                "latency_ms": 10.0,
                                "success_rate": 0.99,
                                "quality": 0.99,
                                "reliability": 0.99,
                                "trust_profile": "e2e-local",
                                "certification": {
                                    "mode": "required",
                                    "probe": {
                                        "execution_id": "bootstrap-e2e-certification",
                                        "mission_id": "bootstrap-e2e-certification-mission",
                                        "objective": "certify bootstrap runtime",
                                        "required_capabilities": ["workflow"],
                                        "context": {
                                            "obligation_id": "execution_result",
                                            "subject_id": "bootstrap-e2e-subject",
                                            "subject_state_id": "bootstrap-e2e-state",
                                            "verification_context_id": "bootstrap-e2e-verification",
                                            "policy_bundle_id": "bootstrap-e2e-policy",
                                            "verifier_id": "adapter-observer",
                                            "authority_id": "metao-runtime",
                                            "created_at_epoch": 100.0,
                                        },
                                    },
                                },
                            }
                        ]
                    }
                ),
                encoding="utf-8",
            )

            mission_path.write_text(
                json.dumps(
                    {
                        "mission": {
                            "mission_id": "bootstrap-e2e-mission",
                            "objective": "bootstrap mission",
                            "required_capabilities": ["workflow"],
                        },
                        "policy": {
                            "policy_bundle_id": "bootstrap-e2e-policy",
                            "allowed": True,
                            "require_human": False,
                        },
                        "budget": {
                            "money_limit": 1.0,
                            "token_limit": 1000,
                            "wall_time_limit_s": 60.0,
                            "verifier_attempt_limit": 3,
                        },
                        "acceptance_context": {
                            "subject_id": "bootstrap-e2e-subject",
                            "subject_state_id": "bootstrap-e2e-state",
                            "verification_context_id": "bootstrap-e2e-verification",
                            "policy_bundle_id": "bootstrap-e2e-policy",
                            "required_obligations": ["execution_result"],
                            "trusted_verifiers": ["adapter-observer"],
                            "trusted_provenance_roots": [],
                            "authorized_authorities": ["metao-runtime"],
                        },
                        "now_epoch": 100.0,
                        "max_attempts": 2,
                    }
                ),
                encoding="utf-8",
            )

            env = os.environ.copy()
            env["METAO_RUNTIME_CATALOG"] = str(manifest_path)
            env["METAO_RUNTIME_CONTROL_DB"] = str(control_db)
            env["METAO_RUNTIME_CERTIFICATION_DB"] = str(certification_db)
            env["METAO_RUNTIME_CERTIFICATION_REVOCATION_DB"] = str(revocation_db)
            env["PYTHONPATH"] = str(root) + os.pathsep + env.get("PYTHONPATH", "")

            self.assertFalse(mission_db.exists())

            doctor = self.run_metao(
                root,
                env,
                "--db",
                str(mission_db),
                "doctor",
                "--factory",
                "metao.runtime_factory:create_operator",
            )
            self.assertEqual(
                doctor["overall_status"],
                "PASS",
                f"doctor failed: {json.dumps(doctor, sort_keys=True)}",
            )
            checks = {item["name"]: item for item in doctor["checks"]}
            self.assertEqual(checks["FACTORY_IMPORT"]["status"], "PASS")
            self.assertEqual(checks["OPERATOR_CONSTRUCTION"]["status"], "PASS")
            self.assertEqual(checks["RUNTIME_CATALOG"]["status"], "PASS")
            self.assertEqual(checks["RUNTIME_CATALOG"]["details"], "count=1")
            self.assertFalse(mission_db.exists(), "doctor must not create mission persistence")

            runtimes = self.run_metao(
                root,
                env,
                "--db",
                str(mission_db),
                "runtimes",
                "--factory",
                "metao.runtime_factory:create_operator",
            )
            self.assertEqual(len(runtimes), 1)
            self.assertEqual(runtimes[0]["orchestrator_id"], "bootstrap-e2e-langgraph")
            self.assertEqual(runtimes[0]["health"], "healthy")

            certificates = self.run_metao(
                root,
                env,
                "--db",
                str(mission_db),
                "runtime-certificates",
                "bootstrap-e2e-langgraph",
            )
            self.assertGreaterEqual(len(certificates), 1)
            self.assertTrue(certificates[-1]["passed"])
            self.assertEqual(
                certificates[-1]["probe_execution_id"],
                "bootstrap-e2e-certification",
            )

            run_result = self.run_metao(
                root,
                env,
                "--db",
                str(mission_db),
                "run",
                str(mission_path),
                "--factory",
                "metao.runtime_factory:create_operator",
            )
            self.assertEqual(run_result["mission_id"], "bootstrap-e2e-mission")
            self.assertEqual(run_result["status"], "ACCEPTED")
            self.assertEqual(run_result["acceptance_decision"], "ACCEPT")
            self.assertEqual(run_result["orchestrator_id"], "bootstrap-e2e-langgraph")
            self.assertEqual(run_result["attempted_orchestrators"], ["bootstrap-e2e-langgraph"])
            self.assertTrue(mission_db.exists())

            inspected = self.run_metao(
                root,
                env,
                "--db",
                str(mission_db),
                "inspect",
                "bootstrap-e2e-mission",
            )
            self.assertEqual(inspected["status"], "ACCEPTED")
            self.assertEqual(inspected["execution"]["status"], "SUCCEEDED")
            self.assertEqual(inspected["execution"]["output"]["result"], "boot:bootstrap mission")
            self.assertEqual(inspected["acceptance"]["decision"], "ACCEPT")
            self.assertIsNotNone(inspected["acceptance"]["proof"])


if __name__ == "__main__":
    unittest.main(verbosity=2)