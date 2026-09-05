"""Explicitly authorized Gemini provider-success smoke for #359.

This is intentionally separate from credential-free authentication probes. It
can perform a real successful model interaction only when both an exact operator
authorization phrase and a valid Gemini API credential are provided.

The model is hard-coded to Gemma 4 26B MoE IT because current Google pricing
lists Gemma 4 input/output as free of charge with no paid tier. Changing the
model therefore requires a code review rather than a workflow input.
"""

from __future__ import annotations

import json
import os
from typing import Mapping

from metao.adapters.gemini_interactions import (
    GeminiInteractionsOrchestratorAdapter,
    normalize_evidence,
)
from metao.core import ExecutionRequest, ExecutionStatus, Mission


AUTHORIZATION_ENV = "METAO_LIVE_PROVIDER_SUCCESS_AUTHORIZATION"
API_KEY_ENV = "METAO_GEMINI_API_KEY"
AUTHORIZATION_PHRASE = "I_AUTHORIZE_GEMINI_GEMMA4_ZERO_COST_SUCCESS_SMOKE"
TARGET = "gemma-4-26b-a4b-it"
BASE_URL = "https://generativelanguage.googleapis.com/v1"


def require_authorization(env: Mapping[str, str]) -> str:
    """Fail closed before network access unless authorization and key exist."""

    if env.get(AUTHORIZATION_ENV, "") != AUTHORIZATION_PHRASE:
        raise RuntimeError("explicit Gemini live-success authorization is required")
    api_key = env.get(API_KEY_ENV, "").strip()
    if not api_key:
        raise RuntimeError("METAO_GEMINI_API_KEY is required for live-success execution")
    return api_key


def main() -> int:
    api_key = require_authorization(os.environ)
    adapter = GeminiInteractionsOrchestratorAdapter(
        api_key=api_key,
        target=TARGET,
        target_kind="model",
        base_url=BASE_URL,
        orchestrator_id="gemini-interactions",
        version="v1",
        background=False,
        max_polls=3,
        poll_interval_s=0.5,
    )
    request = ExecutionRequest(
        "gemini-gemma4-live-success-smoke",
        Mission(
            "gemini-gemma4-live-success-smoke-mission",
            "Return exactly: METAO_GEMINI_SUCCESS",
            frozenset({"agent"}),
        ),
        {
            "created_at_epoch": 0.0,
            "obligation_id": "provider_success_smoke",
            "subject_id": "gemini-gemma4-live-success-smoke",
            "subject_state_id": "authorized-live-provider-call",
            "verification_context_id": "issue-359-provider-success",
            "policy_bundle_id": "explicit-zero-cost-gemini-gemma4-smoke",
            "authority_id": "explicit-workflow-dispatch",
        },
    )

    result = adapter.execute(request)
    if result.status is not ExecutionStatus.SUCCEEDED:
        raise RuntimeError(
            "Gemini provider-success smoke did not succeed: "
            + json.dumps(
                {
                    "status": result.status.value,
                    "error": result.error,
                    "capacity_status": (
                        result.capacity_observation.capacity_status.value
                        if result.capacity_observation is not None
                        else None
                    ),
                },
                sort_keys=True,
                separators=(",", ":"),
            )
        )

    output = result.output if isinstance(result.output, Mapping) else {}
    interaction = output.get("interaction")
    if not isinstance(interaction, Mapping):
        raise RuntimeError("successful Gemini result is missing interaction evidence")
    interaction_id = interaction.get("id")
    interaction_status = interaction.get("status")
    result_text = output.get("result")
    if not isinstance(interaction_id, str) or not interaction_id.strip():
        raise RuntimeError("successful Gemini interaction is missing id")
    if interaction_status != "completed":
        raise RuntimeError(f"unexpected Gemini interaction status: {interaction_status!r}")
    if not isinstance(result_text, str) or not result_text.strip():
        raise RuntimeError("successful Gemini interaction produced no text output")

    envelope = normalize_evidence(
        request=request,
        orchestrator_id=adapter.descriptor.orchestrator_id,
        adapter_version=adapter.descriptor.version,
        output=result.output,
    )

    evidence = {
        "adapter": adapter.descriptor.orchestrator_id,
        "adapter_version": adapter.descriptor.version,
        "base_url": BASE_URL,
        "endpoint": "/interactions",
        "target": TARGET,
        "target_kind": "model",
        "execution_status": result.status.value,
        "interaction_status": interaction_status,
        "interaction_id_present": True,
        "output_text_present": True,
        "evidence_id": envelope.evidence_id,
        "payload_digest": envelope.payload_digest,
        "credential_value_emitted": False,
        "explicit_authorization_observed": True,
        "provider_backed_execution": "PASS",
        "metao_final_acceptance": "NOT_TESTED",
    }
    print(json.dumps(evidence, sort_keys=True, separators=(",", ":")))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
