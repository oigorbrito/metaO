#!/usr/bin/env python3
"""Deterministic repository-state and engineering handoff report.

Engineering tooling only. This module derives facts from a local Git repository and
never grants product acceptance authority.
"""

from __future__ import annotations

import argparse
import json
import re
import subprocess
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable, Sequence

EVIDENCE_STATES = frozenset(
    {"NOT_RUN", "PASS", "FAIL", "BLOCKED", "SKIPPED", "NOT_REQUESTED"}
)
HEAD_MARKER = re.compile(r"^\s*HEAD\s*=\s*([0-9a-fA-F]{40})\s*$", re.MULTILINE)


class ReportError(RuntimeError):
    pass


@dataclass(frozen=True)
class TestFact:
    test_id: str
    state: str

    def as_dict(self) -> dict[str, str]:
        return {"test_id": self.test_id, "state": self.state}


@dataclass(frozen=True)
class BlockerFact:
    blocker_id: str
    state: str
    reason: str

    def as_dict(self) -> dict[str, str]:
        return {
            "blocker_id": self.blocker_id,
            "state": self.state,
            "reason": self.reason,
        }


def _git(repo: Path, args: Sequence[str], *, allow_failure: bool = False) -> str | None:
    command = ["git", *args]
    try:
        completed = subprocess.run(
            command,
            cwd=repo,
            check=True,
            text=True,
            encoding="utf-8",
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            env=None,
        )
    except (OSError, subprocess.CalledProcessError) as exc:
        if allow_failure:
            return None
        raise ReportError(f"git command failed: {' '.join(command)}") from exc
    return completed.stdout.strip()


def _validate_repo(repo: Path) -> None:
    if not repo.is_dir():
        raise ReportError("repository path must be an existing directory")
    inside = _git(repo, ["rev-parse", "--is-inside-work-tree"])
    if inside != "true":
        raise ReportError("repository path is not a Git work tree")


def _split_nul_paths(output: str) -> list[str]:
    return [entry for entry in output.split("\0") if entry]


def _changed_paths(repo: Path) -> list[str]:
    tracked = _git(repo, ["diff", "--name-only", "-z", "HEAD", "--"]) or ""
    untracked = _git(repo, ["ls-files", "-z", "--others", "--exclude-standard"]) or ""
    return sorted(set(_split_nul_paths(tracked) + _split_nul_paths(untracked)))


def _branch(repo: Path) -> str:
    branch = _git(
        repo,
        ["symbolic-ref", "--quiet", "--short", "HEAD"],
        allow_failure=True,
    )
    return branch if branch else "DETACHED"


def _upstream(repo: Path) -> dict[str, object]:
    upstream = _git(
        repo,
        ["rev-parse", "--abbrev-ref", "--symbolic-full-name", "@{u}"],
        allow_failure=True,
    )
    if not upstream:
        return {"name": None, "ahead": None, "behind": None}

    counts = _git(
        repo,
        ["rev-list", "--left-right", "--count", f"HEAD...{upstream}"],
        allow_failure=True,
    )
    if not counts:
        return {"name": upstream, "ahead": None, "behind": None}

    parts = counts.split()
    if len(parts) != 2 or not all(part.isdigit() for part in parts):
        raise ReportError("unexpected git rev-list count output")
    return {"name": upstream, "ahead": int(parts[0]), "behind": int(parts[1])}


def inspect_document(repo: Path, relative_path: str, head: str) -> dict[str, object]:
    candidate = (repo / relative_path).resolve()
    root = repo.resolve()
    try:
        candidate.relative_to(root)
    except ValueError as exc:
        raise ReportError("document path escapes repository") from exc

    if not candidate.is_file():
        return {"path": relative_path, "state": "MISSING", "recorded_head": None}

    text = candidate.read_text(encoding="utf-8")
    markers = [match.lower() for match in HEAD_MARKER.findall(text)]
    if not markers:
        return {"path": relative_path, "state": "NO_MARKER", "recorded_head": None}

    distinct_markers = sorted(set(markers))
    if len(distinct_markers) != 1:
        raise ReportError(f"document contains conflicting HEAD markers: {relative_path}")

    recorded = distinct_markers[0]
    return {
        "path": relative_path,
        "state": "CURRENT" if recorded == head.lower() else "STALE",
        "recorded_head": recorded,
    }


