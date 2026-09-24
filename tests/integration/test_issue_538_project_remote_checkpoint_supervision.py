from __future__ import annotations

import hashlib
import unittest

from metao.acceptance import AcceptanceContext, EvidenceEnvelope
from metao.core import (
    ExecutionRequest,
    ExecutionResult,
    ExecutionStatus,
    HealthReport,
    HealthStatus,
    OrchestratorDescriptor,
    OrchestratorRegistry,
)
from metao.git_checkpoint_transport import EndpointGitCheckpointPort, GitRepositoryEndpoint
from metao.governance import AcceptanceBudget, evaluate_policy
from metao.project_runner import MissionControlPlaneWorkUnitRunner
from metao.project_scheduler import (
    CanonicalProjectExecutorScheduler,
    ExecutorProviderRegistration,
    WorkUnitSchedulingRequirements,
)
from metao.project_supervision import (
    ProjectObjective,
    ProjectTraceKind,
    ProjectVerdict,
    WorkGraph,
    WorkUnit,
    WorkVerificationResult,
    supervise_project,
)
from metao.strategy import OrchestratorPoolState, OrchestratorStatus


class DeterministicRemoteGitTransport:
    def __init__(self, heads: dict[str, str]) -> None:
        self.heads = dict(heads)
        self.commits = {endpoint_id: {head} for endpoint_id, head in heads.items()}
        self.transfers: list[tuple[str, str, str]] = []

    def observe_clean_head(self, endpoint: GitRepositoryEndpoint) -> str:
        return self.heads[endpoint.endpoint_id]

    def require_commit(self, endpoint: GitRepositoryEndpoint, commit_id: str) -> None:
        if commit_id not in self.commits[endpoint.endpoint_id]:
            raise ValueError(f"missing commit at {endpoint.endpoint_id}")

    def transfer_exact(
        self,
        source: GitRepositoryEndpoint,
        destination: GitRepositoryEndpoint,
        commit_id: str,
    ) -> None:
        self.require_commit(source, commit_id)
        if self.heads[source.endpoint_id] != commit_id:
            raise ValueError("source endpoint drifted from checkpoint")
        self.commits[destination.endpoint_id].add(commit_id)
        self.heads[destination.endpoint_id] = commit_id
        self.transfers.append((source.endpoint_id, destination.endpoint_id, commit_id))

    def commit(self, endpoint_id: str, work_unit_id: str, executor_id: str) -> str:
        parent = self.heads[endpoint_id]
        commit_id = hashlib.sha1(
            f"{parent}:{work_unit_id}:{executor_id}".encode("utf-8")
        ).hexdigest()
        self.commits[endpoint_id].add(commit_id)
        self.heads[endpoint_id] = commit_id
        return commit_id


class RemoteStateExecutor:
    def __init__(
        self,
        executor_id: str,
        endpoint_id: str,
        capabilities: frozenset[str],
        transport: DeterministicRemoteGitTransport,
    ) -> None:
        self.endpoint_id = endpoint_id
        self.transport = transport
        self.requests: list[ExecutionRequest] = []
        self._descriptor = OrchestratorDescriptor(executor_id, "1.0", capabilities)

    @property
    def descriptor(self) -> OrchestratorDescriptor:
        return self._descriptor

    def health(self) -> HealthReport:
        return HealthReport(HealthStatus.HEALTHY)

    def execute(self, request: ExecutionRequest) -> ExecutionResult:
        self.requests.append(request)
        expected = str(request.context["repository_state_id"])
        if self.transport.heads[self.endpoint_id] != expected:
            raise AssertionError("executor endpoint was not materialized to trusted checkpoint")
        work_unit_id = str(request.context["work_unit_id"])
        head = self.transport.commit(
            self.endpoint_id,
            work_unit_id,
            self.descriptor.orchestrator_id,
        )
        return ExecutionResult(
            request.execution_id,
            self.descriptor.orchestrator_id,
            ExecutionStatus.SUCCEEDED,
            output={
                "repository_state_id": head,
                "artifact_ref": f"git://repo-metao/{head}",
                "evidence_ref": f"remote:{work_unit_id}:{head}",
            },
        )

    def cancel(self, execution_id: str) -> None:
        pass


class Planner:
    def plan(self, objective: ProjectObjective) -> WorkGraph:
        return WorkGraph(
            "metao",
            (
                WorkUnit("prepare", "prepare repository"),
                WorkUnit("implement", "implement objective", dependencies=("prepare",)),
            ),
        )

    def corrective_work(self, objective, failed_unit, verification, graph):
        return WorkUnit(
            "repair-prepare",
            "repair rejected preparation",
            dependencies=("prepare",),
            corrective=True,
            corrects_work_unit_id="prepare",
        )


class Verifier:
    def __init__(self) -> None:
        self.calls: list[str] = []

    def verify(self, objective, unit, execution, checkpoint):
        self.calls.append(unit.work_unit_id)
        accepted = unit.work_unit_id != "prepare"
        return WorkVerificationResult(
            accepted,
            "project-verifier",
            f"verify:{unit.work_unit_id}:{checkpoint.state_id}",
            f"test:{unit.work_unit_id}",
            "injected verification failure" if not accepted else "",
        )


def pool(executor_id: str, capabilities: frozenset[str], quality: float):
    return OrchestratorPoolState(
        executor_id,
        OrchestratorStatus.HEALTHY,
        capabilities,
        success_rate=quality,
        quality=quality,
        reliability=quality,
        cost=0.01,
    )


