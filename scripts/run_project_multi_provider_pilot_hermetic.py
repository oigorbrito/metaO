from __future__ import annotations

import hashlib
import io
import json
from contextlib import redirect_stdout
from pathlib import Path

import project_multi_provider_pilot

BOOTSTRAP_LOCK = Path("requirements/bootstrap.lock")
RUNTIME_REQUIREMENTS = Path(".runtime-locks/openai-agents-runtime.requirements.txt")
AUTHORITY = Path("requirements/openai-agents-runtime-authority.json")


def sha256(path: Path) -> str:
    if not path.is_file():
        raise SystemExit(f"required dependency identity file missing: {path}")
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main() -> int:
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
    evidence.update(
        {
            "dependency_identity": "VERIFIED",
            "bootstrap_lock_sha256": sha256(BOOTSTRAP_LOCK),
            "runtime_requirements_sha256": sha256(RUNTIME_REQUIREMENTS),
            "runtime_authority_source_commit": authority["source_commit"],
            "runtime_authority_uv_lock_blob_sha1": authority["source_uv_lock_blob_sha1"],
            "runtime_authority_openai_agents_wheel_sha256": authority["pypi_wheel_sha256"],
        }
    )
    print(json.dumps(evidence, sort_keys=True, separators=(",", ":")))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
