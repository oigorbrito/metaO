from __future__ import annotations

import json
import os
from pathlib import Path
import sys
import tempfile
from types import ModuleType
import unittest
from unittest.mock import patch

from metao.acceptance import AcceptanceContext, EvidenceEnvelope
from metao.benchmark_evidence import BenchmarkEvidence, BenchmarkEvidenceSource, BenchmarkMetric
from metao.benchmark_store import SQLiteBenchmarkEvidenceStore
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
from metao.observed_performance import (
    ObservedPerformanceEvidence,
    ObservedPerformanceMetric,
    ObservedPerformanceSource,
)
from metao.observed_performance_store import SQLiteObservedPerformanceStore
from metao.runtime_factory import (
    BENCHMARK_EVIDENCE_DB_ENV,
    BENCHMARK_ROUTING_POLICY_ENV,
    OBSERVED_PERFORMANCE_DB_ENV,
    RUNTIME_CATALOG_ENV,
    RuntimePlugin,
    create_operator,
)


class Runtime:
    def __init__(self, runtime_id: str) -> None:
        self._descriptor = OrchestratorDescriptor(
            runtime_id,
            "1.0",
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
        return None


def normalizer(*, request, orchestrator_id, adapter_version, output, attempt_id):
    return EvidenceEnvelope(
        evidence_id=f"{request.execution_id}:{attempt_id}",
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
        provenance_root="local-test",
        authority_id=request.context["authority_id"],
        passed=True,
        created_at_epoch=request.context["created_at_epoch"],
    )


def benchmark(runtime_id: str, score: float) -> BenchmarkEvidence:
    return BenchmarkEvidence(
        evidence_id=f"bench-{runtime_id}",
        benchmark_id="matrix",
        benchmark_version="v1",
        task_set="coding",
        executor_id=runtime_id,
        executor_version="1.0",
        harness_id="harness",
        harness_version="1",
        model_id="model",
        provider_id="provider",
        model_version="1",
        runtime_config_digest=f"runtime-{runtime_id}",
        tool_policy_digest="tool-policy",
        environment_id="test",
        observed_at_epoch=100.0,
        source=BenchmarkEvidenceSource.METAO_REPRODUCED,
        raw_result_ref=f"artifact://bench-{runtime_id}",
        metrics=(BenchmarkMetric("success_rate", score, "ratio"),),
    )


def observed(runtime_id: str, evidence_id: str, score: float, at: float) -> ObservedPerformanceEvidence:
    return ObservedPerformanceEvidence(
        evidence_id=evidence_id,
        executor_id=runtime_id,
        executor_version="1.0",
        task_family="coding",
        runtime_config_digest=f"runtime-{runtime_id}",
        tool_policy_digest="tool-policy",
        environment_id="test",
        observed_at_epoch=at,
        source=ObservedPerformanceSource.METAO_EXECUTION,
        raw_result_ref=f"artifact://{evidence_id}",
        sample_count=1,
        metrics=(ObservedPerformanceMetric("success_rate", score, "ratio"),),
    )


class ObservedPerformanceRuntimeFactoryTests(unittest.TestCase):
    def test_factory_routes_real_mission_using_benchmark_plus_observed_evidence(self):
        module_name = "metao_observed_routing_test_plugins"
        module = ModuleType(module_name)
        alpha = Runtime("alpha")
        beta = Runtime("beta")
        module.alpha = lambda: RuntimePlugin(alpha, normalizer)
        module.beta = lambda: RuntimePlugin(beta, normalizer)
        sys.modules[module_name] = module

        try:
            with tempfile.TemporaryDirectory() as temp:
                root = Path(temp)
                catalog = root / "runtimes.json"
                benchmark_db = root / "benchmark.db"
                observed_db = root / "observed.db"
                catalog.write_text(
                    json.dumps(
                        {
                            "runtimes": [
                                {
                                    "factory": f"{module_name}:alpha",
                                    "cost": 0.1,
                                    "latency_ms": 100,
                                    "success_rate": 0.8,
                                    "quality": 0.8,
                                    "reliability": 0.8,
                                },
                                {
                                    "factory": f"{module_name}:beta",
                                    "cost": 0.1,
                                    "latency_ms": 100,
                                    "success_rate": 0.8,
                                    "quality": 0.8,
                                    "reliability": 0.8,
                                },
                            ]
                        }
                    ),
                    encoding="utf-8",
                )

                benchmark_store = SQLiteBenchmarkEvidenceStore(benchmark_db)
                benchmark_store.record(benchmark("alpha", 0.95))
                benchmark_store.record(benchmark("beta", 0.70))

                observed_store = SQLiteObservedPerformanceStore(observed_db)
                observed_store.record(observed("alpha", "obs-alpha-1", 0.1, 108.0))
                observed_store.record(observed("alpha", "obs-alpha-2", 0.2, 109.0))
                observed_store.record(observed("beta", "obs-beta-1", 0.9, 108.0))
                observed_store.record(observed("beta", "obs-beta-2", 1.0, 110.0))

                routing_policy = {
                    "families": {
                        "coding": {
                            "benchmark_id": "matrix",
                            "benchmark_version": "v1",
                            "task_set": "coding",
                            "metric_name": "success_rate",
                            "base_weight": 0.1,
                            "benchmark_weight": 0.9,
                            "max_age_seconds": 60,
                            "observed": {
                                "metric_name": "success_rate",
                                "prior_weight": 0.2,
                                "observed_weight": 0.8,
                                "max_age_seconds": 60,
                                "min_samples": 2,
                                "missing_evidence": "prior_only",
                            },
                        }
                    }
                }

                with patch.dict(
                    os.environ,
                    {
                        RUNTIME_CATALOG_ENV: str(catalog),
                        BENCHMARK_EVIDENCE_DB_ENV: str(benchmark_db),
                        OBSERVED_PERFORMANCE_DB_ENV: str(observed_db),
                        BENCHMARK_ROUTING_POLICY_ENV: json.dumps(routing_policy),
                    },
                    clear=False,
                ):
                    operator = create_operator(store=InMemoryMissionStore())
                    outcome = operator.run(
                        Mission(
                            "empirical-routing",
                            "route using observed performance",
                            frozenset({"workflow"}),
                            task_family="coding",
                        ),
                        policy=evaluate_policy(policy_bundle_id="policy", allowed=True),
                        budget=AcceptanceBudget(10.0, 1000, 60.0, 1),
                        acceptance_context=AcceptanceContext(
                            "subject",
                            "state",
                            "verify",
                            "policy",
                            frozenset({"execution_result"}),
                        ),
                        now_epoch=120.0,
                        max_attempts=1,
                    )

                self.assertEqual(outcome.orchestrator_id, "beta")
                self.assertEqual(alpha.calls, 0)
                self.assertEqual(beta.calls, 1)
        finally:
            sys.modules.pop(module_name, None)

    def test_empirical_routing_requires_observed_store(self):
        module_name = "metao_observed_routing_missing_store_plugins"
        module = ModuleType(module_name)
        runtime = Runtime("alpha")
        module.alpha = lambda: RuntimePlugin(runtime, normalizer)
        sys.modules[module_name] = module

        try:
            with tempfile.TemporaryDirectory() as temp:
                root = Path(temp)
                catalog = root / "runtimes.json"
                benchmark_db = root / "benchmark.db"
                catalog.write_text(
                    json.dumps(
                        {
                            "runtimes": [
                                {
                                    "factory": f"{module_name}:alpha",
                                    "success_rate": 0.8,
                                    "quality": 0.8,
                                    "reliability": 0.8,
                                }
                            ]
                        }
                    ),
                    encoding="utf-8",
                )
                routing_policy = {
                    "families": {
                        "coding": {
                            "benchmark_id": "matrix",
                            "benchmark_version": "v1",
                            "task_set": "coding",
                            "metric_name": "success_rate",
                            "observed": {"metric_name": "success_rate"},
                        }
                    }
                }
                with patch.dict(
                    os.environ,
                    {
                        RUNTIME_CATALOG_ENV: str(catalog),
                        BENCHMARK_EVIDENCE_DB_ENV: str(benchmark_db),
                        BENCHMARK_ROUTING_POLICY_ENV: json.dumps(routing_policy),
                    },
                    clear=False,
                ):
                    os.environ.pop(OBSERVED_PERFORMANCE_DB_ENV, None)
                    with self.assertRaisesRegex(ValueError, "required for empirical routing"):
                        create_operator(store=InMemoryMissionStore())
        finally:
            sys.modules.pop(module_name, None)


if __name__ == "__main__":
    unittest.main(verbosity=2)
