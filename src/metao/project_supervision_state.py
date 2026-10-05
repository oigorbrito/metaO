"""Durable Project Plane supervision state with fenced ownership.

This module persists framework-neutral Project Plane progress independently from
repository checkpoints. It provides revision/CAS updates and monotonic owner
generations so a process that lost ownership cannot mutate state after takeover.

It intentionally does not claim duplicate external-effect protection. That
requires the separate idempotent effect/reconciliation contract tracked by #754.
"""

from __future__ import annotations

from collections.abc import Mapping
from contextlib import closing
from dataclasses import dataclass, replace
import json
from pathlib import Path
import sqlite3
from typing import Any, Protocol, runtime_checkable

from .project_supervision import (
    ProjectResumeState,
    ProjectTraceEvent,
    ProjectTraceKind,
    ProjectTraceabilityRecord,
    RepositoryCheckpoint,
    WorkExecutionResult,
    WorkExecutionStatus,
    WorkUnit,
)


_SCHEMA_VERSION = 1


class ProjectSupervisionStateError(RuntimeError):
    """Base durable Project Plane state error."""


class ProjectSupervisionStateNotFound(ProjectSupervisionStateError):
    """Raised when a project supervision snapshot does not exist."""


class ProjectSupervisionStateAlreadyExists(ProjectSupervisionStateError):
    """Raised when creating an already persisted project."""


class ProjectSupervisionStateConflict(ProjectSupervisionStateError):
    """Raised when optimistic revision/CAS validation fails."""


class StaleProjectOwner(ProjectSupervisionStateError):
    """Raised when a stale owner/fencing generation attempts mutation."""


class ProjectSupervisionStateCorrupt(ProjectSupervisionStateError):
    """Raised when durable state fails structural validation."""


@dataclass(frozen=True, slots=True)
class ProjectOwnerToken:
    project_id: str
    holder_id: str
    generation: int

    def __post_init__(self) -> None:
        if not self.project_id or not self.project_id.strip():
            raise ValueError("project_id must be non-empty")
        if not self.holder_id or not self.holder_id.strip():
            raise ValueError("holder_id must be non-empty")
        if self.generation < 1:
            raise ValueError("generation must be >= 1")


ProjectSupervisionSnapshot = ProjectResumeState


@dataclass(frozen=True, slots=True)
class ProjectSupervisionStateRecord:
    snapshot: ProjectSupervisionSnapshot
    revision: int
    owner: ProjectOwnerToken

    def __post_init__(self) -> None:
        if self.revision < 1:
            raise ValueError("revision must be >= 1")
        if self.owner.project_id != self.snapshot.project_id:
            raise ValueError("owner token project binding mismatch")


@runtime_checkable
class ProjectSupervisionStateStorePort(Protocol):
    def create(
        self,
        snapshot: ProjectSupervisionSnapshot,
        *,
        holder_id: str,
    ) -> ProjectSupervisionStateRecord: ...

    def load(self, project_id: str) -> ProjectSupervisionStateRecord: ...

    def acquire(
        self,
        project_id: str,
        *,
        holder_id: str,
    ) -> ProjectSupervisionStateRecord: ...

    def assert_owner(self, owner: ProjectOwnerToken) -> None: ...

    def replace(
        self,
        snapshot: ProjectSupervisionSnapshot,
        *,
        owner: ProjectOwnerToken,
        expected_revision: int,
    ) -> ProjectSupervisionStateRecord: ...


def _work_unit_to_json(unit: WorkUnit) -> dict[str, Any]:
    return {
        "work_unit_id": unit.work_unit_id,
        "objective": unit.objective,
        "dependencies": list(unit.dependencies),
        "corrective": unit.corrective,
        "corrects_work_unit_id": unit.corrects_work_unit_id,
    }


def _work_unit_from_json(data: Mapping[str, Any]) -> WorkUnit:
    return WorkUnit(
        str(data["work_unit_id"]),
        str(data["objective"]),
        tuple(str(item) for item in data.get("dependencies", [])),
        bool(data.get("corrective", False)),
        None
        if data.get("corrects_work_unit_id") is None
        else str(data["corrects_work_unit_id"]),
    )


def _execution_to_json(item: WorkExecutionResult) -> dict[str, Any]:
    return {
        "work_unit_id": item.work_unit_id,
        "executor_id": item.executor_id,
        "provider_id": item.provider_id,
        "status": item.status.value,
        "repository_state_id": item.repository_state_id,
        "artifact_ref": item.artifact_ref,
        "evidence_ref": item.evidence_ref,
    }


