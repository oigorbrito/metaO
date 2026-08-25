from __future__ import annotations

from io import StringIO
import json
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
from types import ModuleType
import unittest

from metao.adapters.langgraph import normalize_evidence
from metao.catalog import OrchestratorCatalog
from metao.cli import main
from metao.core import (
    ExecutionRequest,
    ExecutionResult,
    ExecutionStatus,
    HealthReport,
    HealthStatus,
    OrchestratorDescriptor,
    OrchestratorRegistry,
)
from metao.operator import MissionOperator


class Runtime:
    def __init__(self) -> None:
        self._descriptor = OrchestratorDescriptor("cli-runtime", "v1", frozenset({"workflow"}))
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
            {"result": "cli-done", "mission_id": request.mission.mission_id},
        )

    def cancel(self, execution_id: str) -> None:
        pass


class MetaOCliV1Tests(unittest.TestCase):
    def setUp(self) -> None:
        self.tempdir = tempfile.TemporaryDirectory()
        self.root = Path(self.tempdir.name)
        self.db = self.root / "metao.db"
        self.runtime = Runtime()
        registry = OrchestratorRegistry()
        registry.register(self.runtime)
        catalog = OrchestratorCatalog(registry)
        catalog.register(
            "cli-runtime",
            normalizer=normalize_evidence,
            cost=0.01,
            latency_ms=10.0,
            success_rate=0.99,
            quality=0.99,
            reliability=0.99,
        )

        module = ModuleType("metao_test_factory")

        def create_operator(*, store):
            return MissionOperator(registry=registry, catalog=catalog, store=store)

        module.create_operator = create_operator
        sys.modules["metao_test_factory"] = module
        self.factory = "metao_test_factory:create_operator"

    def tearDown(self) -> None:
        sys.modules.pop("metao_test_factory", None)
        self.tempdir.cleanup()

    def _mission_file(self, mission_id: str, *, require_human: bool = False) -> Path:
        path = self.root / f"{mission_id}.json"
        path.write_text(
            json.dumps(
                {
                    "mission": {
                        "mission_id": mission_id,
                        "objective": "exercise cli",
                        "required_capabilities": ["workflow"],
                    },
                    "policy": {
                        "policy_bundle_id": "policy-1",
                        "allowed": True,
                        "require_human": require_human,
                        "reason": "cli approval" if require_human else "",
                    },
                    "budget": {
                        "money_limit": 2.0,
                        "token_limit": 1000,
                        "wall_time_limit_s": 60,
                        "verifier_attempt_limit": 3,
                    },
                    "acceptance_context": {
                        "subject_id": "subject-1",
                        "subject_state_id": "state-1",
                        "verification_context_id": "verify-1",
                        "policy_bundle_id": "policy-1",
                        "required_obligations": ["execution_result"],
                    },
                    "execution_id_prefix": f"{mission_id}-exec",
                    "now_epoch": 100,
                    "max_attempts": 2,
                }
            ),
            encoding="utf-8",
        )
        return path

    def _call(self, *args: str):
        stdout = StringIO()
        stderr = StringIO()
        code = main(["--db", str(self.db), *args], stdout=stdout, stderr=stderr)
        out = json.loads(stdout.getvalue()) if stdout.getvalue() else None
        err = json.loads(stderr.getvalue()) if stderr.getvalue() else None
        return code, out, err

    def test_run_persists_accepted_mission_and_returns_machine_readable_json(self):
        code, out, err = self._call("run", str(self._mission_file("cli-run")), "--factory", self.factory)
        self.assertEqual(code, 0)
        self.assertIsNone(err)
        self.assertEqual(out["mission_id"], "cli-run")
        self.assertEqual(out["status"], "ACCEPTED")
        self.assertEqual(out["orchestrator_id"], "cli-runtime")
        self.assertEqual(self.runtime.calls, 1)

    def test_status_and_inspect_need_only_sqlite_not_runtime_factory(self):
        self._call("run", str(self._mission_file("cli-inspect")), "--factory", self.factory)
        code, status, _ = self._call("status", "cli-inspect")
        self.assertEqual(code, 0)
        self.assertEqual(status, {"mission_id": "cli-inspect", "revision": 1, "status": "ACCEPTED"})

        code, detail, _ = self._call("inspect", "cli-inspect")
        self.assertEqual(code, 0)
        self.assertEqual(detail["execution"]["output"]["result"], "cli-done")
        self.assertEqual(detail["history"][-1], "ACCEPTED")
        self.assertEqual(detail["attempts"][0]["execution_id"], "cli-inspect-exec-1")

    def test_list_is_deterministic_and_machine_readable(self):
        self._call("run", str(self._mission_file("z-mission")), "--factory", self.factory)
        self._call("run", str(self._mission_file("a-mission")), "--factory", self.factory)
        code, items, _ = self._call("list")
        self.assertEqual(code, 0)
        self.assertEqual([item["mission_id"] for item in items], ["a-mission", "z-mission"])

    def test_cli_human_approval_flow_spans_separate_invocations(self):
        code, waiting, _ = self._call(
            "run",
            str(self._mission_file("cli-approval", require_human=True)),
            "--factory",
            self.factory,
        )
        self.assertEqual(code, 0)
        self.assertEqual(waiting["status"], "WAITING_APPROVAL")
        self.assertEqual(self.runtime.calls, 0)

        code, approved, _ = self._call(
            "approve",
            "cli-approval",
            "--approver",
            "igor",
            "--factory",
            self.factory,
        )
        self.assertEqual(code, 0)
        self.assertEqual(approved["status"], "WAITING_APPROVAL")
        self.assertEqual(approved["revision"], 2)
        self.assertEqual(self.runtime.calls, 0)

        code, resumed, _ = self._call(
            "resume",
            "cli-approval",
            "--factory",
            self.factory,
            "--now-epoch",
            "101",
        )
        self.assertEqual(code, 0)
        self.assertEqual(resumed["status"], "ACCEPTED")
        self.assertEqual(resumed["revision"], 3)
        self.assertEqual(self.runtime.calls, 1)

        _, detail, _ = self._call("inspect", "cli-approval")
        self.assertTrue(detail["approval_record"]["approved"])
        self.assertEqual(detail["approval_record"]["approver_id"], "igor")
        self.assertIn("WAITING_APPROVAL", detail["history"])

    def test_cli_denial_blocks_and_never_executes_runtime(self):
        self._call(
            "run",
            str(self._mission_file("cli-deny", require_human=True)),
            "--factory",
            self.factory,
        )
        code, denied, _ = self._call(
            "approve",
            "cli-deny",
            "--approver",
            "igor",
            "--deny",
            "--factory",
            self.factory,
        )
        self.assertEqual(code, 0)
        self.assertEqual(denied["status"], "BLOCKED")
        self.assertEqual(self.runtime.calls, 0)

    def test_invalid_mission_json_fails_with_structured_error(self):
        path = self.root / "broken.json"
        path.write_text("{broken", encoding="utf-8")
        code, out, err = self._call("run", str(path), "--factory", self.factory)
        self.assertEqual(code, 2)
        self.assertIsNone(out)
        self.assertEqual(err["error"], "CLIInputError")
        self.assertIn("invalid mission JSON", err["message"])

    def test_unknown_mission_status_fails_with_structured_error(self):
        code, out, err = self._call("status", "missing")
        self.assertEqual(code, 2)
        self.assertIsNone(out)
        self.assertEqual(err["error"], "MissionNotFound")

    def test_bad_factory_contract_fails_closed(self):
        bad = ModuleType("metao_bad_factory")
        bad.make = lambda **kwargs: object()
        sys.modules["metao_bad_factory"] = bad
        try:
            code, _, err = self._call(
                "run",
                str(self._mission_file("bad-factory")),
                "--factory",
                "metao_bad_factory:make",
            )
        finally:
            sys.modules.pop("metao_bad_factory", None)
        self.assertEqual(code, 2)
        self.assertEqual(err["error"], "CLIInputError")
        self.assertEqual(self.runtime.calls, 0)

    def test_console_script_is_packaged(self):
        root = Path(__file__).resolve().parents[2]
        pyproject = (root / "pyproject.toml").read_text(encoding="utf-8")
        self.assertIn('[project.scripts]', pyproject)
        self.assertIn('metao = "metao.entrypoint:main"', pyproject)

    def test_installed_console_script_is_executable(self):
        executable = shutil.which("metao")
        if executable is None:
            scripts_dir = Path(sys.executable).resolve().parent
            executable = next(
                (
                    str(candidate)
                    for candidate in (
                        scripts_dir / "metao.exe",
                        scripts_dir / "metao",
                    )
                    if candidate.is_file()
                ),
                None,
            )
        self.assertIsNotNone(executable, "metao console script is not installed in the active environment")
        completed = subprocess.run(
            [executable, "--help"],
            capture_output=True,
            text=True,
            check=False,
        )
        self.assertEqual(completed.returncode, 0, completed.stderr)
        self.assertIn("metaO control-plane operator CLI", completed.stdout)
        self.assertIn("run", completed.stdout)
        self.assertIn("status", completed.stdout)
        self.assertIn("approve", completed.stdout)
        self.assertIn("resume", completed.stdout)

    def test_cli_remains_orchestrator_sdk_neutral(self):
        root = Path(__file__).resolve().parents[2]
        source = (root / "src" / "metao" / "cli.py").read_text(encoding="utf-8").lower()
        for forbidden in ("import langgraph", "from langgraph", "import crewai", "from crewai"):
            self.assertNotIn(forbidden, source)


if __name__ == "__main__":
    unittest.main(verbosity=2)
