from __future__ import annotations

import argparse
from dataclasses import asdict
from hashlib import sha256
import json
import os
from pathlib import Path
import shutil
import subprocess
from typing import Any

from metao.adapters.codex_app_server import (
    CodexAppServerOrchestratorAdapter,
    normalize_evidence,
)
from metao.adapters.codex_app_server_stdio import CodexAppServerStdioTransport
from metao.core import ExecutionRequest, ExecutionStatus, Mission
from metao.project_supervision import (
    ExecutorTarget,
    ProjectObjective,
    ProjectVerdict,
    RepositoryCheckpoint,
    WorkExecutionResult,
    WorkExecutionStatus,
    WorkGraph,
    WorkUnit,
    WorkVerificationResult,
    supervise_project,
)

_EXPECTED_CLI_VERSION = "0.153.3"
_EXECUTOR_ID = "codex-chatgpt-real"
_PROVIDER_ID = "openai-codex-chatgpt"
_MARKERS = {
    "analyze": "METAO_CODEX_REAL_ANALYZE_OK",
    "synthesize": "METAO_CODEX_REAL_SYNTHESIZE_OK",
}


def _run(command: list[str]) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        command,
        check=False,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        encoding="utf-8",
    )


def _require_chatgpt_codex_auth() -> dict[str, str]:
    if os.environ.get("OPENAI_API_KEY", "").strip():
        raise SystemExit(
            "OPENAI_API_KEY must be unset: this pilot requires Codex authenticated through ChatGPT"
        )

    executable = shutil.which("codex")
    if executable is None:
        raise SystemExit("codex CLI is not installed")

    version = _run(["codex", "--version"])
    if version.returncode != 0 or _EXPECTED_CLI_VERSION not in version.stdout:
        raise SystemExit(
            f"expected Codex CLI {_EXPECTED_CLI_VERSION}; observed {version.stdout.strip()!r}"
        )

    status = _run(["codex", "login", "status"])
    normalized = status.stdout.strip().lower()
    if status.returncode != 0 or "chatgpt" not in normalized:
        raise SystemExit(
            "ChatGPT-authenticated Codex session required; run codex login and choose ChatGPT"
        )
    if "api key" in normalized or "workload identity" in normalized:
        raise SystemExit(
            "Codex login status did not prove ChatGPT-plan authentication"
        )
    return {
        "cli_version": version.stdout.strip(),
        "login_status": status.stdout.strip(),
    }


class Planner:
    def plan(self, objective: ProjectObjective) -> WorkGraph:
        return WorkGraph(
            "metao",
            (
                WorkUnit("analyze", "Produce the exact analysis marker."),
                WorkUnit(
                    "synthesize",
                    "Produce the exact synthesis marker.",
                    dependencies=("analyze",),
                ),
            ),
        )

    def corrective_work(self, objective, failed_unit, verification, graph):
        return None


class Scheduler:
    def select(self, unit, *, excluded_executor_ids):
        if _EXECUTOR_ID in excluded_executor_ids:
            return None
        return ExecutorTarget(_EXECUTOR_ID, _PROVIDER_ID)


class Repository:
    def initial(self, objective):
        return RepositoryCheckpoint(
            "checkpoint-root",
            "repo-metao",
            "read-only-root",
            "logical://read-only-root",
        )

    def capture(self, objective, unit, execution):
        return RepositoryCheckpoint(
            f"checkpoint-{unit.work_unit_id}",
            "repo-metao",
            execution.repository_state_id,
            execution.artifact_ref,
        )

    def handoff(self, checkpoint, *, from_executor_id, to_executor_id):
        return checkpoint


class RealCodexRunner:
    def __init__(self, adapter: CodexAppServerOrchestratorAdapter) -> None:
        self.adapter = adapter
        self.outputs: dict[str, dict[str, Any]] = {}
        self.evidence: dict[str, dict[str, Any]] = {}

    def run(self, objective, unit, target, checkpoint):
        marker = _MARKERS[unit.work_unit_id]
        request = ExecutionRequest(
            execution_id=f"{objective.project_id}:{unit.work_unit_id}",
            mission=Mission(
                f"mission-{unit.work_unit_id}",
                (
                    f"Return exactly this text and nothing else: {marker}. "
                    "Do not use tools and do not modify files."
                ),
                frozenset({"agent"}),
            ),
            context={
                "authority_id": "metao-runtime",
                "created_at_epoch": 0.0,
                "obligation_id": f"codex-real:{unit.work_unit_id}",
                "policy_bundle_id": "codex-chatgpt-real-pilot-policy",
                "subject_id": unit.work_unit_id,
                "subject_state_id": checkpoint.state_id,
                "verification_context_id": f"codex-real:{unit.work_unit_id}",
                "verifier_id": "independent-script-verifier",
                "repository_state_id": checkpoint.state_id,
                "work_unit_id": unit.work_unit_id,
            },
        )
        result = self.adapter.execute(request)
        if result.status is not ExecutionStatus.SUCCEEDED:
            return WorkExecutionResult(
                unit.work_unit_id,
                target.executor_id,
                target.provider_id,
                WorkExecutionStatus.FAILED,
                checkpoint.state_id,
                evidence_ref=f"codex-status:{result.status.value}",
            )

        output = dict(result.output or {})
        if marker not in str(output.get("result", "")):
            return WorkExecutionResult(
                unit.work_unit_id,
                target.executor_id,
                target.provider_id,
                WorkExecutionStatus.FAILED,
                checkpoint.state_id,
                evidence_ref="codex-output-marker-missing",
            )
        if str(output.get("diff", "")).strip():
            return WorkExecutionResult(
                unit.work_unit_id,
                target.executor_id,
                target.provider_id,
                WorkExecutionStatus.FAILED,
                checkpoint.state_id,
                evidence_ref="codex-read-only-diff-observed",
            )

        envelope = normalize_evidence(
            request=request,
            orchestrator_id=self.adapter.descriptor.orchestrator_id,
            adapter_version=self.adapter.descriptor.version,
            output=output,
        )
        envelope_dict = asdict(envelope)
        self.outputs[unit.work_unit_id] = output
        self.evidence[unit.work_unit_id] = envelope_dict
        state = "sha256:" + sha256(
            json.dumps(
                {
                    "previous": checkpoint.state_id,
                    "unit": unit.work_unit_id,
                    "payload_digest": envelope_dict["payload_digest"],
                },
                sort_keys=True,
            ).encode()
        ).hexdigest()
        artifact_ref = f"evidence:{envelope_dict['evidence_id']}"
        return WorkExecutionResult(
            unit.work_unit_id,
            target.executor_id,
            target.provider_id,
            WorkExecutionStatus.SUCCEEDED,
            state,
            artifact_ref=artifact_ref,
            evidence_ref=envelope_dict["evidence_id"],
        )


