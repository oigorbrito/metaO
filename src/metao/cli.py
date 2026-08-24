"""Dependency-free operator CLI for metaO.

The CLI owns persistence wiring only. Runtime wiring is supplied explicitly by a
local factory (``module:function``) returning a configured MissionOperator, so
no orchestrator SDK leaks into the CLI or Core. Observability is added by the
CLI as a decorator over that operator and persisted in the same SQLite file.
"""

from __future__ import annotations

import argparse
import importlib
import json
from pathlib import Path
import sys
from typing import Any, Mapping, Sequence, TextIO

from .acceptance import AcceptanceContext
from .core import Mission
from .governance import AcceptanceBudget, evaluate_policy
from .mission_store import MissionAlreadyExists, MissionNotFound, MissionRecord
from .observability import MissionEvent, MissionEventKind, thaw_event_value
from .observed_operator import ObservableMissionOperator
from .operator import MissionApprovalError, MissionOperator
from .sqlite_event_ledger import EventLedgerCorrupt, SQLiteEventLedger
from .sqlite_store import SQLiteMissionStore


DEFAULT_DB = ".metao/metao.db"


class CLIInputError(ValueError):
    pass


def _as_object(value: Any, name: str) -> Mapping[str, Any]:
    if not isinstance(value, dict):
        raise CLIInputError(f"{name} must be a JSON object")
    return value


def _required_string(data: Mapping[str, Any], key: str) -> str:
    value = data.get(key)
    if not isinstance(value, str) or not value:
        raise CLIInputError(f"{key} must be a non-empty string")
    return value


def _string_set(data: Mapping[str, Any], key: str) -> frozenset[str]:
    value = data.get(key, [])
    if not isinstance(value, list) or any(not isinstance(item, str) or not item for item in value):
        raise CLIInputError(f"{key} must be a list of non-empty strings")
    return frozenset(value)


def _load_run_spec(path: str | Path) -> dict[str, Any]:
    try:
        payload = json.loads(Path(path).read_text(encoding="utf-8"))
    except OSError as exc:
        raise CLIInputError(f"cannot read mission file: {path}") from exc
    except json.JSONDecodeError as exc:
        raise CLIInputError(f"invalid mission JSON: {path}") from exc

    root = _as_object(payload, "mission file")
    mission_data = _as_object(root.get("mission"), "mission")
    policy_data = _as_object(root.get("policy"), "policy")
    budget_data = _as_object(root.get("budget"), "budget")
    acceptance_data = _as_object(root.get("acceptance_context"), "acceptance_context")

    mission = Mission(
        _required_string(mission_data, "mission_id"),
        _required_string(mission_data, "objective"),
        _string_set(mission_data, "required_capabilities"),
    )

    allowed = policy_data.get("allowed")
    require_human = policy_data.get("require_human", False)
    if not isinstance(allowed, bool) or not isinstance(require_human, bool):
        raise CLIInputError("policy allowed/require_human must be booleans")
    policy = evaluate_policy(
        policy_bundle_id=_required_string(policy_data, "policy_bundle_id"),
        allowed=allowed,
        require_human=require_human,
        reason=str(policy_data.get("reason", "")),
    )

    try:
        budget = AcceptanceBudget(
            money_limit=float(budget_data["money_limit"]),
            token_limit=int(budget_data["token_limit"]),
            wall_time_limit_s=float(budget_data["wall_time_limit_s"]),
            verifier_attempt_limit=int(budget_data["verifier_attempt_limit"]),
        )
    except (KeyError, TypeError, ValueError) as exc:
        raise CLIInputError("budget requires numeric money/token/wall-time/verifier limits") from exc

    acceptance_context = AcceptanceContext(
        subject_id=_required_string(acceptance_data, "subject_id"),
        subject_state_id=_required_string(acceptance_data, "subject_state_id"),
        verification_context_id=_required_string(acceptance_data, "verification_context_id"),
        policy_bundle_id=_required_string(acceptance_data, "policy_bundle_id"),
        required_obligations=_string_set(acceptance_data, "required_obligations"),
        trusted_verifiers=_string_set(acceptance_data, "trusted_verifiers"),
        trusted_provenance_roots=_string_set(acceptance_data, "trusted_provenance_roots"),
        authorized_authorities=_string_set(acceptance_data, "authorized_authorities"),
    )

    prefix = root.get("execution_id_prefix")
    if prefix is not None and (not isinstance(prefix, str) or not prefix):
        raise CLIInputError("execution_id_prefix must be a non-empty string")
    try:
        now_epoch = float(root.get("now_epoch", 0.0))
        max_attempts = int(root.get("max_attempts", 2))
    except (TypeError, ValueError) as exc:
        raise CLIInputError("now_epoch/max_attempts must be numeric") from exc
    if max_attempts < 1:
        raise CLIInputError("max_attempts must be at least 1")

    return {
        "mission": mission,
        "policy": policy,
        "budget": budget,
        "acceptance_context": acceptance_context,
        "execution_id_prefix": prefix,
        "now_epoch": now_epoch,
        "max_attempts": max_attempts,
    }


