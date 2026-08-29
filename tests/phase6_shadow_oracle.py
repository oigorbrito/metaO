from __future__ import annotations

import json
import sys
import threading
from types import SimpleNamespace
from dataclasses import asdict, is_dataclass, replace
from pathlib import Path
from time import perf_counter
from collections.abc import Mapping

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from metao.acceptance import (
    AcceptanceContext,
    AcceptanceDecision,
    EvidenceEnvelope,
    evaluate_acceptance,
    replay_acceptance_decision,
)
from metao.core import (
    ExecutionRequest,
    ExecutionResult,
    ExecutionStatus,
    Mission,
)
from metao.governance import (
    AcceptanceBudget,
    AcceptanceBudgetAuthority,
    ApprovalRecord,
    PolicyEffect,
    apply_confidence_after_hard_gates,
    evaluate_policy,
    require_human,
    resume_after_approval,
)


def _jsonable(value):
    if is_dataclass(value):
        return _jsonable(asdict(value))
    if isinstance(value, Mapping):
        return {str(k): _jsonable(v) for k, v in value.items()}
    if isinstance(value, (list, tuple, set, frozenset)):
        return [_jsonable(v) for v in value]
    if hasattr(value, "value") and not isinstance(value, str):
        return value.value
    return value


def _comparison_kind(category: str) -> str:
    return "HARNESS_ONLY" if category == "runtime" else "REAL_PYTHON_VS_REAL_RUST"


def _context(
    *,
    subject_id: str = "subject-1",
    subject_state_id: str = "state-1",
    verification_context_id: str = "ctx-1",
    policy_bundle_id: str = "policy-1",
    required_obligations: tuple[str, ...] = ("verify",),
    trusted_verifiers: tuple[str, ...] = ("verifier-1",),
    trusted_provenance_roots: tuple[str, ...] = ("root-1",),
    authorized_authorities: tuple[str, ...] = ("authority-1",),
) -> AcceptanceContext:
    return AcceptanceContext(
        subject_id=subject_id,
        subject_state_id=subject_state_id,
        verification_context_id=verification_context_id,
        policy_bundle_id=policy_bundle_id,
        required_obligations=frozenset(required_obligations),
        trusted_verifiers=frozenset(trusted_verifiers),
        trusted_provenance_roots=frozenset(trusted_provenance_roots),
        authorized_authorities=frozenset(authorized_authorities),
    )


def _evidence(**overrides) -> EvidenceEnvelope:
    data = dict(
        evidence_id="e1",
        obligation_id="verify",
        mission_id="m1",
        execution_id="x1",
        orchestrator_id="orch-a",
        adapter_version="1",
        attempt_id="a1",
        subject_id="subject-1",
        subject_state_id="state-1",
        verification_context_id="ctx-1",
        policy_bundle_id="policy-1",
        verifier_id="verifier-1",
        payload_digest="abc",
        provenance_root="root-1",
        authority_id="authority-1",
        passed=True,
        created_at_epoch=10.0,
        expires_at_epoch=20.0,
        approval_id=None,
        confidence=None,
    )
    data.update(overrides)
    return EvidenceEnvelope(**data)


def _acceptance_result(result):
    proof = result.proof
    return {
        "decision": result.decision.value,
        "reasons": list(result.reasons),
        "proof_digest": None if proof is None else proof.digest,
        "proof_evidence_ids": None if proof is None else list(proof.evidence_ids),
    }


def _policy_result(result):
    return {
        "effect": result.effect.value,
        "policy_bundle_id": result.policy_bundle_id,
        "reason": result.reason,
    }


def _approval_request(**kwargs):
    return require_human(**kwargs)


def _approval_record(**kwargs):
    return ApprovalRecord(**kwargs)


class _SuccessRuntime:
    def __init__(self, runtime_id: str, version: str = "1") -> None:
        self._runtime_id = runtime_id
        self._version = version

    @property
    def descriptor(self):
        return SimpleNamespace(orchestrator_id=self._runtime_id, version=self._version)

    def execute(self, request: ExecutionRequest):
        return ExecutionResult(
            request.execution_id,
            self._runtime_id,
            ExecutionStatus.SUCCEEDED,
            output={"result": f"{self._runtime_id}:{request.mission.mission_id}"},
        )

    def cancel(self, execution_id: str):
        return None


class _CrashRuntime(_SuccessRuntime):
    def execute(self, request: ExecutionRequest):
        raise RuntimeError("simulated runtime crash")