def _execution_from_json(data: Mapping[str, Any]) -> WorkExecutionResult:
    return WorkExecutionResult(
        str(data["work_unit_id"]),
        str(data["executor_id"]),
        str(data["provider_id"]),
        WorkExecutionStatus(str(data["status"])),
        str(data["repository_state_id"]),
        None if data.get("artifact_ref") is None else str(data["artifact_ref"]),
        None if data.get("evidence_ref") is None else str(data["evidence_ref"]),
    )


def _trace_to_json(item: ProjectTraceEvent) -> dict[str, Any]:
    return {
        "kind": item.kind.value,
        "work_unit_id": item.work_unit_id,
        "executor_id": item.executor_id,
        "checkpoint_id": item.checkpoint_id,
        "repository_state_id": item.repository_state_id,
        "artifact_ref": item.artifact_ref,
        "evidence_ref": item.evidence_ref,
    }


def _trace_from_json(data: Mapping[str, Any]) -> ProjectTraceEvent:
    return ProjectTraceEvent(
        ProjectTraceKind(str(data["kind"])),
        None if data.get("work_unit_id") is None else str(data["work_unit_id"]),
        None if data.get("executor_id") is None else str(data["executor_id"]),
        None if data.get("checkpoint_id") is None else str(data["checkpoint_id"]),
        None
        if data.get("repository_state_id") is None
        else str(data["repository_state_id"]),
        None if data.get("artifact_ref") is None else str(data["artifact_ref"]),
        None if data.get("evidence_ref") is None else str(data["evidence_ref"]),
    )


def _traceability_to_json(item: ProjectTraceabilityRecord) -> dict[str, Any]:
    return {
        "requirement_id": item.requirement_id,
        "work_unit_id": item.work_unit_id,
        "artifact_ref": item.artifact_ref,
        "test_ref": item.test_ref,
        "evidence_ref": item.evidence_ref,
        "verdict": item.verdict,
    }


def _traceability_from_json(data: Mapping[str, Any]) -> ProjectTraceabilityRecord:
    return ProjectTraceabilityRecord(
        str(data["requirement_id"]),
        str(data["work_unit_id"]),
        str(data["artifact_ref"]),
        str(data["test_ref"]),
        str(data["evidence_ref"]),
        str(data["verdict"]),
    )


def _snapshot_to_json(snapshot: ProjectSupervisionSnapshot) -> str:
    payload = {
        "schema_version": _SCHEMA_VERSION,
        "project_id": snapshot.project_id,
        "requirement_id": snapshot.requirement_id,
        "objective": snapshot.objective,
        "authority_id": snapshot.authority_id,
        "units": [_work_unit_to_json(unit) for unit in snapshot.units],
        "executed_work_unit_ids": sorted(snapshot.executed_work_unit_ids),
        "accepted_work_unit_ids": sorted(snapshot.accepted_work_unit_ids),
        "accepted_results": [
            _execution_to_json(item) for item in snapshot.accepted_results
        ],
        "awaiting_correction": [list(item) for item in snapshot.awaiting_correction],
        "trace": [_trace_to_json(item) for item in snapshot.trace],
        "traceability": [
            _traceability_to_json(item) for item in snapshot.traceability
        ],
        "executors_used": sorted(snapshot.executors_used),
        "providers_used": sorted(snapshot.providers_used),
        "checkpoint": {
            "checkpoint_id": snapshot.checkpoint.checkpoint_id,
            "repository_id": snapshot.checkpoint.repository_id,
            "state_id": snapshot.checkpoint.state_id,
            "artifact_ref": snapshot.checkpoint.artifact_ref,
        },
        "checkpoint_holder_executor_id": snapshot.checkpoint_holder_executor_id,
        "corrective_count": snapshot.corrective_count,
    }
    return json.dumps(payload, sort_keys=True, separators=(",", ":"))


