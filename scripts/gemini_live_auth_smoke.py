"""Credential-free live Gemini authentication diagnostic for #359.

This intentionally uses a synthetic invalid API key against the provider's real
Interactions endpoint. The diagnostic captures only machine-readable error
metadata needed to decide whether an observed HTTP 400 is specifically an API
key authentication failure. It never prints the credential or authorizes paid
inference.
"""

from __future__ import annotations

import json
from typing import Any, Mapping

from metao.adapters.gemini_interactions import (
    GeminiHttpError,
    GeminiInteractionsOrchestratorAdapter,
)


_INVALID_API_KEY = "metao-intentionally-invalid-live-auth-smoke"


def _structured_error(body: Any) -> tuple[str | None, tuple[dict[str, str], ...]]:
    if not isinstance(body, Mapping):
        return None, ()
    error = body.get("error")
    if not isinstance(error, Mapping):
        return None, ()

    status = error.get("status")
    status_value = status if isinstance(status, str) and status.strip() else None
    details = error.get("details")
    if not isinstance(details, list):
        return status_value, ()

    sanitized: list[dict[str, str]] = []
    for item in details:
        if not isinstance(item, Mapping):
            continue
        reason = item.get("reason")
        domain = item.get("domain")
        entry: dict[str, str] = {}
        if isinstance(reason, str) and reason.strip():
            entry["reason"] = reason
        if isinstance(domain, str) and domain.strip():
            entry["domain"] = domain
        type_name = item.get("@type")
        if isinstance(type_name, str) and type_name.strip():
            entry["type"] = type_name
        if entry:
            sanitized.append(entry)
    return status_value, tuple(sanitized)


def main() -> int:
    adapter = GeminiInteractionsOrchestratorAdapter(
        api_key=_INVALID_API_KEY,
        target="gemini-3.8-flash",
        target_kind="model",
        base_url="https://generativelanguage.googleapis.com/v1beta",
        max_polls=1,
        poll_interval_s=0.0,
    )

    payload = {
        "model": "gemini-3.8-flash",
        "input": "credential validation only; no provider-backed execution is authorized",
    }

    try:
        adapter._default_transport("POST", "/interactions", payload)
    except GeminiHttpError as exc:
        error_status, details = _structured_error(exc.body)
        evidence = {
            "adapter": adapter.descriptor.orchestrator_id,
            "base_url": "https://generativelanguage.googleapis.com/v1beta",
            "endpoint": "/interactions",
            "observed_http_status": exc.status_code,
            "provider_error_status": error_status,
            "provider_error_details": list(details),
            "synthetic_invalid_credential": True,
            "credential_value_emitted": False,
            "capacity_classification": "NOT_YET_QUALIFIED",
            "provider_backed_execution": "NOT_TESTED",
            "paid_inference_authorized": False,
        }
        print(json.dumps(evidence, sort_keys=True, separators=(",", ":")))
        return 0

    raise AssertionError("synthetic invalid Gemini API key unexpectedly succeeded")


if __name__ == "__main__":
    raise SystemExit(main())
