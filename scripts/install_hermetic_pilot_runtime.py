from __future__ import annotations

import hashlib
import json
import subprocess
import sys
from importlib.metadata import version
from pathlib import Path

from fetch_openai_agents_runtime_lock import materialize_runtime_lock
from materialize_openai_agents_runtime_requirements import (
    AUTHORITY_PATH,
    render_requirements,
    runtime_closure,
)
import tomllib

BOOTSTRAP_LOCK = Path("requirements/bootstrap.lock")
UPSTREAM_LOCK = Path(".runtime-locks/openai-agents-v0.20.0.uv.lock")
RUNTIME_REQUIREMENTS = Path(".runtime-locks/openai-agents-runtime.requirements.txt")


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def run_pip(*args: str) -> None:
    subprocess.run(
        [sys.executable, "-m", "pip", "--disable-pip-version-check", *args],
        check=True,
    )


def main() -> int:
    if sys.version_info < (3, 12):
        raise SystemExit("hermetic pilot runtime requires Python 3.12+")
    if not BOOTSTRAP_LOCK.is_file():
        raise SystemExit(f"bootstrap lock missing: {BOOTSTRAP_LOCK}")

    run_pip("install", "--only-binary=:all:", "--require-hashes", "-r", str(BOOTSTRAP_LOCK))
    run_pip("install", "--no-build-isolation", "--no-deps", "-e", ".")

    authority_evidence = materialize_runtime_lock(UPSTREAM_LOCK)
    authority = json.loads(AUTHORITY_PATH.read_text(encoding="utf-8"))
    lock = tomllib.loads(UPSTREAM_LOCK.read_text(encoding="utf-8"))
    packages, conditions = runtime_closure(lock)
    rendered = render_requirements(packages, conditions, authority)
    RUNTIME_REQUIREMENTS.parent.mkdir(parents=True, exist_ok=True)
    RUNTIME_REQUIREMENTS.write_text(rendered, encoding="utf-8", newline="\n")

    run_pip(
        "install",
        "--only-binary=:all:",
        "--require-hashes",
        "-r",
        str(RUNTIME_REQUIREMENTS),
    )
    if version("openai-agents") != "0.20.0":
        raise SystemExit("installed openai-agents version differs from authority")

    evidence = {
        "hermetic_runtime": "PREPARED",
        "python": f"{sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}",
        "bootstrap_lock_sha256": sha256(BOOTSTRAP_LOCK),
        "runtime_requirements_sha256": sha256(RUNTIME_REQUIREMENTS),
        "runtime_package_count": len(packages),
        "source_uv_lock_blob_sha1": authority_evidence["source_uv_lock_blob_sha1"],
        "openai_agents_version": version("openai-agents"),
        "credentials_emitted": False,
    }
    print(json.dumps(evidence, sort_keys=True, separators=(",", ":")))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
