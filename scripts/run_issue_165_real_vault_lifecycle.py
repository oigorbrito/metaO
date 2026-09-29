from __future__ import annotations

import argparse
from datetime import datetime, timezone
from hashlib import sha256
import json
import os
from pathlib import Path
import time
from typing import Any
from urllib import error, request


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def api(
    base: str,
    path: str,
    *,
    root_token: str | None = None,
    child_token: str | None = None,
    payload: dict[str, Any] | None = None,
    expected: tuple[int, ...] = (200, 204),
) -> tuple[int, dict[str, Any]]:
    headers = {"Content-Type": "application/json"}
    token = child_token or root_token
    if token:
        headers["X-Vault-Token"] = token
    body = None if payload is None else json.dumps(payload).encode()
    req = request.Request(base.rstrip("/") + path, data=body, headers=headers, method="POST")
    try:
        with request.urlopen(req, timeout=10) as response:
            status = response.status
            raw = response.read()
    except error.HTTPError as exc:
        status = exc.code
        raw = exc.read()
    data = json.loads(raw.decode()) if raw else {}
    if status not in expected:
        raise RuntimeError(f"Vault {path} returned HTTP {status}")
    return status, data


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--receipt", type=Path, required=True)
    parser.add_argument("--commit", required=True)
    parser.add_argument("--vault-version", required=True)
    args = parser.parse_args()

    base = os.environ["VAULT_ADDR"]
    root_token = os.environ["VAULT_TOKEN"]

    started_at = utc_now()
    started = time.monotonic()

    _, issued = api(
        base,
        "/v1/auth/token/create",
        root_token=root_token,
        payload={
            "policies": ["default"],
            "ttl": "45s",
            "explicit_max_ttl": "120s",
            "renewable": True,
            "display_name": "metao-issue-165",
        },
        expected=(200,),
    )
    auth = issued["auth"]
    child_token = str(auth["client_token"])
    accessor = str(auth["accessor"])
    initial_ttl = int(auth["lease_duration"])
    renewable = bool(auth["renewable"])
    if not child_token or not accessor or not renewable or initial_ttl <= 0:
        raise RuntimeError("Vault did not issue the expected renewable child credential")

    _, renewed = api(
        base,
        "/v1/auth/token/renew",
        root_token=root_token,
        payload={"token": child_token, "increment": "45s"},
        expected=(200,),
    )
    renewed_auth = renewed["auth"]
    renewed_ttl = int(renewed_auth["lease_duration"])
    if not bool(renewed_auth["renewable"]) or renewed_ttl <= 0:
        raise RuntimeError("Vault renewal did not preserve a renewable live credential")

    api(
        base,
        "/v1/auth/token/revoke",
        root_token=root_token,
        payload={"token": child_token},
        expected=(204,),
    )

    revoked_status, _ = api(
        base,
        "/v1/auth/token/lookup-self",
        child_token=child_token,
        expected=(403,),
    )
    revoked_confirmed = revoked_status == 403
    if not revoked_confirmed:
        raise RuntimeError("revoked child credential remained usable")

    ended_at = utc_now()
    duration = time.monotonic() - started
    accessor_digest = "sha256:" + sha256(accessor.encode()).hexdigest()
    revocation_ref = "vault-revoked:" + accessor_digest

    projection = {
        "lease_ref": accessor_digest,
        "binding": {
            "runtime_id": "vault-integration-runtime",
            "workload_identity": "issue-165-hosted-ci",
            "runtime_config_id": f"vault-{args.vault_version}-dev",
            "mission_id": "issue-165-real-broker-lifecycle",
            "execution_id": f"github-actions:{os.environ.get('GITHUB_RUN_ID', 'local')}",
        },
        "credential_class": "vault-child-token",
        "target_service": "hashicorp-vault",
        "policy_authority_ref": "vault-root-authority:ephemeral-dev-run",
        "renewable": True,
        "assurance": "Brokered",
        "evidence_basis": "BrokerVerified",
        "revocation_status": "Revoked",
        "revocation_evidence_ref": revocation_ref,
    }

    evidence = {
        "schema": "metao-real-broker-lifecycle-v1",
        "issue": 165,
        "classification": "REAL_BROKER_LOCAL_EPHEMERAL",
        "broker": {
            "product": "HashiCorp Vault",
            "version": args.vault_version,
            "mode": "dev",
            "address": base,
        },
        "issue": {
            "passed": True,
            "renewable": renewable,
            "initial_ttl_seconds": initial_ttl,
        },
        "renew": {
            "passed": True,
            "renewed_ttl_seconds": renewed_ttl,
        },
        "revoke": {
            "passed": revoked_confirmed,
            "post_revoke_lookup_http_status": revoked_status,
        },
        "metao_projection": projection,
        "secret_material_persisted": False,
        "production_assurance_authorized": False,
        "claim_boundary": (
            "real Vault broker process on hosted CI; dev-mode local ephemeral lifecycle only; "
            "not production Vault topology, workload attestation, or target-service credential use"
        ),
    }

    encoded = json.dumps(evidence, sort_keys=True, separators=(",", ":"))
    if child_token in encoded or root_token in encoded:
        raise RuntimeError("secret credential material leaked into evidence")
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(evidence, indent=2, sort_keys=True) + "\n", encoding="utf-8")

    receipt = {
        "schema": "metao-scientific-gate-receipt-v1",
        "repository": "oigorbrito/metaO",
        "commit": args.commit,
        "gate_id": "T8",
        "gate_level": "L6",
        "runtime_identities": [],
        "runtime_substrate": {"mode": "NONE", "runtimes": []},
        "mission_lineage": [
            "issue-165-real-broker-lifecycle",
            f"github-actions:{os.environ.get('GITHUB_RUN_ID', 'local')}",
        ],
        "commands": [
            "vault server -dev",
            "python scripts/run_issue_165_real_vault_lifecycle.py",
        ],
        "environment": {
            "ci": "GitHub Actions",
            "workflow": "Issue 165 Real Vault Broker Lifecycle",
            "workflow_run_id": os.environ.get("GITHUB_RUN_ID"),
            "runner_os": os.environ.get("RUNNER_OS"),
            "vault_mode": "dev",
        },
        "started_at": started_at,
        "ended_at": ended_at,
        "duration_seconds": round(duration, 6),
        "result": "PASS",
        "failure_reason": None,
        "evidence_ids": [
            f"github-actions-run:{os.environ.get('GITHUB_RUN_ID', 'unknown')}",
            f"vault-accessor:{accessor_digest}",
            revocation_ref,
        ],
        "external_systems": {
            "mode": "REAL",
            "systems": [f"HashiCorp Vault {args.vault_version} dev server"],
        },
    }
    args.receipt.write_text(json.dumps(receipt, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