def _snapshot_from_json(raw: str) -> ProjectSupervisionSnapshot:
    try:
        data = json.loads(raw)
        if not isinstance(data, dict):
            raise ProjectSupervisionStateCorrupt("snapshot root must be object")
        if int(data.get("schema_version", -1)) != _SCHEMA_VERSION:
            raise ProjectSupervisionStateCorrupt("unsupported snapshot schema version")
        checkpoint_data = data["checkpoint"]
        if not isinstance(checkpoint_data, dict):
            raise ProjectSupervisionStateCorrupt("checkpoint must be object")
        awaiting = data.get("awaiting_correction", [])
        if not isinstance(awaiting, list):
            raise ProjectSupervisionStateCorrupt("awaiting_correction must be list")
        return ProjectSupervisionSnapshot(
            str(data["project_id"]),
            str(data["requirement_id"]),
            str(data["objective"]),
            str(data["authority_id"]),
            tuple(_work_unit_from_json(item) for item in data["units"]),
            frozenset(str(item) for item in data.get("executed_work_unit_ids", [])),
            frozenset(str(item) for item in data.get("accepted_work_unit_ids", [])),
            tuple(_execution_from_json(item) for item in data.get("accepted_results", [])),
            tuple((str(item[0]), str(item[1])) for item in awaiting),
            tuple(_trace_from_json(item) for item in data.get("trace", [])),
            tuple(
                _traceability_from_json(item)
                for item in data.get("traceability", [])
            ),
            frozenset(str(item) for item in data.get("executors_used", [])),
            frozenset(str(item) for item in data.get("providers_used", [])),
            RepositoryCheckpoint(
                str(checkpoint_data["checkpoint_id"]),
                str(checkpoint_data["repository_id"]),
                str(checkpoint_data["state_id"]),
                str(checkpoint_data["artifact_ref"]),
            ),
            None
            if data.get("checkpoint_holder_executor_id") is None
            else str(data["checkpoint_holder_executor_id"]),
            int(data.get("corrective_count", 0)),
        )
    except ProjectSupervisionStateCorrupt:
        raise
    except (KeyError, TypeError, ValueError, json.JSONDecodeError, IndexError) as exc:
        raise ProjectSupervisionStateCorrupt("invalid project supervision snapshot") from exc


