"""Explicitly authorized live Jules session smoke for #359/#600.

The smoke creates a real Jules session bound to the metaO repository, observes
its pre-approval state, and then deletes it. It never approves a plan or sends a
message, and it does not treat session creation as provider work completion or
metaO acceptance.
"""

from __future__ import annotations

import json
import os

from metao.adapters.jules_http import JulesHttpOrchestratorAdapter
from metao.core import ExecutionRequest, Mission


_AUTHORIZATION = "I_AUTHORIZE_JULES_LIVE_SESSION_SMOKE"
_SOURCE = "sources/github/oigorbrito/metaO"
_STARTING_BRANCH = "main"
_PREAPPROVAL_STATES = frozenset(
    {
        "QUEUED",
        "PLANNING",
        "AWAITING_PLAN_APPROVAL",
        "AWAITING_USER_FEEDBACK",
        "PAUSED",
    }
)


def _authorized_api_key() -> str:
    if os.environ.get("METAO_JULES_SESSION_SMOKE_AUTHORIZATION") != _AUTHORIZATION:
        raise SystemExit("explicit Jules live-session authorization is required")
    api_key = os.environ.get("METAO_JULES_API_KEY", "").strip()
    if not api_key:
        raise SystemExit("METAO_JULES_API_KEY is required")
    return api_key


def main() -> int:
    adapter = JulesHttpOrchestratorAdapter(
        api_key=_authorized_api_key(),
        source=_SOURCE,
        starting_branch=_STARTING_BRANCH,
        require_plan_approval=True,
        max_polls=1,
        poll_interval_s=0.0,
    )
    request = ExecutionRequest(
        "jules-live-session-smoke",
        Mission(
            "jules-live-session-smoke",
            "Inspect repository context and prepare a plan only. Do not modify files. Await plan approval.",
            frozenset({"workflow", "repository"}),
        ),
        {"created_at_epoch": 0.0},
    )

    session_name: str | None = None
    session_state = ""
    cleanup_completed = False
    try:
        session_name = adapter.start_session(request)
        session = adapter.get_session(request.execution_id)
        session_state = str(session.get("state", "")).upper()
        if session_state not in _PREAPPROVAL_STATES:
            raise AssertionError(
                f"Jules session escaped the pre-approval boundary: {session_state or '<empty>'}"
            )
    finally:
        if session_name is not None:
            adapter.cancel(request.execution_id)
            cleanup_completed = True

    evidence = {
        "adapter": adapter.descriptor.orchestrator_id,
        "adapter_version": adapter.descriptor.version,
        "base_url": "https://jules.googleapis.com/v1alpha",
        "source": _SOURCE,
        "starting_branch": _STARTING_BRANCH,
        "session_created": True,
        "session_id_present": bool(session_name),
        "observed_session_state": session_state,
        "require_plan_approval": True,
        "plan_approved": False,
        "message_sent": False,
        "auto_create_pr": False,
        "session_cleanup_delete": cleanup_completed,
        "credential_value_emitted": False,
        "explicit_authorization_observed": True,
        "live_provider_session_smoke": "PASS",
        "provider_backed_execution": "NOT_TESTED",
        "metao_final_acceptance": "NOT_TESTED",
    }
    print(json.dumps(evidence, sort_keys=True, separators=(",", ":")))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
