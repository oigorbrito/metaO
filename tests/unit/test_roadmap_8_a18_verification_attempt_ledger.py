from __future__ import annotations

import unittest

from metao.acceptance_usage import InMemoryAcceptanceUsageStore
from metao.durable_verifier_accounting import (
    DurableVerificationDecision,
    execute_durable_accounted_verification,
)
from metao.governance import AcceptanceBudget
from metao.verification_attempt import (
    InMemoryVerificationAttemptStore,
    VerificationAttemptDuplicate,
    VerificationAttemptPort,
    VerificationAttemptStarted,
)
from metao.verifier import (
    VerificationRequest,
    VerificationStatus,
    VerifierDescriptor,
    VerifierRegistry,
    VerifierResult,
)
from metao.verifier_accounting import VerificationResourceFacts


class _Verifier:
    descriptor = VerifierDescriptor("verifier-1", "1.0", frozenset({"quality"}))

    def __init__(self, *, raises: bool = False) -> None:
        self.raises = raises

    def verify(self, request: VerificationRequest) -> VerifierResult:
        if self.raises:
            raise RuntimeError("boom")
        return VerifierResult(
            request.request_id,
            self.descriptor.verifier_id,
            self.descriptor.version,
            VerificationStatus.PASS,
            "result-digest",
        )


class _Meter:
    def __init__(self, *, raises: bool = False) -> None:
        self.raises = raises

    def measure(self, **_: object) -> VerificationResourceFacts:
        if self.raises:
            raise RuntimeError("meter unavailable")
        return VerificationResourceFacts(0.25, 10)


class _Clock:
    def __init__(self) -> None:
        self.values = iter((100.0, 102.0))

    def __call__(self) -> float:
        return next(self.values)


class DurableVerificationAttemptTests(unittest.TestCase):
    def request(self) -> VerificationRequest:
        return VerificationRequest(
            "request-1",
            "mission-1",
            "execution-1",
            "obligation-1",
            "subject-1",
            "state-1",
            "context-1",
            "policy-1",
            "payload-digest",
            {"value": 1},
        )

    def budget(self) -> AcceptanceBudget:
        return AcceptanceBudget(10.0, 1000, 100.0, 10)

    def registry(self, *, raises: bool = False) -> VerifierRegistry:
        registry = VerifierRegistry()
        registry.register(_Verifier(raises=raises))
        return registry

    def test_store_satisfies_attempt_port(self) -> None:
        self.assertIsInstance(InMemoryVerificationAttemptStore(), VerificationAttemptPort)

    def test_attempt_start_rejects_missing_binding_and_bad_time(self) -> None:
        with self.assertRaises(ValueError):
            VerificationAttemptStarted("", "m", "e", "r", "a", "v", "1", 1.0)
        for value in (True, float("nan"), float("inf"), -1.0):
            with self.subTest(value=value), self.assertRaises((TypeError, ValueError)):
                VerificationAttemptStarted("id", "m", "e", "r", "a", "v", "1", value)  # type: ignore[arg-type]

    def test_duplicate_factual_attempt_cannot_get_new_record_id(self) -> None:
        store = InMemoryVerificationAttemptStore()
        first = VerificationAttemptStarted("start-1", "m", "e", "r", "a", "v", "1", 1.0)
        store.append_started(first)
        with self.assertRaises(VerificationAttemptDuplicate):
            store.append_started(
                VerificationAttemptStarted("start-2", "m", "e", "r", "a", "v", "1", 2.0)
            )

    def test_success_persists_start_before_usage(self) -> None:
        attempts = InMemoryVerificationAttemptStore()
        usage = InMemoryAcceptanceUsageStore()
        result = execute_durable_accounted_verification(
            request=self.request(),
            registry=self.registry(),
            attempt_port=attempts,
            usage_port=usage,
            budget=self.budget(),
            resource_meter=_Meter(),
            attempt_record_id="start-1",
            usage_id="usage-1",
            attempt_id="attempt-1",
            required_capability="quality",
            clock=_Clock(),
        )
        self.assertEqual(result.decision, DurableVerificationDecision.CONTINUE)
        self.assertEqual(len(attempts.for_mission("mission-1")), 1)
        self.assertEqual(len(usage.for_mission("mission-1")), 1)
        self.assertEqual(result.budget.verifier_attempts_used, 1)

    def test_meter_failure_keeps_attempt_start_and_fabricates_no_usage(self) -> None:
        attempts = InMemoryVerificationAttemptStore()
        usage = InMemoryAcceptanceUsageStore()
        result = execute_durable_accounted_verification(
            request=self.request(),
            registry=self.registry(),
            attempt_port=attempts,
            usage_port=usage,
            budget=self.budget(),
            resource_meter=_Meter(raises=True),
            attempt_record_id="start-1",
            usage_id="usage-1",
            attempt_id="attempt-1",
            clock=_Clock(),
        )
        self.assertEqual(result.decision, DurableVerificationDecision.BLOCK)
        self.assertEqual(result.reason, "usage_measurement_unavailable")
        self.assertEqual(len(attempts.for_verification_request("request-1")), 1)
        self.assertEqual(usage.for_verification_request("request-1"), ())
        self.assertEqual(result.budget, self.budget())

    def test_verifier_error_still_has_start_and_accounted_usage_when_meter_works(self) -> None:
        attempts = InMemoryVerificationAttemptStore()
        usage = InMemoryAcceptanceUsageStore()
        result = execute_durable_accounted_verification(
            request=self.request(),
            registry=self.registry(raises=True),
            attempt_port=attempts,
            usage_port=usage,
            budget=self.budget(),
            resource_meter=_Meter(),
            attempt_record_id="start-1",
            usage_id="usage-1",
            attempt_id="attempt-1",
            clock=_Clock(),
        )
        self.assertEqual(result.decision, DurableVerificationDecision.BLOCK)
        self.assertEqual(result.reason, "verifier_execution_error")
        self.assertEqual(len(attempts.for_mission("mission-1")), 1)
        recorded = usage.for_mission("mission-1")
        self.assertEqual(len(recorded), 1)
        self.assertEqual(recorded[0].outcome.value, "ERROR")


if __name__ == "__main__":
    unittest.main()
