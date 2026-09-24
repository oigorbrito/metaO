"""Minimal read-only GitHub Actions adapter for frozen F2 qualification.

Derived from internal donor PR #364 at
1c9a9728ec4ba69a59c7ae722e06d13616b73fb0.

This qualification slice intentionally excludes all mutation operations and
mutation-authorization types. It exists only to acquire exact workflow-run and
workflow-job evidence for research fixture F2.
"""

from __future__ import annotations

import json
from typing import Any, Mapping, Protocol
from urllib.error import HTTPError
from urllib.request import Request, urlopen


class GitHubAdapterError(RuntimeError):
    """Base error for GitHub read failures."""


class GitHubTransport(Protocol):
    def request(self, method: str, path: str, body: Mapping[str, Any] | None = None) -> Any: ...


class UrllibGitHubTransport:
    """Dependency-free GitHub REST transport for read-only qualification."""

    def __init__(self, token: str, *, api_base: str = "https://api.github.com") -> None:
        if not token:
            raise ValueError("GitHub token cannot be empty")
        self._token = token
        self._api_base = api_base.rstrip("/")

    def request(self, method: str, path: str, body: Mapping[str, Any] | None = None) -> Any:
        method = method.upper()
        if method != "GET":
            raise GitHubAdapterError("qualification transport is read-only")
        if body is not None:
            raise GitHubAdapterError("GET qualification requests cannot include a body")

        request = Request(
            f"{self._api_base}/{path.lstrip('/')}",
            method="GET",
            headers={
                "Accept": "application/vnd.github+json",
                "Authorization": f"Bearer {self._token}",
                "X-GitHub-Api-Version": "2022-11-28",
                "User-Agent": "metaO-github-adapter-f2-qualification",
            },
        )
        try:
            with urlopen(request) as response:
                raw = response.read()
        except HTTPError as exc:
            detail = exc.read().decode("utf-8", errors="replace")
            raise GitHubAdapterError(f"GitHub API {exc.code}: {detail[:500]}") from exc
        return json.loads(raw) if raw else None


class GitHubRepositoryAdapter:
    """Read-only repository adapter containing only frozen F2 mechanics."""

    def __init__(self, transport: GitHubTransport) -> None:
        self._transport = transport

    def workflow_run(self, repository: str, run_id: int) -> Any:
        if not repository:
            raise ValueError("repository cannot be empty")
        if run_id <= 0:
            raise ValueError("run_id must be positive")
        return self._transport.request("GET", f"repos/{repository}/actions/runs/{run_id}")

    def list_workflow_jobs(
        self,
        repository: str,
        run_id: int,
        *,
        filter: str = "latest",
        per_page: int = 100,
    ) -> Any:
        if not repository:
            raise ValueError("repository cannot be empty")
        if run_id <= 0:
            raise ValueError("run_id must be positive")
        if filter not in {"latest", "all"}:
            raise ValueError("unsupported jobs filter")
        if not 1 <= per_page <= 100:
            raise ValueError("per_page must be between 1 and 100")
        return self._transport.request(
            "GET",
            f"repos/{repository}/actions/runs/{run_id}/jobs?filter={filter}&per_page={per_page}",
        )


__all__ = [
    "GitHubAdapterError",
    "GitHubTransport",
    "UrllibGitHubTransport",
    "GitHubRepositoryAdapter",
]
