from __future__ import annotations

import argparse
import hashlib
import json
import re
import tomllib
from collections import defaultdict, deque
from pathlib import Path
from typing import Any

ROOT_NAME = "openai-agents"
ROOT_VERSION = "0.20.0"
AUTHORITY_PATH = Path("requirements/openai-agents-runtime-authority.json")


def normalize_name(name: str) -> str:
    return re.sub(r"[-_.]+", "-", name).lower()


def package_key(package: dict[str, Any]) -> tuple[str, str]:
    return normalize_name(package["name"]), package["version"]


def merge_markers(existing: set[str], marker: str | None) -> None:
    if marker:
        existing.add(marker)


def select_dependency(
    dependency: dict[str, Any],
    packages_by_name: dict[str, list[dict[str, Any]]],
) -> dict[str, Any]:
    name = normalize_name(dependency["name"])
    candidates = packages_by_name.get(name, [])
    version = dependency.get("version")
    if version is not None:
        candidates = [candidate for candidate in candidates if candidate.get("version") == version]
    if len(candidates) != 1:
        versions = sorted(candidate.get("version", "<none>") for candidate in candidates)
        raise SystemExit(
            f"ambiguous dependency resolution for {dependency['name']!r}: "
            f"version={version!r} candidates={versions}"
        )
    return candidates[0]


def runtime_closure(lock: dict[str, Any]) -> tuple[list[dict[str, Any]], dict[tuple[str, str], set[str]]]:
    packages = lock.get("package", [])
    packages_by_name: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for package in packages:
        packages_by_name[normalize_name(package["name"])].append(package)

    roots = [
        package
        for package in packages_by_name.get(normalize_name(ROOT_NAME), [])
        if package.get("version") == ROOT_VERSION
    ]
    if len(roots) != 1:
        raise SystemExit(f"expected exactly one {ROOT_NAME}=={ROOT_VERSION} root, found {len(roots)}")

    visited: dict[tuple[str, str], dict[str, Any]] = {}
    markers: dict[tuple[str, str], set[str]] = defaultdict(set)
    queue: deque[dict[str, Any]] = deque([roots[0]])

    while queue:
        package = queue.popleft()
        key = package_key(package)
        if key in visited:
            continue
        visited[key] = package
        for dependency in package.get("dependencies", []):
            selected = select_dependency(dependency, packages_by_name)
            selected_key = package_key(selected)
            merge_markers(markers[selected_key], dependency.get("marker"))
            if selected_key not in visited:
                queue.append(selected)

    ordered = [visited[key] for key in sorted(visited)]
    return ordered, markers


def render_requirements(
    packages: list[dict[str, Any]],
    markers: dict[tuple[str, str], set[str]],
) -> str:
    lines = [
        "# Generated from the immutable OpenAI Agents upstream uv.lock authority.",
        "# Do not edit package versions or hashes manually.",
        "",
    ]
    for package in packages:
        if normalize_name(package["name"]) == normalize_name(ROOT_NAME):
            continue
        source = package.get("source", {})
        if "registry" not in source:
            raise SystemExit(f"runtime dependency is not registry-backed: {package['name']}=={package['version']}")
        wheels = package.get("wheels", [])
        hashes = sorted({wheel.get("hash", "") for wheel in wheels if wheel.get("hash", "").startswith("sha256:")})
        if not hashes:
            raise SystemExit(f"runtime dependency has no audited wheel hashes: {package['name']}=={package['version']}")
        key = package_key(package)
        package_markers = sorted(markers.get(key, set()))
        marker_suffix = ""
        if package_markers:
            marker_suffix = " ; " + " or ".join(f"({marker})" for marker in package_markers)
        lines.append(f"{package['name']}=={package['version']}{marker_suffix} \\")
        for index, digest in enumerate(hashes):
            suffix = " \\" if index < len(hashes) - 1 else ""
            lines.append(f"    --hash={digest}{suffix}")
    lines.append("")
    return "\n".join(lines)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Materialize the OpenAI Agents runtime requirements lock.")
    parser.add_argument("upstream_lock", type=Path)
    parser.add_argument("output", type=Path)
    args = parser.parse_args(argv)

    authority = json.loads(AUTHORITY_PATH.read_text(encoding="utf-8"))
    raw = args.upstream_lock.read_bytes()
    git_blob_sha1 = hashlib.sha1(f"blob {len(raw)}\0".encode("ascii") + raw).hexdigest()
    expected_blob = authority["upstream_uv_lock"]["git_blob_sha1"]
    if git_blob_sha1 != expected_blob:
        raise SystemExit(f"upstream lock blob mismatch: expected {expected_blob}, observed {git_blob_sha1}")

    lock = tomllib.loads(raw.decode("utf-8"))
    packages, markers = runtime_closure(lock)
    rendered = render_requirements(packages, markers)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(rendered, encoding="utf-8", newline="\n")

    evidence = {
        "runtime_lock_materialized": True,
        "root": f"{ROOT_NAME}=={ROOT_VERSION}",
        "upstream_uv_lock_git_blob_sha1": git_blob_sha1,
        "runtime_package_count": len(packages) - 1,
        "requirements_sha256": hashlib.sha256(rendered.encode("utf-8")).hexdigest(),
        "credentials_emitted": False,
    }
    print(json.dumps(evidence, sort_keys=True, separators=(",", ":")))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
