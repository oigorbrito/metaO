from __future__ import annotations

import hashlib
import io
import json
import os
from contextlib import redirect_stdout
from pathlib import Path

import project_multi_provider_pilot
from provider_target_policy import validate_operational_provider_targets

BOOTSTRAP_LOCK = Path("requirements/bootstrap.lock")
RUNTIME_REQUIREMENTS = Path(".runtime-locks/openai-agents-runtime.requirements.txt")
AUTHORITY = Path("requirements/openai-agents-runtime-authority.json")


def sha256(path: Path) -> str:
    if not path.is_file():
        raise SystemExit(f"required dependency identity file missing: {path}")
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main() -> int:
    approved_targets = validate_operational_provider_targets(
        os.environ.get("METAO_OPENAI_MODEL", "gpt-5.6-luna"),
        os.environ.get("METAO_GEMINI_TARGET", "gemma-4-26b-a4b-it"),
    )
    authority = json.loads(AUTHORITY.read_text(encoding="utf-8"))
    buffer = io.StringIO()
    with redirect_stdout(buffer):
        result = project_multi_provider_pilot.main()
    if result != 0:
        return result
    lines = [line for line in buffer.getvalue().splitlines() if line.strip()]
    if not lines:
        raise SystemExit("pilot produced no bounded evidence")
    evidence = json.loads(lines[-1])
    if evidence.get("openai_model") != approved_targets.openai_model:
        raise SystemExit("pilot OpenAI model evidence differs from approved target")
    if evidence.get("gemini_target") != approved_targets.gemini_target:
        raise SystemExit("pilot Gemini target evidence differs from approved target")
    evidence.update(
        {
            "dependency_identity": "VERIFIED",
            "bootstrap_lock_sha256": sha256(BOOTSTRAP_LOCK),
            "runtime_requirements_sha256": sha256(RUNTIME_REQUIREMENTS),
            "runtime_authority_source_commit": authority["source_commit"],
            "runtime_authority_uv_lock_blob_sha1": authority["source_uv_lock_blob_sha1"],
            "runtime_authority_openai_agents_wheel_sha256": authority["pypi_wheel_sha256"],
            "provider_targets_approved": True,
            "operational_target_policy": "ALLOWLISTED",
        }
    )
    print(json.dumps(evidence, sort_keys=True, separators=(",", ":")))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