def _load_operator(
    factory_spec: str,
    store: SQLiteMissionStore,
    ledger: SQLiteEventLedger | None = None,
) -> MissionOperator | ObservableMissionOperator:
    if ":" not in factory_spec:
        raise CLIInputError("factory must use module:function syntax")
    module_name, attribute = factory_spec.split(":", 1)
    if not module_name or not attribute:
        raise CLIInputError("factory must use module:function syntax")
    module = importlib.import_module(module_name)
    factory: Any = module
    for part in attribute.split("."):
        factory = getattr(factory, part)
    if not callable(factory):
        raise CLIInputError("factory target is not callable")
    operator = factory(store=store)
    if not isinstance(operator, MissionOperator):
        raise CLIInputError("factory must return MissionOperator")
    if ledger is None:
        return operator
    return ObservableMissionOperator(operator, ledger)


def _attempt_view(record: MissionRecord) -> list[dict[str, Any]]:
    assert record.outcome.state is not None
    return [
        {
            "attempt_number": item.attempt_number,
            "execution_id": item.execution_id,
            "orchestrator_id": item.orchestrator_id,
            "execution_status": None if item.execution_status is None else item.execution_status.value,
            "acceptance_decision": item.acceptance_decision.value,
            "reasons": list(item.reasons),
        }
        for item in record.outcome.state.attempts
    ]


def _record_view(record: MissionRecord, *, detailed: bool) -> dict[str, Any]:
    assert record.outcome.state is not None
    base: dict[str, Any] = {
        "mission_id": record.mission_id,
        "status": record.status.value,
        "revision": record.revision,
        "orchestrator_id": record.outcome.orchestrator_id,
        "acceptance_decision": record.outcome.acceptance.decision.value,
        "attempted_orchestrators": list(record.outcome.attempted_orchestrators),
    }
    if not detailed:
        return base

    request = record.approval_request
    decision = record.approval_record
    execution = record.outcome.execution
    proof = record.outcome.acceptance.proof
    base.update(
        {
            "mission": {
                "objective": record.mission.objective,
                "required_capabilities": sorted(record.mission.required_capabilities),
            },
            "history": [item.value for item in record.outcome.state.history],
            "attempts": _attempt_view(record),
            "acceptance": {
                "decision": record.outcome.acceptance.decision.value,
                "reasons": list(record.outcome.acceptance.reasons),
                "proof": None if proof is None else {
                    "decision": proof.decision.value,
                    "reasons": list(proof.reasons),
                    "evidence_ids": list(proof.evidence_ids),
                    "digest": proof.digest,
                },
            },
            "budget": {
                "money_limit": record.outcome.budget.money_limit,
                "money_used": record.outcome.budget.money_used,
                "token_limit": record.outcome.budget.token_limit,
                "tokens_used": record.outcome.budget.tokens_used,
                "wall_time_limit_s": record.outcome.budget.wall_time_limit_s,
                "wall_time_used_s": record.outcome.budget.wall_time_used_s,
                "verifier_attempt_limit": record.outcome.budget.verifier_attempt_limit,
                "verifier_attempts_used": record.outcome.budget.verifier_attempts_used,
            },
            "execution": None if execution is None else {
                "execution_id": execution.execution_id,
                "orchestrator_id": execution.orchestrator_id,
                "status": execution.status.value,
                "output": dict(execution.output),
                "error": execution.error,
            },
            "approval_request": None if request is None else {
                "approval_id": request.approval_id,
                "execution_id": request.execution_id,
                "subject_state_id": request.subject_state_id,
                "policy_bundle_id": request.policy_bundle_id,
                "reason": request.reason,
            },
            "approval_record": None if decision is None else {
                "approval_id": decision.approval_id,
                "approver_id": decision.approver_id,
                "approved": decision.approved,
            },
        }
    )
    return base


