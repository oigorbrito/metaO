from __future__ import annotations

from io import StringIO
import json
import os
from pathlib import Path
import sys
import tempfile
from types import ModuleType
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
from metao.runtime_factory import RUNTIME_CATALOG_ENV, RuntimePlugin


class Runtime:
    def __init__(self, orchestrator_id: str):
        self._descriptor = OrchestratorDescriptor(
            orchestrator_id,
            "v1",
            frozenset({"workflow"}),
        )
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
            {"result": self.descriptor.orchestrator_id},
        )

    def cancel(self, execution_id: str) -> None:
        pass


def catalog_entry(factory: str, *, preferred: bool) -> dict:
    return {
        "factory": factory,
        "cost": 0.01 if preferred else 5.0,
        "latency_ms": 10.0 if preferred else 5000.0,
        "success_rate": 0.99 if preferred else 0.2,
        "quality": 0.99 if preferred else 0.2,
        "reliability": 0.99 if preferred else 0.2,
        "trust_profile": "local-test",
    }


class RuntimeControlCliV1Tests(unittest.TestCase):
    def setUp(self) -> None:
        self.module_name = "metao_wu04_runtime_plugins"
        self.module = ModuleType(self.module_name)
        sys.modules[self.module_name] = self.module

    def tearDown(self) -> None:
        sys.modules.pop(self.module_name, None)

    def factory(self, name: str, runtime: Runtime) -> str:
        setattr(
            self.module,
            name,
            lambda runtime=runtime: RuntimePlugin(runtime, normalize_evidence),
        )
        return f"{self.module_name}:{name}"

    @staticmethod
    def invoke(argv):
        stdout, stderr = StringIO(), StringIO()
        code = main(argv, stdout=stdout, stderr=stderr)
        return code, stdout.getvalue(), stderr.getvalue()

    @staticmethod
    def write_manifest(path: Path, entries: list[dict]) -> Path:
        path.write_text(json.dumps({"runtimes": entries}), encoding="utf-8")
        return path

    @staticmethod
    def write_mission(path: Path, mission_id: str) -> Path:
        path.write_text(
            json.dumps(
                {
                    "mission": {
                        "mission_id": mission_id,
                        "objective": "exercise runtime controls",
                        "required_capabilities": ["workflow"],
                    },
                    "policy": {"policy_bundle_id": "policy-wu04", "allowed": True},
                    "budget": {
                        "money_limit": 10,
                        "token_limit": 10000,
                        "wall_time_limit_s": 60,
                        "verifier_attempt_limit": 4,
                    },
                    "acceptance_context": {
                        "subject_id": "subject-wu04",
                        "subject_state_id": "state-wu04",
                        "verification_context_id": "verify-wu04",
                        "policy_bundle_id": "policy-wu04",
                        "required_obligations": ["execution_result"],
                    },
                    "max_attempts": 2,
                }
            ),
            encoding="utf-8",
        )
        return path

    def test_combined_help_preserves_mission_commands_and_exposes_runtime_commands(self):
        code, stdout, stderr = self.invoke(["--help"])
        self.assertEqual(code, 0, stderr)
        self.assertIn("metaO control-plane operator CLI", stdout)
        for command in (
            "run",
            "status",
            "approve",
            "resume",
            "runtimes",
            "runtime-quarantine",
            "runtime-restore",
            "runtime-history",
        ):
            self.assertIn(command, stdout)

    def test_runtime_quarantine_is_durable_and_machine_readable(self):
        with tempfile.TemporaryDirectory() as temp:
            db = Path(temp) / "metao.db"
            code, stdout, stderr = self.invoke(
                [
                    "--db",
                    str(db),
                    "runtime-quarantine",
                    "primary",
                    "--reason",
                    "operator investigation",
                    "--actor",
                    "igor",
                    "--now-epoch",
                    "10",
                ]
            )
            self.assertEqual(code, 0, stderr)
            payload = json.loads(stdout)
            self.assertEqual(payload["orchestrator_id"], "primary")
            self.assertEqual(payload["disposition"], "QUARANTINED")
            self.assertEqual(payload["revision"], 1)

            code, stdout, stderr = self.invoke(
                ["--db", str(db), "runtime-history", "primary"]
            )
            self.assertEqual(code, 0, stderr)
            history = json.loads(stdout)
            self.assertEqual(len(history), 1)
            self.assertEqual(history[0]["reason"], "operator investigation")

    def test_runtimes_reflects_quarantine_without_executing_runtime(self):
        runtime = Runtime("primary")
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            db = root / "metao.db"
            manifest = self.write_manifest(
                root / "runtimes.json",
                [catalog_entry(self.factory("primary", runtime), preferred=True)],
            )
            with patch.dict(os.environ, {RUNTIME_CATALOG_ENV: str(manifest)}, clear=False):
                self.assertEqual(
                    self.invoke(
                        [
                            "--db",
                            str(db),
                            "runtime-quarantine",
                            "primary",
                            "--reason",
                            "manual hold",
                            "--actor",
                            "operator",
                        ]
                    )[0],
                    0,
                )
                code, stdout, stderr = self.invoke(
                    [
                        "--db",
                        str(db),
                        "runtimes",
                        "--factory",
                        "metao.runtime_factory:create_operator",
                    ]
                )
            self.assertEqual(code, 0, stderr)
            items = json.loads(stdout)
            self.assertEqual(items[0]["orchestrator_id"], "primary")
            self.assertEqual(items[0]["health"], "quarantined")
            self.assertEqual(runtime.calls, 0)

    def test_restore_reenables_live_healthy_runtime_and_preserves_history(self):
        runtime = Runtime("primary")
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            db = root / "metao.db"
            manifest = self.write_manifest(
                root / "runtimes.json",
                [catalog_entry(self.factory("primary", runtime), preferred=True)],
            )
            with patch.dict(os.environ, {RUNTIME_CATALOG_ENV: str(manifest)}, clear=False):
                self.invoke(
                    [
                        "--db",
                        str(db),
                        "runtime-quarantine",
                        "primary",
                        "--reason",
                        "hold",
                        "--actor",
                        "a",
                        "--now-epoch",
                        "1",
                    ]
                )
                code, stdout, stderr = self.invoke(
                    [
                        "--db",
                        str(db),
                        "runtime-restore",
                        "primary",
                        "--reason",
                        "verified",
                        "--actor",
                        "b",
                        "--now-epoch",
                        "2",
                    ]
                )
                self.assertEqual(code, 0, stderr)
                self.assertEqual(json.loads(stdout)["disposition"], "ACTIVE")

                code, stdout, stderr = self.invoke(
                    [
                        "--db",
                        str(db),
                        "runtimes",
                        "--factory",
                        "metao.runtime_factory:create_operator",
                    ]
                )
                self.assertEqual(code, 0, stderr)
                self.assertEqual(json.loads(stdout)[0]["health"], "healthy")

                code, stdout, stderr = self.invoke(
                    ["--db", str(db), "runtime-history", "primary"]
                )
            self.assertEqual(code, 0, stderr)
            history = json.loads(stdout)
            self.assertEqual([item["revision"] for item in history], [1, 2])
            self.assertEqual(
                [item["disposition"] for item in history],
                ["QUARANTINED", "ACTIVE"],
            )

    def test_legacy_run_automatically_honors_quarantine_in_same_db(self):
        primary, fallback = Runtime("primary"), Runtime("fallback")
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            db = root / "metao.db"
            manifest = self.write_manifest(
                root / "runtimes.json",
                [
                    catalog_entry(self.factory("primary", primary), preferred=True),
                    catalog_entry(self.factory("fallback", fallback), preferred=False),
                ],
            )
            mission = self.write_mission(root / "mission.json", "wu04-run")
            with patch.dict(os.environ, {RUNTIME_CATALOG_ENV: str(manifest)}, clear=False):
                code, _, stderr = self.invoke(
                    [
                        "--db",
                        str(db),
                        "runtime-quarantine",
                        "primary",
                        "--reason",
                        "operator hold",
                        "--actor",
                        "operator",
                    ]
                )
                self.assertEqual(code, 0, stderr)
                code, stdout, stderr = self.invoke(
                    [
                        "--db",
                        str(db),
                        "run",
                        str(mission),
                        "--factory",
                        "metao.runtime_factory:create_operator",
                    ]
                )
            self.assertEqual(code, 0, stderr)
            payload = json.loads(stdout)
            self.assertEqual(payload["status"], "ACCEPTED")
            self.assertEqual(payload["orchestrator_id"], "fallback")
            self.assertEqual(primary.calls, 0)
            self.assertEqual(fallback.calls, 1)

    def test_legacy_read_commands_still_delegate_after_runtime_entrypoint(self):
        primary = Runtime("primary")
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            db = root / "metao.db"
            manifest = self.write_manifest(
                root / "runtimes.json",
                [catalog_entry(self.factory("primary", primary), preferred=True)],
            )
            mission = self.write_mission(root / "mission.json", "wu04-legacy")
            with patch.dict(os.environ, {RUNTIME_CATALOG_ENV: str(manifest)}, clear=False):
                self.assertEqual(
                    self.invoke(
                        [
                            "--db",
                            str(db),
                            "run",
                            str(mission),
                            "--factory",
                            "metao.runtime_factory:create_operator",
                        ]
                    )[0],
                    0,
                )
                code, stdout, stderr = self.invoke(
                    ["--db", str(db), "status", "wu04-legacy"]
                )
            self.assertEqual(code, 0, stderr)
            self.assertEqual(json.loads(stdout)["status"], "ACCEPTED")

    def test_runtime_history_for_unseen_runtime_is_empty_and_read_only(self):
        with tempfile.TemporaryDirectory() as temp:
            db = Path(temp) / "metao.db"
            code, stdout, stderr = self.invoke(
                ["--db", str(db), "runtime-history", "never-seen"]
            )
            self.assertEqual(code, 0, stderr)
            self.assertEqual(json.loads(stdout), [])

    def test_invalid_runtime_control_input_fails_closed(self):
        with tempfile.TemporaryDirectory() as temp:
            db = Path(temp) / "metao.db"
            code, stdout, stderr = self.invoke(
                [
                    "--db",
                    str(db),
                    "runtime-quarantine",
                    "primary",
                    "--reason",
                    "",
                    "--actor",
                    "operator",
                ]
            )
            self.assertEqual(code, 2)
            self.assertEqual(stdout, "")
            self.assertEqual(json.loads(stderr)["error"], "ValueError")

    def test_factory_without_runtime_catalog_surface_fails_closed_for_runtimes(self):
        from metao.core import OrchestratorRegistry
        from metao.mission_store import InMemoryMissionStore
        from metao.operator import MissionOperator

        module_name = "metao_wu04_plain_factory"
        module = ModuleType(module_name)
        runtime = Runtime("plain")
        registry = OrchestratorRegistry()
        registry.register(runtime)
        module.create_operator = lambda *, store: MissionOperator(
            registry=registry,
            store=store,
            pools=(),
            normalizers={},
        )
        sys.modules[module_name] = module
        try:
            with tempfile.TemporaryDirectory() as temp:
                code, stdout, stderr = self.invoke(
                    [
                        "--db",
                        str(Path(temp) / "metao.db"),
                        "runtimes",
                        "--factory",
                        f"{module_name}:create_operator",
                    ]
                )
            self.assertEqual(code, 2)
            self.assertEqual(stdout, "")
            self.assertIn("runtime_entries", json.loads(stderr)["message"])
        finally:
            sys.modules.pop(module_name, None)

    def test_entrypoint_and_factory_remain_orchestrator_sdk_neutral(self):
        root = Path(__file__).resolve().parents[2]
        for relative in ("src/metao/entrypoint.py", "src/metao/runtime_factory.py"):
            source = (root / relative).read_text(encoding="utf-8").lower()
            for forbidden in ("import langgraph", "from langgraph", "import crewai", "from crewai"):
                self.assertNotIn(forbidden, source)


if __name__ == "__main__":
    unittest.main(verbosity=2)