def normalizer(*, request, orchestrator_id, adapter_version, output, attempt_id):
    return EvidenceEnvelope(
        evidence_id=f"{request.execution_id}:{attempt_id}",
        obligation_id=request.context["obligation_id"],
        mission_id=request.mission.mission_id,
        execution_id=request.execution_id,
        orchestrator_id=orchestrator_id,
        adapter_version=adapter_version,
        attempt_id=attempt_id,
        subject_id=request.context["subject_id"],
        subject_state_id=request.context["subject_state_id"],
        verification_context_id=request.context["verification_context_id"],
        policy_bundle_id=request.context["policy_bundle_id"],
        verifier_id=request.context["verifier_id"],
        payload_digest="digest",
        provenance_root="issue-538",
        authority_id=request.context["authority_id"],
        passed=True,
        created_at_epoch=request.context["created_at_epoch"],
    )


class Issue538RemoteCheckpointSupervisionIntegrationTests(unittest.TestCase):
    def test_corrective_replan_preserves_remote_checkpoint_authority(self):
        initial_sha = "a" * 40
        transport = DeterministicRemoteGitTransport(
            {
                "host-origin": initial_sha,
                "remote-a": "b" * 40,
                "remote-c": "c" * 40,
            }
        )
        repository = EndpointGitCheckpointPort(
            initial_endpoint=GitRepositoryEndpoint("host-origin", "/repo/origin"),
            executor_endpoints={
                "executor-a": GitRepositoryEndpoint("remote-a", "/repo/a"),
                "executor-c": GitRepositoryEndpoint("remote-c", "/repo/c"),
            },
            repository_id="repo-metao",
            transport=transport,
        )

        executor_a = RemoteStateExecutor(
            "executor-a", "remote-a", frozenset({"code"}), transport
        )
        executor_c = RemoteStateExecutor(
            "executor-c", "remote-c", frozenset({"repair"}), transport
        )
        registry = OrchestratorRegistry()
        registry.register(executor_a)
        registry.register(executor_c)
        pools = (
            pool("executor-a", frozenset({"code"}), 0.99),
            pool("executor-c", frozenset({"repair"}), 0.90),
        )
        scheduler = CanonicalProjectExecutorScheduler(
            pools=pools,
            requirements=(
                WorkUnitSchedulingRequirements("prepare", frozenset({"code"})),
                WorkUnitSchedulingRequirements("repair-prepare", frozenset({"repair"})),
                WorkUnitSchedulingRequirements("implement", frozenset({"code"})),
            ),
            registrations=(
                ExecutorProviderRegistration("executor-a", "provider-x"),
                ExecutorProviderRegistration("executor-c", "provider-y"),
            ),
            provider_diverse_failover=True,
            now_epoch=100.0,
        )
        runner = MissionControlPlaneWorkUnitRunner(
            registry=registry,
            pools=pools,
            normalizers={"executor-a": normalizer, "executor-c": normalizer},
            policy_for=lambda objective, unit: evaluate_policy(
                policy_bundle_id="policy", allowed=True
            ),
            budget_for=lambda objective, unit: AcceptanceBudget(10.0, 1000, 60.0, 2),
            acceptance_context_for=lambda objective, unit, checkpoint: AcceptanceContext(
                subject_id=unit.work_unit_id,
                subject_state_id=checkpoint.state_id,
                verification_context_id=f"verify:{objective.project_id}:{unit.work_unit_id}",
                policy_bundle_id="policy",
                required_obligations=frozenset({"execution_result"}),
            ),
            now_epoch=100.0,
        )
        verifier = Verifier()

        result = supervise_project(
            objective=ProjectObjective("project-360", "req-360", "deliver objective"),
            planner=Planner(),
            scheduler=scheduler,
            runner=runner,
            repository=repository,
            verifier=verifier,
            initial_checkpoint_materializer=repository,
            max_executor_attempts_per_unit=2,
            max_corrective_units=1,
        )

        self.assertEqual(result.verdict, ProjectVerdict.PROJECT_ACCEPTED)
        self.assertEqual(verifier.calls, ["prepare", "repair-prepare", "implement"])
        kinds = tuple(event.kind for event in result.trace)
        self.assertLess(kinds.index(ProjectTraceKind.MATERIALIZED), kinds.index(ProjectTraceKind.DISPATCHED))
        self.assertIn(ProjectTraceKind.VERIFICATION_FAILED, kinds)
        self.assertIn(ProjectTraceKind.CORRECTIVE_WORK_CREATED, kinds)
        self.assertEqual(kinds[-1], ProjectTraceKind.PROJECT_ACCEPTED)

        self.assertEqual(transport.transfers[0], ("host-origin", "remote-a", initial_sha))
        self.assertEqual(transport.transfers[1][0:2], ("remote-a", "remote-c"))
        self.assertEqual(transport.transfers[2][0:2], ("remote-c", "remote-a"))

        prepare_request = executor_a.requests[0]
        repair_request = executor_c.requests[0]
        implement_request = executor_a.requests[1]
        self.assertEqual(prepare_request.context["repository_state_id"], initial_sha)
        self.assertEqual(repair_request.context["repository_state_id"], transport.transfers[1][2])
        self.assertEqual(implement_request.context["repository_state_id"], transport.transfers[2][2])
        self.assertEqual(
            [(record.work_unit_id, record.verdict) for record in result.traceability],
            [
                ("repair-prepare", "PASS"),
                ("prepare", "CORRECTED_PASS"),
                ("implement", "PASS"),
            ],
        )


if __name__ == "__main__":
    unittest.main()
