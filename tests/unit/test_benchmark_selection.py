from __future__ import annotations

from pathlib import Path
import tempfile
import unittest

from metao.acceptance import AcceptanceContext, EvidenceEnvelope
from metao.benchmark_evidence import (
    BenchmarkEvidence,
    BenchmarkEvidenceSource,
    BenchmarkMetric,
)
from metao.benchmark_routing import BenchmarkRoutingPolicy
from metao.benchmark_selection import BenchmarkSelectionPolicy
from metao.core import (
    ExecutionRequest,
    ExecutionResult,
    ExecutionStatus,
    HealthReport,
    HealthStatus,
    Mission,
    OrchestratorDescriptor,
    OrchestratorRegistry,
)
from metao.governance import AcceptanceBudget, evaluate_policy
from metao.mission_store import InMemoryMissionStore
from metao.operator import MissionOperator
from metao.benchmark_store import SQLiteBenchmarkEvidenceStore
from metao.routing_decision import SQLiteRoutingDecisionStore
from metao.strategy import OrchestratorPoolState, OrchestratorStatus


class Runtime:
    def __init__(self, orchestrator_id: str) -> None:
        self._descriptor = OrchestratorDescriptor(
            orchestrator_id,
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


def benchmark(executor_id: str, *, evidence_id: str, value: float) -> BenchmarkEvidence:
    return BenchmarkEvidence(
        evidence_id=evidence_id,
        benchmark_id="software-engineering",
        benchmark_version="v1",
        task_set="verified",
        executor_id=executor_id,
        executor_version="1.0",
        harness_id="harness",
        harness_version="1.0",
        model_id="model",
        provider_id="provider",
        model_version="2026-09",
        runtime_config_digest=f"runtime-{executor_id}",
        tool_policy_digest="tool-policy",
        environment_id="test",
        observed_at_epoch=100.0,
        source=BenchmarkEvidenceSource.METAO_REPRODUCED,
        raw_result_ref=f"artifact://{evidence_id}",
        metrics=(BenchmarkMetric("resolved_rate", value, "ratio"),),
    )


class BenchmarkSelectionPolicyIntegrationTests(unittest.TestCase):
    def test_operator_uses_durable_benchmark_evidence_to_reorder_routable_candidates(self):
        primary = Runtime("primary")
        fallback = Runtime("fallback")
        registry = OrchestratorRegistry()
        registry.register(primary)
        registry.register(fallback)

        with tempfile.TemporaryDirectory() as temp:
            evidence_store = SQLiteBenchmarkEvidenceStore(Path(temp) / "benchmarks.db")
            evidence_store.record(
                benchmark("primary", evidence_id="primary-bench", value=0.1)
            )
            evidence_store.record(
                benchmark("fallback", evidence_id="fallback-bench", value=0.95)
            )
            decision_store = SQLiteRoutingDecisionStore(Path(temp) / "benchmarks.db")
            selection_policy = BenchmarkSelectionPolicy(
                evidence_store,
                BenchmarkRoutingPolicy(
                    benchmark_id="software-engineering",
                    benchmark_version="v1",
                    task_set="verified",
                    metric_name="resolved_rate",
                    base_weight=0.1,
                    benchmark_weight=0.9,
                    max_age_seconds=60.0,
                ),
                decision_store=decision_store,
            )

            operator = MissionOperator(
                registry=registry,
                store=InMemoryMissionStore(),
                pools=(
                    OrchestratorPoolState(
                        "primary",
                        OrchestratorStatus.HEALTHY,
                        frozenset({"workflow"}),
                        success_rate=0.99,
                        quality=0.99,
                        latency_ms=10.0,
                        cost=0.01,
                    ),
                    OrchestratorPoolState(
                        "fallback",
                        OrchestratorStatus.HEALTHY,
                        frozenset({"workflow"}),
                        success_rate=0.8,
                        quality=0.8,
                        latency_ms=100.0,
                        cost=0.1,
                    ),
                ),
                normalizers={"primary": normalizer, "fallback": normalizer},
                selection_policy=selection_policy,
            )

            outcome = operator.run(
                Mission("mission-benchmark-routing", "route empirically", frozenset({"workflow"})),
                policy=evaluate_policy(policy_bundle_id="policy", allowed=True),
                budget=AcceptanceBudget(10.0, 1000, 60.0, 3),
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

        self.assertEqual(outcome.orchestrator_id, "fallback")
        self.assertEqual(primary.calls, 0)
        self.assertEqual(fallback.calls, 1)
        receipts = decision_store.history("mission-benchmark-routing")
        self.assertEqual(len(receipts), 1)
        self.assertEqual(receipts[0].selected_executor_id, "fallback")
        self.assertEqual(tuple(item.executor_id for item in receipts[0].candidates), ("fallback", "primary"))
        self.assertEqual(receipts[0].candidates[0].evidence_id, "fallback-bench")
        self.assertEqual(receipts[0].authority_scope, "routing-audit-only")

    def test_selection_policy_requires_explicit_mission_time(self):
        with tempfile.TemporaryDirectory() as temp:
            policy = BenchmarkSelectionPolicy(
                SQLiteBenchmarkEvidenceStore(Path(temp) / "benchmarks.db"),
                BenchmarkRoutingPolicy(
                    benchmark_id="software-engineering",
                    benchmark_version="v1",
                    task_set="verified",
                    metric_name="resolved_rate",
                ),
            )
            with self.assertRaisesRegex(ValueError, "explicit mission time"):
                policy((), None)


if __name__ == "__main__":
    unittest.main(verbosity=2)
