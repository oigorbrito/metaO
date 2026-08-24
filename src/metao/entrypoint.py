"""Backward-compatible metaO console entrypoint with runtime control commands.

Mission commands continue to delegate to :mod:`metao.cli` unchanged. Runtime
control commands are handled here so Roadmap 1 CLI semantics stay frozen while
Roadmap 2 gains an operational multi-runtime surface.
"""

from __future__ import annotations

import argparse
import importlib
from inspect import Parameter, signature
import json
import os
import sys
from typing import Any, Sequence, TextIO

from .cli import CLIInputError, DEFAULT_DB, main as mission_main
from .operator import MissionOperator
from .runtime_control import RuntimeControlRecord, quarantine, restore
from .runtime_factory import RUNTIME_CONTROL_DB_ENV
from .sqlite_runtime_control import RuntimeControlCorrupt, SQLiteRuntimeControlStore
from .sqlite_store import SQLiteMissionStore


_RUNTIME_COMMANDS = frozenset(
    {"runtimes", "runtime-quarantine", "runtime-restore", "runtime-history"}
)


def _write_json(value: Any, stream: TextIO) -> None:
    stream.write(json.dumps(value, sort_keys=True, separators=(",", ":"), default=str))
    stream.write("\n")


def _first_command(argv: Sequence[str]) -> str | None:
    index = 0
    while index < len(argv):
        token = argv[index]
        if token == "--db":
            index += 2
            continue
        if token.startswith("--db="):
            index += 1
            continue
        return token
    return None


def _db_from_argv(argv: Sequence[str]) -> str:
    for index, token in enumerate(argv):
        if token == "--db" and index + 1 < len(argv):
            return argv[index + 1]
        if token.startswith("--db="):
            return token.split("=", 1)[1]
    return DEFAULT_DB


def _control_db(db: str) -> str:
    return os.environ.get(RUNTIME_CONTROL_DB_ENV) or db


def _combined_help(stream: TextIO) -> None:
    stream.write("usage: metao [--db DB] COMMAND ...\n\n")
    stream.write("metaO control-plane operator CLI\n\n")
    stream.write("mission commands: run, status, inspect, list, events, approve, resume, cancel\n")
    stream.write(
        "runtime commands: runtimes, runtime-quarantine, runtime-restore, runtime-history\n"
    )


def _runtime_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="metao", description="metaO runtime control CLI")
    parser.add_argument("--db", default=DEFAULT_DB, help=f"SQLite database (default: {DEFAULT_DB})")
    sub = parser.add_subparsers(dest="command", required=True)

    runtimes = sub.add_parser("runtimes", help="list configured runtime catalog and live/control health")
    runtimes.add_argument("--factory", required=True, help="configured operator factory module:function")

    quarantine_parser = sub.add_parser("runtime-quarantine", help="durably quarantine one runtime")
    quarantine_parser.add_argument("orchestrator_id")
    quarantine_parser.add_argument("--reason", required=True)
    quarantine_parser.add_argument("--actor", required=True)
    quarantine_parser.add_argument("--now-epoch", type=float, default=0.0)

    restore_parser = sub.add_parser("runtime-restore", help="remove a durable runtime quarantine")
    restore_parser.add_argument("orchestrator_id")
    restore_parser.add_argument("--reason", required=True)
    restore_parser.add_argument("--actor", required=True)
    restore_parser.add_argument("--now-epoch", type=float, default=0.0)

    history_parser = sub.add_parser("runtime-history", help="show runtime quarantine/restore history")
    history_parser.add_argument("orchestrator_id")
    return parser


