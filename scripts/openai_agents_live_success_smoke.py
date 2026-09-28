"""Explicitly authorized provider-backed OpenAI Agents success smoke for #359/#596.

This script performs one bounded provider call through the production metaO
OpenAI Agents adapter. It is intentionally fail-closed: a valid provider key is
not sufficient by itself; the exact authorization token is also required.
Provider success remains execution evidence only and does not mint metaO final
acceptance.
"""

from __future__ import annotations

from dataclasses import asdict
import json
import os


_AUTHORIZATION = "I_AUTHORIZE_OPENAI_AGENTS_PROVIDER_SUCCESS_SMOKE"
_MODEL = "gpt-5.6-luna"
_EXPECTED_OUTPUT = "metao-openai-agents-provider-success-smoke"


def _authorized_api_key() -> str:
    if os.environ.get("METAO_OPENAI_AGENTS_SUCCESS_AUTHORIZATION") != _AUTHORIZATION:
        raise SystemExit("explicit OpenAI Agents provider-success authorization is required")
    api_key = os.environ.get("METAO_OPENAI_API_KEY", "").strip()
    if not api_key:
        raise SystemExit("METAO_OPENAI_API_KEY is required")
    return api_key


def main() -> int:
    api_key = _authorized_api_key()
    os.environ["OPENAI_API_KEY"] = api_key

    from agents import Agent, Runner, set_tracing_disabled

    from metao.adapters.openai_agents import (
        OpenAIAgentsOrchestratorAdapter,
        normalize_evidence,
    )
    from metao.core import ExecutionRequest, ExecutionStatus, Mission

    set_tracing_disabled(True)

    agent = Agent(
        name="metaO OpenAI Agents provider-success smoke",
        instructions=f"Return exactly this text and nothing else: {_EXPECTED_OUTPUT}",
        model=_MODEL,
    )
    adapter = OpenAIAgentsOrchestratorAdapter(
        Runner,
        agent,
        orchestrator_id="openai-agents",
        version="0.20.0",
    )
    request = ExecutionRequest(
        "openai-agents-provider-success-smoke",
        Mission(
            "openai-agents-provider-success-smoke",
            "perform one explicitly authorized provider-backed OpenAI Agents call",
            frozenset({"workflow"}),
        ),
        {
            "authority_id": "metao-runtime",
            "created_at_epoch": 0.0,
            "obligation_id": "provider_success_smoke",
            "policy_bundle_id": "provider-success-smoke-policy",
            "subject_id": "openai-agents-provider-success-smoke",
            "subject_state_id": "provider-call-1",
            "verification_context_id": "provider-success-smoke",
            "verifier_id": "adapter-observer",
        },
    )

    result = adapter.execute(request)
    if result.status is not ExecutionStatus.SUCCEEDED:
        raise AssertionError(
            f"provider-backed OpenAI Agents execution did not succeed: {result.status.value}"
        )
    if result.capacity_observation is not None:
        raise AssertionError("successful provider execution unexpectedly carried capacity failure")

    output = result.output or {}
    serialized_output = json.dumps(output, sort_keys=True, default=str)
    if _EXPECTED_OUTPUT not in serialized_output:
        raise AssertionError("provider output did not contain the exact smoke marker")

    envelope = normalize_evidence(
        request=request,
        orchestrator_id=adapter.descriptor.orchestrator_id,
        adapter_version=adapter.descriptor.version,
        output=output,
    )
    envelope_dict = asdict(envelope)

    evidence = {
        "adapter": adapter.descriptor.orchestrator_id,
        "agents_sdk_version": adapter.descriptor.version,
        "api_surface": "Responses API via OpenAI Agents SDK Runner.run_sync",
        "model": _MODEL,
        "execution_status": result.status.value,
        "output_marker_present": True,
        "credential_value_emitted": False,
        "tracing_disabled": True,
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
