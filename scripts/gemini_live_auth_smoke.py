"""Credential-free live Gemini authentication smoke for #359.

This uses the production Gemini Interactions adapter and its default urllib
transport against the real provider endpoint. A synthetic invalid credential is
used so no paid inference is authorized. PASS is deliberately narrow: the live
HTTP 400 must be normalized to AUTHENTICATION_FAILURE through the exact
structured Google ErrorInfo API_KEY_INVALID rule in the production adapter.
"""

from __future__ import annotations

import json

from metao.adapters.gemini_interactions import GeminiInteractionsOrchestratorAdapter
from metao.capacity import CapacityStatus
from metao.core import ExecutionRequest, ExecutionStatus, Mission


_INVALID_API_KEY = "metao-intentionally-invalid-live-auth-smoke"
_BASE_URL = "https://generativelanguage.googleapis.com/v1beta"


def main() -> int:
    adapter = GeminiInteractionsOrchestratorAdapter(
        api_key=_INVALID_API_KEY,
        target="gemini-3.8-flash",
        target_kind="model",
        base_url=_BASE_URL,
        max_polls=1,
        poll_interval_s=0.0,
    )
    request = ExecutionRequest(
        "gemini-live-auth-smoke",
        Mission(
            "gemini-live-auth-smoke-mission",
            "validate authentication normalization only; do not perform paid inference",
            frozenset({"agent"}),
        ),
        {},
    )

    result = adapter.execute(request)
    assert result.status is ExecutionStatus.FAILED, result
    assert result.error is not None and result.error.startswith("Gemini HTTP 400"), result.error
    assert result.capacity_observation is not None, result
    assert (
        result.capacity_observation.capacity_status
        is CapacityStatus.AUTHENTICATION_FAILURE
    ), result.capacity_observation
    assert result.capacity_observation.recovery is None, result.capacity_observation

    evidence = {
        "adapter": adapter.descriptor.orchestrator_id,
        "base_url": _BASE_URL,
        "endpoint": "/interactions",
        "execution_status": result.status.value,
        "observed_http_status": 400,
        "structured_provider_reason": "API_KEY_INVALID",
        "structured_provider_domain": "googleapis.com",
        "capacity_status": result.capacity_observation.capacity_status.value,
        "recovery": None,
        "synthetic_invalid_credential": True,
        "credential_value_emitted": False,
        "paid_inference_authorized": False,
        "provider_backed_execution": "NOT_TESTED",
        "antigravity_managed_agent_execution": "NOT_TESTED",
    }
    print(json.dumps(evidence, sort_keys=True, separators=(",", ":")))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