class IndependentVerifier:
    def __init__(self, runner: RealCodexRunner) -> None:
        self.runner = runner

    def verify(self, objective, unit, execution, checkpoint):
        output = self.runner.outputs.get(unit.work_unit_id, {})
        marker = _MARKERS[unit.work_unit_id]
        accepted = marker in str(output.get("result", "")) and not str(
            output.get("diff", "")
        ).strip()
        evidence = self.runner.evidence.get(unit.work_unit_id, {})
        return WorkVerificationResult(
            accepted,
            "independent-script-verifier",
            str(evidence.get("evidence_id", "missing-evidence")),
            f"codex-exact-marker:{unit.work_unit_id}",
            "" if accepted else "Codex output did not satisfy the read-only exact-marker verifier",
        )


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--commit", required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--auth-check-only", action="store_true")
    args = parser.parse_args()

    auth = _require_chatgpt_codex_auth()
    if args.auth_check_only:
        print(
            json.dumps(
                {
                    "classification": "CODEX_CHATGPT_AUTH_CHECK",
                    "cli_version": auth["cli_version"],
                    "chatgpt_login": True,
                    "openai_api_key_present": False,
                },
                sort_keys=True,
            )
        )
        return 0

    with CodexAppServerStdioTransport(
        ("codex", "app-server", "--stdio"),
        stderr_tail_lines=100,
    ) as transport:
        adapter = CodexAppServerOrchestratorAdapter(
            request_fn=transport.request,
            notify_fn=transport.notify,
            read_notification_fn=transport.read_notification,
            cwd=str(Path.cwd().resolve()),
            approval_policy="never",
            sandbox="read-only",
            ephemeral=True,
            orchestrator_id="codex-app-server",
            version="v2",
            max_notifications=2000,
        )
        runner = RealCodexRunner(adapter)
        result = supervise_project(
            objective=ProjectObjective(
                "project-540-codex-real",
                "req-codex-real-project-supervision",
                "Prove real Codex execution under metaO project supervision.",
            ),
            planner=Planner(),
            scheduler=Scheduler(),
            runner=runner,
            repository=Repository(),
            verifier=IndependentVerifier(runner),
            max_executor_attempts_per_unit=1,
            max_corrective_units=0,
        )

    if result.verdict is not ProjectVerdict.PROJECT_ACCEPTED:
        raise AssertionError(f"Codex-backed project was not accepted: {result.reason}")

    evidence_ids = {
        unit_id: evidence["evidence_id"] for unit_id, evidence in runner.evidence.items()
    }
    payload = {
        "schema": "metao-codex-chatgpt-project-pilot-v1",
        "commit": args.commit,
        "classification": "REAL_CODEX_CHATGPT_SINGLE_PROVIDER_PROJECT_SUPERVISION",
        "codex_cli_version": auth["cli_version"],
        "chatgpt_authenticated": True,
        "openai_api_key_present": False,
        "provider_id": _PROVIDER_ID,
        "executor_id": _EXECUTOR_ID,
        "real_codex_provider_turns": len(runner.outputs),
        "work_units": list(_MARKERS),
        "project_verdict": result.verdict.value,
        "traceability_records": len(result.traceability),
        "evidence_ids": evidence_ids,
        "repository_mutation": "NONE_READ_ONLY",
        "real_multi_provider": "NOT_TESTED",
        "provider_failover": "NOT_TESTED",
        "real_cross_provider_handoff": "NOT_PROVEN",
        "claim_boundary": [
            "REAL_CODEX_CHATGPT_SINGLE_PROVIDER != REAL_MULTI_PROVIDER",
            "CHATGPT_PLAN_AUTH != OPENAI_API_KEY",
            "READ_ONLY_LOGICAL_CHECKPOINT != REMOTE_GIT_MUTATION",
            "PROJECT_ACCEPTED_SINGLE_PROVIDER != MULTI_PROVIDER_PILOT_PASS",
        ],
    }

    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n")
    print(json.dumps(payload, sort_keys=True, separators=(",", ":")))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