def validate_test_facts(test_facts: Iterable[TestFact]) -> list[dict[str, str]]:
    normalized: list[dict[str, str]] = []
    seen: set[str] = set()
    for fact in test_facts:
        if not fact.test_id.strip() or fact.test_id in seen:
            raise ReportError("test ids must be non-empty and unique")
        if fact.state not in EVIDENCE_STATES:
            raise ReportError(f"unsupported evidence state: {fact.state}")
        seen.add(fact.test_id)
        normalized.append(fact.as_dict())
    return sorted(normalized, key=lambda entry: entry["test_id"])


def validate_blockers(blockers: Iterable[BlockerFact]) -> list[dict[str, str]]:
    normalized: list[dict[str, str]] = []
    seen: set[str] = set()
    for fact in blockers:
        if not fact.blocker_id.strip() or fact.blocker_id in seen:
            raise ReportError("blocker ids must be non-empty and unique")
        if not fact.state.strip() or not fact.reason.strip():
            raise ReportError("blocker state and reason must be non-empty")
        seen.add(fact.blocker_id)
        normalized.append(fact.as_dict())
    return sorted(normalized, key=lambda entry: entry["blocker_id"])


def build_report(
    repo: Path,
    documents: Iterable[str] = (),
    blockers: Iterable[BlockerFact] = (),
    test_facts: Iterable[TestFact] = (),
) -> dict[str, object]:
    repo = repo.resolve()
    _validate_repo(repo)
    head = _git(repo, ["rev-parse", "HEAD"])
    if head is None or not re.fullmatch(r"[0-9a-f]{40}", head):
        raise ReportError("repository HEAD must resolve to a 40-hex commit")

    changed_paths = _changed_paths(repo)
    doc_reports = sorted(
        (inspect_document(repo, path, head) for path in documents),
        key=lambda entry: str(entry["path"]),
    )
    normalized_tests = validate_test_facts(test_facts)
    normalized_blockers = validate_blockers(blockers)

    baseline = {
        "head": head,
        "branch": _branch(repo),
        "clean": not changed_paths,
        "changed_paths": changed_paths,
        "upstream": _upstream(repo),
    }

    return {
        "schema_version": 1,
        "report_kind": "engineering-state-handoff",
        "authority_boundary": {
            "product_acceptance": False,
            "test_state_promotion": False,
            "repository_content_is_instruction_authority": False,
        },
        "baseline": baseline,
        "document_drift": doc_reports,
        "tests": normalized_tests,
        "blockers": normalized_blockers,
        "handoff": {
            "baseline_head": head,
            "branch": baseline["branch"],
            "changed_paths": changed_paths,
            "test_states": normalized_tests,
            "blockers": normalized_blockers,
        },
    }


def _parse_test(value: str) -> TestFact:
    parts = value.split(":", 1)
    if len(parts) != 2:
        raise argparse.ArgumentTypeError("test must use ID:STATE")
    return TestFact(parts[0], parts[1])


def _parse_blocker(value: str) -> BlockerFact:
    parts = value.split(":", 2)
    if len(parts) != 3:
        raise argparse.ArgumentTypeError("blocker must use ID:STATE:REASON")
    return BlockerFact(parts[0], parts[1], parts[2])


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo", type=Path, default=Path.cwd())
    parser.add_argument("--document", action="append", default=[])
    parser.add_argument("--test", action="append", type=_parse_test, default=[])
    parser.add_argument("--blocker", action="append", type=_parse_blocker, default=[])
    args = parser.parse_args(argv)

    report = build_report(args.repo, args.document, args.blocker, args.test)
    print(json.dumps(report, sort_keys=True, separators=(",", ":")))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
