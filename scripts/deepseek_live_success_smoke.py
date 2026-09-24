"""Explicitly authorized provider-backed DeepSeek success smoke for #359/#598.

The smoke performs one bounded stateless Chat Completions call through the
production metaO DeepSeek adapter. Provider success remains execution evidence
only and never becomes metaO final acceptance.
"""

from __future__ import annotations

from dataclasses import asdict
import json
import os

from metao.adapters.deepseek_http import (
    DeepSeekHttpOrchestratorAdapter,
    normalize_evidence,
)
from metao.core import ExecutionRequest, ExecutionStatus, Mission


_AUTHORIZATION = "I_AUTHORIZE_DEEPSEEK_PROVIDER_SUCCESS_SMOKE"
_MODEL = "deepseek-v4-flash"
_EXPECTED_OUTPUT = "metao-deepseek-provider-success-smoke"


def _authorized_api_key() -> str:
    if os.environ.get("METAO_DEEPSEEK_SUCCESS_AUTHORIZATION") != _AUTHORIZATION:
        raise SystemExit("explicit DeepSeek provider-success authorization is required")
    api_key = os.environ.get("METAO_DEEPSEEK_API_KEY", "").strip()
    if not api_key:
        raise SystemExit("METAO_DEEPSEEK_API_KEY is required")
    return api_key


def main() -> int:
    api_key = _authorized_api_key()
    adapter = DeepSeekHttpOrchestratorAdapter(
        api_key=api_key,
        model=_MODEL,
        orchestrator_id="deepseek",
        version="v1",
    )
    request = ExecutionRequest(
        "deepseek-provider-success-smoke",
        Mission(
            "deepseek-provider-success-smoke",
            f"Return exactly this text and nothing else: {_EXPECTED_OUTPUT}",
            frozenset({"agent"}),
        ),
        {
            "authority_id": "metao-runtime",
            "created_at_epoch": 0.0,
            "obligation_id": "provider_success_smoke",
            "policy_bundle_id": "provider-success-smoke-policy",
            "subject_id": "deepseek-provider-success-smoke",
            "subject_state_id": "provider-call-1",
            "verification_context_id": "provider-success-smoke",
            "verifier_id": "adapter-observer",
        },
    )

    result = adapter.execute(request)
    if result.status is not ExecutionStatus.SUCCEEDED:
        raise AssertionError(
            f"provider-backed DeepSeek execution did not succeed: {result.status.value}"
        )
    if result.capacity_observation is not None:
        raise AssertionError("successful provider execution unexpectedly carried capacity failure")

    output = result.output or {}
    serialized_output = json.dumps(output, sort_keys=True, default=str)
    if _EXPECTED_OUTPUT not in serialized_output:
        raise AssertionError("provider output did not contain the exact smoke marker")

    finish_reason = str(output.get("finish_reason", ""))
    if finish_reason not in {"stop", "length"}:
        raise AssertionError(f"unexpected successful finish reason: {finish_reason!r}")

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
        "base_url": "https://api.deepseek.com",
        "endpoint": "/chat/completions",
        "model": _MODEL,
        "execution_status": result.status.value,
        "finish_reason": finish_reason,
        "output_marker_present": True,
        "credential_value_emitted": False,
        "explicit_authorization_observed": True,
        "provider_backed_execution": "PASS",
        "metao_final_acceptance": "NOT_TESTED",
        "evidence_id": envelope_dict["evidence_id"],
        "payload_digest": envelope_dict["payload_digest"],
    }
    print(json.dumps(evidence, sort_keys=True, separators=(",", ":")))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
