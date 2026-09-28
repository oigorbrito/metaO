"""Validate #168 scientific validation matrix and gate receipts."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

LEVELS = tuple(f"L{i}" for i in range(8))
RESULTS = {"PASS", "FAIL", "BLOCKED", "SKIPPED", "NOT_REQUESTED"}
EXTERNAL_MODES = {"REAL", "SIMULATED", "NONE"}
EXPECTED_FAMILIES = {f"T{i}" for i in range(1, 16)}
REQUIRED_RECEIPT_FIELDS = {
    "schema",
    "repository",
    "commit",
    "gate_id",
    "gate_level",
    "runtime_identities",
    "mission_lineage",
    "commands",
    "environment",
    "started_at",
    "ended_at",
    "duration_seconds",
    "result",
    "failure_reason",
    "evidence_ids",
    "external_systems",
}


def validate_matrix(data: dict[str, object]) -> list[str]:
    errors: list[str] = []
    if data.get("schema") != "metao-scientific-validation-matrix-v1":
        errors.append("unexpected matrix schema")
    if data.get("issue") != 168:
        errors.append("matrix must bind to issue #168")
    if tuple(data.get("gate_levels", ())) != LEVELS:
        errors.append("gate levels must remain L0..L7")
    if set(data.get("result_states", ())) != RESULTS:
        errors.append("result states drifted")

    families = data.get("families")
    if not isinstance(families, list):
        return errors + ["families must be a list"]

    ids = {item.get("id") for item in families if isinstance(item, dict)}
    if ids != EXPECTED_FAMILIES:
        errors.append("matrix must contain exactly T1..T15")
    for item in families:
        if not isinstance(item, dict):
            errors.append("family entry must be an object")
            continue
        if not item.get("title"):
            errors.append(f"{item.get('id')}: title missing")
        owners = item.get("owner_issues")
        if not isinstance(owners, list) or not owners or any(
            not isinstance(value, int) or value <= 0 for value in owners
        ):
            errors.append(f"{item.get('id')}: owner_issues must be positive issue ids")

    contract = data.get("receipt_contract")
    if not isinstance(contract, dict):
        errors.append("receipt_contract missing")
    else:
        if set(contract.get("required_fields", ())) != REQUIRED_RECEIPT_FIELDS:
            errors.append("receipt required fields drifted")
    return errors


def validate_receipt(receipt: dict[str, object], matrix: dict[str, object]) -> list[str]:
    errors: list[str] = []
    missing = REQUIRED_RECEIPT_FIELDS - set(receipt)
    if missing:
        errors.append("missing receipt fields: " + ", ".join(sorted(missing)))
        return errors

    if receipt.get("schema") != "metao-scientific-gate-receipt-v1":
        errors.append("unexpected receipt schema")
    family_ids = {
        item["id"]
        for item in matrix["families"]
        if isinstance(item, dict) and "id" in item
    }
    if receipt.get("gate_id") not in family_ids:
        errors.append("receipt gate_id is not registered in T1..T15")
    if receipt.get("gate_level") not in LEVELS:
        errors.append("invalid gate_level")
    if receipt.get("result") not in RESULTS:
        errors.append("invalid result")
    if not isinstance(receipt.get("duration_seconds"), (int, float)) or receipt["duration_seconds"] < 0:
        errors.append("duration_seconds must be non-negative")

    external = receipt.get("external_systems")
    if not isinstance(external, dict):
        errors.append("external_systems must be an object")
    else:
        if external.get("mode") not in EXTERNAL_MODES:
            errors.append("external_systems.mode must be REAL, SIMULATED or NONE")
        systems = external.get("systems")
        if not isinstance(systems, list):
            errors.append("external_systems.systems must be a list")
        if external.get("mode") == "REAL" and not systems:
            errors.append("REAL external mode requires named systems")
        if external.get("mode") == "NONE" and systems:
            errors.append("NONE external mode cannot name systems")

    result = receipt.get("result")
    reason = receipt.get("failure_reason")
    if result == "PASS" and reason not in (None, ""):
        errors.append("PASS receipt cannot carry failure_reason")
    if result in {"FAIL", "BLOCKED"} and (not isinstance(reason, str) or not reason.strip()):
        errors.append(f"{result} receipt requires failure_reason")

    command_list = receipt.get("commands")
    if not isinstance(command_list, list) or not command_list:
        errors.append("commands must contain at least one executed command")
    evidence_ids = receipt.get("evidence_ids")
    if not isinstance(evidence_ids, list):
        errors.append("evidence_ids must be a list")

    return errors


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--matrix",
        type=Path,
        default=Path("docs/scientific-validation-matrix.json"),
    )
    parser.add_argument("--receipt", type=Path)
    args = parser.parse_args()

    matrix = json.loads(args.matrix.read_text(encoding="utf-8"))
    errors = validate_matrix(matrix)
    if args.receipt is not None:
        receipt = json.loads(args.receipt.read_text(encoding="utf-8"))
        errors.extend(validate_receipt(receipt, matrix))
    if errors:
        for error in errors:
            print(f"ERROR: {error}")
        return 1
    print("scientific validation evidence: PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
