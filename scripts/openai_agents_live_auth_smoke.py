"""Credential-free live OpenAI Agents authentication smoke for #359.

This smoke exercises the production metaO OpenAI Agents adapter with the real
pinned Agents SDK runtime. It deliberately supplies a synthetic invalid API key,
disables tracing, and attempts exactly one model call. No valid credential or
paid/provider-authenticated execution is authorized.
"""

from __future__ import annotations

import json
import os
from typing import Any


_INVALID_API_KEY = "sk-metao-intentionally-invalid-openai-agents-live-auth-smoke"
_MODEL = "gpt-5.6-luna"

# The Agents SDK resolves OPENAI_API_KEY lazily at the first model call. Set the
# synthetic credential before importing/constructing the runtime anyway so the
# evidence boundary is explicit and independent of the runner environment.
os.environ["OPENAI_API_KEY"] = _INVALID_API_KEY

from agents import Agent, Runner, set_tracing_disabled  # noqa: E402

from metao.adapters.openai_agents import OpenAIAgentsOrchestratorAdapter  # noqa: E402
from metao.capacity import CapacityStatus  # noqa: E402
from metao.core import ExecutionRequest, ExecutionStatus, Mission  # noqa: E402


class _ObservedRunner:
    """Record structured SDK exception metadata, then re-raise unchanged."""

    observed_status_code: int | None = None
    observed_exception_type: str | None = None

    @classmethod
    def run_sync(cls, agent: Any, input_value: Any) -> Any:
        try:
            return Runner.run_sync(agent, input_value)
        except Exception as exc:
            status_code = getattr(exc, "status_code", None)
            cls.observed_status_code = status_code if isinstance(status_code, int) else None
            cls.observed_exception_type = type(exc).__name__
            raise


def main() -> int:
    set_tracing_disabled(True)

    agent = Agent(
        name="metaO OpenAI Agents live-auth probe",
        instructions="Return exactly: metao-openai-live-auth-smoke",
        model=_MODEL,
    )
    adapter = OpenAIAgentsOrchestratorAdapter(
        _ObservedRunner,
        agent,
        orchestrator_id="openai-agents",
        version="0.20.0",
    )
    request = ExecutionRequest(
        "openai-agents-live-auth-smoke",
        Mission(
            "openai-agents-live-auth-smoke",
            "prove live authentication failure normalization without valid credentials",
            frozenset({"workflow"}),
        ),
        {"created_at_epoch": 0.0},
    )

    result = adapter.execute(request)

    assert result.status is ExecutionStatus.FAILED, result.status
    assert _ObservedRunner.observed_status_code == 401, _ObservedRunner.observed_status_code
    assert result.capacity_observation is not None, result.capacity_observation
    assert (
        result.capacity_observation.capacity_status
        is CapacityStatus.AUTHENTICATION_FAILURE
    ), result.capacity_observation
    assert result.capacity_observation.recovery is None, result.capacity_observation
    assert _INVALID_API_KEY not in (result.error or ""), "synthetic credential leaked into error"

    evidence = {
        "adapter": adapter.descriptor.orchestrator_id,
        "agents_sdk_version": adapter.descriptor.version,
        "api_surface": "Responses API via OpenAI Agents SDK Runner.run_sync",
        "model": _MODEL,
        "execution_status": result.status.value,
        "observed_http_status": _ObservedRunner.observed_status_code,
        "observed_exception_type": _ObservedRunner.observed_exception_type,
        "capacity_status": result.capacity_observation.capacity_status.value,
        "recovery": None,
        "synthetic_invalid_credential": True,
        "credential_value_emitted": False,
        "tracing_disabled": True,
        "model_call_attempted": True,
        "valid_credential_present": False,
        "paid_inference_authorized": False,
        "provider_backed_execution": "NOT_TESTED",
    }
    print(json.dumps(evidence, sort_keys=True, separators=(",", ":")))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
