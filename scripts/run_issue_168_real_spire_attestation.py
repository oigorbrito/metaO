from __future__ import annotations

import argparse
from datetime import datetime, timezone
from hashlib import sha256
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import time


TRUST_DOMAIN = "example.org"
AGENT_SPIFFE_ID = f"spiffe://{TRUST_DOMAIN}/host"
WORKLOAD_SPIFFE_ID = f"spiffe://{TRUST_DOMAIN}/metao/runtime/ci"


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def run(command: list[str], *, cwd: Path, check: bool = True) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        command,
        cwd=cwd,
        check=check,
        capture_output=True,
        text=True,
    )


def retry(fn, *, attempts: int = 30, delay: float = 0.5):
    last = None
    for _ in range(attempts):
        try:
            return fn()
        except Exception as exc:
            last = exc
            time.sleep(delay)
    raise RuntimeError(f"operation did not become ready: {last}")


def parse_join_token(output: str) -> str:
    match = re.search(r"Token:\s*([^\s]+)", output)
    if match is None:
        raise RuntimeError("SPIRE join token output was not recognized")
    return match.group(1)


def fetch_x509(agent_bin: Path, agent_home: Path, output_dir: Path) -> Path:
    output_dir.mkdir(parents=True, exist_ok=True)

    def attempt():
        completed = run(
            [
                str(agent_bin),
                "api",
                "fetch",
                "x509",
                "-socketPath",
                "/tmp/spire-agent/public/api.sock",
                "-write",
                str(output_dir),
            ],
            cwd=agent_home,
        )
        certs = sorted(output_dir.glob("svid.*.pem"))
        if not certs:
            raise RuntimeError(f"no SVID PEM written; output={completed.stdout!r}")
        return certs[0]

    return retry(attempt)


def cert_facts(cert_path: Path) -> dict[str, object]:
    san = subprocess.check_output(
        ["openssl", "x509", "-in", str(cert_path), "-noout", "-ext", "subjectAltName"],
        text=True,
    )
    dates = subprocess.check_output(
        ["openssl", "x509", "-in", str(cert_path), "-noout", "-dates"],
        text=True,
    )
    fingerprint = subprocess.check_output(
        ["openssl", "x509", "-in", str(cert_path), "-noout", "-fingerprint", "-sha256"],
        text=True,
    ).strip()

    uri_match = re.search(r"URI:([^,\s]+)", san)
    if uri_match is None:
        raise RuntimeError("X.509-SVID did not contain a URI SAN")
    spiffe_id = uri_match.group(1)
    if spiffe_id != WORKLOAD_SPIFFE_ID:
        raise RuntimeError(f"unexpected workload SPIFFE ID: {spiffe_id}")

    date_map = {}
    for line in dates.splitlines():
        if "=" in line:
            key, value = line.split("=", 1)
            date_map[key] = value

    return {
        "spiffe_id": spiffe_id,
        "trust_domain": TRUST_DOMAIN,
        "not_before": date_map.get("notBefore"),
        "not_after": date_map.get("notAfter"),
        "sha256_fingerprint": fingerprint.split("=", 1)[-1].replace(":", "").lower(),
    }


