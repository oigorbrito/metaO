"""Production project work-unit runner over the mission control-plane."""

from __future__ import annotations

from typing import Callable, Mapping

from .acceptance import AcceptanceContext, AcceptanceDecision
from .capacity import CapacityStatus
from .control_plane import EvidenceNormalizer, execute_mission
from .core import ExecutionStatus, Mission, OrchestratorRegistry
from .governance import AcceptanceBudget, PolicyDecision
from .project_supervision import (
    ExecutorTarget,
    ProjectObjective,
    RepositoryCheckpoint,
    WorkExecutionResult,
    WorkExecutionStatus,
    WorkUnit,
)
from .strategy import OrchestratorPoolState

ProjectPolicyProvider = Callable[[ProjectObjective, WorkUnit], PolicyDecision]
ProjectBudgetProvider = Callable[[ProjectObjective, WorkUnit], AcceptanceBudget]
ProjectAcceptanceContextProvider = Callable[
    [ProjectObjective, WorkUnit, RepositoryCheckpoint], AcceptanceContext
]

_CAPACITY_FAILURE_STATUSES = frozenset(
    {
        CapacityStatus.TEMPORARILY_RATE_LIMITED,
        CapacityStatus.TEMPORARILY_QUOTA_EXHAUSTED,
        CapacityStatus.PROVIDER_UNAVAILABLE,
        CapacityStatus.CREDIT_EXHAUSTED,
    }
)


