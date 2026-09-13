from __future__ import annotations

import hashlib
import json
import sys
from importlib.metadata import PackageNotFoundError, version
from pathlib import Path

BOOTSTRAP_LOCK = Path("requirements/bootstrap.lock")
BOOTSTRAP_PACKAGES = ("pip", "setuptools", "wheel")


def package_version(name: str) -> str:
    try:
        return version(name)
    except PackageNotFoundError as exc:
        raise SystemExit(f"required bootstrap package is not installed: {name}") from exc


def main() -> int:
    if not BOOTSTRAP_LOCK.is_file():
        raise SystemExit(f"bootstrap lock does not exist: {BOOTSTRAP_LOCK}")
    lock_sha256 = hashlib.sha256(BOOTSTRAP_LOCK.read_bytes()).hexdigest()
    evidence = {
        "dependency_identity": "OBSERVED",
        "python": f"{sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}",
        "bootstrap_lock": str(BOOTSTRAP_LOCK),
        "bootstrap_lock_sha256": lock_sha256,
        "bootstrap_packages": {name: package_version(name) for name in BOOTSTRAP_PACKAGES},
        "credentials_emitted": False,
    }
    print(json.dumps(evidence, sort_keys=True, separators=(",", ":")))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
