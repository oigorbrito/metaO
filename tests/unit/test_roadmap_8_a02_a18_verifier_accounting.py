from __future__ import annotations

import unittest

from metao.acceptance_usage import InMemoryAcceptanceUsageStore, VerificationOutcome
from metao.governance import AcceptanceBudget
from metao.verifier import (
    VerificationRequest,
    VerificationStatus,
    VerifierDescriptor,
    VerifierRegistry,
    VerifierResult,
)
from metao.verifier_accounting import (
    AccountedVerificationDecision,
    VerificationResourceFacts,
    execute_accounted_verification,
)


class _Meter:
    def __init__(self, *, money: float = 0.25, tokens: int = 10, fail: bool = False) -> None:
        self.money = money
        self.tokens = tokens
        self.fail = fail

    def measure(self, *, request, verifier_id, result, error):
        if self.fail:
            raise RuntimeError("telemetry unavailable")
        return VerificationResourceFacts(self.money, self.tokens)


class _Verifier:
    def __init__(self, *, status: VerificationStatus = VerificationStatus.PASS, mismatch: str = "", raises: bool = False) -> None:
        self._descriptor = VerifierDescriptor("verifier-1", "1.0", frozenset({"quality"}))
        self.status = status
        self.mismatch = mismatch
        self.raises = raises

    @property
    def descriptor(self) -> VerifierDescriptor:
        return self._descriptor

    def verify(self, request: VerificationRequest) -> VerifierResult:
        if self.raises:
            raise RuntimeError("verifier exploded")
        return VerifierResult(
            request_id="other" if self.mismatch == "request" else request.request_id,
            verifier_id="other" if self.mismatch == "id" else self.descriptor.verifier_id,
            verifier_version="other" if self.mismatch == "version" else self.descriptor.version,
            status=self.status,
            result_digest="result-1",
        )


class _Clock:
    def __init__(self) -> None:
        self.values = iter((10.0, 12.5))

    def __call__(self) -> float:
        return next(self.values)


class AccountedVerifierTests(unittest.TestCase):
    def request(self) -> VerificationRequest:
        return VerificationRequest(
            "req-1", "mission-1", "exec-1", "obligation-1", "subject-1",
            "state-1", "context-1", "policy-1", "payload-1", {"value": 1},
        )

    def budget(self, **overrides) -> AcceptanceBudget:
        values = dict(
            money_limit=10.0,
            token_limit=1000,
            wall_time_limit_s=100.0,
            verifier_attempt_limit=5,
        )
        values.update(overrides)
        return AcceptanceBudget(**values)

    def registry(self, verifier: _Verifier) -> VerifierRegistry:
        registry = VerifierRegistry()
        registry.register(verifier)
        return registry

    def execute(self, verifier: _Verifier, *, budget=None, meter=None):
        store = InMemoryAcceptanceUsageStore()
        result = execute_accounted_verification(
            request=self.request(),
            registry=self.registry(verifier),
            usage_port=store,
            budget=budget or self.budget(),
            resource_meter=meter or _Meter(),
            usage_id="usage-1",
            attempt_id="attempt-1",
            required_capability="quality",
            clock=_Clock(),
        )
        return result, store

    def test_pass_continues_but_is_not_final_acceptance(self) -> None:
        result, store = self.execute(_Verifier())
        self.assertEqual(result.decision, AccountedVerificationDecision.CONTINUE)
        self.assertTrue(result.verifier_result.passed)
        self.assertFalse(hasattr(result, "acceptance_decision"))
        usage = store.for_mission("mission-1")[0]
        self.assertEqual(usage.outcome, VerificationOutcome.PASS)
        self.assertEqual(usage.verifier_attempts, 1)
        self.assertEqual(usage.wall_time_s, 2.5)

    def test_verifier_error_is_accounted_and_blocks(self) -> None:
        result, store = self.execute(_Verifier(raises=True))
        self.assertEqual(result.decision, AccountedVerificationDecision.BLOCK)
        self.assertEqual(result.reason, "verifier_execution_error")
        self.assertEqual(store.for_mission("mission-1")[0].outcome, VerificationOutcome.ERROR)

    def test_invalid_result_binding_is_accounted_and_blocks(self) -> None:
        for mismatch in ("request", "id", "version"):
            with self.subTest(mismatch=mismatch):
                result, store = self.execute(_Verifier(mismatch=mismatch))
                self.assertEqual(result.decision, AccountedVerificationDecision.BLOCK)
                self.assertEqual(store.for_mission("mission-1")[0].outcome, VerificationOutcome.INVALID_RESULT)

    def test_actual_over_budget_usage_is_persisted_before_block(self) -> None:
        result, store = self.execute(
            _Verifier(),
            budget=self.budget(money_limit=0.1),
            meter=_Meter(money=0.25),
        )
        self.assertEqual(result.decision, AccountedVerificationDecision.BLOCK)
        self.assertEqual(result.reason, "acceptance_budget_exhausted")
        self.assertEqual(len(store.for_mission("mission-1")), 1)
        self.assertEqual(result.budget.money_used, 0.25)

    def test_missing_verifier_blocks_before_attempt(self) -> None:
        store = InMemoryAcceptanceUsageStore()
        result = execute_accounted_verification(
            request=self.request(), registry=VerifierRegistry(), usage_port=store,
            budget=self.budget(), resource_meter=_Meter(), usage_id="u", attempt_id="a",
            required_capability="quality", clock=_Clock(),
        )
        self.assertEqual(result.decision, AccountedVerificationDecision.BLOCK)
        self.assertEqual(result.reason, "verifier_not_found")
        self.assertEqual(store.for_mission("mission-1"), ())

    def test_usage_measurement_failure_fails_closed_without_zero_fabrication(self) -> None:
        result, store = self.execute(_Verifier(), meter=_Meter(fail=True))
        self.assertEqual(result.decision, AccountedVerificationDecision.BLOCK)
        self.assertEqual(result.reason, "usage_measurement_unavailable")
        self.assertEqual(store.for_mission("mission-1"), ())


if __name__ == "__main__":
    unittest.main()
