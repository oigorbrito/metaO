#!/usr/bin/env python3
"""Deterministic read-only repository convergence classification.

The classifier consumes explicit structured facts and returns disposition projections.
It does not call network APIs, mutate Git state, or expose repository write actions.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any, Iterable, Mapping

VALID_DISPOSITIONS = frozenset(
    {
        "ACTIVE_CANONICAL",
        "BLOCKED_EXTERNAL",
        "SATISFIED",
        "ABSORBED",
        "SUPERSEDED_DECISION",
        "PROTECTED_EVIDENCE",
    }
)
SAFE_TO_CLOSE_DISPOSITIONS = frozenset(
    {"SATISFIED", "ABSORBED", "SUPERSEDED_DECISION"}
)


class ClassificationError(ValueError):
    """Raised when structured convergence facts are malformed or ambiguous."""


def _nonblank(value: Any, field: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ClassificationError(f"{field} must be a nonblank string")
    return value.strip()


def _optional_nonblank(value: Any, field: str) -> str | None:
    if value is None:
        return None
    return _nonblank(value, field)


def _string_list(value: Any, field: str) -> tuple[str, ...]:
    if not isinstance(value, list):
        raise ClassificationError(f"{field} must be a list")
    normalized = tuple(_nonblank(item, field) for item in value)
    if len(normalized) != len(set(normalized)):
        raise ClassificationError(f"{field} must not contain duplicates")
    return normalized


def _normalize_case(raw: Mapping[str, Any]) -> dict[str, Any]:
    if not isinstance(raw, Mapping):
        raise ClassificationError("each case must be an object")

    protected = raw.get("protected")
    if not isinstance(protected, bool):
        raise ClassificationError("protected must be boolean")

    return {
        "id": _nonblank(raw.get("id"), "id"),
        "kind": _nonblank(raw.get("kind"), "kind"),
        "obligations": _string_list(raw.get("obligations"), "obligations"),
        "dependencies": _string_list(raw.get("dependencies"), "dependencies"),
        "blocked_by": _optional_nonblank(raw.get("blocked_by"), "blocked_by"),
        "protected": protected,
        "canonical_owner": _optional_nonblank(
            raw.get("canonical_owner"), "canonical_owner"
        ),
        "superseded_by": _optional_nonblank(
            raw.get("superseded_by"), "superseded_by"
        ),
    }


def _authority_set(authority_facts: Mapping[str, Any], field: str) -> frozenset[str]:
    raw = authority_facts.get(field)
    if not isinstance(raw, list):
        raise ClassificationError(f"{field} must be a list")
    normalized = [_nonblank(value, field) for value in raw]
    if len(normalized) != len(set(normalized)):
        raise ClassificationError(f"{field} must not contain duplicates")
    return frozenset(normalized)


def classify_cases(
    cases: Iterable[Mapping[str, Any]], authority_facts: Mapping[str, Any]
) -> list[dict[str, Any]]:
    """Classify structured repository items without mutating repository state.

    Authority-bearing facts that cannot safely be inferred from item shape are supplied
    separately: accepted decision references, documentation items independently known
    complete, and blocker references independently classified as external.
    """

    normalized = [_normalize_case(case) for case in cases]
    by_id: dict[str, dict[str, Any]] = {}
    for case in normalized:
        item_id = case["id"]
        if item_id in by_id:
            raise ClassificationError(f"duplicate item id: {item_id}")
        by_id[item_id] = case

    accepted_decisions = _authority_set(authority_facts, "accepted_decision_refs")
    satisfied_items = _authority_set(authority_facts, "satisfied_item_ids")
    external_blockers = _authority_set(authority_facts, "external_blocker_refs")

    unknown_satisfied = sorted(satisfied_items.difference(by_id))
    if unknown_satisfied:
        raise ClassificationError(
            f"satisfied_item_ids reference unknown items: {unknown_satisfied}"
        )
    for item_id in satisfied_items:
        if by_id[item_id]["kind"] != "DOC":
            raise ClassificationError(
                f"SATISFIED authority is docs-only in this slice: {item_id}"
            )

    depended_on = {
        dependency
        for case in normalized
        for dependency in case["dependencies"]
        if dependency in by_id
    }

    results: list[dict[str, Any]] = []
    for case in sorted(normalized, key=lambda value: value["id"]):
        item_id = case["id"]
        disposition = "ACTIVE_CANONICAL"
        reason = "unique or unresolved obligation remains active"

        if case["protected"]:
            disposition = "PROTECTED_EVIDENCE"
            reason = "protected evidence cannot be terminally disposed"
        elif case["blocked_by"] is not None:
            if case["blocked_by"] in external_blockers:
                disposition = "BLOCKED_EXTERNAL"
                reason = "explicit blocker is independently classified as external"
            else:
                reason = "blocker exists but lacks external-blocker authority"
        elif item_id in depended_on:
            reason = "active dependency references this item"
        elif item_id in satisfied_items:
            disposition = "SATISFIED"
            reason = "documentation obligation is explicitly recorded complete"
        elif (
            case["canonical_owner"] is None
            and case["superseded_by"] in accepted_decisions
        ):
            disposition = "SUPERSEDED_DECISION"
            reason = "accepted authoritative decision resolves the decision question"
        elif (
            case["canonical_owner"] is not None
            and case["canonical_owner"] != item_id
        ):
            owner = by_id.get(case["canonical_owner"])
            if owner is None:
                reason = "canonical owner is not present in the evaluated fact set"
            elif set(case["obligations"]).issubset(owner["obligations"]):
                disposition = "ABSORBED"
                reason = "canonical owner contains every still-valid obligation"
            else:
                reason = "candidate owner does not contain every still-valid obligation"

        if disposition not in VALID_DISPOSITIONS:
            raise AssertionError(f"unknown disposition generated: {disposition}")

        results.append(
            {
                "id": item_id,
                "disposition": disposition,
                "safe_to_close": disposition in SAFE_TO_CLOSE_DISPOSITIONS,
                "canonical_owner": case["canonical_owner"],
                "reason": reason,
            }
        )

    return results


def summarize_against_ground_truth(
    cases: Iterable[Mapping[str, Any]], results: Iterable[Mapping[str, Any]]
) -> dict[str, int]:
    """Compute safety metrics only when expected fixture fields are supplied."""

    case_list = list(cases)
    result_list = list(results)
    expected_by_id = {case["id"]: case for case in case_list}
    result_by_id = {result["id"]: result for result in result_list}
    depended_on = {
        dependency
        for case in case_list
        for dependency in case.get("dependencies", [])
    }

    mismatched_disposition = 0
    false_close = 0
    protected_experiment_loss = 0
    dependency_break = 0
    known_terminal_left_active = 0

    for item_id, expected in expected_by_id.items():
        if item_id not in result_by_id:
            raise ClassificationError(f"missing classification result: {item_id}")
        actual = result_by_id[item_id]
        expected_disposition = expected.get("expected_disposition")
        expected_safe = expected.get("safe_to_close")

        if expected_disposition is not None and actual["disposition"] != expected_disposition:
            mismatched_disposition += 1
        if expected_safe is False and actual["safe_to_close"]:
            false_close += 1
        if expected.get("protected") is True and actual["safe_to_close"]:
            protected_experiment_loss += 1
        if item_id in depended_on and actual["safe_to_close"]:
            dependency_break += 1
        if (
            expected_disposition in {"ABSORBED", "SUPERSEDED_DECISION", "SATISFIED"}
            and actual["disposition"] == "ACTIVE_CANONICAL"
        ):
            known_terminal_left_active += 1

    return {
        "mismatched_disposition": mismatched_disposition,
        "false_close": false_close,
        "protected_experiment_loss": protected_experiment_loss,
        "dependency_break": dependency_break,
        "known_terminal_left_active": known_terminal_left_active,
    }


def _load_json(path: Path) -> dict[str, Any]:
    with path.open("r", encoding="utf-8") as handle:
        value = json.load(handle)
    if not isinstance(value, dict):
        raise ClassificationError(f"{path} must contain a JSON object")
    return value


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Classify repository convergence facts without repository mutation."
    )
    parser.add_argument("fixture", type=Path)
    parser.add_argument("authority_facts", type=Path)
    args = parser.parse_args(argv)

    fixture = _load_json(args.fixture)
    authority_facts = _load_json(args.authority_facts)
    cases = fixture.get("cases")
    if not isinstance(cases, list):
        raise ClassificationError("fixture.cases must be a list")

    results = classify_cases(cases, authority_facts)
    payload = {
        "schema_version": 1,
        "fixture_family": fixture.get("fixture_family"),
        "results": results,
        "metrics": summarize_against_ground_truth(cases, results),
        "claim_boundary": {
            "classifier_mutates_repository": False,
            "similarity_is_close_authority": False,
            "inactivity_is_obsolescence": False,
        },
    }
    print(json.dumps(payload, sort_keys=True, separators=(",", ":")))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