class _TimeoutRuntime(_SuccessRuntime):
    def execute(self, request: ExecutionRequest):
        raise TimeoutError("simulated runtime timeout")


def _mission_outcome(
    *,
    runtime,
    fallback=None,
    execution_id: str,
    mission_id: str,
    now_epoch: float,
    acceptance_context: AcceptanceContext,
    evidence: list[EvidenceEnvelope],
):
    mission = Mission(mission_id, "shadow mode", frozenset({"workflow"}))
    request = SimpleNamespace(execution_id=execution_id, mission=mission)
    attempts = []
    attempted_orchestrators = []
    state = ["CREATED", "PLANNING", "SELECTING"]
    execution = None

    try:
        execution = runtime.execute(request)
        attempts.append(
            {
                "attempt_number": 1,
                "execution_id": execution.execution_id,
                "orchestrator_id": runtime.descriptor.orchestrator_id,
                "execution_status": execution.status.value,
                "acceptance_decision": "NOT_DONE",
                "reasons": [],
            }
        )
        attempted_orchestrators.append(runtime.descriptor.orchestrator_id)
        state.extend(["RUNNING", "VERIFYING"])
    except Exception as exc:
        attempts.append(
            {
                "attempt_number": 1,
                "execution_id": execution_id,
                "orchestrator_id": runtime.descriptor.orchestrator_id,
                "execution_status": "FAILED",
                "acceptance_decision": "NOT_DONE",
                "reasons": [type(exc).__name__.lower()],
                "error": str(exc),
            }
        )
        attempted_orchestrators.append(runtime.descriptor.orchestrator_id)
        state.extend(["RUNNING", "FAILED", "REPLANNING"])
        if fallback is None:
            execution = ExecutionResult(execution_id, runtime.descriptor.orchestrator_id, ExecutionStatus.FAILED, error=str(exc))
        else:
            try:
                execution = fallback.execute(request)
                attempts.append(
                    {
                        "attempt_number": 2,
                        "execution_id": execution.execution_id,
                        "orchestrator_id": fallback.descriptor.orchestrator_id,
                        "execution_status": execution.status.value,
                        "acceptance_decision": "NOT_DONE",
                        "reasons": [],
                    }
                )
                attempted_orchestrators.append(fallback.descriptor.orchestrator_id)
                state.extend(["RUNNING", "VERIFYING"])
            except Exception as retry_exc:
                attempts.append(
                    {
                        "attempt_number": 2,
                        "execution_id": execution_id,
                        "orchestrator_id": fallback.descriptor.orchestrator_id,
                        "execution_status": "FAILED",
                        "acceptance_decision": "NOT_DONE",
                        "reasons": [type(retry_exc).__name__.lower()],
                        "error": str(retry_exc),
                    }
                )
                attempted_orchestrators.append(fallback.descriptor.orchestrator_id)
                execution = ExecutionResult(
                    execution_id,
                    fallback.descriptor.orchestrator_id,
                    ExecutionStatus.FAILED,
                    error=str(retry_exc),
                )

    acceptance = evaluate_acceptance(
        acceptance_context,
        tuple(evidence),
        now_epoch=now_epoch,
        executor_done=True,
    )
    mission_state = {
        "status": "ACCEPTED" if acceptance.decision is AcceptanceDecision.ACCEPT else ("FAILED" if execution.status is ExecutionStatus.FAILED else "VERIFYING"),
        "history": state + ([ "ACCEPTED" ] if acceptance.decision is AcceptanceDecision.ACCEPT else []),
        "attempts": attempts,
    }
    execution_summary = None
    if execution is not None:
        execution_summary = {
            "execution_id": execution.execution_id,
            "orchestrator_id": execution.orchestrator_id,
            "status": execution.status.value,
            "output": None if execution.output is None else _jsonable(execution.output),
            "error": execution.error,
        }

    return {
        "mission_id": mission_id,
        "orchestrator_id": getattr(execution, "orchestrator_id", None) if execution is not None else None,
        "attempted_orchestrators": attempted_orchestrators,
        "execution": execution_summary,
        "acceptance": acceptance,
        "state": mission_state,
        "budget": AcceptanceBudget(1.0, 1000, 60.0, 4),
    }


