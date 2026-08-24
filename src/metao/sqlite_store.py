"""SQLite-backed MissionStorePort implementation.

SQLite is an infrastructure adapter. The control-plane, Core contracts and
MissionStorePort remain framework- and database-neutral.

Records are stored as a versioned JSON snapshot plus a few indexed operational
columns. Deserialization is explicit and typed; pickle and silent ``str``
coercion are intentionally avoided.
"""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import replace
import json
from pathlib import Path
import sqlite3
from typing import Any

from .acceptance import AcceptanceDecision, AcceptanceProof, AcceptanceResult
from .control_plane import MissionAttempt, MissionOutcome, MissionState, MissionStatus
from .core import EvidenceEnvelope as CoreEvidenceEnvelope
from .core import ExecutionResult, ExecutionStatus, Mission
from .governance import AcceptanceBudget
from .mission_store import MissionAlreadyExists, MissionNotFound, MissionRecord


_SCHEMA_VERSION = 1


class MissionStoreCorrupt(RuntimeError):
    """Raised when durable data fails structural or cross-column validation."""


def _json_value(value: Any) -> Any:
    if value is None or isinstance(value, (str, bool, int)):
        return value
    if isinstance(value, float):
        if value != value or value in (float("inf"), float("-inf")):
            raise TypeError("non-finite floats are not supported in mission snapshots")
        return value
    if isinstance(value, Mapping):
        result: dict[str, Any] = {}
        for key, item in value.items():
            if not isinstance(key, str):
                raise TypeError("mission snapshot mappings require string keys")
            result[key] = _json_value(item)
        return result
    if isinstance(value, (list, tuple)):
        return [_json_value(item) for item in value]
    raise TypeError(f"unsupported mission snapshot value: {type(value).__name__}")


def _encode_core_evidence(item: CoreEvidenceEnvelope) -> dict[str, Any]:
    return {
        "mission_id": item.mission_id,
        "execution_id": item.execution_id,
        "orchestrator_id": item.orchestrator_id,
        "adapter_id": item.adapter_id,
        "adapter_version": item.adapter_version,
        "attempt_id": item.attempt_id,
        "subject_id": item.subject_id,
        "subject_state_id": item.subject_state_id,
        "verification_context_id": item.verification_context_id,
        "policy_bundle_id": item.policy_bundle_id,
        "obligation_ids": sorted(item.obligation_ids),
        "evidence_payload_digest": item.evidence_payload_digest,
        "provenance": item.provenance,
        "verifier_id": item.verifier_id,
        "approval_evidence": item.approval_evidence,
        "confidence": item.confidence,
        "verification_cost_units": item.verification_cost_units,
    }


def _decode_core_evidence(data: Mapping[str, Any]) -> CoreEvidenceEnvelope:
    return CoreEvidenceEnvelope(
        mission_id=str(data["mission_id"]),
        execution_id=str(data["execution_id"]),
        orchestrator_id=str(data["orchestrator_id"]),
        adapter_id=str(data["adapter_id"]),
        adapter_version=str(data["adapter_version"]),
        attempt_id=str(data["attempt_id"]),
        subject_id=str(data["subject_id"]),
        subject_state_id=str(data["subject_state_id"]),
        verification_context_id=str(data["verification_context_id"]),
        policy_bundle_id=str(data["policy_bundle_id"]),
        obligation_ids=frozenset(str(item) for item in data["obligation_ids"]),
        evidence_payload_digest=str(data["evidence_payload_digest"]),
        provenance=str(data["provenance"]),
        verifier_id=str(data["verifier_id"]),
        approval_evidence=str(data.get("approval_evidence", "")),
        confidence=data.get("confidence"),
        verification_cost_units=int(data.get("verification_cost_units", 0)),
    )


def _encode_execution(execution: ExecutionResult | None) -> dict[str, Any] | None:
    if execution is None:
        return None
    return {
        "execution_id": execution.execution_id,
        "orchestrator_id": execution.orchestrator_id,
        "status": execution.status.value,
        "output": _json_value(execution.output),
        "evidence": [_encode_core_evidence(item) for item in execution.evidence],
        "error": execution.error,
    }


def _decode_execution(data: Mapping[str, Any] | None) -> ExecutionResult | None:
    if data is None:
        return None
    output = data.get("output", {})
    if not isinstance(output, dict):
        raise MissionStoreCorrupt("execution output must be an object")
    evidence = data.get("evidence", [])
    if not isinstance(evidence, list):
        raise MissionStoreCorrupt("execution evidence must be a list")
    return ExecutionResult(
        execution_id=str(data["execution_id"]),
        orchestrator_id=str(data["orchestrator_id"]),
        status=ExecutionStatus(str(data["status"])),
        output=output,
        evidence=tuple(_decode_core_evidence(item) for item in evidence),
        error=str(data.get("error", "")),
    )