class MissionControlPlaneWorkUnitRunner:
    """Execute exactly one scheduler-selected project target.

    Project supervision owns executor/provider failover. This adapter therefore
    constrains the mission control-plane to the selected executor and sets
    ``max_attempts=1``. Policy, budget and mission acceptance inputs are injected
    by caller-owned authorities; this runner does not derive replacements.
    """

    def __init__(
        self,
        *,
        registry: OrchestratorRegistry,
        pools: tuple[OrchestratorPoolState, ...],
        normalizers: Mapping[str, EvidenceNormalizer],
        policy_for: ProjectPolicyProvider,
        budget_for: ProjectBudgetProvider,
        acceptance_context_for: ProjectAcceptanceContextProvider,
        now_epoch: float = 0.0,
    ) -> None:
        self._registry = registry
        self._pools = self._unique_pools(pools)
        self._normalizers = dict(normalizers)
        self._policy_for = policy_for
        self._budget_for = budget_for
        self._acceptance_context_for = acceptance_context_for
        self._now_epoch = now_epoch

    @staticmethod
    def _unique_pools(
        pools: tuple[OrchestratorPoolState, ...],
    ) -> dict[str, OrchestratorPoolState]:
        result: dict[str, OrchestratorPoolState] = {}
        for pool in pools:
            if pool.orchestrator_id in result:
                raise ValueError(f"duplicate project runner pool: {pool.orchestrator_id}")
            result[pool.orchestrator_id] = pool
        return result

    @staticmethod
    def _evidence_ref(outcome) -> str | None:
        if outcome.acceptance.proof is not None:
            return outcome.acceptance.proof.digest
        if outcome.execution is not None:
            recovery = outcome.execution.capacity_observation
            if recovery is not None and recovery.recovery is not None:
                return recovery.recovery.evidence_ref
            if outcome.execution.error:
                return outcome.execution.error
        return None

    def run(
        self,
        objective: ProjectObjective,
        unit: WorkUnit,
        target: ExecutorTarget,
        checkpoint: RepositoryCheckpoint,
    ) -> WorkExecutionResult:
        target_pool = self._pools.get(target.executor_id)
        if target_pool is None:
            raise ValueError(f"selected executor pool missing: {target.executor_id}")

        orchestrator = self._registry.get(target.executor_id)
        if orchestrator.descriptor.orchestrator_id != target.executor_id:
            raise ValueError("registry executor binding mismatch")
        normalizer = self._normalizers.get(target.executor_id)
        if normalizer is None:
            raise ValueError(f"selected executor normalizer missing: {target.executor_id}")

        mission = Mission(
            mission_id=f"project:{objective.project_id}:work:{unit.work_unit_id}",
            objective=unit.objective,
        )
        policy = self._policy_for(objective, unit)
        budget = self._budget_for(objective, unit)
        acceptance_context = self._acceptance_context_for(objective, unit, checkpoint)
        execution_context = {
            "project_id": objective.project_id,
            "work_unit_id": unit.work_unit_id,
            "checkpoint_id": checkpoint.checkpoint_id,
            "repository_id": checkpoint.repository_id,
            "repository_state_id": checkpoint.state_id,
            "artifact_ref": checkpoint.artifact_ref,
        }

        outcome = execute_mission(
            mission=mission,
            registry=self._registry,
            pools=(target_pool,),
            normalizers={target.executor_id: normalizer},
            policy=policy,
            budget=budget,
            acceptance_context=acceptance_context,
            execution_id_prefix=f"project-{objective.project_id}-{unit.work_unit_id}",
            execution_context=execution_context,
            max_attempts=1,
            now_epoch=self._now_epoch,
        )

        if outcome.orchestrator_id not in {None, target.executor_id}:
            raise ValueError("mission executor escaped scheduler-selected target")
        execution = outcome.execution
        if execution is not None and execution.orchestrator_id != target.executor_id:
            raise ValueError("mission result executor binding mismatch")

        evidence_ref = self._evidence_ref(outcome)
        if execution is None:
            return WorkExecutionResult(
                unit.work_unit_id,
                target.executor_id,
                target.provider_id,
                WorkExecutionStatus.FAILED,
                checkpoint.state_id,
                checkpoint.artifact_ref,
                evidence_ref,
            )

        if execution.status is not ExecutionStatus.SUCCEEDED:
            observation = execution.capacity_observation
            capacity_failed = (
                observation is not None
                and observation.capacity_status in _CAPACITY_FAILURE_STATUSES
            )
            return WorkExecutionResult(
                unit.work_unit_id,
                target.executor_id,
                target.provider_id,
                WorkExecutionStatus.CAPACITY_FAILED
                if capacity_failed
                else WorkExecutionStatus.FAILED,
                checkpoint.state_id,
                checkpoint.artifact_ref,
                evidence_ref,
            )

        if outcome.acceptance.decision is not AcceptanceDecision.ACCEPT:
            return WorkExecutionResult(
                unit.work_unit_id,
                target.executor_id,
                target.provider_id,
                WorkExecutionStatus.FAILED,
                checkpoint.state_id,
                checkpoint.artifact_ref,
                evidence_ref,
            )

        repository_state_id = execution.output.get("repository_state_id")
        artifact_ref = execution.output.get("artifact_ref")
        if (
            not isinstance(repository_state_id, str)
            or not repository_state_id.strip()
            or not isinstance(artifact_ref, str)
            or not artifact_ref.strip()
        ):
            return WorkExecutionResult(
                unit.work_unit_id,
                target.executor_id,
                target.provider_id,
                WorkExecutionStatus.FAILED,
                checkpoint.state_id,
                checkpoint.artifact_ref,
                evidence_ref,
            )

        output_evidence_ref = execution.output.get("evidence_ref")
        if isinstance(output_evidence_ref, str) and output_evidence_ref.strip():
            evidence_ref = output_evidence_ref

        return WorkExecutionResult(
            unit.work_unit_id,
            target.executor_id,
            target.provider_id,
            WorkExecutionStatus.SUCCEEDED,
            repository_state_id,
            artifact_ref,
            evidence_ref,
        )


__all__ = [
    "ProjectPolicyProvider",
    "ProjectBudgetProvider",
    "ProjectAcceptanceContextProvider",
    "MissionControlPlaneWorkUnitRunner",
]
