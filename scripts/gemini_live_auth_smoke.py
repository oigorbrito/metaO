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
_MACHINE_FIELDS = ("code", "status", "reason", "domain", "@type", "errorCode", "type")


def _safe_scalar(value: Any) -> str | int | float | bool | None:
    if isinstance(value, (str, int, float, bool)) or value is None:
        return value
    return None


def _text_metadata(value: Any) -> dict[str, Any]:
    if not isinstance(value, str):
        return {"present": False, "length": None, "sha256": None}
    return {
        "present": True,
        "length": len(value),
        "sha256": sha256(value.encode("utf-8")).hexdigest(),
    }


def _shallow_mapping_summary(value: Mapping[Any, Any]) -> dict[str, Any]:
    summary: dict[str, Any] = {
        "keys": sorted(str(key) for key in value.keys()),
        "machine_fields": {},
        "message": _text_metadata(value.get("message")),
    }
    for key in _MACHINE_FIELDS:
        if key in value:
            scalar = _safe_scalar(value.get(key))
            if scalar is not None:
                summary["machine_fields"][key] = scalar
    return summary


def _item_summary(value: Any) -> dict[str, Any]:
    result: dict[str, Any] = {"kind": type(value).__name__}
    if isinstance(value, Mapping):
        result.update(_shallow_mapping_summary(value))
    elif isinstance(value, str):
        result["text"] = _text_metadata(value)
    elif isinstance(value, (int, float, bool)) or value is None:
        result["scalar"] = value
    return result


def _mapping_summary(value: Mapping[Any, Any]) -> dict[str, Any]:
    summary = _shallow_mapping_summary(value)
    nested_error = value.get("error")
    if isinstance(nested_error, Mapping):
        nested = _shallow_mapping_summary(nested_error)
        details = nested_error.get("details")
        nested["details_kind"] = type(details).__name__ if details is not None else None
        nested["details_length"] = len(details) if isinstance(details, list) else None
        nested["details"] = (
            [_item_summary(item) for item in details[:3]]
            if isinstance(details, list)
            else []
        )
        summary["nested_error"] = nested
    return summary


def _structured_error(body: Any) -> dict[str, Any]:
    evidence: dict[str, Any] = {
        "body_kind": type(body).__name__,
        "body_list_length": None,
        "body_list_items": [],
        "top_level_keys": [],
        "error_kind": None,
        "error_keys": [],
        "error_code_type": None,
        "error_code_value": None,
        "error_status": None,
        "error_message": {"present": False, "length": None, "sha256": None},
        "provider_error_details": [],
    }

    if isinstance(body, list):
        evidence["body_list_length"] = len(body)
        evidence["body_list_items"] = [_item_summary_with_nested_error(item) for item in body[:3]]
        return evidence

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
    evidence["error_message"] = _text_metadata(error.get("message"))

    details = error.get("details")
    if isinstance(details, list):
        evidence["provider_error_details"] = [_item_summary(item) for item in details[:3]]
    return evidence


def _item_summary_with_nested_error(value: Any) -> dict[str, Any]:
    result: dict[str, Any] = {"kind": type(value).__name__}
    if isinstance(value, Mapping):
        result.update(_mapping_summary(value))
    elif isinstance(value, str):
        result["text"] = _text_metadata(value)
    elif isinstance(value, (int, float, bool)) or value is None:
        result["scalar"] = value
    return result


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
