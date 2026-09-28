"""Validate immutable adversarial-certification donor pins for issue #162."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

ALLOWED_CATEGORY_STATUSES = {
    "Pass",
    "Fail",
    "Skipped",
    "NotRequested",
    "Unknown",
    "EvaluatorError",
}


def _is_sha256(value: object) -> bool:
    if not isinstance(value, str) or len(value) != 64:
        return False
    return all(ch in "0123456789abcdef" for ch in value)


def validate_manifest(data: dict[str, object]) -> list[str]:
    errors: list[str] = []

    if data.get("schema") != "metao-adversarial-certification-donors-v1":
        errors.append("unexpected manifest schema")
    if data.get("issue") != 162:
        errors.append("manifest must bind to issue #162")
    if data.get("evidence_classification") != "REFERENCE_PIN_ONLY":
        errors.append("donor pin evidence must remain REFERENCE_PIN_ONLY")
    if data.get("real_adversarial_campaign_executed") is not False:
        errors.append("pin manifest cannot claim a real adversarial campaign")
    if data.get("changes_product_runtime_dependencies") is not False:
        errors.append("evaluation donors must not become product runtime dependencies")

    donors = data.get("donors")
    if not isinstance(donors, dict) or set(donors) != {"agentdojo", "pyrit"}:
        errors.append("manifest must pin exactly agentdojo and pyrit")
        return errors

    for donor_id, donor in donors.items():
        if not isinstance(donor, dict):
            errors.append(f"{donor_id}: donor entry must be an object")
            continue
        for key in ("repository", "package", "version", "git_ref", "released_on"):
            value = donor.get(key)
            if not isinstance(value, str) or not value.strip():
                errors.append(f"{donor_id}: {key} must be non-empty")

        paths = donor.get("reference_paths")
        if not isinstance(paths, list) or not paths or any(
            not isinstance(item, str) or not item.strip() for item in paths
        ):
            errors.append(f"{donor_id}: reference_paths must be non-empty")

        artifacts = donor.get("artifacts")
        if not isinstance(artifacts, dict):
            errors.append(f"{donor_id}: artifacts must be present")
        else:
            for key in ("sdist_sha256", "wheel_sha256"):
                if not _is_sha256(artifacts.get(key)):
                    errors.append(f"{donor_id}: {key} must be a lowercase SHA-256")

        paper = donor.get("paper")
        if not isinstance(paper, dict) or not paper.get("title") or not paper.get("url"):
            errors.append(f"{donor_id}: paper title/url must be pinned")

        normalization = donor.get("normalization")
        if not isinstance(normalization, dict):
            errors.append(f"{donor_id}: normalization mapping missing")
            continue
        for key, value in normalization.items():
            if key in {
                "evaluator_or_api_error",
                "omitted_category",
                "unavailable_or_ambiguous_result",
                "attack_success_against_forbidden_objective",
                "conclusive_attack_failure_with_complete_category_evidence",
                "undetermined_score_or_outcome",
                "evaluator_or_scorer_error",
            } and value not in ALLOWED_CATEGORY_STATUSES:
                errors.append(f"{donor_id}: invalid category status mapping for {key}")

    agentdojo = donors["agentdojo"]
    if agentdojo.get("release_commit") != "a75aba7631d3ca5fb7ab938965c97ead2f9ff84b":
        errors.append("agentdojo release commit must remain exact")
    pyrit = donors["pyrit"]
    if pyrit.get("release_commit_prefix") != "d0524f0":
        errors.append("pyrit v1.1.0 release commit prefix drifted")

    authority = data.get("authority_boundary")
    if not isinstance(authority, dict):
        errors.append("authority_boundary missing")
    else:
        required_false = (
            "donor_is_runtime_dependency",
            "donor_can_self_certify",
            "donor_result_is_universal_safety_proof",
        )
        for key in required_false:
            if authority.get(key) is not False:
                errors.append(f"authority boundary requires {key}=false")
        if authority.get("independent_metaO_certification_remains_authority") is not True:
            errors.append("metaO certification authority must remain independent")
        if authority.get("attacks_default_to_controlled_non_production_fixture") is not True:
            errors.append("adversarial attacks must default to controlled fixtures")

    return errors


def validate_product_dependencies(pyproject_text: str) -> list[str]:
    lowered = pyproject_text.lower()
    errors: list[str] = []
    for package in ("agentdojo", "pyrit"):
        if f'"{package}"' in lowered or f"'{package}'" in lowered:
            errors.append(f"{package} must not be a product runtime dependency")
    return errors


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--manifest",
        type=Path,
        default=Path("docs/adversarial-certification-donors.json"),
    )
    parser.add_argument("--pyproject", type=Path, default=Path("pyproject.toml"))
    args = parser.parse_args()

    data = json.loads(args.manifest.read_text(encoding="utf-8"))
    errors = validate_manifest(data)
    errors.extend(
        validate_product_dependencies(args.pyproject.read_text(encoding="utf-8"))
    )
    if errors:
        for error in errors:
            print(f"ERROR: {error}")
        return 1
    print("adversarial certification donor pins: PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
