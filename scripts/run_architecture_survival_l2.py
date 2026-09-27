#!/usr/bin/env python3
"""Run current-metaO Architecture Survival L2 fixtures and emit receipts."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import subprocess
import sys
import time

FIXTURES = (
    (
        "L2-A01",
        "executor DONE without evidence is not Acceptance",
        ["cargo", "test", "-p", "metao-kernel", "--test", "evidence_binding",
         "executor_done_without_evidence_does_not_accept", "--", "--exact"],
        "experiments/rust-chassis-a/metao-kernel/tests/evidence_binding.rs",
    ),
    (
        "L2-A02",
        "executor WorkGraph proposal cannot acquire Project Plane authority",
        ["cargo", "test", "-p", "metao-testkit", "--test", "l2_a06_workgraph_authority",
         "executor_produced_decomposition_never_becomes_authoritative_automatically", "--", "--exact"],
        "experiments/rust-chassis-a/metao-testkit/tests/l2_a06_workgraph_authority.rs",
    ),
    (
        "L2-A03",
        "state drift makes evidence stale",
        ["cargo", "test", "-p", "metao-kernel", "--test", "evidence_binding",
         "subject_state_mismatch_is_stale", "--", "--exact"],
        "experiments/rust-chassis-a/metao-kernel/tests/evidence_binding.rs",
    ),
    (
        "L2-A04",
        "unknown/self-reported usage is not authoritative",
        ["cargo", "test", "-p", "metao-contracts", "--test", "execution_governance_tests",
         "caller_declared_or_unknown_observed_usage_is_not_authoritative", "--", "--exact"],
        "experiments/rust-chassis-a/metao-contracts/tests/execution_governance_tests.rs",
    ),
    (
        "L2-A05",
        "zero budget blocks before runtime",
        ["cargo", "test", "-p", "metao-contracts", "--test", "execution_governance_tests",
         "explicit_zero_budget_blocks_before_runtime", "--", "--exact"],
        "experiments/rust-chassis-a/metao-contracts/tests/execution_governance_tests.rs",
    ),
    (
        "L2-A06",
        "authoritative validated immutable WorkGraph is required before dispatch",
        ["cargo", "test", "-p", "metao-testkit", "--test", "l2_a06_workgraph_authority"],
        "experiments/rust-chassis-a/metao-testkit/tests/l2_a06_workgraph_authority.rs",
    ),
    (
        "L2-A07",
        "caller-declared completion evidence cannot prove project completion",
        ["cargo", "test", "-p", "metao-contracts", "--test", "project_completion_boundary_tests",
         "caller_declared_pass_is_not_independent_completion_evidence", "--", "--exact"],
        "experiments/rust-chassis-a/metao-contracts/tests/project_completion_boundary_tests.rs",
    ),
)


def run_fixture(root: Path, fixture: tuple[str, str, list[str], str]) -> dict:
    fixture_id, claim, command, source = fixture
    started = time.monotonic()
    completed = subprocess.run(
        command,
        cwd=root / "experiments" / "rust-chassis-a",
        text=True,
        capture_output=True,
        check=False,
    )
    elapsed = time.monotonic() - started
    return {
        "fixture_id": fixture_id,
        "claim": claim,
        "result": "PASS" if completed.returncode == 0 else "FAIL",
        "exit_code": completed.returncode,
        "elapsed_seconds": round(elapsed, 3),
        "command": command,
        "source": source,
        "stdout": completed.stdout,
        "stderr": completed.stderr,
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()

    root = Path(__file__).resolve().parents[1]
    results = [run_fixture(root, fixture) for fixture in FIXTURES]
    receipt = {
        "schema": "metao.architecture-survival.l2-receipt.v1",
        "strategy_id": "metao-current-main",
        "authority": "qualification-only; no Acceptance authority",
        "fixtures": results,
        "result": "PASS" if all(item["result"] == "PASS" for item in results) else "FAIL",
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(receipt, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(args.output.read_text(encoding="utf-8"))
    return 0 if receipt["result"] == "PASS" else 1


if __name__ == "__main__":
    sys.exit(main())