def _runtime_summary(outcome):
    execution = outcome["execution"]
    state = outcome["state"]
    return {
        "mission_id": outcome["mission_id"],
        "orchestrator_id": outcome["orchestrator_id"],
        "attempted_orchestrators": list(outcome["attempted_orchestrators"]),
        "execution_status": None if execution is None else execution["status"],
        "execution_error": None if execution is None else execution.get("error"),
        "execution_output": None if execution is None else execution.get("output"),
        "acceptance": {
            "decision": outcome["acceptance"].decision.value,
            "reasons": list(outcome["acceptance"].reasons),
        },
        "state": state,
        "budget": _jsonable(outcome["budget"]),
    }


def _budget_authority():
    return AcceptanceBudgetAuthority(AcceptanceBudget(10.0, 10_000, 60.0, 10))


def _proof_payload(result):
    proof = result.proof
    replay = replay_acceptance_decision(proof)
    return {
        "decision": result.decision.value,
        "replay_decision": replay.value,
        "reasons": list(result.reasons),
        "proof_digest": proof.digest,
        "proof_evidence_ids": list(proof.evidence_ids),
    }


def _acceptance_context(**kwargs):
    return _context(**kwargs)


def _run_case(case: dict) -> dict:
    scenario = case["scenario"]
    started = perf_counter()
    semantic: dict
    metrics: dict

    if case["category"] in {"acceptance", "authority_provenance"}:
        ctx = _acceptance_context()
        evidence = [_evidence()]
        now_epoch = 15.0
        if scenario == "succeeded_without_evidence":
            evidence = []
        elif scenario == "failed_obligation":
            evidence = [_evidence(passed=False)]
        elif scenario == "stale_evidence":
            evidence = [_evidence(expires_at_epoch=12.0)]
        elif scenario == "future_evidence":
            evidence = [_evidence(created_at_epoch=20.0, expires_at_epoch=30.0)]
        elif scenario == "subject_mismatch":
            evidence = [_evidence(subject_id="other-subject")]
        elif scenario == "subject_state_mismatch":
            evidence = [_evidence(subject_state_id="other-state")]
        elif scenario == "verification_context_mismatch":
            evidence = [_evidence(verification_context_id="other-ctx")]
        elif scenario == "policy_bundle_mismatch":
            evidence = [_evidence(policy_bundle_id="other-policy")]
        elif scenario == "missing_provenance":
            evidence = [_evidence(payload_digest="", provenance_root="")]
        elif scenario == "untrusted_verifier":
            evidence = [_evidence(verifier_id="evil-verifier")]
        elif scenario == "untrusted_provenance_root":
            evidence = [_evidence(provenance_root="evil-root")]
        elif scenario == "missing_authority":
            evidence = [_evidence(authority_id="")]
        elif scenario == "unauthorized_authority":
            evidence = [_evidence(authority_id="evil-authority")]
        elif scenario == "trusted_exact_evidence":
            ctx = _acceptance_context()
            evidence = [_evidence()]
        result = evaluate_acceptance(ctx, tuple(evidence), now_epoch=now_epoch, executor_done=True)
        semantic = _acceptance_result(result)

    elif case["category"] == "policy":
        if scenario == "allow_default":
            result = evaluate_policy(policy_bundle_id="policy-1", allowed=True)
        elif scenario == "deny_default":
            result = evaluate_policy(policy_bundle_id="policy-1", allowed=False)
        elif scenario == "require_human_default":
            result = evaluate_policy(policy_bundle_id="policy-1", allowed=True, require_human=True)
        elif scenario == "deny_overrides_require_human":
            result = evaluate_policy(policy_bundle_id="policy-1", allowed=False, require_human=True)
        else:
            raise ValueError(scenario)
        semantic = _policy_result(result)

    elif case["category"] == "approval":
        request = _approval_request(
            approval_id="ap-1",
            mission_id="m1",
            execution_id="x1",
            subject_state_id="s1",
            policy_bundle_id="p1",
            reason="high risk",
        )
        if scenario == "approved_exact_binding":
            record = _approval_record(
                approval_id="ap-1",
                mission_id="m1",
                execution_id="x1",
                subject_state_id="s1",
                policy_bundle_id="p1",
                approver_id="human-1",
                approved=True,
            )
            decision = resume_after_approval(request, record)
            semantic = {"request": _jsonable(request), "record": _jsonable(record), "decision": decision.value}
        elif scenario == "denied_exact_binding":
            record = _approval_record(
                approval_id="ap-1",
                mission_id="m1",
                execution_id="x1",
                subject_state_id="s1",
                policy_bundle_id="p1",
                approver_id="human-1",
                approved=False,
            )
            decision = resume_after_approval(request, record)
            semantic = {"request": _jsonable(request), "record": _jsonable(record), "decision": decision.value}
        elif scenario == "approval_id_mismatch":
            record = _approval_record(
                approval_id="ap-2",
                mission_id="m1",
                execution_id="x1",
                subject_state_id="s1",
                policy_bundle_id="p1",
                approver_id="human-1",
                approved=True,
            )
            decision = resume_after_approval(request, record)
            semantic = {"request": _jsonable(request), "record": _jsonable(record), "decision": decision.value}
        elif scenario == "low_confidence_requires_human":
            decision = apply_confidence_after_hard_gates(AcceptanceDecision.ACCEPT, confidence=0.4)
            semantic = {"decision": decision.value, "confidence": 0.4, "threshold": 0.8}
        elif scenario == "invalid_confidence_fails_closed":
            try:
                apply_confidence_after_hard_gates(AcceptanceDecision.ACCEPT, confidence=1.1)
            except Exception as exc:
                semantic = {"error_category": "invalid_confidence"}
            else:
                raise AssertionError("invalid confidence must fail closed")
        else:
            raise ValueError(scenario)

    elif case["category"] == "budget":
        authority = _budget_authority()
        if scenario == "shared_budget_no_oversubscription":
            barrier = threading.Barrier(2)
            accepted: list[str] = []
            rejected: list[str] = []
            lock = threading.Lock()

            def reserve_six(reservation_id: str):
                barrier.wait()
                try:
                    authority.reserve(reservation_id, money=6.0)
                except Exception:
                    with lock:
                        rejected.append(reservation_id)
                    return
                with lock:
                    accepted.append(reservation_id)

            threads = [
                threading.Thread(target=reserve_six, args=("r1",)),
                threading.Thread(target=reserve_six, args=("r2",)),
            ]
            for thread in threads:
                thread.start()
            for thread in threads:
                thread.join()
            semantic = {
                "accepted": sorted(accepted),
                "rejected": sorted(rejected),
                "winner_money": authority.reservation(accepted[0]).money if accepted else None,
                "money_used": authority.snapshot().money_used,
            }
        elif scenario == "exact_capacity_admission":
            authority.reserve("r1", money=5.0)
            authority.reserve("r2", money=5.0)
            semantic = {
                "reservation_r1": _jsonable(authority.reservation("r1")),
                "reservation_r2": _jsonable(authority.reservation("r2")),
                "money_used": authority.snapshot().money_used,
            }
        elif scenario == "failed_reservation_no_mutation":
            authority.reserve("winner", money=8.0)
            try:
                authority.reserve("loser", money=3.0)
            except Exception as exc:
                rejected = "budget_exhausted"
            semantic = {
                "winner": _jsonable(authority.reservation("winner")),
                "loser": _jsonable(authority.reservation("loser")),
                "reject_error": rejected,
                "money_used": authority.snapshot().money_used,
                "settled": _jsonable(authority.settle("winner")),
            }
        elif scenario == "duplicate_reservation_replay_idempotent":
            first = authority.reserve("reservation-1", money=4.0, tokens=10)
            retry = authority.reserve("reservation-1", money=4.0, tokens=10)
            semantic = {
                "first": _jsonable(first),
                "retry": _jsonable(retry),
                "money_used": authority.snapshot().money_used,
            }
        elif scenario == "conflicting_reservation_replay_fails_closed":
            authority.reserve("reservation-1", money=4.0)
            try:
                authority.reserve("reservation-1", money=5.0)
            except Exception as exc:
                semantic = {
                    "error_category": "replay_conflict",
                    "reservation": _jsonable(authority.reservation("reservation-1")),
                }
            else:
                raise AssertionError("conflicting reservation must fail")
        elif scenario == "settlement_retry_idempotent":
            authority.reserve("reservation-1", money=4.0)
            first = authority.settle("reservation-1")
            retry = authority.settle("reservation-1")
            semantic = {
                "first": _jsonable(first),
                "retry": _jsonable(retry),
                "reservation": _jsonable(authority.reservation("reservation-1")),
            }
        elif scenario == "concurrent_same_settlement_single_effect":
            authority.reserve("reservation-1", money=4.0)
            barrier = threading.Barrier(2)
            results: list[float] = []
            lock = threading.Lock()

            def settle_same():
                barrier.wait()
                snapshot = authority.settle("reservation-1")
                with lock:
                    results.append(snapshot.money_used)

            threads = [threading.Thread(target=settle_same) for _ in range(2)]
            for thread in threads:
                thread.start()
            for thread in threads:
                thread.join()
            semantic = {
                "results": sorted(results),
                "money_used": authority.snapshot().money_used,
                "reservation": _jsonable(authority.reservation("reservation-1")),
            }
        elif scenario == "unknown_settlement_id_fails_closed":
            try:
                authority.settle("missing-reservation")
            except Exception as exc:
                semantic = {
                    "error_category": "unknown_reservation",
                    "money_used": authority.snapshot().money_used,
                }
            else:
                raise AssertionError("unknown settlement must fail closed")
        else:
            raise ValueError(scenario)

    elif case["category"] == "proof":
        evidence_a = EvidenceEnvelope(
            evidence_id="e-a",
            obligation_id="a",
            mission_id="mission-l5",
            execution_id="exec-l5",
            orchestrator_id="runtime-l5",
            adapter_version="1",
            attempt_id="attempt-l5",
            subject_id="subject-l5",
            subject_state_id="state-l5",
            verification_context_id="verify-l5",
            policy_bundle_id="policy-l5",
            verifier_id="verifier-l5",
            payload_digest="digest-e-a",
            provenance_root="root-l5",
            authority_id="authority-l5",
            passed=True,
            created_at_epoch=10.0,
            expires_at_epoch=100.0,
            approval_id=None,
            confidence=None,
        )
        evidence_b = EvidenceEnvelope(
            evidence_id="e-b",
            obligation_id="b",
            mission_id="mission-l5",
            execution_id="exec-l5",
            orchestrator_id="runtime-l5",
            adapter_version="1",
            attempt_id="attempt-l5",
            subject_id="subject-l5",
            subject_state_id="state-l5",
            verification_context_id="verify-l5",
            policy_bundle_id="policy-l5",
            verifier_id="verifier-l5",
            payload_digest="digest-e-b",
            provenance_root="root-l5",
            authority_id="authority-l5",
            passed=True,
            created_at_epoch=11.0,
            expires_at_epoch=100.0,
            approval_id=None,
            confidence=None,
        )
        base = evaluate_acceptance(
            _context(required_obligations=("a", "b"), subject_id="subject-l5", subject_state_id="state-l5", verification_context_id="verify-l5", policy_bundle_id="policy-l5", trusted_verifiers=("verifier-l5",), trusted_provenance_roots=("root-l5",), authorized_authorities=("authority-l5",)),
            (evidence_a, evidence_b),
            now_epoch=20.0,
            executor_done=True,
        )
        if scenario == "valid_replay":
            semantic = _proof_payload(base)
        elif scenario == "tampered_evidence_ids":
            tampered = replace(base.proof, evidence_ids=("forged",))
            try:
                replay_acceptance_decision(tampered)
            except Exception as exc:
                semantic = {"error_category": "proof_digest_mismatch", "proof_digest": base.proof.digest}
            else:
                raise AssertionError("tampered proof must fail")
        elif scenario == "tampered_decision":
            tampered = replace(base.proof, decision=AcceptanceDecision.BLOCK)
            try:
                replay_acceptance_decision(tampered)
            except Exception as exc:
                semantic = {"error_category": "proof_digest_mismatch"}
            else:
                raise AssertionError("tampered proof decision must fail")
        elif scenario == "tampered_reasons":
            tampered = replace(base.proof, reasons=("forged",))
            try:
                replay_acceptance_decision(tampered)
            except Exception as exc:
                semantic = {"error_category": "proof_digest_mismatch"}
            else:
                raise AssertionError("tampered proof reasons must fail")
        elif scenario == "tampered_digest":
            tampered = replace(base.proof, digest="forged")
            try:
                replay_acceptance_decision(tampered)
            except Exception as exc:
                semantic = {"error_category": "proof_digest_mismatch"}
            else:
                raise AssertionError("tampered proof digest must fail")
        elif scenario == "order_independent":
            shuffled = evaluate_acceptance(
                _context(
                    required_obligations=("a", "b"),
                    subject_id="subject-l5",
                    subject_state_id="state-l5",
                    verification_context_id="verify-l5",
                    policy_bundle_id="policy-l5",
                    trusted_verifiers=("verifier-l5",),
                    trusted_provenance_roots=("root-l5",),
                    authorized_authorities=("authority-l5",),
                ),
                (evidence_b, evidence_a),
                now_epoch=20.0,
                executor_done=True,
            )
            semantic = {
                "base": _proof_payload(base),
                "shuffled": _proof_payload(shuffled),
                "proof_equal": base.proof == shuffled.proof,
            }
        else:
            raise ValueError(scenario)

    elif case["category"] == "runtime":
        acceptance_context = _context(
            subject_id="subject-rt",
            subject_state_id="state-rt",
            verification_context_id="verify-rt",
            policy_bundle_id="policy-rt",
            required_obligations=("execution_result",),
            trusted_verifiers=("verifier-rt",),
            trusted_provenance_roots=("root-rt",),
            authorized_authorities=("authority-rt",),
        )
        mission_id = "mission-rt"
        execution_id = "exec-rt"
        output_evidence = _evidence(
            evidence_id="e-rt",
            obligation_id="execution_result",
            mission_id="mission-rt",
            execution_id="exec-rt",
            orchestrator_id="runtime-a",
            adapter_version="wire-1",
            attempt_id="attempt-1",
            subject_id="subject-rt",
            subject_state_id="state-rt",
            verification_context_id="verify-rt",
            policy_bundle_id="policy-rt",
            verifier_id="verifier-rt",
            payload_digest="digest-runtime",
            provenance_root="root-rt",
            authority_id="authority-rt",
            passed=True,
            created_at_epoch=10.0,
            expires_at_epoch=40.0,
        )

        if scenario == "success_without_evidence":
            runtime = _SuccessRuntime("runtime-a")
            outcome = _mission_outcome(
                runtime=runtime,
                execution_id=execution_id,
                mission_id=mission_id,
                now_epoch=20.0,
                acceptance_context=acceptance_context,
                evidence=[],
            )
            semantic = _runtime_summary(outcome)
        elif scenario == "recovered_success_without_evidence":
            runtime = _CrashRuntime("runtime-a")
            fallback = _SuccessRuntime("runtime-b")
            outcome = _mission_outcome(
                runtime=runtime,
                fallback=fallback,
                execution_id=execution_id,
                mission_id=mission_id,
                now_epoch=20.0,
                acceptance_context=acceptance_context,
                evidence=[],
            )
            semantic = _runtime_summary(outcome)
        elif scenario == "failover_success_without_evidence":
            runtime = _CrashRuntime("runtime-a")
            fallback = _SuccessRuntime("runtime-b")
            outcome = _mission_outcome(
                runtime=runtime,
                fallback=fallback,
                execution_id=execution_id,
                mission_id=mission_id,
                now_epoch=20.0,
                acceptance_context=acceptance_context,
                evidence=[],
            )
            semantic = _runtime_summary(outcome)
        elif scenario == "failover_success_with_valid_evidence":
            runtime = _CrashRuntime("runtime-a")
            fallback = _SuccessRuntime("runtime-b")
            outcome = _mission_outcome(
                runtime=runtime,
                fallback=fallback,
                execution_id=execution_id,
                mission_id=mission_id,
                now_epoch=20.0,
                acceptance_context=acceptance_context,
                evidence=[output_evidence],
            )
            semantic = _runtime_summary(outcome)
        elif scenario == "crash_recovery":
            runtime = _CrashRuntime("runtime-a")
            fallback = _SuccessRuntime("runtime-b")
            outcome = _mission_outcome(
                runtime=runtime,
                fallback=fallback,
                execution_id=execution_id,
                mission_id=mission_id,
                now_epoch=20.0,
                acceptance_context=acceptance_context,
                evidence=[],
            )
            semantic = _runtime_summary(outcome)
        elif scenario == "timeout_recovery":
            runtime = _TimeoutRuntime("runtime-a")
            fallback = _SuccessRuntime("runtime-b")
            outcome = _mission_outcome(
                runtime=runtime,
                fallback=fallback,
                execution_id=execution_id,
                mission_id=mission_id,
                now_epoch=20.0,
                acceptance_context=acceptance_context,
                evidence=[],
            )
            semantic = _runtime_summary(outcome)
        else:
            raise ValueError(scenario)

    else:
        raise ValueError(case["category"])

    elapsed_ms = (perf_counter() - started) * 1000.0
    metrics = {"duration_ms": round(elapsed_ms, 3)}
    return {
        "case_id": case["case_id"],
        "category": case["category"],
        "scenario": scenario,
        "comparison_kind": _comparison_kind(case["category"]),
        "semantic": semantic,
        "metrics": metrics,
    }


def main() -> int:
    fixture = json.loads(Path(sys.argv[1]).read_text(encoding="utf-8"))
    results = [_run_case(case) for case in fixture["cases"]]
    json.dump(results, sys.stdout, sort_keys=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
