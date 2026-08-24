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

from metao.acceptance import AcceptanceContext, AcceptanceDecision
from metao.adapters.langgraph import normalize_evidence
from metao.cli import main
from metao.core import (
    ExecutionRequest,
    ExecutionResult,
    ExecutionStatus,
    HealthReport,
    HealthStatus,
    Mission,
    OrchestratorDescriptor,
)
from metao.governance import AcceptanceBudget, evaluate_policy
from metao.mission_store import InMemoryMissionStore
from metao.runtime_factory import (
    RUNTIME_CATALOG_ENV,
    RuntimeCatalogConfigError,
    RuntimePlugin,
    create_operator,
    create_operator_from_catalog,
)


class Runtime:
    def __init__(self, orchestrator_id: str, status: ExecutionStatus = ExecutionStatus.SUCCEEDED):
        self._descriptor = OrchestratorDescriptor(
            orchestrator_id,
            "v1",
            frozenset({"workflow"}),
        )
        self.status = status
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
            self.status,
            {"result": f"done:{self.descriptor.orchestrator_id}"},
            error="runtime failure" if self.status is ExecutionStatus.FAILED else "",
        )

    def cancel(self, execution_id: str) -> None:
        pass


def manifest(path: Path, entries: list[dict]) -> Path:
    path.write_text(json.dumps({"runtimes": entries}), encoding="utf-8")
    return path


def entry(factory: str, *, cost: float = 0.01, quality: float = 0.9) -> dict:
    return {
        "factory": factory,
        "cost": cost,
        "latency_ms": 10.0,
        "success_rate": quality,
        "quality": quality,
        "reliability": quality,
        "trust_profile": "local-test",
    }


