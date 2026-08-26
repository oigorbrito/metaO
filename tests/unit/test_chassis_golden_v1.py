import json
from pathlib import Path
import unittest

from metao.acceptance import (
    AcceptanceContext,
    AcceptanceDecision,
    EvidenceEnvelope,
    evaluate_acceptance,
)
from metao.control_plane import execute_mission_once
from metao.core import (
    HealthReport,
    HealthStatus,
    Mission,
    OrchestratorDescriptor,
    OrchestratorRegistry,
)
from metao.governance import AcceptanceBudget, evaluate_policy
from metao.strategy import OrchestratorPoolState, OrchestratorStatus


BASELINE = "b69a4e502b07ddfa1f5e05399710e335d5edfbc0"
FIXTURE = Path(__file__).parents[1] / "golden" / "chassis_v1.json"


def evidence(**overrides):
    data = dict(
        evidence_id="e1",
        obligation_id="verify",
        mission_id="m1",
        execution_id="x1",
        orchestrator_id="orch-a",
        adapter_version="1",
        attempt_id="a1",
        subject_id="s1",
        subject_state_id="state-1",
        verification_context_id="ctx-1",
        policy_bundle_id="policy-1",
        verifier_id="verifier-1",
        payload_digest="abc",
        provenance_root="root-1",
        authority_id="authority-1",
        passed=True,
        created_at_epoch=10,
        expires_at_epoch=20,
    )
    data.update(overrides)
    return EvidenceEnvelope(**data)


def context():
    return AcceptanceContext(
        subject_id="s1",
        subject_state_id="state-1",
        verification_context_id="ctx-1",
        policy_bundle_id="policy-1",
        required_obligations=frozenset({"verify"}),
        trusted_verifiers=frozenset({"verifier-1"}),
        trusted_provenance_roots=frozenset({"root-1"}),
        authorized_authorities=frozenset({"authority-1"}),
    )


class ExplodingRuntime:
    @property
    def descriptor(self):
        return OrchestratorDescriptor("exploder", "1", frozenset({"workflow"}))

    def health(self):
        return HealthReport(HealthStatus.HEALTHY)

    def execute(self, request):
        raise RuntimeError("unexpected runtime exception")

    def cancel(self, execution_id: str):
        return None


class ChassisGoldenV1(unittest.TestCase):
    def test_replay_golden_cases(self):
        fixture = json.loads(FIXTURE.read_text(encoding="utf-8"))
        self.assertEqual(fixture["baseline_commit"], BASELINE)

        for case in fixture["cases"]:
            with self.subTest(case=case["name"]):
                if case["evidence"] == "none":
                    items = []
                    now_epoch = 15
                elif case["evidence"] == "evil_verifier":
                    items = [evidence(verifier_id="evil")]
                    now_epoch = 15
                elif case["evidence"] == "stale":
                    items = [evidence()]
                    now_epoch = 21
                else:
                    items = [evidence()]
                    now_epoch = 15

                result = evaluate_acceptance(
                    context(),
                    items,
                    now_epoch=now_epoch,
                    executor_done=case["executor_done"],
                )
                self.assertEqual(result.decision, AcceptanceDecision[case["expected"]])

    def test_c5_unexpected_runtime_exception_is_contained_by_control_plane(self):
        registry = OrchestratorRegistry()
        registry.register(ExplodingRuntime())
        mission = Mission("c5-mission", "exercise failure containment", frozenset({"workflow"}))
        pools = (
            OrchestratorPoolState(
                "exploder",
                OrchestratorStatus.HEALTHY,
                frozenset({"workflow"}),
            ),
        )

        try:
            outcome = execute_mission_once(
                mission=mission,
                registry=registry,
                pools=pools,
                normalizers={"exploder": lambda **_: evidence()},
                policy=evaluate_policy(policy_bundle_id="policy-1", allowed=True),
                budget=AcceptanceBudget(1.0, 1000, 60.0, 2),
                acceptance_context=context(),
                execution_id="c5-exec",
                now_epoch=15.0,
            )
        except Exception as exc:
            self.fail(
                "C5 failure containment violated: unexpected runtime exception escaped "
                f"the control-plane boundary: {type(exc).__name__}: {exc}"
            )

        self.assertNotEqual(outcome.acceptance.decision, AcceptanceDecision.ACCEPT)


if __name__ == "__main__":
    unittest.main()