def _event_view(event: MissionEvent) -> dict[str, Any]:
    return {
        "event_id": event.event_id,
        "mission_id": event.mission_id,
        "sequence": event.sequence,
        "kind": event.kind.value,
        "occurred_at_epoch": event.occurred_at_epoch,
        "payload": thaw_event_value(event.payload),
    }


def _write_json(value: Any, stream: TextIO) -> None:
    stream.write(json.dumps(value, sort_keys=True, separators=(",", ":"), default=str))
    stream.write("\n")


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="metao", description="metaO control-plane operator CLI")
    parser.add_argument("--db", default=DEFAULT_DB, help=f"SQLite mission database (default: {DEFAULT_DB})")
    sub = parser.add_subparsers(dest="command", required=True)

    run_parser = sub.add_parser("run", help="run a mission JSON specification")
    run_parser.add_argument("mission_file")
    run_parser.add_argument("--factory", required=True, help="configured operator factory module:function")

    status_parser = sub.add_parser("status", help="show mission status")
    status_parser.add_argument("mission_id")

    inspect_parser = sub.add_parser("inspect", help="show auditable mission record")
    inspect_parser.add_argument("mission_id")

    sub.add_parser("list", help="list persisted missions")

    events_parser = sub.add_parser("events", help="show persisted mission event ledger")
    events_parser.add_argument("mission_id")
    events_parser.add_argument("--kind", choices=[kind.value for kind in MissionEventKind])

    approve_parser = sub.add_parser("approve", help="record human approval or denial")
    approve_parser.add_argument("mission_id")
    approve_parser.add_argument("--approver", required=True)
    approve_parser.add_argument("--deny", action="store_true")
    approve_parser.add_argument("--factory", required=True, help="configured operator factory module:function")
    approve_parser.add_argument("--now-epoch", type=float, default=0.0)

    resume_parser = sub.add_parser("resume", help="resume an approved waiting mission")
    resume_parser.add_argument("mission_id")
    resume_parser.add_argument("--factory", required=True, help="configured operator factory module:function")
    resume_parser.add_argument("--now-epoch", type=float, default=0.0)
    return parser


def main(argv: Sequence[str] | None = None, *, stdout: TextIO | None = None, stderr: TextIO | None = None) -> int:
    out = stdout or sys.stdout
    err = stderr or sys.stderr
    args = _parser().parse_args(argv)

    try:
        store = SQLiteMissionStore(args.db)
        ledger = SQLiteEventLedger(args.db)
        if args.command == "run":
            operator = _load_operator(args.factory, store, ledger)
            spec = _load_run_spec(args.mission_file)
            outcome = operator.run(**spec)
            _write_json(_record_view(operator.inspect(outcome.mission_id), detailed=False), out)
            return 0
        if args.command == "status":
            record = store.get(args.mission_id)
            _write_json({"mission_id": record.mission_id, "status": record.status.value, "revision": record.revision}, out)
            return 0
        if args.command == "inspect":
            _write_json(_record_view(store.get(args.mission_id), detailed=True), out)
            return 0
        if args.command == "list":
            _write_json([_record_view(record, detailed=False) for record in store.list()], out)
            return 0
        if args.command == "events":
            items = ledger.list(args.mission_id)
            if not items:
                store.get(args.mission_id)
            if args.kind is not None:
                requested = MissionEventKind(args.kind)
                items = tuple(event for event in items if event.kind is requested)
            _write_json([_event_view(event) for event in items], out)
            return 0
        if args.command == "approve":
            operator = _load_operator(args.factory, store, ledger)
            record = operator.approve(
                args.mission_id,
                approver_id=args.approver,
                approved=not args.deny,
                now_epoch=args.now_epoch,
            )
            _write_json(_record_view(record, detailed=False), out)
            return 0
        if args.command == "resume":
            operator = _load_operator(args.factory, store, ledger)
            operator.resume(args.mission_id, now_epoch=args.now_epoch)
            _write_json(_record_view(operator.inspect(args.mission_id), detailed=False), out)
            return 0
        raise CLIInputError(f"unsupported command: {args.command}")
    except (
        CLIInputError,
        MissionNotFound,
        MissionAlreadyExists,
        MissionApprovalError,
        EventLedgerCorrupt,
        ImportError,
        AttributeError,
        KeyError,
        TypeError,
        ValueError,
    ) as exc:
        _write_json({"error": type(exc).__name__, "message": str(exc)}, err)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())


__all__ = ["CLIInputError", "DEFAULT_DB", "main"]
