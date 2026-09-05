"""Credential-free live DeepSeek authentication smoke for #359.

This intentionally uses a synthetic invalid API key against the provider's real
Chat Completions endpoint. The smoke proves live HTTP reachability and adapter
normalization of the documented 401 authentication failure. It does not claim a
provider-backed model execution or any paid inference.
"""

from __future__ import annotations

import json

from metao.adapters.deepseek_http import DeepSeekHttpOrchestratorAdapter
from metao.capacity import CapacityStatus
from metao.core import ExecutionRequest, ExecutionStatus, Mission


_INVALID_API_KEY = "metao-intentionally-invalid-live-auth-smoke"


def main() -> int:
    adapter = DeepSeekHttpOrchestratorAdapter(
        api_key=_INVALID_API_KEY,
        model="deepseek-v4-flash",
        base_url="https://api.deepseek.com",
    )
    request = ExecutionRequest(
        "deepseek-live-auth-smoke-exec",
        Mission(
            "deepseek-live-auth-smoke-mission",
            "credential validation only; no provider-backed execution is authorized",
            frozenset({"agent"}),
        ),
        {
            "created_at_epoch": 0.0,
            "subject_id": "deepseek-live-auth-smoke",
            "subject_state_id": "invalid-credential",
            "verification_context_id": "deepseek-live-auth-smoke",
            "policy_bundle_id": "no-paid-inference",
        },
    )

    result = adapter.execute(request)
    observation = result.capacity_observation

    assert result.status is ExecutionStatus.FAILED, result
    assert result.error == "DeepSeek HTTP 401", result.error
    assert observation is not None, result
    assert observation.capacity_status is CapacityStatus.AUTHENTICATION_FAILURE, observation
    assert observation.recovery is None, observation

    evidence = {
        "adapter": adapter.descriptor.orchestrator_id,
        "base_url": "https://api.deepseek.com",
        "endpoint": "/chat/completions",
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
