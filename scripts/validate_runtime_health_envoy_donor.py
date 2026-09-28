"""Validate immutable Envoy runtime-health donor pin for issue #160."""

from __future__ import annotations

import argparse
import json
from pathlib import Path


EXPECTED_RELEASE = "v1.39.1"
EXPECTED_COMMIT = "b579d07d3ad7ee11d32b105e91a5a39ad24718d7"
EXPECTED_PATHS = {
    "api/envoy/config/cluster/v3/outlier_detection.proto":
        "2cd3bb943e47ceee3e05fa696b778ccf7a1ee99c",
    "source/common/upstream/outlier_detection_impl.cc":
        "d610d2163e87cc1bab72980cb49c7f86480d7f0d",
    "api/envoy/config/cluster/v3/circuit_breaker.proto":
        "fdc0af5460a08d7b63b852a5da37af5961eb9ff6",
}


def validate_manifest(data: dict[str, object]) -> list[str]:
    errors: list[str] = []
    if data.get("schema") != "metao-runtime-health-donor-v1":
        errors.append("unexpected schema")
    if data.get("issue") != 160:
        errors.append("manifest must bind to issue #160")
    if data.get("evidence_classification") != "REFERENCE_PIN_ONLY":
        errors.append("evidence classification must remain REFERENCE_PIN_ONLY")
    if data.get("changes_product_dependencies") is not False:
        errors.append("donor pin must not change product dependencies")

    donor = data.get("donor")
    if not isinstance(donor, dict):
        return errors + ["donor entry missing"]
    if donor.get("release") != EXPECTED_RELEASE:
        errors.append("Envoy release pin drifted")
    if donor.get("release_commit") != EXPECTED_COMMIT:
        errors.append("Envoy release commit drifted")

    paths = donor.get("paths")
    if not isinstance(paths, list):
        return errors + ["donor paths missing"]
    actual = {
        item.get("path"): item.get("blob_sha")
        for item in paths
        if isinstance(item, dict)
    }
    if actual != EXPECTED_PATHS:
        errors.append("Envoy consumed path/blob pins drifted")

    fit = data.get("metao_fit")
    if not isinstance(fit, dict):
        errors.append("metao_fit missing")
    else:
        for key in (
            "envoy_runtime_dependency",
            "envoy_specific_types_in_core",
            "health_as_acceptance_authority",
        ):
            if fit.get(key) != "REJECT":
                errors.append(f"{key} must remain REJECT")
        if fit.get("outlier_detection") != "ADAPT_SEMANTICS":
            errors.append("outlier detection fit must remain ADAPT_SEMANTICS")
    return errors


def validate_product_dependencies(pyproject_text: str) -> list[str]:
    lowered = pyproject_text.lower()
    if '"envoy"' in lowered or "'envoy'" in lowered:
        return ["Envoy must not become a Python product dependency"]
    return []


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--manifest",
        type=Path,
        default=Path("docs/runtime-health-envoy-donor.json"),
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
    print("runtime health Envoy donor pin: PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
