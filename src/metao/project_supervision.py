"""Framework-neutral project supervision above mission/executor control-plane.

This module owns project decomposition, work-graph progress, checkpoint handoff,
corrective work and project verdicts. Executor/framework-specific execution stays
behind ports; a production runner may delegate each work unit to
``control_plane.execute_mission``.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum
from typing import Protocol, runtime_checkable


class ProjectVerdict(StrEnum):
    PROJECT_ACCEPTED = "PROJECT_ACCEPTED"
    PROJECT_BLOCKED = "PROJECT_BLOCKED"


class WorkExecutionStatus(StrEnum):
    SUCCEEDED = "SUCCEEDED"
    CAPACITY_FAILED = "CAPACITY_FAILED"
    FAILED = "FAILED"


class ProjectTraceKind(StrEnum):
    PLANNED = "PLANNED"
    DISPATCHED = "DISPATCHED"
    FAILED_CAPACITY = "FAILED_CAPACITY"
    CHECKPOINTED = "CHECKPOINTED"
    HANDED_OFF = "HANDED_OFF"
    ARTIFACT_PRODUCED = "ARTIFACT_PRODUCED"
    VERIFICATION_FAILED = "VERIFICATION_FAILED"
    CORRECTIVE_WORK_CREATED = "CORRECTIVE_WORK_CREATED"
    VERIFICATION_PASSED = "VERIFICATION_PASSED"
    PROJECT_ACCEPTED = "PROJECT_ACCEPTED"
    PROJECT_BLOCKED = "PROJECT_BLOCKED"


@dataclass(frozen=True, slots=True)
class ProjectObjective:
    project_id: str
    requirement_id: str
    objective: str

    def __post_init__(self) -> None:
        for name, value in (
            ("project_id", self.project_id),
            ("requirement_id", self.requirement_id),
            ("objective", self.objective),
        ):
            if not value or not value.strip():
                raise ValueError(f"{name} must be non-empty")


@dataclass(frozen=True, slots=True)
class WorkUnit:
    work_unit_id: str
    objective: str
    dependencies: tuple[str, ...] = ()
    corrective: bool = False
    corrects_work_unit_id: str | None = None

    def __post_init__(self) -> None:
        if not self.work_unit_id or not self.work_unit_id.strip():
            raise ValueError("work_unit_id must be non-empty")
        if not self.objective or not self.objective.strip():
            raise ValueError("work unit objective must be non-empty")
        if self.corrective != (self.corrects_work_unit_id is not None):
            raise ValueError("corrective work must identify exactly one corrected work unit")


@dataclass(frozen=True, slots=True)
class WorkGraph:
    authority_id: str
    units: tuple[WorkUnit, ...]

    def __post_init__(self) -> None:
        if not self.authority_id or not self.authority_id.strip():
            raise ValueError("work graph authority_id must be non-empty")
        if not self.units:
            raise ValueError("work graph must contain work units")
        _validate_graph(self.units)


@dataclass(frozen=True, slots=True)
class ExecutorTarget:
    executor_id: str
    provider_id: str

    def __post_init__(self) -> None:
        if not self.executor_id or not self.provider_id:
            raise ValueError("executor target requires executor and provider ids")


@dataclass(frozen=True, slots=True)
class RepositoryCheckpoint:
    checkpoint_id: str
    repository_id: str
    state_id: str
    artifact_ref: str

    def __post_init__(self) -> None:
        for name, value in (
            ("checkpoint_id", self.checkpoint_id),
            ("repository_id", self.repository_id),
            ("state_id", self.state_id),
            ("artifact_ref", self.artifact_ref),
        ):
            if not value or not value.strip():
                raise ValueError(f"{name} must be non-empty")


@dataclass(frozen=True, slots=True)
class WorkExecutionResult:
    work_unit_id: str
    executor_id: str
    provider_id: str
    status: WorkExecutionStatus
    repository_state_id: str
    artifact_ref: str | None = None
    evidence_ref: str | None = None


@dataclass(frozen=True, slots=True)
class WorkVerificationResult:
    accepted: bool
    verifier_id: str
    evidence_ref: str
    test_ref: str
    reason: str = ""

    def __post_init__(self) -> None:
        for name, value in (
            ("verifier_id", self.verifier_id),
            ("evidence_ref", self.evidence_ref),
            ("test_ref", self.test_ref),
        ):
            if not value or not value.strip():
                raise ValueError(f"{name} must be non-empty")


@dataclass(frozen=True, slots=True)
class ProjectTraceEvent:
    kind: ProjectTraceKind
    work_unit_id: str | None = None
    executor_id: str | None = None
    checkpoint_id: str | None = None
    repository_state_id: str | None = None
    artifact_ref: str | None = None
    evidence_ref: str | None = None


@dataclass(frozen=True, slots=True)
class ProjectTraceabilityRecord:
    requirement_id: str
    work_unit_id: str
    artifact_ref: str
    test_ref: str
    verdict: str


@dataclass(frozen=True, slots=True)
class ProjectSupervisionResult:
    project_id: str
    verdict: ProjectVerdict
    graph: WorkGraph
    trace: tuple[ProjectTraceEvent, ...]
    traceability: tuple[ProjectTraceabilityRecord, ...]
    executors_used: frozenset[str]
    providers_used: frozenset[str]
    reason: str = ""


@runtime_checkable
class ProjectPlannerPort(Protocol):
    def plan(self, objective: ProjectObjective) -> WorkGraph: ...

    def corrective_work(
        self,
        objective: ProjectObjective,
        failed_unit: WorkUnit,
        verification: WorkVerificationResult,
        graph: WorkGraph,
    ) -> WorkUnit | None: ...


@runtime_checkable
class ExecutorSchedulerPort(Protocol):
    def select(
        self,
        unit: WorkUnit,
        *,
        excluded_executor_ids: frozenset[str],
    ) -> ExecutorTarget | None: ...


@runtime_checkable
class WorkUnitRunnerPort(Protocol):
    def run(
        self,
        objective: ProjectObjective,
        unit: WorkUnit,
        target: ExecutorTarget,
        checkpoint: RepositoryCheckpoint,
    ) -> WorkExecutionResult: ...


@runtime_checkable
class RepositoryCheckpointPort(Protocol):
    def initial(self, objective: ProjectObjective) -> RepositoryCheckpoint: ...

    def capture(
        self,
        objective: ProjectObjective,
        unit: WorkUnit,
        execution: WorkExecutionResult,
    ) -> RepositoryCheckpoint: ...

    def handoff(
        self,
        checkpoint: RepositoryCheckpoint,
        *,
        from_executor_id: str,
        to_executor_id: str,
    ) -> RepositoryCheckpoint: ...


@runtime_checkable
class WorkUnitVerifierPort(Protocol):
    def verify(
        self,
        objective: ProjectObjective,
        unit: WorkUnit,
        execution: WorkExecutionResult,
        checkpoint: RepositoryCheckpoint,
    ) -> WorkVerificationResult: ...


def _validate_graph(units: tuple[WorkUnit, ...]) -> None:
    ids = [unit.work_unit_id for unit in units]
    if len(set(ids)) != len(ids):
        raise ValueError("work graph contains duplicate work_unit_id")
    known = set(ids)
    for unit in units:
        if unit.work_unit_id in unit.dependencies:
            raise ValueError("work unit cannot depend on itself")
        unknown = set(unit.dependencies) - known
        if unknown:
            raise ValueError(
                f"work graph contains unknown dependency: {sorted(unknown)[0]}"
            )
    visiting: set[str] = set()
    visited: set[str] = set()
    deps = {unit.work_unit_id: unit.dependencies for unit in units}

    def visit(node: str) -> None:
        if node in visiting:
            raise ValueError("work graph contains dependency cycle")
        if node in visited:
            return
        visiting.add(node)
        for dependency in deps[node]:
            visit(dependency)
        visiting.remove(node)
        visited.add(node)

    for node in ids:
        visit(node)


def supervise_project(
    *,
    objective: ProjectObjective,
    planner: ProjectPlannerPort,
    scheduler: ExecutorSchedulerPort,
    runner: WorkUnitRunnerPort,
    repository: RepositoryCheckpointPort,
    verifier: WorkUnitVerifierPort,
    max_executor_attempts_per_unit: int = 3,
    max_corrective_units: int = 3,
) -> ProjectSupervisionResult:
    if max_executor_attempts_per_unit < 1 or max_corrective_units < 0:
        raise ValueError("invalid project supervision limits")
    graph = planner.plan(objective)
    if graph.authority_id != "metao":
        raise ValueError("project decomposition authority must be metao")
    _validate_graph(graph.units)
    units = list(graph.units)
    executed: set[str] = set()
    accepted: set[str] = set()
    awaiting_correction: dict[str, str] = {}
    trace: list[ProjectTraceEvent] = [ProjectTraceEvent(ProjectTraceKind.PLANNED)]
    traceability: list[ProjectTraceabilityRecord] = []
    executors_used: set[str] = set()
    providers_used: set[str] = set()
    checkpoint = repository.initial(objective)
    checkpoint_holder_executor_id: str | None = None
    checkpoint_holder_target: ExecutorTarget | None = None
    corrective_count = 0

    def blocked(reason: str) -> ProjectSupervisionResult:
        trace.append(
            ProjectTraceEvent(
                ProjectTraceKind.PROJECT_BLOCKED,
                checkpoint_id=checkpoint.checkpoint_id,
                repository_state_id=checkpoint.state_id,
            )
        )
        return ProjectSupervisionResult(
            objective.project_id,
            ProjectVerdict.PROJECT_BLOCKED,
            WorkGraph(graph.authority_id, tuple(units)),
            tuple(trace),
            tuple(traceability),
            frozenset(executors_used),
            frozenset(providers_used),
            reason,
        )

    while True:
        unresolved = [unit for unit in units if unit.work_unit_id not in accepted]
        if not unresolved:
            trace.append(
                ProjectTraceEvent(
                    ProjectTraceKind.PROJECT_ACCEPTED,
                    checkpoint_id=checkpoint.checkpoint_id,
                    repository_state_id=checkpoint.state_id,
                )
            )
            return ProjectSupervisionResult(
                objective.project_id,
                ProjectVerdict.PROJECT_ACCEPTED,
                WorkGraph(graph.authority_id, tuple(units)),
                tuple(trace),
                tuple(traceability),
                frozenset(executors_used),
                frozenset(providers_used),
            )

        def dependency_satisfied(unit: WorkUnit, dependency: str) -> bool:
            if unit.corrective and unit.corrects_work_unit_id == dependency:
                return dependency in executed
            return dependency in accepted

        ready = [
            unit
            for unit in unresolved
            if unit.work_unit_id not in awaiting_correction
            and all(
                dependency_satisfied(unit, dependency)
                for dependency in unit.dependencies
            )
        ]
        if not ready:
            return blocked("no dependency-ready work unit")
        unit = ready[0]
        excluded: set[str] = set()
        execution: WorkExecutionResult | None = None
        selected_target: ExecutorTarget | None = None
        pinned_target: ExecutorTarget | None = None

        for _ in range(max_executor_attempts_per_unit):
            target = (
                pinned_target
                or (
                    checkpoint_holder_target
                    if checkpoint_holder_target is not None
                    and checkpoint_holder_target.executor_id not in excluded
                    else None
                )
                or scheduler.select(
                    unit,
                    excluded_executor_ids=frozenset(excluded),
                )
            )
            pinned_target = None
            if target is None:
                return blocked(f"no executor available for {unit.work_unit_id}")
            if checkpoint_holder_executor_id is None and initial_checkpoint_materializer is not None:
                materialized = initial_checkpoint_materializer.materialize(
                    checkpoint,
                    to_executor_id=target.executor_id,
                )
                if materialized != checkpoint:
                    return blocked("repository checkpoint changed during initial materialization")
                trace.append(
                    ProjectTraceEvent(
                        ProjectTraceKind.MATERIALIZED,
                        unit.work_unit_id,
                        target.executor_id,
                        checkpoint.checkpoint_id,
                        checkpoint.state_id,
                        checkpoint.artifact_ref,
                    )
                )
                checkpoint_holder_executor_id = target.executor_id
                checkpoint_holder_target = target
            elif (
                checkpoint_holder_executor_id is not None
                and checkpoint_holder_executor_id != target.executor_id
            ):
                handed = repository.handoff(
                    checkpoint,
                    from_executor_id=checkpoint_holder_executor_id,
                    to_executor_id=target.executor_id,
                )
                if handed != checkpoint:
                    return blocked("repository checkpoint changed during handoff")
                trace.append(
                    ProjectTraceEvent(
                        ProjectTraceKind.HANDED_OFF,
                        unit.work_unit_id,
                        target.executor_id,
                        checkpoint.checkpoint_id,
                        checkpoint.state_id,
                        checkpoint.artifact_ref,
                    )
                )
                checkpoint_holder_executor_id = target.executor_id
                checkpoint_holder_target = target

            selected_target = target
            executors_used.add(target.executor_id)
            providers_used.add(target.provider_id)
            checkpoint_holder_executor_id = target.executor_id
            checkpoint_holder_target = target
            trace.append(
                ProjectTraceEvent(
                    ProjectTraceKind.DISPATCHED,
                    unit.work_unit_id,
                    target.executor_id,
                    checkpoint.checkpoint_id,
                    checkpoint.state_id,
                )
            )
            execution = runner.run(objective, unit, target, checkpoint)
            if (
                execution.work_unit_id != unit.work_unit_id
                or execution.executor_id != target.executor_id
                or execution.provider_id != target.provider_id
            ):
                return blocked("runner result binding mismatch")
            if execution.status is WorkExecutionStatus.CAPACITY_FAILED:
                trace.append(
                    ProjectTraceEvent(
                        ProjectTraceKind.FAILED_CAPACITY,
                        unit.work_unit_id,
                        target.executor_id,
                        checkpoint.checkpoint_id,
                        checkpoint.state_id,
                        evidence_ref=execution.evidence_ref,
                    )
                )
                excluded.add(target.executor_id)
                next_target = scheduler.select(
                    unit,
                    excluded_executor_ids=frozenset(excluded),
                )
                if next_target is None:
                    return blocked(f"capacity exhausted for {unit.work_unit_id}")
                handed = repository.handoff(
                    checkpoint,
                    from_executor_id=target.executor_id,
                    to_executor_id=next_target.executor_id,
                )
                if handed != checkpoint:
                    return blocked("repository checkpoint changed during handoff")
                trace.append(
                    ProjectTraceEvent(
                        ProjectTraceKind.HANDED_OFF,
                        unit.work_unit_id,
                        next_target.executor_id,
                        checkpoint.checkpoint_id,
                        checkpoint.state_id,
                        checkpoint.artifact_ref,
                    )
                )
                checkpoint_holder_executor_id = next_target.executor_id
                checkpoint_holder_target = next_target
                pinned_target = next_target
                continue
            if execution.status is WorkExecutionStatus.FAILED:
                return blocked(f"work unit execution failed: {unit.work_unit_id}")
            break

        if (
            execution is None
            or selected_target is None
            or execution.status is not WorkExecutionStatus.SUCCEEDED
        ):
            return blocked(f"work unit did not complete: {unit.work_unit_id}")
        executed.add(unit.work_unit_id)
        previous_repository_id = checkpoint.repository_id
        checkpoint = repository.capture(objective, unit, execution)
        checkpoint_holder_executor_id = execution.executor_id
        checkpoint_holder_target = selected_target
        if checkpoint.repository_id != previous_repository_id:
            return blocked("captured checkpoint changed repository identity")
        if (
            checkpoint.state_id != execution.repository_state_id
            or checkpoint.artifact_ref != execution.artifact_ref
        ):
            return blocked(
                "captured checkpoint does not match execution repository state"
            )
        trace.append(
            ProjectTraceEvent(
                ProjectTraceKind.CHECKPOINTED,
                unit.work_unit_id,
                execution.executor_id,
                checkpoint.checkpoint_id,
                checkpoint.state_id,
                checkpoint.artifact_ref,
            )
        )
        trace.append(
            ProjectTraceEvent(
                ProjectTraceKind.ARTIFACT_PRODUCED,
                unit.work_unit_id,
                execution.executor_id,
                checkpoint.checkpoint_id,
                checkpoint.state_id,
                checkpoint.artifact_ref,
            )
        )

        verification = verifier.verify(objective, unit, execution, checkpoint)
        if verification.verifier_id == execution.executor_id:
            return blocked("work unit verifier is not independent from executor")
        if verification.accepted:
            accepted.add(unit.work_unit_id)
            trace.append(
                ProjectTraceEvent(
                    ProjectTraceKind.VERIFICATION_PASSED,
                    unit.work_unit_id,
                    execution.executor_id,
                    checkpoint.checkpoint_id,
                    checkpoint.state_id,
                    checkpoint.artifact_ref,
                    verification.evidence_ref,
                )
            )
            traceability.append(
                ProjectTraceabilityRecord(
                    objective.requirement_id,
                    unit.work_unit_id,
                    checkpoint.artifact_ref,
                    verification.test_ref,
                    "PASS",
                )
            )
            if unit.corrective and unit.corrects_work_unit_id is not None:
                corrected_id = unit.corrects_work_unit_id
                accepted.add(corrected_id)
                awaiting_correction.pop(corrected_id, None)
                traceability.append(
                    ProjectTraceabilityRecord(
                        objective.requirement_id,
                        corrected_id,
                        checkpoint.artifact_ref,
                        verification.test_ref,
                        "CORRECTED_PASS",
                    )
                )
            continue

        trace.append(
            ProjectTraceEvent(
                ProjectTraceKind.VERIFICATION_FAILED,
                unit.work_unit_id,
                execution.executor_id,
                checkpoint.checkpoint_id,
                checkpoint.state_id,
                checkpoint.artifact_ref,
                verification.evidence_ref,
            )
        )
        if unit.corrective:
            return blocked(f"corrective work failed verification: {unit.work_unit_id}")
        if corrective_count >= max_corrective_units:
            return blocked("corrective work limit reached")
        corrective = planner.corrective_work(
            objective,
            unit,
            verification,
            WorkGraph(graph.authority_id, tuple(units)),
        )
        if corrective is None:
            return blocked(
                f"verification failed without corrective work: {unit.work_unit_id}"
            )
        if (
            not corrective.corrective
            or corrective.corrects_work_unit_id != unit.work_unit_id
        ):
            return blocked("planner returned invalid corrective work")
        if unit.work_unit_id not in corrective.dependencies:
            return blocked("corrective work does not depend on corrected work unit")
        if corrective.work_unit_id in {item.work_unit_id for item in units}:
            return blocked("planner returned duplicate corrective work id")
        units.append(corrective)
        _validate_graph(tuple(units))
        corrective_count += 1
        awaiting_correction[unit.work_unit_id] = corrective.work_unit_id
        trace.append(
            ProjectTraceEvent(
                ProjectTraceKind.CORRECTIVE_WORK_CREATED,
                corrective.work_unit_id,
                repository_state_id=checkpoint.state_id,
                artifact_ref=verification.evidence_ref,
            )
        )


__all__ = [
    "ProjectVerdict",
    "WorkExecutionStatus",
    "ProjectTraceKind",
    "ProjectObjective",
    "WorkUnit",
    "WorkGraph",
    "ExecutorTarget",
    "RepositoryCheckpoint",
    "WorkExecutionResult",
    "WorkVerificationResult",
    "ProjectTraceEvent",
    "ProjectTraceabilityRecord",
    "ProjectSupervisionResult",
    "ProjectPlannerPort",
    "ExecutorSchedulerPort",
    "WorkUnitRunnerPort",
    "RepositoryCheckpointPort",
    "WorkUnitVerifierPort",
    "supervise_project",
]
