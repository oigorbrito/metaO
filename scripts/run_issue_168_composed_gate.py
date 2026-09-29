from __future__ import annotations

import argparse
from datetime import datetime, timezone
import json
import os
from pathlib import Path
import subprocess
import time


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--commit", required=True)
    args = parser.parse_args()

    started_at = utc_now()
    started = time.monotonic()
    command = [
        "cargo",
        "test",
        "-p",
        "metao-testkit",
        "--test",
        "composed_system_closure_tests",
        "--",
        "--nocapture",
    ]
    result = subprocess.run(
        command,
        cwd=Path("experiments/rust-chassis-a"),
        check=False,
        text=True,
    )
    ended_at = utc_now()
    duration = time.monotonic() - started

    passed = result.returncode == 0
    receipt = {
        "schema": "metao-scientific-gate-receipt-v1",
        "repository": "oigorbrito/metaO",
        "commit": args.commit,
        "gate_id": "T12",
        "gate_level": "L6",
        "runtime_identities": [
            "runtime-a:simulated:config-a:generation-1",
            "runtime-b:simulated:config-b:generation-2",
        ],
        "runtime_substrate": {
            "mode": "SIMULATED",
            "runtimes": ["runtime-a", "runtime-b"],
        },
        "mission_lineage": [
            "closure-marketplace-mission",
            "exec-a:generation-1",
            "exec-b:generation-2",
        ],
        "commands": [" ".join(command)],
        "environment": {
            "ci": "GitHub Actions",
            "workflow": "Issue 168 Composed Restart Failover",
            "workflow_run_id": os.environ.get("GITHUB_RUN_ID"),
            "runner_os": os.environ.get("RUNNER_OS"),
            "faults": [
                "lost_ack_after_external_effect",
                "runtime_health_degradation",
                "ownership_takeover",
                "late_stale_owner_mutation",
                "effect_service_restart",
            ],
        },
        "started_at": started_at,
        "ended_at": ended_at,
        "duration_seconds": round(duration, 6),
        "result": "PASS" if passed else "FAIL",
        "failure_reason": None if passed else f"composed cargo test exited {result.returncode}",
        "evidence_ids": [
            f"github-actions-run:{os.environ.get('GITHUB_RUN_ID', 'unknown')}",
            "test:metao-testkit/composed_system_closure_tests",
            "effect:create-marketplace-ticket",
            "fence:exec-a:generation-2",
        ],
        "external_systems": {
            "mode": "REAL",
            "systems": [
                "metao-testkit-effect-service-local-process",
                "metao-testkit-fence-service-local-process",
            ],
        },
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(
        json.dumps(receipt, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    return result.returncode


if __name__ == "__main__":
    raise SystemExit(main())