def terminate(process: subprocess.Popen[bytes]) -> None:
    if process.poll() is not None:
        return
    process.terminate()
    try:
        process.wait(timeout=10)
    except subprocess.TimeoutExpired:
        process.kill()
        process.wait(timeout=5)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--spire-root", type=Path, required=True)
    parser.add_argument("--spire-version", required=True)
    parser.add_argument("--commit", required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--receipt", type=Path, required=True)
    args = parser.parse_args()

    spire_root = args.spire_root.resolve()
    server_bin = spire_root / "bin" / "spire-server"
    agent_bin = spire_root / "bin" / "spire-agent"
    if not server_bin.exists() or not agent_bin.exists():
        raise SystemExit("SPIRE binaries missing from extracted release")

    work_root = Path(os.environ.get("RUNNER_TEMP", "/tmp")) / f"metao-spire-{os.getpid()}"
    server_home = work_root / "server"
    agent_home = work_root / "agent"
    (server_home / "conf").mkdir(parents=True, exist_ok=True)
    (agent_home / "conf").mkdir(parents=True, exist_ok=True)
    shutil.copytree(spire_root / "conf" / "server", server_home / "conf" / "server")
    shutil.copytree(spire_root / "conf" / "agent", agent_home / "conf" / "agent")

    started_at = utc_now()
    started = time.monotonic()
    server = subprocess.Popen(
        [str(server_bin), "run", "-config", "conf/server/server.conf"],
        cwd=server_home,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )
    agent = None
    try:
        def token_attempt():
            completed = run(
                [
                    str(server_bin),
                    "token",
                    "generate",
                    "-spiffeID",
                    AGENT_SPIFFE_ID,
                ],
                cwd=server_home,
            )
            return parse_join_token(completed.stdout + completed.stderr)

        join_token = retry(token_attempt)

        agent = subprocess.Popen(
            [
                str(agent_bin),
                "run",
                "-config",
                "conf/agent/agent.conf",
                "-joinToken",
                join_token,
            ],
            cwd=agent_home,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )

        uid_selector = f"unix:uid:{os.getuid()}"

        def create_entry():
            return run(
                [
                    str(server_bin),
                    "entry",
                    "create",
                    "-parentID",
                    AGENT_SPIFFE_ID,
                    "-spiffeID",
                    WORKLOAD_SPIFFE_ID,
                    "-selector",
                    uid_selector,
                ],
                cwd=server_home,
            )

        retry(create_entry)

        first_cert = fetch_x509(agent_bin, agent_home, work_root / "svid-first")
        first = cert_facts(first_cert)

        terminate(agent)
        agent = subprocess.Popen(
            [str(agent_bin), "run", "-config", "conf/agent/agent.conf"],
            cwd=agent_home,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )

        second_cert = fetch_x509(agent_bin, agent_home, work_root / "svid-after-restart")
        second = cert_facts(second_cert)
        if second["spiffe_id"] != first["spiffe_id"]:
            raise RuntimeError("workload identity changed across agent restart")

        root_cert = server_home / "conf" / "server" / "dummy_upstream_ca.crt"
        trust_root_ref = "sha256:" + sha256(root_cert.read_bytes()).hexdigest()
        credential_ref = "sha256:" + str(second["sha256_fingerprint"])

        ended_at = utc_now()
        duration = time.monotonic() - started

        evidence = {
            "schema": "metao-real-workload-attestation-v1",
            "issue": 168,
            "classification": "REAL_SPIRE_LOCAL_EPHEMERAL",
            "identity_provider": {
                "product": "SPIRE",
                "version": args.spire_version,
                "mode": "local_ephemeral",
                "trust_domain": TRUST_DOMAIN,
            },
            "node_attestation": {
                "method": "join_token",
                "agent_spiffe_id": AGENT_SPIFFE_ID,
                "passed": True,
            },
            "workload_attestation": {
                "method": "unix",
                "selector": uid_selector,
                "spiffe_id": WORKLOAD_SPIFFE_ID,
                "credential_kind": "X509Svid",
                "first_fetch": first,
                "after_agent_restart": second,
                "restart_reconnect_passed": True,
            },
            "metao_projection": {
                "binding": {
                    "runtime_id": "spire-attested-runtime",
                    "runtime_version": args.spire_version,
                    "config_id": "issue-168-spire-local-v1",
                },
                "workload_subject": WORKLOAD_SPIFFE_ID,
                "trust_domain": TRUST_DOMAIN,
                "credential_kind": "X509Svid",
                "assurance": "Attested",
                "evidence_basis": "IdentityProviderVerified",
                "trust_root_ref": trust_root_ref,
                "credential_ref": credential_ref,
                "verifier_provenance": f"spire:{args.spire_version}:workload-api",
            },
            "private_key_persisted": False,
            "join_token_persisted": False,
            "production_attestation_assurance_authorized": False,
            "claim_boundary": (
                "real SPIRE server/agent and real Workload API X.509-SVID on hosted CI; "
                "local ephemeral join-token node attestation and unix workload attestation only"
            ),
        }
        serialized = json.dumps(evidence, sort_keys=True)
        if join_token in serialized or "PRIVATE KEY" in serialized:
            raise RuntimeError("secret identity material leaked into evidence")

        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(
            json.dumps(evidence, indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
        )

        receipt = {
            "schema": "metao-scientific-gate-receipt-v1",
            "repository": "oigorbrito/metaO",
            "commit": args.commit,
            "gate_id": "T5",
            "gate_level": "L6",
            "runtime_identities": [
                f"spire-attested-runtime:{args.spire_version}:issue-168-spire-local-v1"
            ],
            "runtime_substrate": {
                "mode": "REAL",
                "runtimes": [f"SPIRE workload identity provider {args.spire_version}"],
            },
            "mission_lineage": [
                "issue-168-real-workload-attestation",
                f"github-actions:{os.environ.get('GITHUB_RUN_ID', 'local')}",
            ],
            "commands": [
                "spire-server run",
                "spire-server token generate",
                "spire-agent run -joinToken <redacted>",
                "spire-server entry create",
                "spire-agent api fetch x509",
                "spire-agent restart",
                "spire-agent api fetch x509",
            ],
            "environment": {
                "ci": "GitHub Actions",
                "workflow": "Issue 168 Real SPIRE Workload Attestation",
                "workflow_run_id": os.environ.get("GITHUB_RUN_ID"),
                "runner_os": os.environ.get("RUNNER_OS"),
                "trust_domain": TRUST_DOMAIN,
            },
            "started_at": started_at,
            "ended_at": ended_at,
            "duration_seconds": round(duration, 6),
            "result": "PASS",
            "failure_reason": None,
            "evidence_ids": [
                f"github-actions-run:{os.environ.get('GITHUB_RUN_ID', 'unknown')}",
                trust_root_ref,
                credential_ref,
                f"spiffe-id:{WORKLOAD_SPIFFE_ID}",
            ],
            "external_systems": {
                "mode": "REAL",
                "systems": [f"SPIRE {args.spire_version} server+agent"],
            },
        }
        args.receipt.write_text(
            json.dumps(receipt, indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
        )
    finally:
        if agent is not None:
            terminate(agent)
        terminate(server)
        shutil.rmtree(work_root, ignore_errors=True)

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
