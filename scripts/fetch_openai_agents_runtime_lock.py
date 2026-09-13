from __future__ import annotations

import argparse
import hashlib
import json
import urllib.request
from pathlib import Path

AUTHORITY_PATH = Path("requirements/openai-agents-runtime-authority.json")


def git_blob_sha1(data: bytes) -> str:
    header = f"blob {len(data)}\0".encode("ascii")
    return hashlib.sha1(header + data).hexdigest()


def load_authority(path: Path = AUTHORITY_PATH) -> dict[str, object]:
    data = json.loads(path.read_text(encoding="utf-8"))
    required = {
        "package",
        "version",
        "source_repository",
        "source_commit",
        "source_uv_lock_blob_sha1",
        "pypi_wheel",
        "pypi_wheel_sha256",
        "direct_dependencies",
    }
    missing = sorted(required.difference(data))
    if missing:
        raise SystemExit(f"runtime authority missing fields: {','.join(missing)}")
    return data


def materialize_runtime_lock(destination: Path) -> dict[str, object]:
    authority = load_authority()
    repository = str(authority["source_repository"])
    commit = str(authority["source_commit"])
    expected_blob = str(authority["source_uv_lock_blob_sha1"])
    url = f"https://raw.githubusercontent.com/{repository}/{commit}/uv.lock"
    with urllib.request.urlopen(url, timeout=30) as response:
        content = response.read()
    observed_blob = git_blob_sha1(content)
    if observed_blob != expected_blob:
        raise SystemExit(
            "upstream uv.lock identity mismatch: "
            f"expected={expected_blob} observed={observed_blob}"
        )
    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_bytes(content)
    evidence = {
        "runtime_lock_authority": "VERIFIED",
        "package": authority["package"],
        "version": authority["version"],
        "source_commit": commit,
        "source_uv_lock_blob_sha1": observed_blob,
        "credentials_emitted": False,
    }
    return evidence


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Fetch the OpenAI Agents upstream uv.lock from an immutable commit and verify its Git blob identity."
    )
    parser.add_argument(
        "destination",
        nargs="?",
        default=".runtime-locks/openai-agents-v0.20.0.uv.lock",
    )
    args = parser.parse_args(argv)
    evidence = materialize_runtime_lock(Path(args.destination))
    print(json.dumps(evidence, sort_keys=True, separators=(",", ":")))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
