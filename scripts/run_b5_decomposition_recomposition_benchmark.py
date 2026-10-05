"""B5 decomposition -> execution -> recomposition diagnostic benchmark.

Issue #744. This benchmark does not modify product semantics. It exercises the
current project-supervision surface and compares it with an explicit deterministic
recomposition baseline on the same fixture.
"""

from __future__ import annotations

import argparse
from dataclasses import fields
import json
from pathlib import Path

from metao.project_supervision import (
    ExecutorTarget,
    ProjectObjective,
    ProjectSupervisionResult,
    ProjectTraceKind,
    ProjectVerdict,
    RepositoryCheckpoint,
    WorkExecutionResult,
    WorkExecutionStatus,
    WorkGraph,
    WorkUnit,
    WorkVerificationResult,
    supervise_project,
)


EXPECTED_COMPOSITE = "AB"


class Planner:
    def plan(self, objective: ProjectObjective) -> WorkGraph:
        return WorkGraph(
            "metao",
            (
                WorkUnit("left", "produce the left fragment A"),
                WorkUnit(
                    "right",
                    "produce the right fragment B after accepted left",
                    ("left",),
                ),
            ),
        )

    def corrective_work(self, objective, failed_unit, verification, graph):
        return None


class Scheduler:
    def select(self, unit, *, excluded_executor_ids):
        if "executor-b5" in excluded_executor_ids:
            return None
        return ExecutorTarget("executor-b5", "provider-deterministic")


class Runner:
    def __init__(self, right_fragment: str) -> None:
        self.fragments = {"left": "A", "right": right_fragment}
        self.calls: list[str] = []

    def run(self, objective, unit, target, checkpoint):
        self.calls.append(unit.work_unit_id)
        fragment = self.fragments[unit.work_unit_id]
        state = f"state-{unit.work_unit_id}-{fragment}"
        return WorkExecutionResult(
            unit.work_unit_id,
            target.executor_id,
            target.provider_id,
            WorkExecutionStatus.SUCCEEDED,
            state,
            artifact_ref=f"fragment:{unit.work_unit_id}:{fragment}",
            evidence_ref=f"execution:{unit.work_unit_id}",
        )


class Repository:
    def initial(self, objective):
        return RepositoryCheckpoint(
            "checkpoint-root",
            "repo-b5",
            "root",
            "artifact-root",
        )

    def capture(self, objective, unit, execution):
        return RepositoryCheckpoint(
            f"checkpoint-{unit.work_unit_id}",
            "repo-b5",
            execution.repository_state_id,
            execution.artifact_ref or "missing-artifact",
        )

    def handoff(self, checkpoint, *, from_executor_id, to_executor_id):
        return checkpoint


class LocalVerifier:
    """Intentionally local verifier: validates unit artifact presence only."""

    def verify(self, objective, unit, execution, checkpoint):
        accepted = bool(execution.artifact_ref and execution.artifact_ref.startswith("fragment:"))
        return WorkVerificationResult(
            accepted,
            "independent-local-verifier",
            f"verification:{unit.work_unit_id}",
            f"local-contract:{unit.work_unit_id}",
            "" if accepted else "missing unit fragment",
        )


def baseline_recompose_and_verify(fragments: dict[str, str]) -> dict[str, object]:
    composite = fragments["left"] + fragments["right"]
    return {
        "composite": composite,
        "expected": EXPECTED_COMPOSITE,
        "spec_satisfied": composite == EXPECTED_COMPOSITE,
    }