class SQLiteProjectSupervisionStateStore:
    """SQLite state store with revision CAS and monotonic fenced ownership."""

    def __init__(self, path: str | Path) -> None:
        self._path = str(path)
        if self._path == ":memory:":
            raise ValueError("project supervision state must survive process restart")
        Path(self._path).parent.mkdir(parents=True, exist_ok=True)
        self._initialize()

    def _connect(self) -> sqlite3.Connection:
        connection = sqlite3.connect(self._path, timeout=5.0)
        connection.execute("PRAGMA foreign_keys = ON")
        return connection

    def _initialize(self) -> None:
        with closing(self._connect()) as connection, connection:
            connection.execute(
                """
                CREATE TABLE IF NOT EXISTS project_supervision_state (
                    project_id TEXT PRIMARY KEY,
                    revision INTEGER NOT NULL CHECK (revision >= 1),
                    owner_id TEXT NOT NULL,
                    fencing_generation INTEGER NOT NULL CHECK (fencing_generation >= 1),
                    schema_version INTEGER NOT NULL,
                    snapshot_json TEXT NOT NULL
                )
                """
            )

    @staticmethod
    def _record(row: tuple[Any, ...]) -> ProjectSupervisionStateRecord:
        project_id, revision, owner_id, generation, schema_version, raw = row
        if int(schema_version) != _SCHEMA_VERSION:
            raise ProjectSupervisionStateCorrupt("unsupported database schema version")
        snapshot = _snapshot_from_json(str(raw))
        if snapshot.project_id != str(project_id):
            raise ProjectSupervisionStateCorrupt("project id column does not match snapshot")
        return ProjectSupervisionStateRecord(
            snapshot,
            int(revision),
            ProjectOwnerToken(str(project_id), str(owner_id), int(generation)),
        )

    def create(
        self,
        snapshot: ProjectSupervisionSnapshot,
        *,
        holder_id: str,
    ) -> ProjectSupervisionStateRecord:
        owner = ProjectOwnerToken(snapshot.project_id, holder_id, 1)
        raw = _snapshot_to_json(snapshot)
        try:
            with closing(self._connect()) as connection, connection:
                connection.execute(
                    """
                    INSERT INTO project_supervision_state(
                        project_id, revision, owner_id, fencing_generation,
                        schema_version, snapshot_json
                    ) VALUES(?,?,?,?,?,?)
                    """,
                    (
                        snapshot.project_id,
                        1,
                        holder_id,
                        1,
                        _SCHEMA_VERSION,
                        raw,
                    ),
                )
        except sqlite3.IntegrityError as exc:
            raise ProjectSupervisionStateAlreadyExists(snapshot.project_id) from exc
        return ProjectSupervisionStateRecord(snapshot, 1, owner)

    def load(self, project_id: str) -> ProjectSupervisionStateRecord:
        with closing(self._connect()) as connection, connection:
            row = connection.execute(
                """
                SELECT project_id, revision, owner_id, fencing_generation,
                       schema_version, snapshot_json
                FROM project_supervision_state
                WHERE project_id = ?
                """,
                (project_id,),
            ).fetchone()
        if row is None:
            raise ProjectSupervisionStateNotFound(project_id)
        return self._record(row)

    def acquire(
        self,
        project_id: str,
        *,
        holder_id: str,
    ) -> ProjectSupervisionStateRecord:
        if not holder_id or not holder_id.strip():
            raise ValueError("holder_id must be non-empty")
        with closing(self._connect()) as connection, connection:
            connection.execute("BEGIN IMMEDIATE")
            row = connection.execute(
                """
                SELECT project_id, revision, owner_id, fencing_generation,
                       schema_version, snapshot_json
                FROM project_supervision_state
                WHERE project_id = ?
                """,
                (project_id,),
            ).fetchone()
            if row is None:
                raise ProjectSupervisionStateNotFound(project_id)
            current = self._record(row)
            if current.owner.holder_id == holder_id:
                return current
            new_generation = current.owner.generation + 1
            new_revision = current.revision + 1
            connection.execute(
                """
                UPDATE project_supervision_state
                SET revision = ?, owner_id = ?, fencing_generation = ?
                WHERE project_id = ? AND revision = ?
                  AND owner_id = ? AND fencing_generation = ?
                """,
                (
                    new_revision,
                    holder_id,
                    new_generation,
                    project_id,
                    current.revision,
                    current.owner.holder_id,
                    current.owner.generation,
                ),
            )
            if connection.total_changes != 1:
                raise ProjectSupervisionStateConflict(project_id)
        return ProjectSupervisionStateRecord(
            current.snapshot,
            new_revision,
            ProjectOwnerToken(project_id, holder_id, new_generation),
        )

    def assert_owner(self, owner: ProjectOwnerToken) -> None:
        with closing(self._connect()) as connection, connection:
            row = connection.execute(
                """
                SELECT owner_id, fencing_generation
                FROM project_supervision_state
                WHERE project_id = ?
                """,
                (owner.project_id,),
            ).fetchone()
        if row is None:
            raise ProjectSupervisionStateNotFound(owner.project_id)
        owner_id, generation = str(row[0]), int(row[1])
        if owner_id != owner.holder_id or generation != owner.generation:
            raise StaleProjectOwner(owner.project_id)

    def replace(
        self,
        snapshot: ProjectSupervisionSnapshot,
        *,
        owner: ProjectOwnerToken,
        expected_revision: int,
    ) -> ProjectSupervisionStateRecord:
        if snapshot.project_id != owner.project_id:
            raise ValueError("snapshot/owner project binding mismatch")
        raw = _snapshot_to_json(snapshot)
        with closing(self._connect()) as connection, connection:
            connection.execute("BEGIN IMMEDIATE")
            row = connection.execute(
                """
                SELECT revision, owner_id, fencing_generation
                FROM project_supervision_state
                WHERE project_id = ?
                """,
                (snapshot.project_id,),
            ).fetchone()
            if row is None:
                raise ProjectSupervisionStateNotFound(snapshot.project_id)
            revision, owner_id, generation = int(row[0]), str(row[1]), int(row[2])
            if owner_id != owner.holder_id or generation != owner.generation:
                raise StaleProjectOwner(snapshot.project_id)
            if revision != expected_revision:
                raise ProjectSupervisionStateConflict(snapshot.project_id)
            new_revision = revision + 1
            connection.execute(
                """
                UPDATE project_supervision_state
                SET revision = ?, schema_version = ?, snapshot_json = ?
                WHERE project_id = ? AND revision = ?
                  AND owner_id = ? AND fencing_generation = ?
                """,
                (
                    new_revision,
                    _SCHEMA_VERSION,
                    raw,
                    snapshot.project_id,
                    revision,
                    owner.holder_id,
                    owner.generation,
                ),
            )
            if connection.total_changes != 1:
                raise ProjectSupervisionStateConflict(snapshot.project_id)
        return ProjectSupervisionStateRecord(snapshot, new_revision, owner)


__all__ = [
    "ProjectOwnerToken",
    "ProjectSupervisionSnapshot",
    "ProjectSupervisionStateRecord",
    "ProjectSupervisionStateStorePort",
    "ProjectSupervisionStateError",
    "ProjectSupervisionStateNotFound",
    "ProjectSupervisionStateAlreadyExists",
    "ProjectSupervisionStateConflict",
    "StaleProjectOwner",
    "ProjectSupervisionStateCorrupt",
    "SQLiteProjectSupervisionStateStore",
]
