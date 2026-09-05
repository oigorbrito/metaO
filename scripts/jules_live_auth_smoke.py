"""Credential-free live Jules authentication smoke for #359.

The smoke uses the production Jules urllib transport against the documented
read-only List Sessions endpoint. A synthetic invalid API key is intentional.
No session is created, no repository is touched, and no paid/provider-backed
execution is authorized.
"""

from __future__ import annotations

import json

from metao.adapters.jules_http import (
    JulesHttpError,
    JulesHttpOrchestratorAdapter,
    _capacity_observation_from_http_error,
)
from metao.capacity import CapacityStatus


_INVALID_API_KEY = "metao-intentionally-invalid-jules-live-auth-smoke"
_BASE_URL = "https://jules.googleapis.com/v1alpha"
_PATH = "/sessions?pageSize=1"


def main() -> int:
    adapter = JulesHttpOrchestratorAdapter(
        api_key=_INVALID_API_KEY,
        base_url=_BASE_URL,
        max_polls=1,
        poll_interval_s=0.0,
    )

    try:
        adapter._default_transport("GET", _PATH, None)
    except JulesHttpError as exc:
        assert exc.status_code == 401, exc.status_code
        observation = _capacity_observation_from_http_error(
            exc,
            created_at_epoch=0.0,
        )
        assert observation is not None, observation
        assert observation.capacity_status is CapacityStatus.AUTHENTICATION_FAILURE, observation
        assert observation.recovery is None, observation

        evidence = {
            "adapter": adapter.descriptor.orchestrator_id,
            "base_url": _BASE_URL,
            "endpoint": "/sessions",
            "http_method": "GET",
            "page_size": 1,
            "observed_http_status": exc.status_code,
            "capacity_status": observation.capacity_status.value,
            "recovery": None,
            "synthetic_invalid_credential": True,
            "credential_value_emitted": False,
            "session_created": False,
            "repository_touched": False,
            "paid_inference_authorized": False,
            "provider_backed_execution": "NOT_TESTED",
        }
        print(json.dumps(evidence, sort_keys=True, separators=(",", ":")))
        return 0

    raise AssertionError("synthetic invalid Jules API key unexpectedly listed sessions")


if __name__ == "__main__":
    raise SystemExit(main())
