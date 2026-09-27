#!/usr/bin/env python3
"""Evaluate local branch/change hygiene against metaO repository review budgets.

This guard is intentionally narrow. It measures repository state and change size;
it does not claim code quality, test success, or metaO Acceptance.
"""

from __future__ import annotations

import argparse
import enum
import subprocess
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable


SOFT_FILE_LIMIT = 20
SOFT_LINE_LIMIT = 600
BLOCK_FILE_LIMIT = 40
BLOCK_LINE_LIMIT = 1200

EXCEPTION_ELIGIBLE_CLASSES = {
    "MECHANICAL",
    "GENERATED",
    "DEPENDENCY_VENDOR",
    "EVIDENCE_ARTIFACT",
    "MIGRATION",
}


class BudgetState(str, enum.Enum):
    PASS = "PASS"
    WARN = "WARN"
    BLOCK = "BLOCK"


@dataclass(frozen=True)
class ChangeSnapshot:
    branch: str
    head_sha: str
    base_ref: str
    base_sha: str
    merge_base_sha: str
    changed_files: int
    additions: int
    deletions: int
    ahead: int
    behind: int
    worktree_clean: bool

    @property
    def changed_lines(self) -> int:
        return self.additions + self.deletions


@dataclass(frozen=True)
class Evaluation:
    state: BudgetState
    reasons: tuple[str, ...]


def evaluate(
    snapshot: ChangeSnapshot,
    *,
    change_class: str,
    exception_id: str | None = None,
    require_clean: bool = True,
    require_current_base: bool = False,
) -> Evaluation:
    change_class = change_class.upper()
    reasons: list[str] = []
    blocked = False
    warned = False

    if snapshot.branch in {"main", "master"}:
        blocked = True
        reasons.append("work must be evaluated from a dedicated non-canonical branch")

    if snapshot.ahead <= 0:
        blocked = True
        reasons.append("branch has no commits ahead of the selected base")

    if require_clean and not snapshot.worktree_clean:
        blocked = True
        reasons.append("worktree is dirty at the requested hygiene boundary")

    if snapshot.behind > 0:
        message = f"branch is {snapshot.behind} commit(s) behind {snapshot.base_ref}"
        if require_current_base:
            blocked = True
            reasons.append(message)
        else:
            warned = True
            reasons.append(message)

    over_block = (
        snapshot.changed_files > BLOCK_FILE_LIMIT
        or snapshot.changed_lines > BLOCK_LINE_LIMIT
    )
    over_soft = (
        snapshot.changed_files > SOFT_FILE_LIMIT
        or snapshot.changed_lines > SOFT_LINE_LIMIT
    )

    if over_block:
        if change_class in EXCEPTION_ELIGIBLE_CLASSES and exception_id:
            warned = True
            reasons.append(
                "normal review budget exceeded under explicit large-change exception "
                f"{exception_id}"
            )
        else:
            blocked = True
            reasons.append(
                "normal review budget exceeded: "
                f"{snapshot.changed_files} files / {snapshot.changed_lines} lines; "
                "decompose or use an eligible explicit exception"
            )
    elif over_soft:
        warned = True
        reasons.append(
            "soft decomposition trigger crossed: "
            f"{snapshot.changed_files} files / {snapshot.changed_lines} lines"
        )

    if blocked:
        return Evaluation(BudgetState.BLOCK, tuple(reasons))
    if warned:
        return Evaluation(BudgetState.WARN, tuple(reasons))
    return Evaluation(BudgetState.PASS, tuple(reasons))


def _git(repo: Path, *args: str) -> str:
    completed = subprocess.run(
        ["git", "-C", str(repo), *args],
        check=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
    )
    return completed.stdout.strip()


def _parse_numstat(lines: Iterable[str]) -> tuple[int, int]:
    additions = 0
    deletions = 0
    for line in lines:
        if not line:
            continue
        added, deleted, *_ = line.split("\t")
        if added.isdigit():
            additions += int(added)
        if deleted.isdigit():
            deletions += int(deleted)
    return additions, deletions


def collect_snapshot(repo: Path, base_ref: str) -> ChangeSnapshot:
    branch = _git(repo, "rev-parse", "--abbrev-ref", "HEAD")
    head_sha = _git(repo, "rev-parse", "HEAD")
    base_sha = _git(repo, "rev-parse", base_ref)
    merge_base_sha = _git(repo, "merge-base", base_ref, "HEAD")

    names = _git(repo, "diff", "--name-only", f"{merge_base_sha}..HEAD")
    changed_files = len([line for line in names.splitlines() if line.strip()])

    numstat = _git(repo, "diff", "--numstat", f"{merge_base_sha}..HEAD")
    additions, deletions = _parse_numstat(numstat.splitlines())

    divergence = _git(repo, "rev-list", "--left-right", "--count", f"{base_ref}...HEAD")
    behind_text, ahead_text = divergence.split()

    status = _git(repo, "status", "--porcelain", "--untracked-files=normal")

    return ChangeSnapshot(
        branch=branch,
        head_sha=head_sha,
        base_ref=base_ref,
        base_sha=base_sha,
        merge_base_sha=merge_base_sha,
        changed_files=changed_files,
        additions=additions,
        deletions=deletions,
        ahead=int(ahead_text),
        behind=int(behind_text),
        worktree_clean=not bool(status),
    )


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Check metaO local/branch/PR hygiene against repository review budgets."
    )
    parser.add_argument("--repo", default=".", help="repository worktree path")
    parser.add_argument("--base-ref", default="origin/main")
    parser.add_argument(
        "--change-class",
        default="ORDINARY",
        choices=[
            "ORDINARY",
            "DOCUMENTATION",
            "MECHANICAL",
            "GENERATED",
            "DEPENDENCY_VENDOR",
            "EVIDENCE_ARTIFACT",
            "MIGRATION",
        ],
    )
    parser.add_argument("--exception-id")
    parser.add_argument(
        "--allow-dirty",
        action="store_true",
        help="diagnostic only; do not require a clean worktree",
    )
    parser.add_argument(
        "--require-current-base",
        action="store_true",
        help="block when the branch is behind the selected base ref",
    )
    return parser


def main() -> int:
    args = _parser().parse_args()
    snapshot = collect_snapshot(Path(args.repo).resolve(), args.base_ref)
    result = evaluate(
        snapshot,
        change_class=args.change_class,
        exception_id=args.exception_id,
        require_clean=not args.allow_dirty,
        require_current_base=args.require_current_base,
    )

    print(f"branch={snapshot.branch}")
    print(f"head_sha={snapshot.head_sha}")
    print(f"base_ref={snapshot.base_ref}")
    print(f"base_sha={snapshot.base_sha}")
    print(f"merge_base_sha={snapshot.merge_base_sha}")
    print(f"change_class={args.change_class}")
    print(f"changed_files={snapshot.changed_files}")
    print(f"changed_lines={snapshot.changed_lines}")
    print(f"additions={snapshot.additions}")
    print(f"deletions={snapshot.deletions}")
    print(f"ahead={snapshot.ahead}")
    print(f"behind={snapshot.behind}")
    print(f"worktree_clean={str(snapshot.worktree_clean).lower()}")
    print(f"budget_state={result.state.value}")
    for reason in result.reasons:
        print(f"reason={reason}")

    if result.state is BudgetState.PASS:
        return 0
    if result.state is BudgetState.WARN:
        return 2
    return 3


if __name__ == "__main__":
    raise SystemExit(main())
