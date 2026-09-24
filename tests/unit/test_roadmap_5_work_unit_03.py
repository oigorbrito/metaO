from __future__ import annotations

from io import StringIO
import json
import os
from pathlib import Path
import sys
import tempfile
from types import ModuleType, SimpleNamespace
import unittest
from unittest.mock import patch

from metao.adapters.langgraph import normalize_evidence
from metao.core import (
    ExecutionRequest,
    ExecutionResult,
    ExecutionStatus,
    HealthReport,
    HealthStatus,
    OrchestratorDescriptor,
)
from metao.entrypoint import main
from metao.runtime_certification import RuntimeCertification, certificate_identity
from metao.runtime_factory import RUNTIME_CATALOG_ENV, RuntimePlugin
from metao.sqlite_runtime_certification import SQLiteRuntimeCertificationStore
from metao.sqlite_runtime_certification_revocation import (
    SQLiteRuntimeCertificationRevocationStore,
)


class Runtime:
    def __init__(self) -> None:
        self._descriptor = OrchestratorDescriptor("runtime-a", "v1", frozenset({"workflow"}))
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


def certificate(epoch: float = 100.0) -> RuntimeCertification:
    return RuntimeCertification(
        certificate_id=certificate_identity(
            "runtime-a", "v1", "probe-v1", certified_at_epoch=epoch
        ),
        orchestrator_id="runtime-a",
        runtime_version="v1",
        probe_execution_id="probe-v1",
        passed=True,
        failed_checks=(),
        checks_digest="a" * 64,
        total_checks=8,
        certified_at_epoch=epoch,
    )


def catalog_entry(factory: str) -> dict:
    return {
        "factory": factory,
        "cost": 0.1,
        "latency_ms": 10.0,
        "success_rate": 0.8,
        "quality": 0.8,
        "reliability": 0.8,
        "certification": {
            "mode": "required",
            "reuse_passed": True,
            "probe": {
                "execution_id": "probe-v1",
                "objective": "certify lifecycle runtime",
                "required_capabilities": ["workflow"],
            },
        },
    }


