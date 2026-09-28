"""Validate immutable SPIFFE/SPIRE workload-identity donor pins for issue #159."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

EXPECTED_SPIFFE_REVISION = "f97c46dfd0ff0d4e412cce5c73846a9ca32a99a2"
EXPECTED_SPIFFE_PATHS = {
    "standards/SPIFFE-ID.md": "caa1bef4671a9f825cffc342d5802f430c7e1258",
    "standards/X509-SVID.md": "cec8b73004a5ea4c90c18478999dfddb1ef841bc",
    "standards/JWT-SVID.md": "8f0f39c1007ce786b5a7214ac02e21c453081270",
    "standards/SPIFFE_Workload_API.md": "f56a8761f9f906bc54e3541636253afc700f7696",
    "standards/SPIFFE_Trust_Domain_and_Bundle.md": "33746e4703f8056a5631a1de1cc2d35ffadaff35",
}
EXPECTED_SPIRE_RELEASE = "v1.15.3"
EXPECTED_SPIRE_TAG_OBJECT = "af69d3fae6c82db1e19107b53a311cb5ec264ec7"
EXPECTED_SPIRE_COMMIT = "2f7861ae3923caf1f57eb087fc2928d58c0fb1d2"
EXPECTED_SPIRE_PATHS = {
    "pkg/agent/endpoints/workload/handler.go": "d67c15e01d11e9da5b3e1f935379d8fe08f31d0a",
    "pkg/agent/agent.go": "c96b52ea1762316d23e4195671857dbda196d294",
    "cmd/spire-agent/cli/run/run.go": "11b3a42dabc6403f94548cbede4637d6a00467bd",
}


def _path_map(value: object) -> dict[str, str]:
    if not isinstance(value, list):
        return {}
    return {
        item["path"]: item["blob_sha"]
        for item in value
        if isinstance(item, dict)
        and isinstance(item.get("path"), str)
        and isinstance(item.get("blob_sha"), str)
    }


def validate_manifest(data: dict[str, object]) -> list[str]:
    errors: list[str] = []
    if data.get("schema") != "metao-workload-identity-donors-v1":
        errors.append("unexpected manifest schema")
    if data.get("issue") != 159:
        errors.append("manifest must bind to issue #159")
    if data.get("evidence_classification") != "REFERENCE_PIN_ONLY":
        errors.append("evidence classification must remain REFERENCE_PIN_ONLY")
    if data.get("real_spire_execution") is not False:
        errors.append("pin manifest cannot claim real SPIRE execution")
    if data.get("changes_product_runtime_dependencies") is not False:
        errors.append("reference pins must not change product runtime dependencies")

    spiffe = data.get("spiffe")
    if not isinstance(spiffe, dict):
        errors.append("spiffe entry missing")
    else:
        if spiffe.get("revision") != EXPECTED_SPIFFE_REVISION:
            errors.append("SPIFFE standards revision drifted")
        if _path_map(spiffe.get("reference_paths")) != EXPECTED_SPIFFE_PATHS:
            errors.append("SPIFFE specification path/blob pins drifted")

    spire = data.get("spire")
    if not isinstance(spire, dict):
        errors.append("spire entry missing")
    else:
        if spire.get("release") != EXPECTED_SPIRE_RELEASE:
            errors.append("SPIRE release drifted")
        if spire.get("annotated_tag_object") != EXPECTED_SPIRE_TAG_OBJECT:
            errors.append("SPIRE annotated tag object drifted")
        if spire.get("release_commit") != EXPECTED_SPIRE_COMMIT:
            errors.append("SPIRE release commit drifted")
        if _path_map(spire.get("reference_paths")) != EXPECTED_SPIRE_PATHS:
            errors.append("SPIRE reference path/blob pins drifted")

    authority = data.get("authority_boundary")
    if not isinstance(authority, dict):
        errors.append("authority_boundary missing")
    else:
        required_false = (
            "spiffe_identity_is_policy_authority",
            "caller_supplied_trust_root_allowed",
            "dev_identity_can_claim_production_attestation",
            "spire_runtime_dependency_in_core",
        )
        for key in required_false:
            if authority.get(key) is not False:
                errors.append(f"authority boundary requires {key}=false")
        if authority.get("metao_policy_authority_remains_authoritative") is not True:
            errors.append("metaO policy authority must remain authoritative")

    remaining = data.get("remaining_external_evidence")
    if not isinstance(remaining, list) or not remaining:
        errors.append("remaining external evidence must stay explicit")
    return errors


def validate_product_dependencies(pyproject_text: str) -> list[str]:
    lowered = pyproject_text.lower()
    errors: list[str] = []
    for package in ("spiffe", "spire"):
        if f'"{package}"' in lowered or f"'{package}'" in lowered:
            errors.append(f"{package} must not become a product runtime dependency")
    return errors


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--manifest",
        type=Path,
        default=Path("docs/workload-identity-spiffe-spire-donors.json"),
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
    print("SPIFFE/SPIRE workload identity donor pins: PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
