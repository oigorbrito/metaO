"""Fail-closed normalizers for the initial benchmark evidence families.

The profiles pin upstream benchmark subjects independently from any observed
result.  A normalized record remains advisory evidence and never grants
qualification or Acceptance authority.
"""

from __future__ import annotations

from dataclasses import dataclass
from math import isfinite
from typing import Any, Mapping

from .benchmark_evidence import (
    BenchmarkEvidence,
    BenchmarkEvidenceSource,
    BenchmarkMetric,
)


@dataclass(frozen=True, slots=True)
class BenchmarkFamilyProfile:
    family_id: str
    upstream_repository: str
    upstream_revision: str
    benchmark_version: str
    metric_name: str
    default_task_set: str

    @property
    def subject_pin(self) -> str:
        return f"{self.upstream_repository}@{self.upstream_revision}"


BENCHMARK_FAMILY_PROFILES: Mapping[str, BenchmarkFamilyProfile] = {
    "swe-bench": BenchmarkFamilyProfile(
        family_id="swe-bench",
        upstream_repository="princeton-nlp/SWE-bench",
        upstream_revision="02e7a74ffd0b707aab73d203fe87bdc7c76afc8e",
        benchmark_version="pinned-revision",
        metric_name="resolved_rate",
        default_task_set="verified",
    ),
    "terminal-bench-core": BenchmarkFamilyProfile(
        family_id="terminal-bench-core",
        upstream_repository="laude-institute/terminal-bench",
        upstream_revision="d28711d0da2675d0bb1d56de45ae5df6082438a3",
        benchmark_version="0.1.1",
        metric_name="pass_rate",
        default_task_set="terminal-bench-core",
    ),
    "agentgovbench": BenchmarkFamilyProfile(
        family_id="agentgovbench",
        upstream_repository="agentic-control-plane/agentgovbench",
        upstream_revision="e0ce93ae175376d7847c69a64d0c36bdfa6ca717",
        benchmark_version="0.2",
        metric_name="pass_rate",
        default_task_set="all-scenarios",
    ),
}


def _ratio(value: Any, *, field: str) -> float:
    try:
        result = float(value)
    except (TypeError, ValueError) as exc:
        raise ValueError(f"benchmark result requires numeric {field}") from exc
    if not isfinite(result) or not 0.0 <= result <= 1.0:
        raise ValueError(f"benchmark result {field} must be a finite ratio")
    return result


def _extract_ratio(profile: BenchmarkFamilyProfile, payload: Mapping[str, Any]) -> float:
    if profile.family_id == "agentgovbench":
        aggregate = payload.get("aggregate")
        if not isinstance(aggregate, Mapping):
            raise ValueError("agentgovbench result requires aggregate")
        if "pass_rate" in aggregate:
            return _ratio(aggregate["pass_rate"], field="aggregate.pass_rate")
        try:
            passed = float(aggregate["total_passed"])
            total = float(aggregate["total_scenarios"])
        except (KeyError, TypeError, ValueError) as exc:
            raise ValueError(
                "agentgovbench aggregate requires total_passed and total_scenarios"
            ) from exc
        if not isfinite(total) or total <= 0:
            raise ValueError("agentgovbench total_scenarios must be positive")
        return _ratio(passed / total, field="aggregate pass rate")

    for field in (profile.metric_name, "pass_rate", "resolved_rate", "accuracy"):
        if field in payload:
            return _ratio(payload[field], field=field)
    try:
        passed = float(payload["passed"] if "passed" in payload else payload["resolved"])
        total = float(payload["total"])
    except (KeyError, TypeError, ValueError) as exc:
        raise ValueError("benchmark result requires a supported aggregate metric") from exc
    if not isfinite(total) or total <= 0:
        raise ValueError("benchmark result total must be positive")
    return _ratio(passed / total, field="passed/total")


def ingest_benchmark_family_result(
    family: str,
    payload: Mapping[str, Any],
    *,
    evidence_id: str,
    task_set: str | None,
    executor_id: str,
    executor_version: str,
    harness_id: str,
    harness_version: str,
    model_id: str,
    provider_id: str,
    model_version: str,
    runtime_config_digest: str,
    tool_policy_digest: str,
    environment_id: str,
    observed_at_epoch: float,
    source: BenchmarkEvidenceSource,
    raw_result_ref: str,
) -> BenchmarkEvidence:
    try:
        profile = BENCHMARK_FAMILY_PROFILES[family]
    except KeyError as exc:
        raise ValueError(f"unsupported benchmark family: {family}") from exc
    if not isinstance(payload, Mapping):
        raise ValueError("benchmark result must be an object")
    selected_task_set = task_set or profile.default_task_set
    metric = BenchmarkMetric(
        profile.metric_name,
        _extract_ratio(profile, payload),
        "ratio",
    )
    return BenchmarkEvidence(
        evidence_id=evidence_id,
        benchmark_id=profile.family_id,
        benchmark_version=profile.benchmark_version,
        task_set=selected_task_set,
        executor_id=executor_id,
        executor_version=executor_version,
        harness_id=harness_id,
        harness_version=harness_version,
        model_id=model_id,
        provider_id=provider_id,
        model_version=model_version,
        runtime_config_digest=runtime_config_digest,
        tool_policy_digest=tool_policy_digest,
        environment_id=environment_id,
        observed_at_epoch=observed_at_epoch,
        source=source,
        raw_result_ref=raw_result_ref,
        metrics=(metric,),
    )


__all__ = [
    "BENCHMARK_FAMILY_PROFILES",
    "BenchmarkFamilyProfile",
    "ingest_benchmark_family_result",
]
