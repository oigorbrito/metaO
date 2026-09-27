from __future__ import annotations

import argparse
import re
from pathlib import Path

USES_RE = re.compile(r"^\s*-?\s*uses:\s*([^\s#]+)")
FULL_SHA_RE = re.compile(r"^[0-9a-fA-F]{40}$")


def find_mutable_action_refs(workflows_dir: Path) -> list[str]:
    violations: list[str] = []
    for path in sorted(workflows_dir.glob("*.y*ml")):
        for line_number, line in enumerate(path.read_text(encoding="utf-8").splitlines(), start=1):
            match = USES_RE.match(line)
            if match is None:
                continue
            target = match.group(1)
            if target.startswith("./") or target.startswith("docker://"):
                continue
            if "@" not in target:
                violations.append(f"{path}:{line_number}: action reference has no immutable ref: {target}")
                continue
            _, ref = target.rsplit("@", 1)
            if FULL_SHA_RE.fullmatch(ref) is None:
                violations.append(f"{path}:{line_number}: mutable action ref: {target}")
    return violations


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Fail if external GitHub Actions are not pinned to full commit SHAs.")
    parser.add_argument("workflows_dir", nargs="?", default=".github/workflows")
    args = parser.parse_args(argv)
    workflows_dir = Path(args.workflows_dir)
    if not workflows_dir.is_dir():
        parser.error(f"workflow directory does not exist: {workflows_dir}")
    violations = find_mutable_action_refs(workflows_dir)
    if violations:
        print("github_action_pin_validation=FAIL")
        for violation in violations:
            print(violation)
        return 1
    print("github_action_pin_validation=PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
