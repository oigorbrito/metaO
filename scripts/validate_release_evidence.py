from __future__ import annotations

import argparse
from datetime import datetime
import json
from pathlib import Path
import re
from typing import Any

EXPECTED_RUNTIME_PINS = {
    "openai_agents": "0.20.0",
    "crewai": "1.15.16",
    "langgraph": "1.2.11",
}

EXPECTED_GATE_NAMES = (
    "exact_runtime_versions",
    "installed_cli_help",
    "installed_import_smoke",
    "r2_wu05_feedback",
    "r7_wu01_failure_aware_replan",
    "r7_wu02_durable_escalation",
    "full_unit_suite",
    "r2_real_runtime_sandbox",
    "r3_real_runtime_certification",
    "r4_real_declarative_certified_runtimes",
    "r5_real_certificate_lifecycle",
    "r6_wu04_openai_adapter_unit",
    "r6_wu04_openai_real_conformance",
    "r6_wu05_three_real_runtimes",
    "r7_wu03_three_runtime_recovery",
    "block_o1_langgraph_real",
    "block_o2_e2e_sandbox",
    "block_o3_failover_sandbox",
    "block_o4_governance_gates",
    "block_o5_runtime_swap",
    "sdk_neutral_boundary",
)


def _is_int(value: object) -> bool:
    return isinstance(value, int) and not isinstance(value, bool)


def _valid_utc_timestamp(value: object) -> bool:
    if not isinstance(value, str) or not value:
        return False
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return False
    return parsed.tzinfo is not None


def validate_evidence(
    evidence: object,
    *,
    expected_commit: str,
    expected_branch: str,
) -> list[str]:
    errors: list[str] = []

    if not isinstance(evidence, dict):
        return ["evidence root must be a JSON object"]

    data: dict[str, Any] = evidence

    if data.get("schema_version") != 1:
        errors.append("schema_version must be 1")

    if not _valid_utc_timestamp(data.get("generated_at_utc")):
        errors.append("generated_at_utc must be an offset-aware ISO-8601 timestamp")

    if data.get("branch") != expected_branch:
        errors.append(
            f"branch mismatch: expected {expected_branch!r}, got {data.get('branch')!r}"
        )

    if data.get("commit") != expected_commit:
        errors.append(
            f"commit mismatch: expected {expected_commit!r}, got {data.get('commit')!r}"
        )

    if data.get("clean_worktree") is not True:
        errors.append("clean_worktree must be true")

    python_version = data.get("python_version")
    if not isinstance(python_version, str) or re.match(r"^3\.13(?:\.|$)", python_version) is None:
        errors.append(f"python_version must be 3.13.x, got {python_version!r}")

    pins = data.get("runtime_pins")
    if pins != EXPECTED_RUNTIME_PINS:
        errors.append(
            f"runtime_pins mismatch: expected {EXPECTED_RUNTIME_PINS!r}, got {pins!r}"
        )

    blocker = data.get("hosted_runner_blocker")
    if not isinstance(blocker, str) or not blocker.strip():
        errors.append("hosted_runner_blocker must be a non-empty string")

    if data.get("phase") != "complete":
        errors.append(f"phase must be 'complete', got {data.get('phase')!r}")

    if data.get("fatal_error") is not None:
        errors.append(f"fatal_error must be null, got {data.get('fatal_error')!r}")

    if not _is_int(data.get("failure_count")) or data.get("failure_count") != 0:
        errors.append(f"failure_count must be integer 0, got {data.get('failure_count')!r}")

    if data.get("overall") != "PASS":
        errors.append(f"overall must be 'PASS', got {data.get('overall')!r}")

    results = data.get("results")
    if not isinstance(results, list):
        errors.append("results must be a list")
        return errors

    if len(results) != len(EXPECTED_GATE_NAMES):
        errors.append(
            f"results must contain exactly {len(EXPECTED_GATE_NAMES)} gates, got {len(results)}"
        )

    names: list[str] = []
    for index, result in enumerate(results):
        prefix = f"results[{index}]"
        if not isinstance(result, dict):
            errors.append(f"{prefix} must be an object")
            continue

        name = result.get("name")
        if not isinstance(name, str) or not name:
            errors.append(f"{prefix}.name must be a non-empty string")
        else:
            names.append(name)

        if result.get("status") != "PASS":
            errors.append(f"{prefix}.status must be 'PASS', got {result.get('status')!r}")

        exit_code = result.get("exit_code")
        if not _is_int(exit_code) or exit_code != 0:
            errors.append(f"{prefix}.exit_code must be integer 0, got {exit_code!r}")

        duration = result.get("duration_seconds")
        if isinstance(duration, bool) or not isinstance(duration, (int, float)) or duration < 0:
            errors.append(
                f"{prefix}.duration_seconds must be a non-negative number, got {duration!r}"
            )

        detail = result.get("detail")
        if detail is not None and not isinstance(detail, str):
            errors.append(f"{prefix}.detail must be a string when present")

    if len(names) != len(set(names)):
        errors.append("gate names must be unique")

    expected = set(EXPECTED_GATE_NAMES)
    actual = set(names)
    missing = sorted(expected - actual)
    unexpected = sorted(actual - expected)
    if missing:
        errors.append(f"missing gates: {', '.join(missing)}")
    if unexpected:
        errors.append(f"unexpected gates: {', '.join(unexpected)}")

    return errors


def _load_json(path: Path) -> object:
    # Windows PowerShell 5.1 may emit a UTF-8 BOM; utf-8-sig accepts both forms.
    with path.open("r", encoding="utf-8-sig") as handle:
        return json.load(handle)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Fail-closed validator for metaO local release-gate JSON evidence."
    )
    parser.add_argument("evidence", type=Path, help="Path to gate-<timestamp>.json")
    parser.add_argument("--expected-commit", required=True, help="Exact candidate SHA")
    parser.add_argument(
        "--expected-branch",
        default="roadmap7/integration-candidate-v1",
        help="Expected evidence branch",
    )
    args = parser.parse_args(argv)

    try:
        evidence = _load_json(args.evidence)
    except (OSError, json.JSONDecodeError) as exc:
        print("RELEASE_EVIDENCE = INVALID")
        print(f"ERROR = unable to read evidence: {exc}")
        return 2

    errors = validate_evidence(
        evidence,
        expected_commit=args.expected_commit,
        expected_branch=args.expected_branch,
    )

    if errors:
        print("RELEASE_EVIDENCE = INVALID")
        print(f"ERROR_COUNT = {len(errors)}")
        for error in errors:
            print(f"ERROR = {error}")
        return 1

    print("RELEASE_EVIDENCE = VALID_PASS")
    print(f"BRANCH = {args.expected_branch}")
    print(f"COMMIT = {args.expected_commit}")
    print(f"GATES = {len(EXPECTED_GATE_NAMES)}")
    print("FAILURES = 0")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