def run_case(case_id: str, right_fragment: str) -> dict[str, object]:
    runner = Runner(right_fragment)
    result = supervise_project(
        objective=ProjectObjective(
            f"b5-{case_id}",
            "req-b5-composite",
            f"Produce exactly the recomposed project artifact {EXPECTED_COMPOSITE!r}.",
        ),
        planner=Planner(),
        scheduler=Scheduler(),
        runner=runner,
        repository=Repository(),
        verifier=LocalVerifier(),
        max_executor_attempts_per_unit=1,
        max_corrective_units=0,
    )
    baseline = baseline_recompose_and_verify(runner.fragments)
    trace_kinds = [event.kind.value for event in result.trace]
    return {
        "case_id": case_id,
        "right_fragment": right_fragment,
        "candidate_project_verdict": result.verdict.value,
        "candidate_calls": runner.calls,
        "candidate_trace_kinds": trace_kinds,
        "candidate_traceability": [
            {
                "work_unit_id": record.work_unit_id,
                "verdict": record.verdict,
                "test_ref": record.test_ref,
            }
            for record in result.traceability
        ],
        "baseline": baseline,
        "decomposition_observed": len(result.graph.units) == 2,
        "dependency_order_observed": runner.calls == ["left", "right"],
        "all_local_units_accepted": all(
            record.verdict == "PASS" for record in result.traceability
        ),
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--commit", required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()

    control = run_case("control", "B")
    adversarial = run_case("adversarial-global-mismatch", "X")

    recomposition_trace_surface = any(
        "RECOMPOS" in member.name for member in ProjectTraceKind
    )
    result_fields = {field.name for field in fields(ProjectSupervisionResult)}
    project_artifact_surface = any(
        name in result_fields for name in ("artifact", "artifact_ref", "project_artifact")
    )

    control_ok = (
        control["candidate_project_verdict"] == ProjectVerdict.PROJECT_ACCEPTED.value
        and control["baseline"]["spec_satisfied"] is True
        and control["decomposition_observed"] is True
        and control["dependency_order_observed"] is True
    )
    adversarial_exposes_gap = (
        adversarial["candidate_project_verdict"] == ProjectVerdict.PROJECT_ACCEPTED.value
        and adversarial["all_local_units_accepted"] is True
        and adversarial["baseline"]["spec_satisfied"] is False
    )

    if not control_ok:
        result = "FAIL"
        reason = "control fixture did not establish decomposition/execution behavior"
    elif adversarial_exposes_gap and not recomposition_trace_surface and not project_artifact_surface:
        result = "GAP_IDENTIFIED"
        reason = (
            "local unit acceptance can yield PROJECT_ACCEPTED while explicit recomposition "
            "violates the original specification; current supervision result/trace surface "
            "does not expose project-level recomposition evidence"
        )
    else:
        result = "NOT_PROVEN"
        reason = "benchmark did not establish either B5 completion or the expected bounded gap"

    payload = {
        "schema": "metao-b5-decompose-recompose-v1",
        "commit": args.commit,
        "result": result,
        "reason": reason,
        "candidate": "metao.project_supervision.supervise_project",
        "baseline": "deterministic-concatenate-then-exact-original-spec-check",
        "expected_composite": EXPECTED_COMPOSITE,
        "cases": [control, adversarial],
        "surface_observations": {
            "project_trace_has_recomposition_kind": recomposition_trace_surface,
            "project_result_has_project_artifact_field": project_artifact_surface,
        },
        "boundary": {
            "decomposition": "PASS" if control["decomposition_observed"] else "FAIL",
            "work_unit_execution": "PASS" if control["dependency_order_observed"] else "FAIL",
            "dependency_preservation": "PASS" if control["dependency_order_observed"] else "FAIL",
            "local_unit_verification": "PASS" if control["all_local_units_accepted"] else "FAIL",
            "recomposition": "GAP_IDENTIFIED" if adversarial_exposes_gap else "NOT_PROVEN",
            "original_spec_verification_after_recomposition": (
                "GAP_IDENTIFIED" if adversarial_exposes_gap else "NOT_PROVEN"
            ),
        },
        "claim_boundary": [
            "LOCAL_WORK_UNIT_ACCEPTANCE != ORIGINAL_SPEC_SATISFIED",
            "PROJECT_ACCEPTED_WITHOUT_RECOMPOSITION_EVIDENCE != B5_PASS",
            "DECOMPOSITION_EXECUTION_PASS != RECOMPOSITION_PASS",
            "B5_EVIDENCE != B6_CONTINUITY_EVIDENCE",
        ],
    }

    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n")
    print(json.dumps(payload, indent=2, sort_keys=True))

    # GAP_IDENTIFIED is a successful benchmark adjudication, not a harness/test failure.
    return 0 if result in {"GAP_IDENTIFIED", "PASS"} else 1


if __name__ == "__main__":
    raise SystemExit(main())
