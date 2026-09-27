"""SSH work-product applier for configured executor Git workspaces."""

from __future__ import annotations

from base64 import b64encode
from dataclasses import dataclass
from hashlib import sha256
import json
import re

from .core import ExecutionRequest
from .provider_workspace_executor import WorkProductUpdate
from .ssh_git_transport import (
    SshCommandExecutorPort,
    SshGitRepositoryEndpoint,
    SshGitRepositoryTransport,
)

_WORK_UNIT_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]{0,127}$")
_SHA_RE = re.compile(r"^[0-9a-fA-F]{40,64}$")
_WRITE_SCRIPT = (
    "import base64,pathlib,sys;"
    "repo=pathlib.Path(sys.argv[1]).resolve();"
    "rel=pathlib.PurePosixPath(sys.argv[2]);"
    "assert not rel.is_absolute() and '..' not in rel.parts;"
    "dst=(repo/pathlib.Path(*rel.parts)).resolve();"
    "assert repo==dst or repo in dst.parents;"
    "dst.parent.mkdir(parents=True,exist_ok=True);"
    "dst.write_bytes(base64.b64decode(sys.argv[3],validate=True))"
)


@dataclass(frozen=True, slots=True)
class SshGitWorkProductApplier:
    endpoint: SshGitRepositoryEndpoint
    repository_id: str
    executor: SshCommandExecutorPort

    def __post_init__(self) -> None:
        if not self.repository_id or not self.repository_id.strip():
            raise ValueError("repository_id must be non-empty")

    def _git(self, *args: str) -> bytes:
        return self.executor.run(
            self.endpoint,
            ("git", "-C", self.endpoint.repository_locator, *args),
        )

    @staticmethod
    def _context(request: ExecutionRequest) -> tuple[str, str]:
        work_unit_id = request.context.get("work_unit_id")
        state_id = request.context.get("repository_state_id")
        if not isinstance(work_unit_id, str) or not _WORK_UNIT_RE.fullmatch(work_unit_id):
            raise ValueError("execution context requires canonical work_unit_id")
        if not isinstance(state_id, str) or not _SHA_RE.fullmatch(state_id):
            raise ValueError("execution context requires canonical repository_state_id")
        return work_unit_id, state_id

    def apply(self, request: ExecutionRequest, *, provider_output) -> WorkProductUpdate:
        work_unit_id, expected_state = self._context(request)
        transport = SshGitRepositoryTransport(self.executor)
        if transport.observe_clean_head(self.endpoint) != expected_state:
            raise ValueError("SSH executor workspace HEAD does not match dispatched checkpoint")

        payload = (
            json.dumps(
                dict(provider_output),
                sort_keys=True,
                default=str,
                separators=(",", ":"),
            )
            + "\n"
        ).encode()
        relative = f".metao/work-products/{work_unit_id}.json"
        encoded = b64encode(payload).decode("ascii")
        self.executor.run(
            self.endpoint,
            ("python3", "-c", _WRITE_SCRIPT, self.endpoint.repository_locator, relative, encoded),
        )
        self._git("add", "--", relative)
        self._git("commit", "-m", f"metaO work product: {work_unit_id}")

        head = transport.observe_clean_head(self.endpoint)
        if head == expected_state or not _SHA_RE.fullmatch(head):
            raise ValueError("SSH executor workspace did not produce a new canonical commit")
        digest = sha256(payload).hexdigest()
        return WorkProductUpdate(
            repository_state_id=head,
            artifact_ref=f"git://{self.repository_id}/{head}",
            evidence_ref=f"work-product:{work_unit_id}:{digest}",
        )


__all__ = ["SshGitWorkProductApplier"]
