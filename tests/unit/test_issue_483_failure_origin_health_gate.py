from __future__ import annotations

from pathlib import Path
import tempfile
import unittest

from metao.adapters.crewai import CrewAIOrchestratorAdapter
from metao.adapters.langgraph import LangGraphOrchestratorAdapter
from metao.core import ExecutionRequest, ExecutionStatus, Mission
from metao.failure_origin import (
    BoundFailureOriginEvidence,
    FailureOrigin,
    FactualFailureOutcome,
)
from metao.runtime_health import RuntimeHealthState
from metao.sqlite_runtime_health import SQLiteRuntimeHealthStore


class _FailingGraph:
    def invoke(self, payload):
        raise RuntimeError("graph failure")


class _FailingCrew:
    def kickoff(self, *, inputs):
        raise RuntimeError("crew failure")


class _HealthyGraph:
    def invoke(self, payload):
        return {"result": "ok"}


class _StaticOriginAuthority:
    def __init__(self, origin: FailureOrigin, outcome: FactualFailureOutcome = FactualFailureOutcome.FAILED):
        self.origin = origin
        self.outcome = outcome

    def resolve_failure_origin(self, *, request, runtime_id, runtime_version, config_id, error):
        return BoundFailureOriginEvidence(
            producer_id=f"authority:{self.origin.value}",
            mission_id=request.mission.mission_id,
            execution_id=request.execution_id,
            origin=self.origin,
            outcome=self.outcome,
            evidence_ref=f"origin://{request.execution_id}/{self.origin.value}",
        )


def _request(execution_id: str) -> ExecutionRequest:
    return ExecutionRequest(
        execution_id,
        Mission("issue-483", "exercise origin gate", frozenset({"workflow"})),
    )


