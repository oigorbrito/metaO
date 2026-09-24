from __future__ import annotations

import json
import platform
import shutil
import sys
import tempfile
from pathlib import Path

_REQUIRED_EXECUTABLES = ("git", "ssh", "scp", "curl", "tar")
_REQUIRED_LABELS = ("self-hosted", "linux", "x64", "metao-project-pilot")


def evaluate_readiness() -> dict[str, object]:
    system = platform.system().lower()
    machine = platform.machine().lower()
    linux = system == "linux"
    x64 = machine in {"x86_64", "amd64"}
    python_ok = sys.version_info >= (3, 12)

    executables = {
        name: shutil.which(name) is not None for name in _REQUIRED_EXECUTABLES
    }

    temp_write_ok = False
    with tempfile.TemporaryDirectory(prefix="metao-runner-readiness-") as root:
        probe = Path(root) / "probe"
        probe.write_text("metao-runner-readiness\n", encoding="utf-8")
        temp_write_ok = probe.read_text(encoding="utf-8") == "metao-runner-readiness\n"

    ready = (
        linux
        and x64
        and python_ok
        and all(executables.values())
        and temp_write_ok
    )

    return {
        "runner_readiness": "PASS" if ready else "FAIL",
        "linux": linux,
        "x64": x64,
        "python_3_12_plus": python_ok,
        "required_executables": executables,
        "temp_write_ok": temp_write_ok,
        "required_labels": list(_REQUIRED_LABELS),
        "registration_token_present": False,
        "repository_secrets_checked": False,
        "provider_calls_made": False,
        "credentials_emitted": False,
        "host_values_emitted": False,
        "pilot_operational_pass": False,
    }


def main() -> int:
    evidence = evaluate_readiness()
    print(json.dumps(evidence, sort_keys=True, separators=(",", ":")))
    return 0 if evidence["runner_readiness"] == "PASS" else 2


if __name__ == "__main__":
    raise SystemExit(main())