class DeclarativeRuntimeCatalogV1Tests(unittest.TestCase):
    def setUp(self) -> None:
        self.module_name = "metao_wu02_runtime_plugins"
        self.module = ModuleType(self.module_name)
        sys.modules[self.module_name] = self.module
        self.context = AcceptanceContext(
            "subject-wu02",
            "state-wu02",
            "verify-wu02",
            "policy-wu02",
            frozenset({"execution_result"}),
        )
        self.policy = evaluate_policy(policy_bundle_id="policy-wu02", allowed=True)
        self.budget = AcceptanceBudget(10.0, 10_000, 60.0, 4)

    def tearDown(self) -> None:
        sys.modules.pop(self.module_name, None)

    def plugin(self, name: str, runtime: Runtime) -> str:
        setattr(self.module, name, lambda runtime=runtime: RuntimePlugin(runtime, normalize_evidence))
        return f"{self.module_name}:{name}"

    def test_manifest_builds_multi_runtime_operator_and_strategy_selects_best(self):
        preferred = Runtime("preferred")
        alternate = Runtime("alternate")
        with tempfile.TemporaryDirectory() as temp:
            path = manifest(
                Path(temp) / "runtimes.json",
                [
                    entry(self.plugin("preferred", preferred), cost=0.01, quality=0.99),
                    entry(self.plugin("alternate", alternate), cost=2.0, quality=0.20),
                ],
            )
            operator = create_operator_from_catalog(path, store=InMemoryMissionStore())
            outcome = operator.run(
                Mission("wu02-select", "select declared runtime", frozenset({"workflow"})),
                policy=self.policy,
                budget=self.budget,
                acceptance_context=self.context,
                max_attempts=2,
            )
        self.assertEqual(outcome.state.status.value, "ACCEPTED")
        self.assertEqual(outcome.orchestrator_id, "preferred")
        self.assertEqual(preferred.calls, 1)
        self.assertEqual(alternate.calls, 0)

    def test_manifest_supports_failover_across_declared_plugins(self):
        primary = Runtime("primary", ExecutionStatus.FAILED)
        fallback = Runtime("fallback")
        with tempfile.TemporaryDirectory() as temp:
            path = manifest(
                Path(temp) / "runtimes.json",
                [
                    entry(self.plugin("primary", primary), cost=0.01, quality=0.99),
                    entry(self.plugin("fallback", fallback), cost=3.0, quality=0.10),
                ],
            )
            operator = create_operator_from_catalog(path, store=InMemoryMissionStore())
            outcome = operator.run(
                Mission("wu02-failover", "fail over declared runtime", frozenset({"workflow"})),
                policy=self.policy,
                budget=self.budget,
                acceptance_context=self.context,
                max_attempts=2,
            )
        self.assertEqual(outcome.state.status.value, "ACCEPTED")
        self.assertEqual(outcome.attempted_orchestrators, ("primary", "fallback"))
        self.assertEqual(primary.calls, 1)
        self.assertEqual(fallback.calls, 1)

    def test_environment_factory_is_directly_compatible_with_cli_factory_contract(self):
        runtime = Runtime("cli-runtime")
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            path = manifest(root / "runtimes.json", [entry(self.plugin("cli", runtime))])
            with patch.dict(os.environ, {RUNTIME_CATALOG_ENV: str(path)}):
                operator = create_operator(store=InMemoryMissionStore())
            outcome = operator.run(
                Mission("wu02-env", "environment factory", frozenset({"workflow"})),
                policy=self.policy,
                budget=self.budget,
                acceptance_context=self.context,
            )
        self.assertEqual(outcome.acceptance.decision, AcceptanceDecision.ACCEPT)

    def test_cli_run_uses_declarative_catalog_without_custom_operator_factory(self):
        runtime = Runtime("cli-runtime")
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            catalog_path = manifest(root / "runtimes.json", [entry(self.plugin("cli", runtime))])
            mission_path = root / "mission.json"
            mission_path.write_text(
                json.dumps(
                    {
                        "mission": {
                            "mission_id": "wu02-cli",
                            "objective": "run declarative catalog",
                            "required_capabilities": ["workflow"],
                        },
                        "policy": {"policy_bundle_id": "policy-wu02", "allowed": True},
                        "budget": {
                            "money_limit": 10,
                            "token_limit": 10000,
                            "wall_time_limit_s": 60,
                            "verifier_attempt_limit": 4,
                        },
                        "acceptance_context": {
                            "subject_id": "subject-wu02",
                            "subject_state_id": "state-wu02",
                            "verification_context_id": "verify-wu02",
                            "policy_bundle_id": "policy-wu02",
                            "required_obligations": ["execution_result"],
                        },
                    }
                ),
                encoding="utf-8",
            )
            stdout, stderr = StringIO(), StringIO()
            with patch.dict(os.environ, {RUNTIME_CATALOG_ENV: str(catalog_path)}):
                code = main(
                    [
                        "--db",
                        str(root / "metao.db"),
                        "run",
                        str(mission_path),
                        "--factory",
                        "metao.runtime_factory:create_operator",
                    ],
                    stdout=stdout,
                    stderr=stderr,
                )
        self.assertEqual(code, 0, stderr.getvalue())
        payload = json.loads(stdout.getvalue())
        self.assertEqual(payload["status"], "ACCEPTED")
        self.assertEqual(payload["orchestrator_id"], "cli-runtime")
        self.assertEqual(runtime.calls, 1)

    def test_missing_environment_path_and_bad_json_fail_closed(self):
        with patch.dict(os.environ, {}, clear=True):
            with self.assertRaises(RuntimeCatalogConfigError):
                create_operator(store=InMemoryMissionStore())
        with tempfile.TemporaryDirectory() as temp:
            path = Path(temp) / "bad.json"
            path.write_text("not-json", encoding="utf-8")
            with self.assertRaises(RuntimeCatalogConfigError):
                create_operator_from_catalog(path, store=InMemoryMissionStore())

    def test_empty_manifest_and_invalid_profile_fail_closed(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            empty = manifest(root / "empty.json", [])
            with self.assertRaises(RuntimeCatalogConfigError):
                create_operator_from_catalog(empty, store=InMemoryMissionStore())

            runtime = Runtime("invalid-profile")
            invalid = manifest(
                root / "invalid.json",
                [entry(self.plugin("invalid", runtime), quality=1.5)],
            )
            with self.assertRaises(RuntimeCatalogConfigError):
                create_operator_from_catalog(invalid, store=InMemoryMissionStore())

    def test_factory_must_return_runtime_plugin(self):
        setattr(self.module, "bad", lambda: object())
        with tempfile.TemporaryDirectory() as temp:
            path = manifest(Path(temp) / "runtimes.json", [entry(f"{self.module_name}:bad")])
            with self.assertRaises(RuntimeCatalogConfigError):
                create_operator_from_catalog(path, store=InMemoryMissionStore())

    def test_factory_module_remains_orchestrator_sdk_neutral(self):
        root = Path(__file__).resolve().parents[2]
        source = (root / "src/metao/runtime_factory.py").read_text(encoding="utf-8").lower()
        for forbidden in ("import langgraph", "from langgraph", "import crewai", "from crewai"):
            self.assertNotIn(forbidden, source)


if __name__ == "__main__":
    unittest.main(verbosity=2)
