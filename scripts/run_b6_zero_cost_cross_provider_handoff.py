from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
from typing import Mapping

from metao.adapters.gemini_interactions import GeminiInteractionsOrchestratorAdapter
from metao.core import ExecutionRequest, ExecutionStatus, Mission


AUTHORIZATION_ENV = "METAO_B6_CROSS_PROVIDER_AUTHORIZATION"
API_KEY_ENV = "METAO_GEMINI_API_KEY"
AUTHORIZATION_PHRASE = "I_AUTHORIZE_B6_ZERO_COST_CROSS_PROVIDER_HANDOFF"
TARGET = "gemma-4-26b-a4b-it"
BASE_URL = "https://generativelanguage.googleapis.com/v1"
SOURCE_COMMIT = "c35a0fa98d27c9cca082441b72ab77ff0ea0e16d"
SOURCE_PATH = "experiments/provider-handoff-smoke/handoff.txt"
EXPECTED_SOURCE = "METAO_HANDOFF_VERSION=1\nCODEX_LEG=COMPLETE\n"
SOURCE_PROVIDER_ID = "openai-codex-chatgpt"
DESTINATION_PROVIDER_ID = "google-gemini"


def require_authorization(env: Mapping[str, str]) -> str:
    if env.get(AUTHORIZATION_ENV, "") != AUTHORIZATION_PHRASE:
        raise RuntimeError("explicit zero-cost B6 cross-provider authorization is required")
    api_key = env.get(API_KEY_ENV, "").strip()
    if not api_key:
        raise RuntimeError("METAO_GEMINI_API_KEY is required for zero-cost handoff execution")
    return api_key


def validate_checkpoint(path: Path) -> tuple[str, str]:
    data = path.read_text(encoding="utf-8")
    if data != EXPECTED_SOURCE:
        raise RuntimeError("Codex handoff checkpoint content mismatch")
    digest = hashlib.sha256(data.encode("utf-8")).hexdigest()
    return data, digest


def expected_continuation(source_digest: str) -> str:
    return (
        "METAO_GOOGLE_LEG=COMPLETE\n"
        f"PARENT_SHA={SOURCE_COMMIT}\n"
        f"SOURCE_SHA256={source_digest}"
    )


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--checkpoint-file", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()

    api_key = require_authorization(os.environ)
    checkpoint, source_digest = validate_checkpoint(args.checkpoint_file)
    expected = expected_continuation(source_digest)

    adapter = GeminiInteractionsOrchestratorAdapter(
        api_key=api_key,
        target=TARGET,
        target_kind="model",
        base_url=BASE_URL,
        orchestrator_id="gemini-interactions-b6-handoff",
        version="v1",
        background=False,
        max_polls=3,
        poll_interval_s=0.5,
    )

    request = ExecutionRequest(
        "b6-cross-provider-google-leg",
        Mission(
            "b6-cross-provider-google-leg",
            (
                "Continue an already completed Codex handoff from an exact trusted Git checkpoint. "
                "The checkpoint is:\n"
                f"{checkpoint}\n"
                "Return exactly these three lines and nothing else:\n"
                f"{expected}"
            ),
            frozenset({"agent"}),
        ),
        {
            "created_at_epoch": 0.0,
            "obligation_id": "b6_cross_provider_external_handoff",
            "subject_id": SOURCE_COMMIT,
            "subject_state_id": source_digest,
            "verification_context_id": "b6-zero-cost-cross-provider-handoff",
            "policy_bundle_id": "explicit-zero-cost-cross-provider-handoff",
            "authority_id": "explicit-workflow-dispatch",
        },
    )

    result = adapter.execute(request)
    if result.status is not ExecutionStatus.SUCCEEDED:
        raise RuntimeError(
            "Gemini continuation did not succeed: "
            + json.dumps(
                {
                    "status": result.status.value,
                    "error": result.error,
                    "capacity_status": (
                        result.capacity_observation.capacity_status.value
                        if result.capacity_observation is not None
                        else None
                    ),
                },
                sort_keys=True,
                separators=(",", ":"),
            )
        )

    output = result.output if isinstance(result.output, Mapping) else {}
    interaction = output.get("interaction")
    if not isinstance(interaction, Mapping):
        raise RuntimeError("Gemini continuation is missing interaction evidence")
    interaction_id = interaction.get("id")
    interaction_status = interaction.get("status")
    result_text = output.get("result")

    if not isinstance(interaction_id, str) or not interaction_id.strip():
        raise RuntimeError("Gemini continuation interaction id missing")
    if interaction_status != "completed":
        raise RuntimeError(f"unexpected Gemini interaction status: {interaction_status!r}")
    if not isinstance(result_text, str):
        raise RuntimeError("Gemini continuation output text missing")
    if result_text.strip() != expected:
        raise RuntimeError("Gemini continuation output did not match exact independent verifier")

    evidence = {
        "schema": "metao-b6-zero-cost-cross-provider-handoff-v1",
        "source_provider_id": SOURCE_PROVIDER_ID,
        "destination_provider_id": DESTINATION_PROVIDER_ID,
        "source_commit": SOURCE_COMMIT,
        "source_path": SOURCE_PATH,
        "source_sha256": source_digest,
        "source_checkpoint_validated": True,
        "destination_target": TARGET,
        "destination_interaction_id_present": True,
        "destination_interaction_status": interaction_status,
        "destination_output_exactly_verified": True,
        "provider_backed_destination_execution": "PASS",
        "cross_provider_external_handoff": "EXECUTED",
        "incremental_provider_cost_policy": "ZERO_COST_TARGET_ONLY",
        "credential_value_emitted": False,
        "metao_final_acceptance": "NOT_IMPLIED_BY_PROVIDER_SUCCESS",
    }

    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(
        json.dumps(evidence, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    print(json.dumps(evidence, sort_keys=True, separators=(",", ":")))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
