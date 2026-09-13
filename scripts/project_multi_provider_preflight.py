from __future__ import annotations

import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path


_AUTHORIZATION = "I_AUTHORIZE_METAO_MULTI_PROVIDER_PROJECT_PILOT"
_REQUIRED_SSH = (
    "METAO_SSH_SMOKE_SOURCE_HOST",
    "METAO_SSH_SMOKE_DESTINATION_HOST",
    "METAO_SSH_SMOKE_SOURCE_USER",
    "METAO_SSH_SMOKE_DESTINATION_USER",
)
_PROVIDER_PRESENCE = (
    "METAO_OPENAI_CREDENTIAL_PRESENT",
    "METAO_GEMINI_CREDENTIAL_PRESENT",
)
_PORT_RE = re.compile(r"^[0-9]{1,5}$")


def _require(name: str) -> str:
    value = os.environ.get(name, "")
    if not value.strip():
        raise RuntimeError(f"required pilot configuration missing: {name}")
    return value


def _require_presence(name: str) -> None:
    value = os.environ.get(name, "").strip()
    if value != "1":
        raise RuntimeError(f"required provider credential presence flag missing: {name}")


def _port(name: str) -> str:
    value = os.environ.get(name, "").strip() or "22"
    if not _PORT_RE.fullmatch(value) or not 1 <= int(value) <= 65535:
        raise RuntimeError(f"invalid SSH port configuration: {name}")
    return value


def _run(args: list[str], *, input_text: str | None = None) -> str:
    return subprocess.run(
        args,
        input=input_text,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=True,
    ).stdout.strip()


def _ssh_base(*, host: str, user: str, port: str, known_hosts: Path, identity: Path | None) -> list[str]:
    args = [
        "ssh",
        "-o", "BatchMode=yes",
        "-o", "StrictHostKeyChecking=yes",
        "-o", f"UserKnownHostsFile={known_hosts}",
        "-p", port,
    ]
    if identity is not None:
        args += ["-i", str(identity), "-o", "IdentitiesOnly=yes"]
    args.append(f"{user}@{host}")
    return args


def _probe_host(*, host: str, user: str, port: str, known_hosts: Path, identity: Path | None) -> dict[str, str]:
    command = (
        "set -eu; "
        "git --version; "
        "python3 --version; "
        "d=$(mktemp -d /tmp/metao-project-pilot-preflight.XXXXXX); "
        "test -d \"$d\"; rmdir \"$d\"; "
        "printf 'METAO_PREFLIGHT_OK\\n'"
    )
    output = _run(_ssh_base(host=host, user=user, port=port, known_hosts=known_hosts, identity=identity) + [command])
    lines = [line.strip() for line in output.splitlines() if line.strip()]
    if not lines or lines[-1] != "METAO_PREFLIGHT_OK":
        raise RuntimeError("remote preflight marker missing")
    git_version = next((line for line in lines if line.startswith("git version ")), "")
    python_version = next((line for line in lines if line.startswith("Python ")), "")
    if not git_version or not python_version:
        raise RuntimeError("remote Git/Python version evidence missing")
    return {"git": git_version, "python": python_version}


def _configured_file(name: str) -> Path | None:
    raw = os.environ.get(name, "").strip()
    if not raw:
        return None
    path = Path(raw)
    if not path.is_file():
        raise RuntimeError(f"configured SSH file is not readable: {name}")
    return path


def main() -> int:
    if os.environ.get("METAO_MULTI_PROVIDER_PILOT_AUTHORIZATION", "") != _AUTHORIZATION:
        raise RuntimeError("explicit multi-provider pilot authorization is required")
    for name in _PROVIDER_PRESENCE:
        _require_presence(name)
    for name in _REQUIRED_SSH:
        _require(name)

    source_host = _require("METAO_SSH_SMOKE_SOURCE_HOST")
    destination_host = _require("METAO_SSH_SMOKE_DESTINATION_HOST")
    if source_host == destination_host:
        raise RuntimeError("pilot requires distinct SSH hosts")

    source_user = _require("METAO_SSH_SMOKE_SOURCE_USER")
    destination_user = _require("METAO_SSH_SMOKE_DESTINATION_USER")
    source_port = _port("METAO_SSH_SMOKE_SOURCE_PORT")
    destination_port = _port("METAO_SSH_SMOKE_DESTINATION_PORT")

    for executable in ("git", "ssh", "scp"):
        if shutil.which(executable) is None:
            raise RuntimeError(f"runner executable missing: {executable}")
    if not sys.executable or not Path(sys.executable).is_file():
        raise RuntimeError("active Python interpreter is not executable")

    with tempfile.TemporaryDirectory(prefix="metao-project-pilot-preflight-") as root:
        root_path = Path(root)
        known_hosts = _configured_file("METAO_SSH_KNOWN_HOSTS_FILE")
        if known_hosts is None:
            known_hosts = root_path / "known_hosts"
            known_hosts.write_text(_require("METAO_SSH_SMOKE_KNOWN_HOSTS") + "\n", encoding="utf-8")
            if os.name != "nt":
                known_hosts.chmod(0o600)

        identity = _configured_file("METAO_SSH_IDENTITY_FILE")
        if identity is None:
            identity_value = os.environ.get("METAO_SSH_SMOKE_IDENTITY", "")
            if identity_value.strip():
                identity = root_path / "identity"
                identity.write_text(identity_value + "\n", encoding="utf-8")
                if os.name != "nt":
                    identity.chmod(0o600)

        source = _probe_host(
            host=source_host,
            user=source_user,
            port=source_port,
            known_hosts=known_hosts,
            identity=identity,
        )
        destination = _probe_host(
            host=destination_host,
            user=destination_user,
            port=destination_port,
            known_hosts=known_hosts,
            identity=identity,
        )

    evidence = {
        "preflight": "PASS",
        "runner_git_present": True,
        "runner_python_present": True,
        "runner_ssh_present": True,
        "runner_scp_present": True,
        "source_reachable": True,
        "destination_reachable": True,
        "distinct_hosts": True,
        "source_remote_git_present": bool(source["git"]),
        "source_remote_python_present": bool(source["python"]),
        "destination_remote_git_present": bool(destination["git"]),
        "destination_remote_python_present": bool(destination["python"]),
        "provider_credentials_present": True,
        "provider_credential_values_received": False,
        "credentials_emitted": False,
        "hosts_emitted": False,
        "provider_calls_made": False,
    }
    print(json.dumps(evidence, sort_keys=True, separators=(",", ":")))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
