"""Project-level effect deduplication and crash-window reconciliation.

This module is an opt-in safety boundary for work units with externally visible,
potentially non-idempotent effects. It does not change the legacy
WorkUnitRunnerPort contract. Instead, ReconciledWorkUnitRunner adapts an
effect-safe runner plus an authoritative reconciliation port to that contract.

Claim boundary:
- APPLIED reconciliation reuses the authoritative prior execution result.
- NOT_APPLIED may execute using the stable idempotency key.
- AMBIGUOUS fails closed and must never silently reissue.
- This is logical-effect deduplication, not a generic exactly-once claim.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum
import hashlib
import json
from typing import Protocol, runtime_checkable

from .project_supervision import (
    ExecutorTarget,
    ProjectObjective,
    RepositoryCheckpoint,
    WorkExecutionResult,
    WorkExecutionStatus,
    WorkUnit,
)


class ProjectEffectState(StrEnum):
    NOT_APPLIED = "NOT_APPLIED"
    APPLIED = "APPLIED"
    AMBIGUOUS = "AMBIGUOUS"


class ProjectEffectAmbiguous(RuntimeError):
    """Raised when effect authority cannot determine whether an effect applied."""


@dataclass(frozen=True, slots=True)
class ProjectEffectKey:
    project_id: str
    work_unit_id: str
    logical_effect_id: str

    def __post_init__(self) -> None:
        for name, value in (
            ("project_id", self.project_id),
            ("work_unit_id", self.work_unit_id),
            ("logical_effect_id", self.logical_effect_id),
        ):
            if not value or not value.strip():
                raise ValueError(f"{name} must be non-empty")

    @property
    def value(self) -> str:
        # Deliberately stable across process restarts and executor attempts.
        # Hash a canonical tuple instead of delimiter-joining caller-controlled
        # identifiers, avoiding collisions such as ("a:b", "c", "d") and
        # ("a", "b:c", "d").
        payload = json.dumps(
            [self.project_id, self.work_unit_id, self.logical_effect_id],
            ensure_ascii=False,
            separators=(",", ":"),
        ).encode("utf-8")
        return "metao-project-effect-v1:" + hashlib.sha256(payload).hexdigest()


@dataclass(frozen=True, slots=True)
class ProjectEffectReconciliation:
    key: ProjectEffectKey
    state: ProjectEffectState
    execution: WorkExecutionResult | None = None
    authority_ref: str = ""

    def __post_init__(self) -> None:
        if not self.authority_ref or not self.authority_ref.strip():
            raise ValueError("authority_ref must be non-empty")
        if self.state is ProjectEffectState.APPLIED and self.execution is None:
            raise ValueError("APPLIED reconciliation requires execution result")
        if self.state is not ProjectEffectState.APPLIED and self.execution is not None:
            raise ValueError("non-APPLIED reconciliation cannot carry execution result")


@runtime_checkable
class ProjectEffectReconciliationPort(Protocol):
    def reconcile(
        self,
        objective: ProjectObjective,
        unit: WorkUnit,
        target: ExecutorTarget,
        checkpoint: RepositoryCheckpoint,
        key: ProjectEffectKey,
    ) -> ProjectEffectReconciliation: ...


@runtime_checkable
class IdempotentWorkUnitRunnerPort(Protocol):
    def logical_effect_id(
        self,
        objective: ProjectObjective,
        unit: WorkUnit,
    ) -> str: ...

    def run_with_idempotency_key(
        self,
        objective: ProjectObjective,
        unit: WorkUnit,
        target: ExecutorTarget,
        checkpoint: RepositoryCheckpoint,
        *,
        idempotency_key: str,
    ) -> WorkExecutionResult: ...


class ReconciledWorkUnitRunner:
    """Adapter that prevents blind reissue across an effect crash window."""

    def __init__(
        self,
        *,
        runner: IdempotentWorkUnitRunnerPort,
        reconciliation: ProjectEffectReconciliationPort,
    ) -> None:
        self._runner = runner
        self._reconciliation = reconciliation

    def run(
        self,
        objective: ProjectObjective,
        unit: WorkUnit,
        target: ExecutorTarget,
        checkpoint: RepositoryCheckpoint,
    ) -> WorkExecutionResult:
        logical_effect_id = self._runner.logical_effect_id(objective, unit)
        key = ProjectEffectKey(
            objective.project_id,
            unit.work_unit_id,
            logical_effect_id,
        )
        reconciled = self._reconciliation.reconcile(
            objective,
            unit,
            target,
            checkpoint,
            key,
        )
        if reconciled.key != key:
            raise ValueError("effect reconciliation key binding mismatch")
        if reconciled.state is ProjectEffectState.AMBIGUOUS:
            return WorkExecutionResult(
                unit.work_unit_id,
                target.executor_id,
                target.provider_id,
                WorkExecutionStatus.FAILED,
                checkpoint.state_id,
                evidence_ref=(
                    f"{reconciled.authority_ref};"
                    f"ambiguous-effect:{key.value}"
                ),
            )
        if reconciled.state is ProjectEffectState.APPLIED:
            assert reconciled.execution is not None
            execution = reconciled.execution
            if (
                execution.work_unit_id != unit.work_unit_id
                or execution.executor_id != target.executor_id
                or execution.provider_id != target.provider_id
            ):
                raise ValueError("reconciled execution binding mismatch")
            return execution

        return self._runner.run_with_idempotency_key(
            objective,
            unit,
            target,
            checkpoint,
            idempotency_key=key.value,
        )


__all__ = [
    "ProjectEffectState",
    "ProjectEffectAmbiguous",
    "ProjectEffectKey",
    "ProjectEffectReconciliation",
    "ProjectEffectReconciliationPort",
    "IdempotentWorkUnitRunnerPort",
    "ReconciledWorkUnitRunner",
]
