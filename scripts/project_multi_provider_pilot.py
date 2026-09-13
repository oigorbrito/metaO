"""Credential-backed multi-provider project supervision pilot for #540.

This is intentionally opt-in. It composes real OpenAI Agents and Gemini provider
calls with the real project scheduler/runner/supervisor and trusted SSH Git
checkpoint/work-product boundaries. It prints only bounded evidence metadata.
"""

from __future__ import annotations

from dataclasses import dataclass
from importlib.metadata import version
import json
import os
import re

from metao.acceptance import AcceptanceContext
from metao.adapters.gemini_interactions import (
    GeminiInteractionsOrchestratorAdapter,
    normalize_evidence as normalize_gemini_evidence,
)
from metao.adapters.openai_agents import (
    OpenAIAgentsOrchestratorAdapter,
    normalize_evidence as normalize_openai_evidence,
)
from metao.capacity import CapacityObservation, CapacityStatus
from metao.core import ExecutionResult, ExecutionStatus, OrchestratorRegistry
from metao.git_checkpoint_transport import EndpointGitCheckpointPort
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
from metao.provider_workspace_executor import ProviderWorkspaceOrchestratorAdapter
from metao.ssh_git_transport import (
    OpenSshCommandExecutor,
    SshGitRepositoryEndpoint,
    SshGitRepositoryTransport,
)
from metao.ssh_work_product import SshGitWorkProductApplier
from metao.strategy import OrchestratorPoolState, OrchestratorStatus

_AUTHORIZATION = "I_AUTHORIZE_METAO_MULTI_PROVIDER_PROJECT_PILOT"
_REMOTE_ROOT_RE = re.compile(r"^/tmp/metao-project-pilot\.[A-Za-z0-9]+$")


def required(name: str) -> str:
    value = os.environ.get(name, "").strip()
    if not value:
        raise RuntimeError(f"required pilot configuration is missing: {name}")
    return value


def optional_port(name: str) -> int:
    raw = os.environ.get(name, "").strip()
    return int(raw) if raw else 22


class InjectOneCapacityFailure:
    """Typed one-shot capacity fault; delegates all later calls unchanged."""

    def __init__(self, provider) -> None:
        self.provider = provider
        self.injected = False

    @property
    def descriptor(self):
        return self.provider.descriptor

    def health(self):
        return self.provider.health()

    def execute(self, request):
        if not self.injected:
            self.injected = True
            return ExecutionResult(
                request.execution_id,
                self.descriptor.orchestrator_id,
                ExecutionStatus.FAILED,
                error="injected typed capacity fault",
                capacity_observation=CapacityObservation(
                    CapacityStatus.TEMPORARILY_RATE_LIMITED
                ),
            )
        return self.provider.execute(request)

    def cancel(self, execution_id: str):
        self.provider.cancel(execution_id)


@dataclass
class Planner:
    def plan(self, objective: ProjectObjective) -> WorkGraph:
        return WorkGraph(
            "metao",
            (
                WorkUnit("prepare", "Return a concise preparation note for the project artifact."),
                WorkUnit(
                    "implement",
                    "Return a concise implementation note building on the accepted preparation.",
                    dependencies=("prepare",),
                ),
            ),
        )

    def corrective_work(self, objective, failed_unit, verification, graph):
        if failed_unit.work_unit_id != "prepare":
            return None
        return WorkUnit(
            "repair-prepare",
            "Return a corrected preparation note addressing independent verification feedback.",
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
            accepted=accepted,
            verifier_id="project-verifier",
            evidence_ref=f"pilot-verifier:{unit.work_unit_id}:{checkpoint.state_id}",
            test_ref=f"pilot-check:{unit.work_unit_id}",
            reason="injected independent verification rejection" if not accepted else "",
        )


def pool(executor_id: str, quality: float) -> OrchestratorPoolState:
    return OrchestratorPoolState(
        executor_id,
        OrchestratorStatus.HEALTHY,
        frozenset({"code"}),
        success_rate=quality,
        quality=quality,
        reliability=quality,
        cost=0.01,
    )


def remote_root(executor: OpenSshCommandExecutor, endpoint: SshGitRepositoryEndpoint) -> str:
    value = executor.run(
        endpoint,
        ("mktemp", "-d", "/tmp/metao-project-pilot.XXXXXXXXXX"),
    ).decode().strip()
    if not _REMOTE_ROOT_RE.fullmatch(value):
        raise RuntimeError("remote pilot temp root was not canonical")
    return value


def init_repo(executor: OpenSshCommandExecutor, endpoint: SshGitRepositoryEndpoint) -> None:
    path = endpoint.repository_locator
    executor.run(endpoint, ("git", "init", path))
    executor.run(endpoint, ("git", "-C", path, "config", "user.email", "metao@example.invalid"))
    executor.run(endpoint, ("git", "-C", path, "config", "user.name", "metaO"))
    executor.run(endpoint, ("git", "-C", path, "commit", "--allow-empty", "-m", f"seed {endpoint.endpoint_id}"))


