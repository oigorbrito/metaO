"""Explicitly authorized provider-backed Codex App Server turn smoke for #359/#602.

The smoke starts one ephemeral, read-only Codex App Server thread and executes a
single text-only turn through the production metaO adapter. Provider completion
is execution evidence only; it does not mint metaO final acceptance.
"""

from __future__ import annotations

from dataclasses import asdict
import json
import os
from pathlib import Path
import shutil
import subprocess

from metao.adapters.codex_app_server import (
    CodexAppServerOrchestratorAdapter,
    normalize_evidence,
)
from metao.adapters.codex_app_server_stdio import CodexAppServerStdioTransport
from metao.core import ExecutionRequest, ExecutionStatus, Mission


_AUTHORIZATION = "I_AUTHORIZE_CODEX_PROVIDER_TURN_SMOKE"
_EXPECTED_OUTPUT = "metao-codex-provider-turn-smoke"
_EXPECTED_CLI_VERSION = "0.153.3"


def _require_authorized_environment() -> None:
    if os.environ.get("METAO_CODEX_TURN_SMOKE_AUTHORIZATION") != _AUTHORIZATION:
        raise SystemExit("explicit Codex provider-turn authorization is required")
    if not os.environ.get("OPENAI_API_KEY", "").strip():
        raise SystemExit("OPENAI_API_KEY is required for the Codex provider-turn smoke")


def _codex_version() -> str:
    executable = shutil.which("codex")
    if executable is None:
        raise SystemExit("codex CLI is not installed")
    executable_path = Path(executable).resolve()
    if not executable_path.is_file():
        raise SystemExit("codex CLI path is not a regular file")
    completed = subprocess.run(
        [str(executable_path), "--version"],
        check=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        encoding="utf-8",
    )
    version = completed.stdout.strip()
    if _EXPECTED_CLI_VERSION not in version:
        raise AssertionError(
            f"expected Codex CLI {_EXPECTED_CLI_VERSION}, observed {version!r}"
        )
    return version


def main() -> int:
    _require_authorized_environment()
    cli_version = _codex_version()
    cwd = str(Path.cwd().resolve())

    with CodexAppServerStdioTransport(
        ("codex", "app-server", "--stdio"),
        stderr_tail_lines=100,
    ) as transport:
        adapter = CodexAppServerOrchestratorAdapter(
            request_fn=transport.request,
            notify_fn=transport.notify,
            read_notification_fn=transport.read_notification,
            cwd=cwd,
            approval_policy="never",
            sandbox="read-only",
            ephemeral=True,
            orchestrator_id="codex-app-server",
            version="v2",
            max_notifications=2000,
        )
        request = ExecutionRequest(
            "codex-provider-turn-smoke",
            Mission(
                "codex-provider-turn-smoke",
                f"Return exactly this text and nothing else. Do not use tools or modify files: {_EXPECTED_OUTPUT}",
                frozenset({"agent"}),
            ),
            {
                "authority_id": "metao-runtime",
                "created_at_epoch": 0.0,
                "obligation_id": "provider_success_smoke",
                "policy_bundle_id": "provider-success-smoke-policy",
                "subject_id": "codex-provider-turn-smoke",
                "subject_state_id": "provider-call-1",
                "verification_context_id": "provider-success-smoke",
                "verifier_id": "adapter-observer",
            },
        )
        result = adapter.execute(request)

    if result.status is not ExecutionStatus.SUCCEEDED:
        raise AssertionError(
            f"provider-backed Codex turn did not succeed: {result.status.value}"
        )
    if result.capacity_observation is not None:
        raise AssertionError("successful Codex turn unexpectedly carried capacity failure")

    output = result.output or {}
    if _EXPECTED_OUTPUT not in str(output.get("result", "")):
        raise AssertionError("Codex provider output did not contain the exact smoke marker")
    if str(output.get("diff", "")).strip():
        raise AssertionError("read-only Codex smoke unexpectedly produced a repository diff")

    envelope = normalize_evidence(
        request=request,
        orchestrator_id=adapter.descriptor.orchestrator_id,
        adapter_version=adapter.descriptor.version,
        output=output,
    )
    envelope_dict = asdict(envelope)

    evidence = {
        "adapter": adapter.descriptor.orchestrator_id,
        "adapter_version": adapter.descriptor.version,
        "codex_cli_version": cli_version,
        "thread_ephemeral": True,
        "thread_id_present": bool(output.get("thread_id")),
        "approval_policy": "never",
        "sandbox": "read-only",
        "execution_status": result.status.value,
        "output_marker_present": True,
        "repository_diff_present": False,
        "credential_value_emitted": False,
        "explicit_authorization_observed": True,
        "provider_backed_turn": "PASS",
        "metao_final_acceptance": "NOT_TESTED",
        "evidence_id": envelope_dict["evidence_id"],
        "payload_digest": envelope_dict["payload_digest"],
    }
    print(json.dumps(evidence, sort_keys=True, separators=(",", ":")))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
