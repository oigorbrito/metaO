from __future__ import annotations

import argparse
from datetime import datetime, timezone
import json
import os
from pathlib import Path
import subprocess
import time


CASES = (
    (
        "project_supervisor_core",
        ["python", "tests/unit/test_issue_507_project_supervision.py"],
        [
            "decomposition",
            "capacity_failover",
            "corrective_work",
            "independent_acceptance",
            "traceability",
        ],
    ),
    (
        "trusted_git_handoff",
        ["python", "tests/integration/test_issue_523_project_supervision_trusted_git_bridge.py"],
        [
            "trusted_git_checkpoint",
            "provider_diverse_failover",
            "repository_state_handoff",
            "project_acceptance",
        ],
    ),
    (
        "corrective_replan_multi_worktree",
        ["python", "tests/integration/test_issue_528_project_corrective_replan.py"],
        [
            "failed_verification",
            "corrective_replan",
            "cross_executor_handoff",
            "traceability",
        ],
    ),
    (
        "remote_checkpoint_supervision",
        ["python", "tests/integration/test_issue_538_project_remote_checkpoint_supervision.py"],
        [
            "remote_checkpoint_materialization",
            "remote_handoff",
            "corrective_replan",
            "project_acceptance",
        ],
    ),
)


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--commit", required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()

    started_at = utc_now()
    started = time.monotonic()
    results = []
    failed = False

    for case_id, command, proves in CASES:
        case_started = time.monotonic()
        completed = subprocess.run(
            command,
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            check=False,
        )
        duration = time.monotonic() - case_started
        status = "PASS" if completed.returncode == 0 else "FAIL"
        failed = failed or completed.returncode != 0
        print(f"[{case_id}] {status} ({duration:.3f}s)")
        if completed.returncode != 0:
            print(completed.stdout[-4000:])
        results.append(
            {
                "case_id": case_id,
                "command": command,
                "status": status,
                "duration_seconds": round(duration, 6),
                "proves": proves,
                "output_tail": completed.stdout[-4000:],
            }
        )

    ended_at = utc_now()
    duration = time.monotonic() - started

    payload = {
        "schema": "metao-mechanical-project-supervision-pilot-v1",
        "commit": args.commit,
        "workflow_run_id": os.environ.get("GITHUB_RUN_ID"),
        "classification": "MECHANICAL_PROVIDER_FREE_PROJECT_SUPERVISION",
        "started_at": started_at,
        "ended_at": ended_at,
        "duration_seconds": round(duration, 6),
        "result": "PASS" if not failed else "FAIL",
        "cases": results,
        "claims": {
            "project_decomposition": "EXECUTED",
            "multiple_work_units": "EXECUTED",
            "multiple_executor_identities": "EXECUTED",
            "capacity_failover": "EXECUTED",
            "trusted_repository_handoff": "EXECUTED",
            "failed_verification_detected": "EXECUTED",
            "corrective_work_created": "EXECUTED",
            "independent_acceptance": "EXECUTED",
            "requirement_to_verdict_traceability": "EXECUTED",
            "remote_checkpoint_semantics": "EXECUTED",
            "real_provider_calls": "NOT_EXECUTED",
            "real_provider_credentials": "NOT_USED",
            "real_provider_cost": "NOT_MEASURED",
            "cross_provider_external_handoff": "NOT_PROVEN",
        },
        "claim_boundary": [
            "MECHANICAL_SUBSTITUTE != REAL_PROVIDER_PILOT",
            "SIMULATED_PROVIDER_IDENTITY != REAL_PROVIDER_EXECUTION",
            "PROJECT_ACCEPTED_IN_FIXTURE != #360_OPERATIONAL_PASS",
            "NO_PROVIDER_CREDIT != PROVIDER_PASS",
        ],
    }

    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(main())
