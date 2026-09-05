"""Credential-free live Gemini authentication diagnostic for #359.

The diagnostic sends a synthetic invalid API key to the real Interactions
endpoint and emits only non-secret structural metadata from the error envelope.
Message content and credential values are never emitted.
"""

from __future__ import annotations

from hashlib import sha256
import json
from typing import Any, Mapping

from metao.adapters.gemini_interactions import (
    GeminiHttpError,
    GeminiInteractionsOrchestratorAdapter,
)


_INVALID_API_KEY = "metao-intentionally-invalid-live-auth-smoke"


def _safe_scalar(value: Any) -> str | int | float | bool | None:
    if isinstance(value, (str, int, float, bool)) or value is None:
        return value
    return None


def _message_metadata(value: Any) -> dict[str, Any]:
    if not isinstance(value, str):
        return {"present": False, "length": None, "sha256": None}
    return {
        "present": True,
        "length": len(value),
        "sha256": sha256(value.encode("utf-8")).hexdigest(),
    }


def _structured_error(body: Any) -> dict[str, Any]:
    evidence: dict[str, Any] = {
        "body_kind": type(body).__name__,
        "top_level_keys": [],
        "error_kind": None,
        "error_keys": [],
        "error_code_type": None,
        "error_code_value": None,
        "error_status": None,
        "error_message": {"present": False, "length": None, "sha256": None},
        "provider_error_details": [],
    }
    if not isinstance(body, Mapping):
        if isinstance(body, str):
            evidence["body_text_length"] = len(body)
            evidence["body_text_sha256"] = sha256(body.encode("utf-8")).hexdigest()
        return evidence

    evidence["top_level_keys"] = sorted(str(key) for key in body.keys())
    error = body.get("error")
    evidence["error_kind"] = type(error).__name__ if error is not None else None
    if not isinstance(error, Mapping):
        return evidence

    evidence["error_keys"] = sorted(str(key) for key in error.keys())
    code = error.get("code")
    evidence["error_code_type"] = type(code).__name__ if code is not None else None
    evidence["error_code_value"] = _safe_scalar(code)
    status = error.get("status")
    evidence["error_status"] = status if isinstance(status, str) else None
    evidence["error_message"] = _message_metadata(error.get("message"))

    details = error.get("details")
    if isinstance(details, list):
        sanitized: list[dict[str, Any]] = []
        for item in details:
            if not isinstance(item, Mapping):
                continue
            entry: dict[str, Any] = {"keys": sorted(str(key) for key in item.keys())}
            for source_key, output_key in (
                ("reason", "reason"),
                ("domain", "domain"),
                ("@type", "type"),
            ):
                value = item.get(source_key)
                if isinstance(value, str) and value.strip():
                    entry[output_key] = value
            sanitized.append(entry)
        evidence["provider_error_details"] = sanitized
    return evidence


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
        evidence = {
            "adapter": adapter.descriptor.orchestrator_id,
            "base_url": "https://generativelanguage.googleapis.com/v1beta",
            "endpoint": "/interactions",
            "observed_http_status": exc.status_code,
            "synthetic_invalid_credential": True,
            "credential_value_emitted": False,
            "capacity_classification": "NOT_YET_QUALIFIED",
            "provider_backed_execution": "NOT_TESTED",
            "paid_inference_authorized": False,
            **_structured_error(exc.body),
        }
        print(json.dumps(evidence, sort_keys=True, separators=(",", ":")))
        return 0

    raise AssertionError("synthetic invalid Gemini API key unexpectedly succeeded")


if __name__ == "__main__":
    raise SystemExit(main())