def _encode_acceptance(result: AcceptanceResult) -> dict[str, Any]:
    proof = result.proof
    return {
        "decision": result.decision.value,
        "reasons": list(result.reasons),
        "proof": None if proof is None else {
            "decision": proof.decision.value,
            "reasons": list(proof.reasons),
            "evidence_ids": list(proof.evidence_ids),
            "digest": proof.digest,
        },
    }


def _decode_acceptance(data: Mapping[str, Any]) -> AcceptanceResult:
    proof_data = data.get("proof")
    proof = None
    if proof_data is not None:
        if not isinstance(proof_data, dict):
            raise MissionStoreCorrupt("acceptance proof must be an object")
        proof = AcceptanceProof(
            decision=AcceptanceDecision(str(proof_data["decision"])),
            reasons=tuple(str(item) for item in proof_data.get("reasons", [])),
            evidence_ids=tuple(str(item) for item in proof_data.get("evidence_ids", [])),
            digest=str(proof_data["digest"]),
        )
    return AcceptanceResult(
        decision=AcceptanceDecision(str(data["decision"])),
        reasons=tuple(str(item) for item in data.get("reasons", [])),
        proof=proof,
    )


def _encode_budget(budget: AcceptanceBudget) -> dict[str, Any]:
    return {
        "money_limit": budget.money_limit,
        "token_limit": budget.token_limit,
        "wall_time_limit_s": budget.wall_time_limit_s,
        "verifier_attempt_limit": budget.verifier_attempt_limit,
        "money_used": budget.money_used,
        "tokens_used": budget.tokens_used,
        "wall_time_used_s": budget.wall_time_used_s,
        "verifier_attempts_used": budget.verifier_attempts_used,
    }


def _decode_budget(data: Mapping[str, Any]) -> AcceptanceBudget:
    return AcceptanceBudget(
        money_limit=float(data["money_limit"]),
        token_limit=int(data["token_limit"]),
        wall_time_limit_s=float(data["wall_time_limit_s"]),
        verifier_attempt_limit=int(data["verifier_attempt_limit"]),
        money_used=float(data.get("money_used", 0.0)),
        tokens_used=int(data.get("tokens_used", 0)),
        wall_time_used_s=float(data.get("wall_time_used_s", 0.0)),
        verifier_attempts_used=int(data.get("verifier_attempts_used", 0)),
    )


def _encode_state(state: MissionState) -> dict[str, Any]:
    return {
        "mission_id": state.mission_id,
        "status": state.status.value,
        "attempts": [
            {
                "attempt_number": item.attempt_number,
                "execution_id": item.execution_id,
                "orchestrator_id": item.orchestrator_id,
                "execution_status": None if item.execution_status is None else item.execution_status.value,
                "acceptance_decision": item.acceptance_decision.value,
                "reasons": list(item.reasons),
            }
            for item in state.attempts
        ],
        "history": [item.value for item in state.history],
    }


def _decode_state(data: Mapping[str, Any]) -> MissionState:
    attempts_data = data.get("attempts", [])
    if not isinstance(attempts_data, list):
        raise MissionStoreCorrupt("mission attempts must be a list")
    attempts = tuple(
        MissionAttempt(
            attempt_number=int(item["attempt_number"]),
            execution_id=str(item["execution_id"]),
            orchestrator_id=str(item["orchestrator_id"]),
            execution_status=None if item.get("execution_status") is None else ExecutionStatus(str(item["execution_status"])),
            acceptance_decision=AcceptanceDecision(str(item["acceptance_decision"])),
            reasons=tuple(str(reason) for reason in item.get("reasons", [])),
        )
        for item in attempts_data
    )
    return MissionState(
        mission_id=str(data["mission_id"]),
        status=MissionStatus(str(data["status"])),
        attempts=attempts,
        history=tuple(MissionStatus(str(item)) for item in data.get("history", [])),
    )


def _record_to_json(record: MissionRecord) -> str:
    outcome = record.outcome
    assert outcome.state is not None
    payload = {
        "schema_version": _SCHEMA_VERSION,
        "revision": record.revision,
        "mission": {
            "mission_id": record.mission.mission_id,
            "objective": record.mission.objective,
            "required_capabilities": sorted(record.mission.required_capabilities),
        },
        "outcome": {
            "mission_id": outcome.mission_id,
            "orchestrator_id": outcome.orchestrator_id,
            "execution": _encode_execution(outcome.execution),
            "acceptance": _encode_acceptance(outcome.acceptance),
            "budget": _encode_budget(outcome.budget),
            "attempted_orchestrators": list(outcome.attempted_orchestrators),
            "state": _encode_state(outcome.state),
        },
    }
    return json.dumps(payload, sort_keys=True, separators=(",", ":"), allow_nan=False)


