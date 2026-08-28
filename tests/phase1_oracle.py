from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from metao.acceptance import AcceptanceContext, EvidenceEnvelope, evaluate_acceptance
from metao.core import Mission


def context(data: dict) -> AcceptanceContext:
    return AcceptanceContext(
        subject_id=data["subject_id"],
        subject_state_id=data["subject_state_id"],
        verification_context_id=data["verification_context_id"],
        policy_bundle_id=data["policy_bundle_id"],
        required_obligations=frozenset(data["required_obligations"]),
        trusted_verifiers=frozenset(data.get("trusted_verifiers", [])),
        trusted_provenance_roots=frozenset(data.get("trusted_provenance_roots", [])),
        authorized_authorities=frozenset(data.get("authorized_authorities", [])),
    )


def evidence(item: dict) -> EvidenceEnvelope:
    return EvidenceEnvelope(**item)


def acceptance_output(name: str, result) -> dict:
    output = {
        "name": name,
        "decision": result.decision.value,
        "reasons": list(result.reasons),
    }
    if result.proof is not None:
        output["proof_digest"] = result.proof.digest
    return output


def main() -> int:
    fixture = json.loads(Path(sys.argv[1]).read_text(encoding="utf-8"))
    results = []
    for case in fixture["cases"]:
        kind = case["kind"]
        if kind == "acceptance":
            items = [evidence(item) for item in case["input"]["evidence"]]
            result = evaluate_acceptance(
                context(case["input"]["context"]),
                items,
                now_epoch=case["input"]["now_epoch"],
                executor_done=True,
            )
            results.append(acceptance_output(case["name"], result))
        elif kind == "identity":
            try:
                Mission(case["input"]["mission_id"], "objective")
                results.append({"name": case["name"], "decision": "ACCEPT"})
            except Exception:
                results.append({"name": case["name"], "decision": "REJECT"})
        else:
            raise ValueError(f"unsupported differential case kind: {kind}")
    json.dump(results, sys.stdout, sort_keys=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
