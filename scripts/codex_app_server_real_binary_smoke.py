"""Real Codex App Server binary compatibility smoke for #359.

This smoke deliberately stops before ``turn/start``. It proves that the pinned
real Codex CLI/App Server binary can complete the published initialization and
thread-creation protocol through metaO's production stdio transport. It does
not prove credential-backed model execution and must not be cited as such.
"""

from __future__ import annotations

import json
import os
from pathlib import Path

from metao.adapters.codex_app_server_stdio import CodexAppServerStdioTransport


def _nonempty_string(value: object, *, field: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise AssertionError(f"Codex App Server response missing non-empty {field}")
    return value


def main() -> int:
    cwd = str(Path.cwd().resolve())
    command = ("codex", "app-server", "--stdio")

    with CodexAppServerStdioTransport(command, stderr_tail_lines=100) as transport:
        initialized = transport.request(
            "initialize",
            {
                "clientInfo": {
                    "name": "metao_real_binary_smoke",
                    "title": "metaO real Codex binary smoke",
                    "version": "1",
                }
            },
        )
        transport.notify("initialized", {})

        user_agent = _nonempty_string(initialized.get("userAgent"), field="userAgent")

        thread_result = transport.request(
            "thread/start",
            {
                "cwd": cwd,
                "ephemeral": True,
                "approvalPolicy": "on-request",
                "sandbox": "workspace-write",
            },
        )
        thread = thread_result.get("thread")
        if not isinstance(thread, dict):
            raise AssertionError("Codex thread/start response missing thread object")
        thread_id = _nonempty_string(thread.get("id"), field="thread.id")
        if thread.get("ephemeral") is not True:
            raise AssertionError(
                f"Codex thread/start did not preserve ephemeral=true: {thread.get('ephemeral')!r}"
            )

        evidence = {
            "binary": "codex",
            "protocol": "app-server-stdio",
            "initialize": "PASS",
            "thread_start": "PASS",
            "thread_ephemeral": True,
            "thread_id_present": bool(thread_id),
            "user_agent": user_agent,
            "provider_turn_started": False,
            "provider_backed_execution": "NOT_TESTED",
            "openai_api_key_present": bool(os.environ.get("OPENAI_API_KEY")),
        }
        print(json.dumps(evidence, sort_keys=True, separators=(",", ":")))

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
