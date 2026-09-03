"""Governed GitHub repository operations.

The adapter is deliberately split from metaO governance and orchestration. Reads
are always available; mutations require an explicit MutationAuthorization bound
to the repository, operation, execution and policy bundle.
"""

from __future__ import annotations

import base64
import json
from dataclasses import dataclass
from typing import Any, Mapping, Protocol
from urllib.error import HTTPError
from urllib.request import Request, urlopen


class GitHubAdapterError(RuntimeError):
    """Base error for adapter failures."""


class MutationDenied(GitHubAdapterError):
    """Raised when a mutation does not have matching authority."""


class GitHubTransport(Protocol):
    def request(self, method: str, path: str, body: Mapping[str, Any] | None = None) -> Any: ...


@dataclass(frozen=True)
class MutationAuthorization:
    repository: str
    operation: str
    execution_id: str
    policy_bundle_id: str
    actor_id: str

    def permits(self, repository: str, operation: str) -> bool:
        return bool(self.execution_id) and bool(self.policy_bundle_id) and bool(self.actor_id) and self.repository == repository and self.operation == operation


@dataclass(frozen=True)
class GitHubOperationResult:
    operation: str
    repository: str
    resource: str
    evidence: Mapping[str, Any]


def require_mutation(authorization: MutationAuthorization | None, *, repository: str, operation: str) -> MutationAuthorization:
    if authorization is None or not authorization.permits(repository, operation):
        raise MutationDenied(f"mutation denied: {operation} on {repository}")
    return authorization


class UrllibGitHubTransport:
    """Minimal dependency-free GitHub REST transport."""
    def __init__(self, token: str, *, api_base: str = "https://api.github.com") -> None:
        if not token:
            raise ValueError("GitHub token cannot be empty")
        self._token, self._api_base = token, api_base.rstrip("/")

    def request(self, method: str, path: str, body: Mapping[str, Any] | None = None) -> Any:
        payload = None if body is None else json.dumps(body).encode("utf-8")
        request = Request(f"{self._api_base}/{path.lstrip('/')}", data=payload, method=method.upper(), headers={"Accept": "application/vnd.github+json", "Authorization": f"Bearer {self._token}", "X-GitHub-Api-Version": "2022-11-28", "User-Agent": "metaO-github-adapter", **({"Content-Type": "application/json"} if payload is not None else {})})
        try:
            with urlopen(request) as response:
                raw = response.read()
        except HTTPError as exc:
            detail = exc.read().decode("utf-8", errors="replace")
            raise GitHubAdapterError(f"GitHub API {exc.code}: {detail[:500]}") from exc
        return json.loads(raw) if raw else None


