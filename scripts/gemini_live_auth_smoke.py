"""Credential-free live Gemini authentication smoke for #359.

This intentionally uses a synthetic invalid API key against the provider's real
Interactions endpoint. The smoke proves live HTTP reachability and production
adapter normalization of the documented 401 authentication failure. It does not
claim provider-backed model execution or authorize paid inference.
"""

from __future__ import annotations

import json

from metao.adapters.gemini_interactions import GeminiInteractionsOrchestratorAdapter
from metao.capacity import CapacityStatus
from metao.core import ExecutionRequest, ExecutionStatus, Mission


_INVALID_API_KEY = "metao-intentionally-invalid-live-auth-smoke"


def main() -> int:
    adapter = GeminiInteractionsOrchestratorAdapter(
        api_key=_INVALID_API_KEY,
        target="gemini-3.8-flash",
        target_kind="model",
        base_url="https://generativelanguage.googleapis.com/v1beta",
        max_polls=1,
        poll_interval_s=0.0,
    )
    request = ExecutionRequest(
        "gemini-live-auth-smoke-exec",
        Mission(
            "gemini-live-auth-smoke-mission",
            "credential validation only; no provider-backed execution is authorized",
            frozenset({"agent"}),
        ),
        {
            "created_at_epoch": 0.0,
            "subject_id": "gemini-live-auth-smoke",
            "subject_state_id": "invalid-credential",
            "verification_context_id": "gemini-live-auth-smoke",
            "policy_bundle_id": "no-paid-inference",
        },
    )

    result = adapter.execute(request)
    observation = result.capacity_observation

    assert result.status is ExecutionStatus.FAILED, result
    assert result.error is not None and result.error.startswith("Gemini HTTP 401"), result.error
    assert observation is not None, result
    assert observation.capacity_status is CapacityStatus.AUTHENTICATION_FAILURE, observation
    assert observation.recovery is None, observation

    evidence = {
        "adapter": adapter.descriptor.orchestrator_id,
        "base_url": "https://generativelanguage.googleapis.com/v1beta",
        "endpoint": "/interactions",
        "execution_status": result.status.value,
        "observed_http_status": 401,
        "capacity_status": observation.capacity_status.value,
        "recovery": None,
        "synthetic_invalid_credential": True,
        "provider_backed_execution": "NOT_TESTED",
        "paid_inference_authorized": False,
    }
    print(json.dumps(evidence, sort_keys=True, separators=(",", ":")))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
