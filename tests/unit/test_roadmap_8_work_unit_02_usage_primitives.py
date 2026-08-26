from __future__ import annotations

import math
import unittest

from metao.acceptance_usage import (
    AcceptanceUsagePort,
    DuplicateUsage,
    InMemoryAcceptanceUsageStore,
    VerificationOutcome,
    VerificationUsage,
)


class AcceptanceUsagePrimitiveTests(unittest.TestCase):
    def usage(self, **overrides: object) -> VerificationUsage:
        values: dict[str, object] = {
            "usage_id": "usage-1",
            "mission_id": "mission-1",
            "execution_id": "execution-1",
            "attempt_id": "attempt-1",
            "verifier_id": "verifier-1",
            "verification_request_id": "request-1",
            "subject_id": "subject-1",
            "subject_state_id": "state-1",
            "verification_context_id": "context-1",
            "policy_bundle_id": "policy-1",
            "started_at_epoch": 10.0,
            "ended_at_epoch": 12.5,
            "money": 0.25,
            "tokens": 100,
            "wall_time_s": 2.5,
            "verifier_attempts": 1,
            "outcome": VerificationOutcome.PASS,
        }
        values.update(overrides)
        return VerificationUsage(**values)  # type: ignore[arg-type]

    def test_in_memory_store_satisfies_port(self) -> None:
        store = InMemoryAcceptanceUsageStore()
        self.assertIsInstance(store, AcceptanceUsagePort)

    def test_usage_preserves_all_required_bindings(self) -> None:
        item = self.usage()
        self.assertEqual(item.verification_request_id, "request-1")
        self.assertEqual(item.subject_state_id, "state-1")
        self.assertEqual(item.policy_bundle_id, "policy-1")
        self.assertEqual(item.verifier_attempts, 1)

    def test_missing_identity_binding_fails_closed(self) -> None:
        with self.assertRaises(ValueError):
            self.usage(verifier_id="")

    def test_negative_usage_is_rejected(self) -> None:
        for field in ("money", "tokens", "wall_time_s"):
            with self.subTest(field=field):
                with self.assertRaises(ValueError):
                    self.usage(**{field: -1})

    def test_non_finite_usage_is_rejected(self) -> None:
        for field in ("started_at_epoch", "ended_at_epoch", "money", "wall_time_s"):
            for value in (math.nan, math.inf, -math.inf):
                with self.subTest(field=field, value=value):
                    with self.assertRaises(ValueError):
                        self.usage(**{field: value})

    def test_boolean_or_non_numeric_factual_usage_is_rejected(self) -> None:
        for field in ("started_at_epoch", "ended_at_epoch", "money", "wall_time_s"):
            for value in (True, False, "1"):
                with self.subTest(field=field, value=value):
                    with self.assertRaises((TypeError, ValueError)):
                        self.usage(**{field: value})

    def test_tokens_must_be_non_boolean_integer(self) -> None:
        for value in (True, 1.5):
            with self.subTest(value=value), self.assertRaises((TypeError, ValueError)):
                self.usage(tokens=value)

    def test_end_before_start_is_rejected(self) -> None:
        with self.assertRaises(ValueError):
            self.usage(started_at_epoch=10.0, ended_at_epoch=9.0)

    def test_one_record_represents_exactly_one_started_attempt(self) -> None:
        for attempts in (0, 2, True, 1.0):
            with self.subTest(attempts=attempts):
                with self.assertRaises((TypeError, ValueError)):
                    self.usage(verifier_attempts=attempts)

    def test_failed_attempt_still_carries_resource_usage(self) -> None:
        item = self.usage(
            outcome=VerificationOutcome.ERROR,
            money=0.10,
            tokens=20,
            wall_time_s=0.75,
        )
        self.assertEqual(item.outcome, VerificationOutcome.ERROR)
        self.assertEqual(item.verifier_attempts, 1)
        self.assertGreater(item.wall_time_s, 0)

    def test_append_is_immutable_and_duplicate_id_fails_closed(self) -> None:
        store = InMemoryAcceptanceUsageStore()
        item = self.usage()
        store.append(item)
        with self.assertRaises(DuplicateUsage):
            store.append(item)

    def test_same_bound_attempt_cannot_be_appended_under_new_usage_id(self) -> None:
        store = InMemoryAcceptanceUsageStore()
        store.append(self.usage())
        with self.assertRaises(DuplicateUsage):
            store.append(self.usage(usage_id="usage-forged-duplicate"))

    def test_queries_are_bound_and_deterministic(self) -> None:
        store = InMemoryAcceptanceUsageStore()
        second = self.usage(
            usage_id="usage-2",
            mission_id="mission-1",
            attempt_id="attempt-2",
            verification_request_id="request-2",
            started_at_epoch=20.0,
            ended_at_epoch=21.0,
            wall_time_s=1.0,
        )
        first = self.usage()
        other = self.usage(
            usage_id="usage-3",
            mission_id="mission-2",
            execution_id="execution-2",
            attempt_id="attempt-2",
            verification_request_id="request-3",
        )
        store.append(second)
        store.append(other)
        store.append(first)

        self.assertEqual(
            tuple(item.usage_id for item in store.for_mission("mission-1")),
            ("usage-1", "usage-2"),
        )
        self.assertEqual(
            tuple(
                item.usage_id
                for item in store.for_verification_request("request-2")
            ),
            ("usage-2",),
        )

    def test_opaque_cost_units_are_not_part_of_usage_contract(self) -> None:
        self.assertNotIn("verification_cost_units", VerificationUsage.__dataclass_fields__)


if __name__ == "__main__":
    unittest.main()
