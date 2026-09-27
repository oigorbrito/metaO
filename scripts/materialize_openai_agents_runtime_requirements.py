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


def select_dependency(
    dependency: dict[str, Any],
    packages_by_name: dict[str, list[dict[str, Any]]],
) -> dict[str, Any]:
    name = normalize_name(dependency["name"])
    candidates = packages_by_name.get(name, [])
    version = dependency.get("version")
    if version is not None:
        candidates = [candidate for candidate in candidates if candidate.get("version") == version]
    source = dependency.get("source")
    if source is not None and len(candidates) > 1:
        candidates = [candidate for candidate in candidates if candidate.get("source") == source]
    if len(candidates) != 1:
        versions = sorted(candidate.get("version", "<none>") for candidate in candidates)
        raise SystemExit(
            f"ambiguous dependency resolution for {dependency['name']!r}: "
            f"version={version!r} candidates={versions}"
        )
    return candidates[0]


def combine_marker(parent: str, edge: str | None) -> str:
    if not parent:
        return edge or ""
    if not edge:
        return parent
    return f"({parent}) and ({edge})"


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

    selected_packages: dict[tuple[str, str], dict[str, Any]] = {}
    conditions: dict[tuple[str, str], set[str]] = defaultdict(set)
    queue: deque[tuple[dict[str, Any], str]] = deque([(roots[0], "")])
    seen_states: set[tuple[tuple[str, str], str]] = set()

    while queue:
        package, inherited_condition = queue.popleft()
        key = package_key(package)
        state = (key, inherited_condition)
        if state in seen_states:
            continue
        seen_states.add(state)
        selected_packages[key] = package
        conditions[key].add(inherited_condition)
        for dependency in package.get("dependencies", []):
            selected = select_dependency(dependency, packages_by_name)
            dependency_condition = combine_marker(inherited_condition, dependency.get("marker"))
            queue.append((selected, dependency_condition))

    ordered = [selected_packages[key] for key in sorted(selected_packages)]
    return ordered, conditions


def marker_suffix(package_conditions: set[str]) -> str:
    if not package_conditions or "" in package_conditions:
        return ""
    return " ; " + " or ".join(f"({condition})" for condition in sorted(package_conditions))


def render_requirement(name: str, version: str, hashes: list[str], suffix: str = "") -> list[str]:
    if not hashes:
        raise SystemExit(f"runtime dependency has no audited wheel hashes: {name}=={version}")
    lines = [f"{name}=={version}{suffix} \\"]
    for index, digest in enumerate(hashes):
        continuation = " \\" if index < len(hashes) - 1 else ""
        lines.append(f"    --hash={digest}{continuation}")
    return lines


def render_requirements(
    packages: list[dict[str, Any]],
    conditions: dict[tuple[str, str], set[str]],
    authority: dict[str, Any],
) -> str:
    lines = [
        "# Generated from the immutable OpenAI Agents upstream uv.lock authority.",
        "# Do not edit package versions or hashes manually.",
        "",
    ]
    root_hash = str(authority["pypi_wheel_sha256"])
    if not re.fullmatch(r"[0-9a-f]{64}", root_hash):
        raise SystemExit("authority pypi_wheel_sha256 must be lowercase SHA-256")
    lines.extend(render_requirement(ROOT_NAME, ROOT_VERSION, [f"sha256:{root_hash}"]))

    for package in packages:
        if normalize_name(package["name"]) == normalize_name(ROOT_NAME):
            continue
        source = package.get("source", {})
        if "registry" not in source:
            raise SystemExit(f"runtime dependency is not registry-backed: {package['name']}=={package['version']}")
        hashes = sorted(
            {
                wheel.get("hash", "")
                for wheel in package.get("wheels", [])
                if wheel.get("hash", "").startswith("sha256:")
            }
        )
        key = package_key(package)
        lines.extend(
            render_requirement(
                package["name"],
                package["version"],
                hashes,
                marker_suffix(conditions.get(key, set())),
            )
        )
    lines.append("")
    return "\n".join(lines)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Materialize the OpenAI Agents runtime requirements lock.")
    parser.add_argument("upstream_lock", type=Path)
    parser.add_argument("output", type=Path)
    args = parser.parse_args(argv)

    authority = json.loads(AUTHORITY_PATH.read_text(encoding="utf-8"))
    if authority.get("package") != ROOT_NAME or authority.get("version") != ROOT_VERSION:
        raise SystemExit("runtime authority root package/version mismatch")
    raw = args.upstream_lock.read_bytes()
    git_blob_sha1 = hashlib.sha1(f"blob {len(raw)}\0".encode("ascii") + raw).hexdigest()
    expected_blob = str(authority["source_uv_lock_blob_sha1"])
    if git_blob_sha1 != expected_blob:
        raise SystemExit(f"upstream lock blob mismatch: expected {expected_blob}, observed {git_blob_sha1}")

    lock = tomllib.loads(raw.decode("utf-8"))
    packages, conditions = runtime_closure(lock)
    rendered = render_requirements(packages, conditions, authority)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(rendered, encoding="utf-8", newline="\n")

    evidence = {
        "runtime_lock_materialized": True,
        "root": f"{ROOT_NAME}=={ROOT_VERSION}",
        "upstream_uv_lock_git_blob_sha1": git_blob_sha1,
        "runtime_package_count": len(packages),
        "requirements_sha256": hashlib.sha256(rendered.encode("utf-8")).hexdigest(),
        "credentials_emitted": False,
    }
    print(json.dumps(evidence, sort_keys=True, separators=(",", ":")))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