def main() -> int:
    if required("METAO_MULTI_PROVIDER_PILOT_AUTHORIZATION") != _AUTHORIZATION:
        raise RuntimeError("explicit multi-provider pilot authorization was not supplied")

    source_host = required("METAO_SSH_SMOKE_SOURCE_HOST")
    destination_host = required("METAO_SSH_SMOKE_DESTINATION_HOST")
    if source_host == destination_host:
        raise RuntimeError("multi-provider pilot requires distinct SSH hosts")
    source_user = required("METAO_SSH_SMOKE_SOURCE_USER")
    destination_user = required("METAO_SSH_SMOKE_DESTINATION_USER")
    known_hosts_file = required("METAO_SSH_KNOWN_HOSTS_FILE")
    identity_file = os.environ.get("METAO_SSH_IDENTITY_FILE", "").strip() or None
    openai_key = required("METAO_OPENAI_API_KEY")
    gemini_key = required("METAO_GEMINI_API_KEY")
    openai_model = os.environ.get("METAO_OPENAI_MODEL", "gpt-5.6-luna").strip()
    gemini_target = os.environ.get("METAO_GEMINI_TARGET", "gemma-4-26b-a4b-it").strip()

    os.environ["OPENAI_API_KEY"] = openai_key
    from agents import Agent, Runner, set_tracing_disabled

    set_tracing_disabled(True)
    ssh = OpenSshCommandExecutor()
    source_control = SshGitRepositoryEndpoint(
        "source-control",
        "/tmp",
        source_host,
        source_user,
        known_hosts_file,
        optional_port("METAO_SSH_SMOKE_SOURCE_PORT"),
        identity_file,
    )
    destination_control = SshGitRepositoryEndpoint(
        "destination-control",
        "/tmp",
        destination_host,
        destination_user,
        known_hosts_file,
        optional_port("METAO_SSH_SMOKE_DESTINATION_PORT"),
        identity_file,
    )
    source_root = None
    destination_root = None
    try:
        source_root = remote_root(ssh, source_control)
        destination_root = remote_root(ssh, destination_control)
        origin = SshGitRepositoryEndpoint(
            "origin",
            f"{source_root}/origin",
            source_host,
            source_user,
            known_hosts_file,
            optional_port("METAO_SSH_SMOKE_SOURCE_PORT"),
            identity_file,
        )
        openai_endpoint = SshGitRepositoryEndpoint(
            "executor-openai",
            f"{source_root}/executor-openai",
            source_host,
            source_user,
            known_hosts_file,
            optional_port("METAO_SSH_SMOKE_SOURCE_PORT"),
            identity_file,
        )
        gemini_endpoint = SshGitRepositoryEndpoint(
            "executor-gemini",
            f"{destination_root}/executor-gemini",
            destination_host,
            destination_user,
            known_hosts_file,
            optional_port("METAO_SSH_SMOKE_DESTINATION_PORT"),
            identity_file,
        )
        for endpoint in (origin, openai_endpoint, gemini_endpoint):
            init_repo(ssh, endpoint)

        openai_provider = OpenAIAgentsOrchestratorAdapter(
            Runner,
            Agent(
                name="metaO project pilot OpenAI executor",
                instructions="Return only a concise text work product for the requested project unit.",
                model=openai_model,
            ),
            orchestrator_id="openai-agents-live",
            version=version("openai-agents"),
        )
        openai_provider_with_fault = InjectOneCapacityFailure(openai_provider)
        gemini_provider = GeminiInteractionsOrchestratorAdapter(
            api_key=gemini_key,
            target=gemini_target,
            target_kind="model",
            base_url="https://generativelanguage.googleapis.com/v1",
            orchestrator_id="gemini-interactions-live",
            version="v1",
        )

        executor_openai = ProviderWorkspaceOrchestratorAdapter(
            openai_provider_with_fault,
            SshGitWorkProductApplier(openai_endpoint, "repo-metao", ssh),
            executor_id="executor-openai",
            capabilities=frozenset({"code"}),
        )
        executor_gemini = ProviderWorkspaceOrchestratorAdapter(
            gemini_provider,
            SshGitWorkProductApplier(gemini_endpoint, "repo-metao", ssh),
            executor_id="executor-gemini",
            capabilities=frozenset({"code"}),
        )
        registry = OrchestratorRegistry()
        registry.register(executor_openai)
        registry.register(executor_gemini)
        pools = (pool("executor-openai", 0.99), pool("executor-gemini", 0.90))
        scheduler = CanonicalProjectExecutorScheduler(
            pools=pools,
            requirements=(
                WorkUnitSchedulingRequirements("prepare", frozenset({"code"})),
                WorkUnitSchedulingRequirements("repair-prepare", frozenset({"code"})),
                WorkUnitSchedulingRequirements("implement", frozenset({"code"})),
            ),
            registrations=(
                ExecutorProviderRegistration("executor-openai", "provider-openai"),
                ExecutorProviderRegistration("executor-gemini", "provider-google"),
            ),
            provider_diverse_failover=True,
            now_epoch=100.0,
        )
        runner = MissionControlPlaneWorkUnitRunner(
            registry=registry,
            pools=pools,
            normalizers={
                "executor-openai": normalize_openai_evidence,
                "executor-gemini": normalize_gemini_evidence,
            },
            policy_for=lambda objective, unit: evaluate_policy(
                policy_bundle_id="pilot-policy",
                allowed=True,
            ),
            budget_for=lambda objective, unit: AcceptanceBudget(100.0, 100000, 600.0, 1),
            acceptance_context_for=lambda objective, unit, checkpoint: AcceptanceContext(
                subject_id=unit.work_unit_id,
                subject_state_id=checkpoint.state_id,
                verification_context_id=f"verify:{objective.project_id}:{unit.work_unit_id}",
                policy_bundle_id="pilot-policy",
                required_obligations=frozenset({"execution_result"}),
            ),
            now_epoch=100.0,
        )
        repository = EndpointGitCheckpointPort(
            initial_endpoint=origin,
            executor_endpoints={
                "executor-openai": openai_endpoint,
                "executor-gemini": gemini_endpoint,
            },
            repository_id="repo-metao",
            transport=SshGitRepositoryTransport(ssh),
        )
        verifier = Verifier()
        result = supervise_project(
            objective=ProjectObjective(
                "project-360-pilot",
                "req-360",
                "complete the multi-provider project supervision pilot",
            ),
            planner=Planner(),
            scheduler=scheduler,
            runner=runner,
            repository=repository,
            initial_checkpoint_materializer=repository,
            verifier=verifier,
            max_executor_attempts_per_unit=2,
            max_corrective_units=1,
        )

        kinds = tuple(event.kind for event in result.trace)
        assert result.verdict is ProjectVerdict.PROJECT_ACCEPTED, result.reason
        assert result.executors_used == frozenset({"executor-openai", "executor-gemini"})
        assert result.providers_used == frozenset({"provider-openai", "provider-google"})
        assert ProjectTraceKind.FAILED_CAPACITY in kinds
        assert ProjectTraceKind.MATERIALIZED in kinds
        assert kinds.count(ProjectTraceKind.HANDED_OFF) >= 2
        assert ProjectTraceKind.VERIFICATION_FAILED in kinds
        assert ProjectTraceKind.CORRECTIVE_WORK_CREATED in kinds
        assert verifier.calls == ["prepare", "repair-prepare", "implement"]
        assert openai_provider_with_fault.injected is True

        checkpoint_lineage = [
            event.repository_state_id
            for event in result.trace
            if event.kind is ProjectTraceKind.CHECKPOINTED and event.repository_state_id
        ]
        evidence = {
            "project_head": os.environ.get("GITHUB_SHA", "local-unqualified"),
            "project_verdict": result.verdict.value,
            "executors_used": sorted(result.executors_used),
            "providers_used": sorted(result.providers_used),
            "openai_adapter": openai_provider.descriptor.orchestrator_id,
            "openai_adapter_version": openai_provider.descriptor.version,
            "openai_model": openai_model,
            "gemini_adapter": gemini_provider.descriptor.orchestrator_id,
            "gemini_adapter_version": gemini_provider.descriptor.version,
            "gemini_target": gemini_target,
            "typed_capacity_failure_injected": True,
            "provider_diverse_failover_observed": True,
            "independent_verifier_id": "project-verifier",
            "verification_failure_observed": True,
            "corrective_work_observed": True,
            "checkpoint_sha_lineage": checkpoint_lineage,
            "cross_host": True,
            "credentials_emitted": False,
            "remote_paths_emitted": False,
            "operational_pilot": "PASS",
        }
        print(json.dumps(evidence, sort_keys=True, separators=(",", ":")))
        return 0
    finally:
        if source_root is not None and _REMOTE_ROOT_RE.fullmatch(source_root):
            try:
                ssh.run(source_control, ("rm", "-rf", "--", source_root))
            except ValueError:
                pass
        if destination_root is not None and _REMOTE_ROOT_RE.fullmatch(destination_root):
            try:
                ssh.run(destination_control, ("rm", "-rf", "--", destination_root))
            except ValueError:
                pass


if __name__ == "__main__":
    raise SystemExit(main())