def _load_factory_operator(factory_spec: str, *, db: str, control_db: str) -> MissionOperator:
    if ":" not in factory_spec:
        raise CLIInputError("factory must use module:function syntax")
    module_name, attribute = factory_spec.split(":", 1)
    if not module_name or not attribute:
        raise CLIInputError("factory must use module:function syntax")
    target: Any = importlib.import_module(module_name)
    for part in attribute.split("."):
        target = getattr(target, part)
    if not callable(target):
        raise CLIInputError("factory target is not callable")

    kwargs: dict[str, Any] = {"store": SQLiteMissionStore(db)}
    try:
        parameters = signature(target).parameters.values()
        supports_control_db = any(
            item.name == "runtime_control_db" or item.kind is Parameter.VAR_KEYWORD
            for item in parameters
        )
    except (TypeError, ValueError):
        supports_control_db = False
    if supports_control_db:
        kwargs["runtime_control_db"] = control_db

    operator = target(**kwargs)
    if not isinstance(operator, MissionOperator):
        raise CLIInputError("factory must return MissionOperator")
    return operator


def _runtime_entry_view(item: Any) -> dict[str, Any]:
    return {
        "orchestrator_id": item.orchestrator_id,
        "version": item.version,
        "capabilities": sorted(item.capabilities),
        "health": item.health.value,
        "cost": item.cost,
        "latency_ms": item.latency_ms,
        "trust_profile": item.trust_profile,
        "success_rate": item.success_rate,
        "quality": item.quality,
        "reliability": item.reliability,
    }


def _control_view(item: RuntimeControlRecord) -> dict[str, Any]:
    return {
        "orchestrator_id": item.orchestrator_id,
        "disposition": item.disposition.value,
        "reason": item.reason,
        "actor_id": item.actor_id,
        "updated_at_epoch": item.updated_at_epoch,
        "revision": item.revision,
    }


def _legacy_main(
    argv: Sequence[str],
    *,
    stdout: TextIO,
    stderr: TextIO,
) -> int:
    db = _db_from_argv(argv)
    previous = os.environ.get(RUNTIME_CONTROL_DB_ENV)
    if previous is None:
        os.environ[RUNTIME_CONTROL_DB_ENV] = db
    try:
        return mission_main(argv, stdout=stdout, stderr=stderr)
    finally:
        if previous is None:
            os.environ.pop(RUNTIME_CONTROL_DB_ENV, None)
        else:
            os.environ[RUNTIME_CONTROL_DB_ENV] = previous


def main(
    argv: Sequence[str] | None = None,
    *,
    stdout: TextIO | None = None,
    stderr: TextIO | None = None,
) -> int:
    out = stdout or sys.stdout
    err = stderr or sys.stderr
    args_list = list(sys.argv[1:] if argv is None else argv)
    command = _first_command(args_list)

    if command in {"-h", "--help"}:
        _combined_help(out)
        return 0
    if command not in _RUNTIME_COMMANDS:
        return _legacy_main(args_list, stdout=out, stderr=err)

    args = _runtime_parser().parse_args(args_list)
    control_db = _control_db(args.db)
    controls = SQLiteRuntimeControlStore(control_db)

    try:
        if args.command == "runtimes":
            operator = _load_factory_operator(args.factory, db=args.db, control_db=control_db)
            runtime_entries = getattr(operator, "runtime_entries", None)
            if not callable(runtime_entries):
                raise CLIInputError("factory operator does not expose runtime_entries()")
            _write_json([_runtime_entry_view(item) for item in runtime_entries()], out)
            return 0
        if args.command == "runtime-quarantine":
            record = quarantine(
                controls,
                args.orchestrator_id,
                reason=args.reason,
                actor_id=args.actor,
                updated_at_epoch=args.now_epoch,
            )
            _write_json(_control_view(record), out)
            return 0
        if args.command == "runtime-restore":
            record = restore(
                controls,
                args.orchestrator_id,
                reason=args.reason,
                actor_id=args.actor,
                updated_at_epoch=args.now_epoch,
            )
            _write_json(_control_view(record), out)
            return 0
        if args.command == "runtime-history":
            _write_json([_control_view(item) for item in controls.history(args.orchestrator_id)], out)
            return 0
        raise CLIInputError(f"unsupported runtime command: {args.command}")
    except (
        CLIInputError,
        RuntimeControlCorrupt,
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


__all__ = ["main"]