class Issue483FailureOriginHealthGateTests(unittest.TestCase):
    def test_runtime_local_failure_is_persisted_as_health_failure(self):
        adapter = LangGraphOrchestratorAdapter(
            _FailingGraph(),
            failure_origin_authority=_StaticOriginAuthority(FailureOrigin.RUNTIME_LOCAL),
        )
        result = adapter.execute(_request("runtime-local"))
        self.assertEqual(result.status, ExecutionStatus.FAILED)
        facts = adapter.runtime_health_facts()
        self.assertEqual(facts.attempts, 1)
        self.assertEqual(facts.failures, 1)
        self.assertEqual(facts.state, RuntimeHealthState.UNHEALTHY)
        self.assertEqual(adapter.failure_origin_evidence("runtime-local").origin, FailureOrigin.RUNTIME_LOCAL)

    def test_provider_failure_preserves_origin_but_does_not_increment_local_health(self):
        adapter = CrewAIOrchestratorAdapter(
            _FailingCrew(),
            failure_origin_authority=_StaticOriginAuthority(FailureOrigin.PROVIDER_SERVICE),
        )
        result = adapter.execute(_request("provider"))
        self.assertEqual(result.status, ExecutionStatus.FAILED)
        facts = adapter.runtime_health_facts()
        self.assertEqual(facts.attempts, 0)
        self.assertEqual(facts.failures, 0)
        self.assertEqual(facts.state, RuntimeHealthState.UNKNOWN)
        self.assertEqual(adapter.failure_origin_evidence("provider").origin, FailureOrigin.PROVIDER_SERVICE)

    def test_network_timeout_does_not_increment_local_health(self):
        adapter = LangGraphOrchestratorAdapter(
            _FailingGraph(),
            failure_origin_authority=_StaticOriginAuthority(
                FailureOrigin.NETWORK_TRANSPORT,
                FactualFailureOutcome.TIMEOUT,
            ),
        )
        result = adapter.execute(_request("network"))
        self.assertEqual(result.status, ExecutionStatus.FAILED)
        self.assertEqual(adapter.runtime_health_facts().attempts, 0)
        evidence = adapter.failure_origin_evidence("network")
        self.assertEqual(evidence.origin, FailureOrigin.NETWORK_TRANSPORT)
        self.assertEqual(evidence.outcome, FactualFailureOutcome.TIMEOUT)

    def test_policy_and_capacity_origin_never_mint_execution_health_failure(self):
        for origin in (FailureOrigin.POLICY, FailureOrigin.CAPACITY):
            with self.subTest(origin=origin):
                adapter = CrewAIOrchestratorAdapter(
                    _FailingCrew(),
                    failure_origin_authority=_StaticOriginAuthority(origin),
                )
                result = adapter.execute(_request(f"preexec-{origin.value}"))
                self.assertEqual(result.status, ExecutionStatus.FAILED)
                self.assertEqual(adapter.runtime_health_facts().attempts, 0)

    def test_generic_exception_without_origin_authority_fails_closed_for_health(self):
        adapter = LangGraphOrchestratorAdapter(_FailingGraph())
        result = adapter.execute(_request("unclassified"))
        self.assertEqual(result.status, ExecutionStatus.FAILED)
        self.assertEqual(adapter.runtime_health_facts().state, RuntimeHealthState.UNKNOWN)
        self.assertIsNone(adapter.failure_origin_evidence("unclassified"))

    def test_success_still_records_health_without_failure_origin_authority(self):
        adapter = LangGraphOrchestratorAdapter(_HealthyGraph())
        result = adapter.execute(_request("success"))
        self.assertEqual(result.status, ExecutionStatus.SUCCEEDED)
        facts = adapter.runtime_health_facts()
        self.assertEqual(facts.attempts, 1)
        self.assertEqual(facts.successes, 1)
        self.assertEqual(facts.state, RuntimeHealthState.HEALTHY)

    def test_wrong_execution_binding_is_not_admitted_to_health_or_origin_ledger(self):
        class WrongBindingAuthority(_StaticOriginAuthority):
            def resolve_failure_origin(self, *, request, runtime_id, runtime_version, config_id, error):
                evidence = super().resolve_failure_origin(
                    request=request,
                    runtime_id=runtime_id,
                    runtime_version=runtime_version,
                    config_id=config_id,
                    error=error,
                )
                return BoundFailureOriginEvidence(
                    producer_id=evidence.producer_id,
                    mission_id=evidence.mission_id,
                    execution_id="other-execution",
                    origin=evidence.origin,
                    outcome=evidence.outcome,
                    evidence_ref=evidence.evidence_ref,
                )

        adapter = LangGraphOrchestratorAdapter(
            _FailingGraph(),
            failure_origin_authority=WrongBindingAuthority(FailureOrigin.RUNTIME_LOCAL),
        )
        result = adapter.execute(_request("bound"))
        self.assertEqual(result.status, ExecutionStatus.FAILED)
        self.assertEqual(adapter.runtime_health_facts().attempts, 0)
        self.assertIsNone(adapter.failure_origin_evidence("bound"))

    def test_durable_external_origin_survives_restart_and_blocks_reclassification(self):
        with tempfile.TemporaryDirectory() as temp:
            path = Path(temp) / "health.sqlite3"
            first_store = SQLiteRuntimeHealthStore(path)
            first = LangGraphOrchestratorAdapter(
                _FailingGraph(),
                orchestrator_id="runtime-a",
                version="1",
                config_id="cfg-a",
                health_store=first_store,
                failure_origin_authority=_StaticOriginAuthority(FailureOrigin.PROVIDER_SERVICE),
            )
            self.assertEqual(first.execute(_request("same-execution")).status, ExecutionStatus.FAILED)
            history = first_store.history(runtime_id="runtime-a", runtime_version="1", config_id="cfg-a")
            self.assertEqual(len(history), 1)
            self.assertEqual(history[0].failure_origin, FailureOrigin.PROVIDER_SERVICE)
            self.assertEqual(first.runtime_health_facts().attempts, 0)

            reopened_store = SQLiteRuntimeHealthStore(path)
            reopened = LangGraphOrchestratorAdapter(
                _FailingGraph(),
                orchestrator_id="runtime-a",
                version="1",
                config_id="cfg-a",
                health_store=reopened_store,
                failure_origin_authority=_StaticOriginAuthority(FailureOrigin.RUNTIME_LOCAL),
            )
            self.assertEqual(reopened.execute(_request("same-execution")).status, ExecutionStatus.FAILED)
            replay = reopened_store.history(runtime_id="runtime-a", runtime_version="1", config_id="cfg-a")
            self.assertEqual(len(replay), 1)
            self.assertEqual(replay[0].failure_origin, FailureOrigin.PROVIDER_SERVICE)
            self.assertEqual(reopened.runtime_health_facts().attempts, 0)


if __name__ == "__main__":
    unittest.main(verbosity=2)