class CertificationLifecycleCliV1Tests(unittest.TestCase):
    def setUp(self) -> None:
        self.module_name = "metao_r5_wu03_plugins"
        self.module = ModuleType(self.module_name)
        sys.modules[self.module_name] = self.module

    def tearDown(self) -> None:
        sys.modules.pop(self.module_name, None)

    def bind(self, runtime: Runtime) -> str:
        setattr(
            self.module,
            "make_runtime",
            lambda runtime=runtime: RuntimePlugin(runtime, normalize_evidence),
        )
        return f"{self.module_name}:make_runtime"

    @staticmethod
    def invoke(argv):
        stdout, stderr = StringIO(), StringIO()
        code = main(argv, stdout=stdout, stderr=stderr)
        return code, stdout.getvalue(), stderr.getvalue()

    @staticmethod
    def write_manifest(path: Path, factory: str) -> Path:
        path.write_text(json.dumps({"runtimes": [catalog_entry(factory)]}), encoding="utf-8")
        return path

    def test_help_exposes_certificate_lifecycle_without_removing_existing_commands(self):
        code, stdout, stderr = self.invoke(["--help"])
        self.assertEqual(code, 0, stderr)
        for command in (
            "run",
            "runtimes",
            "runtime-inspect",
            "runtime-quarantine",
            "runtime-certificates",
            "runtime-certificate-revoke",
            "runtime-certificate-revocations",
        ):
            self.assertIn(command, stdout)

    def test_runtime_inspect_aggregates_catalog_control_and_certificate_evidence(self):
        runtime = Runtime()
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            db = root / "metao.db"
            manifest = self.write_manifest(root / "runtimes.json", self.bind(runtime))
            with patch.dict(os.environ, {RUNTIME_CATALOG_ENV: str(manifest)}, clear=False):
                with patch("metao.runtime_factory.time.time", return_value=100.0):
                    code, _, stderr = self.invoke(
                        [
                            "--db",
                            str(db),
                            "runtimes",
                            "--factory",
                            "metao.runtime_factory:create_operator",
                        ]
                    )
                self.assertEqual(code, 0, stderr)

                benchmark_path = root / "benchmark.json"
                benchmark_path.write_text(
                    json.dumps(
                        {
                            "evidence_id": "runtime-a-benchmark-1",
                            "benchmark_id": "software-engineering",
                            "benchmark_version": "v1",
                            "task_set": "verified",
                            "executor_id": "runtime-a",
                            "executor_version": "v1",
                            "harness_id": "test-harness",
                            "harness_version": "v1",
                            "model_id": "test-model",
                            "provider_id": "test-provider",
                            "model_version": "v1",
                            "runtime_config_digest": "runtime-config",
                            "tool_policy_digest": "tool-policy",
                            "environment_id": "unit-test",
                            "observed_at_epoch": 110.0,
                            "source": "METAO_REPRODUCED",
                            "raw_result_ref": "artifact://runtime-a-benchmark-1",
                            "metrics": [
                                {
                                    "name": "resolved_rate",
                                    "value": 0.75,
                                    "unit": "ratio",
                                }
                            ],
                        }
                    ),
                    encoding="utf-8",
                )
                code, _, stderr = self.invoke(
                    [
                        "--db",
                        str(db),
                        "benchmark-import",
                        str(benchmark_path),
                    ]
                )
                self.assertEqual(code, 0, stderr)

                code, stdout, stderr = self.invoke(
                    [
                        "--db",
                        str(db),
                        "runtime-inspect",
                        "runtime-a",
                        "--factory",
                        "metao.runtime_factory:create_operator",
                        "--now-epoch",
                        "120",
                        "--max-age-seconds",
                        "60",
                    ]
                )

        self.assertEqual(code, 0, stderr)
        view = json.loads(stdout)
        self.assertEqual(view["runtime"]["orchestrator_id"], "runtime-a")
        self.assertEqual(view["runtime"]["version"], "v1")
        self.assertEqual(view["runtime"]["capabilities"], ["workflow"])
        self.assertIsNone(view["control"])
        self.assertEqual(len(view["certificates"]), 1)
        self.assertTrue(view["certificates"][0]["passed"])
        self.assertTrue(view["certificates"][0]["fresh"])
        self.assertTrue(view["certificates"][0]["reusable"])
        self.assertEqual(len(view["benchmark_evidence"]), 1)
        self.assertEqual(
            view["benchmark_evidence"][0]["evidence_id"],
            "runtime-a-benchmark-1",
        )
        self.assertEqual(
            view["benchmark_evidence"][0]["metrics"][0]["name"],
            "resolved_rate",
        )
        self.assertTrue(view["benchmark_evidence"][0]["fresh"])

    def test_runtime_inspect_requires_complete_freshness_pair(self):
        with tempfile.TemporaryDirectory() as temp:
            db = Path(temp) / "metao.db"
            code, stdout, stderr = self.invoke(
                [
                    "--db",
                    str(db),
                    "runtime-inspect",
                    "runtime-a",
                    "--now-epoch",
                    "10",
                ]
            )
        self.assertEqual(code, 2)
        self.assertEqual(stdout, "")
        payload = json.loads(stderr)
        self.assertEqual(payload["error"], "CLIInputError")
        self.assertEqual(
            payload["message"],
            "runtime-inspect freshness requires both --now-epoch and --max-age-seconds",
        )

    def test_runtime_inspect_rejects_missing_runtime_identity(self):
        entry = SimpleNamespace(
            orchestrator_id="runtime-a",
            version="v1",
            capabilities=frozenset({"workflow"}),
            health=HealthStatus.HEALTHY,
            cost=0.1,
            latency_ms=10.0,
        )
        with patch("metao.entrypoint._load_factory_operator") as load_operator:
            load_operator.return_value = SimpleNamespace(runtime_entries=lambda: [entry])
            code, stdout, stderr = self.invoke(
                ["runtime-inspect", "runtime-missing"]
            )

        self.assertEqual(code, 2)
        self.assertEqual(stdout, "")
        payload = json.loads(stderr)
        self.assertEqual(payload["error"], "CLIInputError")
        self.assertEqual(payload["message"], "runtime not found: runtime-missing")

    def test_runtime_inspect_rejects_non_unique_runtime_identity(self):
        entry = SimpleNamespace(
            orchestrator_id="runtime-a",
            version="v1",
            capabilities=frozenset({"workflow"}),
            health=HealthStatus.HEALTHY,
            cost=0.1,
            latency_ms=10.0,
        )
        with patch("metao.entrypoint._load_factory_operator") as load_operator:
            load_operator.return_value = SimpleNamespace(runtime_entries=lambda: [entry, entry])
            code, stdout, stderr = self.invoke(
                ["runtime-inspect", "runtime-a"]
            )

        self.assertEqual(code, 2)
        self.assertEqual(stdout, "")
        payload = json.loads(stderr)
        self.assertEqual(payload["error"], "CLIInputError")
        self.assertEqual(
            payload["message"],
            "runtime identity is not unique: runtime-a",
        )

    def test_runtime_certificates_is_machine_readable_and_can_compute_freshness(self):
        with tempfile.TemporaryDirectory() as temp:
            db = Path(temp) / "metao.db"
            SQLiteRuntimeCertificationStore(db).record(certificate(100.0))
            code, stdout, stderr = self.invoke(
                [
                    "--db",
                    str(db),
                    "runtime-certificates",
                    "runtime-a",
                    "--now-epoch",
                    "150",
                    "--max-age-seconds",
                    "60",
                ]
            )
        self.assertEqual(code, 0, stderr)
        items = json.loads(stdout)
        self.assertEqual(len(items), 1)
        self.assertTrue(items[0]["passed"])
        self.assertTrue(items[0]["fresh"])
        self.assertFalse(items[0]["revoked"])
        self.assertTrue(items[0]["reusable"])

    def test_runtime_certificates_requires_complete_freshness_pair(self):
        with tempfile.TemporaryDirectory() as temp:
            db = Path(temp) / "metao.db"
            code, stdout, stderr = self.invoke(
                ["--db", str(db), "runtime-certificates", "runtime-a", "--now-epoch", "10"]
            )
        self.assertEqual(code, 2)
        self.assertEqual(stdout, "")
        payload = json.loads(stderr)
        self.assertEqual(payload["error"], "CLIInputError")

    def test_revoke_existing_certificate_and_list_revocation_history(self):
        with tempfile.TemporaryDirectory() as temp:
            db = Path(temp) / "metao.db"
            item = certificate(100.0)
            SQLiteRuntimeCertificationStore(db).record(item)
            code, stdout, stderr = self.invoke(
                [
                    "--db",
                    str(db),
                    "runtime-certificate-revoke",
                    item.certificate_id,
                    "--reason",
                    "operator distrust",
                    "--actor",
                    "igor",
                    "--now-epoch",
                    "120",
                ]
            )
            self.assertEqual(code, 0, stderr)
            record = json.loads(stdout)
            self.assertEqual(record["certificate_id"], item.certificate_id)
            self.assertEqual(record["reason"], "operator distrust")

            code, stdout, stderr = self.invoke(
                ["--db", str(db), "runtime-certificate-revocations", "runtime-a"]
            )
        self.assertEqual(code, 0, stderr)
        history = json.loads(stdout)
        self.assertEqual(len(history), 1)
        self.assertEqual(history[0]["actor_id"], "igor")

    def test_revoke_unknown_certificate_fails_closed(self):
        with tempfile.TemporaryDirectory() as temp:
            db = Path(temp) / "metao.db"
            code, stdout, stderr = self.invoke(
                [
                    "--db",
                    str(db),
                    "runtime-certificate-revoke",
                    "missing",
                    "--reason",
                    "bad id",
                    "--actor",
                    "igor",
                ]
            )
            self.assertEqual(code, 2)
            self.assertEqual(stdout, "")
            self.assertEqual(
                SQLiteRuntimeCertificationRevocationStore(db).history("runtime-a"),
                (),
            )
        self.assertEqual(json.loads(stderr)["error"], "UnknownRuntimeCertification")

    def test_revoked_certificate_view_is_not_reusable_even_when_fresh(self):
        with tempfile.TemporaryDirectory() as temp:
            db = Path(temp) / "metao.db"
            item = certificate(100.0)
            SQLiteRuntimeCertificationStore(db).record(item)
            self.assertEqual(
                self.invoke(
                    [
                        "--db",
                        str(db),
                        "runtime-certificate-revoke",
                        item.certificate_id,
                        "--reason",
                        "manual revoke",
                        "--actor",
                        "igor",
                        "--now-epoch",
                        "110",
                    ]
                )[0],
                0,
            )
            code, stdout, stderr = self.invoke(
                [
                    "--db",
                    str(db),
                    "runtime-certificates",
                    "runtime-a",
                    "--now-epoch",
                    "120",
                    "--max-age-seconds",
                    "60",
                ]
            )
        self.assertEqual(code, 0, stderr)
        view = json.loads(stdout)[0]
        self.assertTrue(view["fresh"])
        self.assertTrue(view["revoked"])
        self.assertFalse(view["reusable"])

    def test_identical_revoke_command_is_idempotent_but_conflicting_rewrite_fails(self):
        with tempfile.TemporaryDirectory() as temp:
            db = Path(temp) / "metao.db"
            item = certificate(100.0)
            SQLiteRuntimeCertificationStore(db).record(item)
            argv = [
                "--db",
                str(db),
                "runtime-certificate-revoke",
                item.certificate_id,
                "--reason",
                "manual revoke",
                "--actor",
                "igor",
                "--now-epoch",
                "110",
            ]
            self.assertEqual(self.invoke(argv)[0], 0)
            self.assertEqual(self.invoke(argv)[0], 0)
            code, stdout, stderr = self.invoke(
                [
                    "--db",
                    str(db),
                    "runtime-certificate-revoke",
                    item.certificate_id,
                    "--reason",
                    "rewrite",
                    "--actor",
                    "igor",
                    "--now-epoch",
                    "110",
                ]
            )
        self.assertEqual(code, 2)
        self.assertEqual(stdout, "")
        self.assertEqual(json.loads(stderr)["error"], "RuntimeCertificationRevocationConflict")

    def test_cli_revoke_forces_next_declarative_load_to_recertify_then_reuse_new_generation(self):
        first_runtime = Runtime()
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            db = root / "metao.db"
            manifest = self.write_manifest(root / "runtimes.json", self.bind(first_runtime))
            with patch.dict(os.environ, {RUNTIME_CATALOG_ENV: str(manifest)}, clear=False):
                with patch("metao.runtime_factory.time.time", return_value=100.0):
                    code, _, stderr = self.invoke(
                        [
                            "--db",
                            str(db),
                            "runtimes",
                            "--factory",
                            "metao.runtime_factory:create_operator",
                        ]
                    )
                self.assertEqual(code, 0, stderr)
                self.assertEqual(first_runtime.calls, 1)

                code, stdout, stderr = self.invoke(
                    ["--db", str(db), "runtime-certificates", "runtime-a"]
                )
                self.assertEqual(code, 0, stderr)
                old_id = json.loads(stdout)[0]["certificate_id"]
                self.assertEqual(
                    self.invoke(
                        [
                            "--db",
                            str(db),
                            "runtime-certificate-revoke",
                            old_id,
                            "--reason",
                            "rotate",
                            "--actor",
                            "igor",
                            "--now-epoch",
                            "110",
                        ]
                    )[0],
                    0,
                )

                second_runtime = Runtime()
                self.bind(second_runtime)
                with patch("metao.runtime_factory.time.time", return_value=120.0):
                    code, _, stderr = self.invoke(
                        [
                            "--db",
                            str(db),
                            "runtimes",
                            "--factory",
                            "metao.runtime_factory:create_operator",
                        ]
                    )
                self.assertEqual(code, 0, stderr)
                self.assertEqual(second_runtime.calls, 1)

                third_runtime = Runtime()
                self.bind(third_runtime)
                with patch("metao.runtime_factory.time.time", return_value=130.0):
                    code, _, stderr = self.invoke(
                        [
                            "--db",
                            str(db),
                            "runtimes",
                            "--factory",
                            "metao.runtime_factory:create_operator",
                        ]
                    )
                self.assertEqual(code, 0, stderr)
                self.assertEqual(third_runtime.calls, 0)

                code, stdout, stderr = self.invoke(
                    ["--db", str(db), "runtime-certificates", "runtime-a"]
                )
            self.assertEqual(code, 0, stderr)
            items = json.loads(stdout)
        self.assertEqual(len(items), 2)
        self.assertTrue(items[0]["revoked"])
        self.assertFalse(items[1]["revoked"])

    def test_entrypoint_remains_sdk_neutral(self):
        root = Path(__file__).resolve().parents[2]
        source = (root / "src/metao/entrypoint.py").read_text(encoding="utf-8").lower()
        self.assertNotIn("import crewai", source)
        self.assertNotIn("from crewai", source)
        self.assertNotIn("import langgraph", source)
        self.assertNotIn("from langgraph", source)


if __name__ == "__main__":
    unittest.main()