class GitHubRepositoryAdapter:
    """Operational GitHub adapter with fail-closed mutation boundaries."""
    def __init__(self, transport: GitHubTransport) -> None:
        self._transport = transport

    def repository(self, repository: str) -> Any: return self._transport.request("GET", f"repos/{repository}")
    def issue(self, repository: str, number: int) -> Any: return self._transport.request("GET", f"repos/{repository}/issues/{number}")
    def pull_request(self, repository: str, number: int) -> Any: return self._transport.request("GET", f"repos/{repository}/pulls/{number}")
    def pull_request_reviews(self, repository: str, number: int) -> Any: return self._transport.request("GET", f"repos/{repository}/pulls/{number}/reviews")
    def pull_request_review_comments(self, repository: str, number: int) -> Any: return self._transport.request("GET", f"repos/{repository}/pulls/{number}/comments")
    def workflow_run(self, repository: str, run_id: int) -> Any: return self._transport.request("GET", f"repos/{repository}/actions/runs/{run_id}")
    def list_workflow_runs(self, repository: str, *, workflow_id: str | int | None = None, branch: str | None = None, event: str | None = None, status: str | None = None, per_page: int = 30) -> Any:
        if not 1 <= per_page <= 100: raise ValueError("per_page must be between 1 and 100")
        query = [f"per_page={per_page}"]
        for key, value in (("branch", branch), ("event", event), ("status", status)):
            if value: query.append(f"{key}={value}")
        base = f"repos/{repository}/actions/workflows/{workflow_id}/runs" if workflow_id is not None else f"repos/{repository}/actions/runs"
        return self._transport.request("GET", base + "?" + "&".join(query))
    def list_workflow_jobs(self, repository: str, run_id: int, *, filter: str = "latest", per_page: int = 100) -> Any:
        if filter not in {"latest", "all"}: raise ValueError("unsupported jobs filter")
        if not 1 <= per_page <= 100: raise ValueError("per_page must be between 1 and 100")
        return self._transport.request("GET", f"repos/{repository}/actions/runs/{run_id}/jobs?filter={filter}&per_page={per_page}")

    def create_issue(self, repository: str, *, title: str, body: str = "", authorization: MutationAuthorization | None = None) -> GitHubOperationResult:
        require_mutation(authorization, repository=repository, operation="issue.create")
        return self._result("issue.create", repository, self._transport.request("POST", f"repos/{repository}/issues", {"title": title, "body": body}))
    def create_branch(self, repository: str, *, branch: str, sha: str, authorization: MutationAuthorization | None = None) -> GitHubOperationResult:
        require_mutation(authorization, repository=repository, operation="branch.create")
        return self._result("branch.create", repository, self._transport.request("POST", f"repos/{repository}/git/refs", {"ref": f"refs/heads/{branch}", "sha": sha}))
    def create_file(self, repository: str, *, path: str, content: str, message: str, branch: str, authorization: MutationAuthorization | None = None) -> GitHubOperationResult:
        require_mutation(authorization, repository=repository, operation="file.create")
        payload={"message": message, "content": base64.b64encode(content.encode()).decode(), "branch": branch}
        return self._result("file.create", repository, self._transport.request("PUT", f"repos/{repository}/contents/{path}", payload))
    def create_pr(self, repository: str, *, head: str, base: str, title: str, body: str = "", authorization: MutationAuthorization | None = None) -> GitHubOperationResult:
        require_mutation(authorization, repository=repository, operation="pull_request.create")
        return self._result("pull_request.create", repository, self._transport.request("POST", f"repos/{repository}/pulls", {"head": head,"base": base,"title": title,"body": body}))
    def comment_pr(self, repository: str, *, number: int, body: str, authorization: MutationAuthorization | None = None) -> GitHubOperationResult:
        require_mutation(authorization, repository=repository, operation="pull_request.comment")
        return self._result("pull_request.comment", repository, self._transport.request("POST", f"repos/{repository}/issues/{number}/comments", {"body": body}))
    def submit_review(self, repository: str, *, number: int, body: str = "", event: str = "COMMENT", authorization: MutationAuthorization | None = None) -> GitHubOperationResult:
        require_mutation(authorization, repository=repository, operation="pull_request.review.submit")
        if event not in {"APPROVE","REQUEST_CHANGES","COMMENT"}: raise ValueError("unsupported review event")
        return self._result("pull_request.review.submit", repository, self._transport.request("POST", f"repos/{repository}/pulls/{number}/reviews", {"body": body,"event": event}))
    def merge_pr(self, repository: str, *, number: int, expected_head_sha: str, authorization: MutationAuthorization | None = None, merge_method: str = "squash") -> GitHubOperationResult:
        require_mutation(authorization, repository=repository, operation="pull_request.merge")
        if merge_method not in {"merge","squash","rebase"}: raise ValueError("unsupported merge method")
        return self._result("pull_request.merge", repository, self._transport.request("PUT", f"repos/{repository}/pulls/{number}/merge", {"sha": expected_head_sha,"merge_method": merge_method}))

    @staticmethod
    def _result(operation: str, repository: str, payload: Mapping[str, Any]) -> GitHubOperationResult:
        resource=str(payload.get("html_url") or payload.get("url") or payload.get("sha") or "")
        evidence={key: payload[key] for key in ("id","number","sha","ref","merged","message","html_url") if key in payload}
        return GitHubOperationResult(operation, repository, resource, evidence)


__all__=["GitHubAdapterError","MutationDenied","GitHubTransport","MutationAuthorization","GitHubOperationResult","UrllibGitHubTransport","GitHubRepositoryAdapter","require_mutation"]