def _record_from_json(raw: str) -> MissionRecord:
    try:
        payload = json.loads(raw)
        if not isinstance(payload, dict):
            raise MissionStoreCorrupt("mission snapshot root must be an object")
        if int(payload.get("schema_version", -1)) != _SCHEMA_VERSION:
            raise MissionStoreCorrupt("unsupported mission snapshot schema version")
        mission_data = payload["mission"]
        outcome_data = payload["outcome"]
        mission = Mission(
            mission_id=str(mission_data["mission_id"]),
            objective=str(mission_data["objective"]),
            required_capabilities=frozenset(str(item) for item in mission_data.get("required_capabilities", [])),
        )
        state_data = outcome_data["state"]
        outcome = MissionOutcome(
            mission_id=str(outcome_data["mission_id"]),
            orchestrator_id=None if outcome_data.get("orchestrator_id") is None else str(outcome_data["orchestrator_id"]),
            execution=_decode_execution(outcome_data.get("execution")),
            acceptance=_decode_acceptance(outcome_data["acceptance"]),
            budget=_decode_budget(outcome_data["budget"]),
            attempted_orchestrators=tuple(str(item) for item in outcome_data.get("attempted_orchestrators", [])),
            state=_decode_state(state_data),
        )
        return MissionRecord(mission, outcome, revision=int(payload["revision"]))
    except MissionStoreCorrupt:
        raise
    except (KeyError, TypeError, ValueError, json.JSONDecodeError) as exc:
        raise MissionStoreCorrupt("invalid mission snapshot") from exc


class SQLiteMissionStore:
    """File-backed SQLite implementation of MissionStorePort."""

    def __init__(self, path: str | Path) -> None:
        self._path = str(path)
        if self._path == ":memory:":
            raise ValueError("use InMemoryMissionStore for process-local storage")
        Path(self._path).parent.mkdir(parents=True, exist_ok=True)
        self._initialize()

    def _connect(self) -> sqlite3.Connection:
        connection = sqlite3.connect(self._path, timeout=5.0)
        connection.execute("PRAGMA foreign_keys = ON")
        return connection

    def _initialize(self) -> None:
        with self._connect() as connection:
            connection.execute(
                """
                CREATE TABLE IF NOT EXISTS mission_records (
                    mission_id TEXT PRIMARY KEY,
                    status TEXT NOT NULL,
                    revision INTEGER NOT NULL CHECK (revision >= 1),
                    schema_version INTEGER NOT NULL,
                    record_json TEXT NOT NULL
                )
                """
            )
            connection.execute(
                "CREATE INDEX IF NOT EXISTS idx_mission_records_status ON mission_records(status)"
            )

    @staticmethod
    def _validated(row: tuple[Any, ...]) -> MissionRecord:
        mission_id, status, revision, schema_version, raw = row
        if int(schema_version) != _SCHEMA_VERSION:
            raise MissionStoreCorrupt("unsupported database schema version")
        record = _record_from_json(str(raw))
        if record.mission_id != str(mission_id):
            raise MissionStoreCorrupt("mission id column does not match snapshot")
        if record.status.value != str(status):
            raise MissionStoreCorrupt("mission status column does not match snapshot")
        if record.revision != int(revision):
            raise MissionStoreCorrupt("mission revision column does not match snapshot")
        return record

    def contains(self, mission_id: str) -> bool:
        with self._connect() as connection:
            row = connection.execute(
                "SELECT 1 FROM mission_records WHERE mission_id = ?", (mission_id,)
            ).fetchone()
        return row is not None

    def create(self, record: MissionRecord) -> None:
        raw = _record_to_json(record)
        try:
            with self._connect() as connection:
                connection.execute(
                    "INSERT INTO mission_records(mission_id,status,revision,schema_version,record_json) VALUES(?,?,?,?,?)",
                    (record.mission_id, record.status.value, record.revision, _SCHEMA_VERSION, raw),
                )
        except sqlite3.IntegrityError as exc:
            raise MissionAlreadyExists(record.mission_id) from exc

    def get(self, mission_id: str) -> MissionRecord:
        with self._connect() as connection:
            row = connection.execute(
                "SELECT mission_id,status,revision,schema_version,record_json FROM mission_records WHERE mission_id = ?",
                (mission_id,),
            ).fetchone()
        if row is None:
            raise MissionNotFound(mission_id)
        return self._validated(row)

    def replace(self, record: MissionRecord) -> MissionRecord:
        with self._connect() as connection:
            connection.execute("BEGIN IMMEDIATE")
            row = connection.execute(
                "SELECT revision FROM mission_records WHERE mission_id = ?", (record.mission_id,)
            ).fetchone()
            if row is None:
                raise MissionNotFound(record.mission_id)
            updated = replace(record, revision=int(row[0]) + 1)
            raw = _record_to_json(updated)
            connection.execute(
                "UPDATE mission_records SET status=?, revision=?, schema_version=?, record_json=? WHERE mission_id=?",
                (updated.status.value, updated.revision, _SCHEMA_VERSION, raw, updated.mission_id),
            )
        return updated

    def list(self) -> tuple[MissionRecord, ...]:
        with self._connect() as connection:
            rows = connection.execute(
                "SELECT mission_id,status,revision,schema_version,record_json FROM mission_records ORDER BY mission_id"
            ).fetchall()
        return tuple(self._validated(row) for row in rows)


__all__ = ["MissionStoreCorrupt", "SQLiteMissionStore"]
