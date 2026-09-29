from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from metao.benchmark_evidence import (
    BenchmarkEvidenceSource,
    benchmark_evidence_from_record,
    benchmark_evidence_to_record,
)
from metao.benchmark_ingestion import ingest_benchmark_family_result
from metao.benchmark_qualification import (
    BenchmarkQualificationPolicy,
    qualify_benchmark_evidence,
)
from metao.executor_market import QualificationOutcome


def identity(evidence_id: str, *, observed_at_epoch: float = 100.0):
    return {
        "evidence_id": evidence_id,
        "task_set": None,
        "executor_id": "executor-a",
        "executor_version": "1.0",
        "harness_id": "harness-a",
        "harness_version": "2.0",
        "model_id": "model-a",
        "provider_id": "provider-a",
        "model_version": "2026-09",
        "runtime_config_digest": "runtime-config-sha256",
        "tool_policy_digest": "tool-policy-sha256",
        "environment_id": "linux-x86_64",
        "observed_at_epoch": observed_at_epoch,
        "source": BenchmarkEvidenceSource.METAO_REPRODUCED,
        "raw_result_ref": f"artifact://{evidence_id}",
    }


def evidence_set(*, observed_at_epoch: float = 100.0):
    return (
        ingest_benchmark_family_result(
            "swe-bench",
            {"resolved": 9, "total": 10},
            **identity("swe", observed_at_epoch=observed_at_epoch),
        ),
        ingest_benchmark_family_result(
            "terminal-bench-core",
            {"pass_rate": 0.8},
            **identity("terminal", observed_at_epoch=observed_at_epoch),
        ),
        ingest_benchmark_family_result(
            "agentgovbench",
            {"aggregate": {"pass_rate": 0.75}},
            **identity("gov", observed_at_epoch=observed_at_epoch),
        ),
    )


def policy():
    return BenchmarkQualificationPolicy(
        policy_version="benchmark-policy-v1",
        required_families=("swe-bench", "terminal-bench-core", "agentgovbench"),
        minimum_scores={
            "swe-bench": 0.8,
            "terminal-bench-core": 0.7,
            "agentgovbench": 0.7,
        },
        max_age_seconds=50.0,
    )


class BenchmarkQualificationPipelineTests(unittest.TestCase):
    def test_three_pinned_families_qualify_deterministically(self):
        first = qualify_benchmark_evidence(evidence_set(), policy(), now_epoch=120.0)
        second = qualify_benchmark_evidence(evidence_set(), policy(), now_epoch=120.0)
        self.assertEqual(first, second)
        self.assertIs(first.outcome, QualificationOutcome.QUALIFIED)

    def test_missing_or_stale_evidence_restricts_executor(self):
        incomplete = qualify_benchmark_evidence(
            evidence_set()[:2], policy(), now_epoch=120.0
        )
        stale = qualify_benchmark_evidence(
            evidence_set(observed_at_epoch=10.0), policy(), now_epoch=120.0
        )
        self.assertIs(incomplete.outcome, QualificationOutcome.QUALIFIED_RESTRICTED)
        self.assertIs(stale.outcome, QualificationOutcome.QUALIFIED_RESTRICTED)

    def test_below_threshold_is_unqualified(self):
        records = list(evidence_set())
        records[1] = ingest_benchmark_family_result(
            "terminal-bench-core",
            {"pass_rate": 0.2},
            **identity("terminal-low"),
        )
        result = qualify_benchmark_evidence(records, policy(), now_epoch=120.0)
        self.assertIs(result.outcome, QualificationOutcome.UNQUALIFIED)

    def test_security_or_policy_hard_gate_cannot_be_overridden_by_benchmark(self):
        result = qualify_benchmark_evidence(
            evidence_set(), policy(), now_epoch=120.0, hard_gate_blocked=True
        )
        self.assertIs(result.outcome, QualificationOutcome.BLOCKED)

    def test_mixed_executor_identity_fails_closed(self):
        records = list(evidence_set())
        records[2] = ingest_benchmark_family_result(
            "agentgovbench",
            {"aggregate": {"pass_rate": 1.0}},
            **{**identity("foreign"), "executor_id": "executor-b"},
        )
        result = qualify_benchmark_evidence(records, policy(), now_epoch=120.0)
        self.assertIs(result.outcome, QualificationOutcome.BLOCKED)

    def test_persisted_evidence_reproduces_same_decision_and_preserves_raw_ref(self):
        records = evidence_set()
        with tempfile.TemporaryDirectory() as temp:
            path = Path(temp) / "benchmark-evidence.json"
            payload = [benchmark_evidence_to_record(item) for item in records]
            path.write_text(json.dumps(payload, sort_keys=True), encoding="utf-8")
            persisted = json.loads(path.read_text(encoding="utf-8"))

        replay = tuple(benchmark_evidence_from_record(item) for item in persisted)
        self.assertEqual(
            qualify_benchmark_evidence(records, policy(), now_epoch=120.0),
            qualify_benchmark_evidence(replay, policy(), now_epoch=120.0),
        )
        self.assertEqual(replay[0].raw_result_ref, "artifact://swe")


if __name__ == "__main__":
    unittest.main(verbosity=2)
