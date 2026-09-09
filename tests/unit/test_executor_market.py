from __future__ import annotations

import unittest

from metao.executor_market import (
    DiscoveredExecutor,
    DiscoveredExecutorRegistry,
    ExecutorMarketScout,
    ExecutorSourceProvenance,
    QualificationEvidence,
    QualificationOutcome,
    QualificationPolicy,
    RegistryAuthority,
    qualify_executor,
)


NOW = 1_000.0


def candidate(
    *,
    vendor_or_country: str | None = None,
    authorized: bool = True,
    observed_at: float = 950.0,
    confidence: float = 0.9,
    unknown_provider: bool = False,
) -> DiscoveredExecutor:
    return DiscoveredExecutor(
        executor_id="executor-1",
        provider_id="provider-1",
        capabilities=frozenset({"agent", "repository-task"}),
        provenance=ExecutorSourceProvenance(
            source_id="official-provider-docs",
            locator="https://example.invalid/provider",
            authorized=authorized,
            observed_at_epoch_s=observed_at,
            max_age_s=100.0,
            vendor_or_country=vendor_or_country,
        ),
        confidence=confidence,
        unknown_provider=unknown_provider,
    )


def evidence(
    *,
    canary: bool | None = True,
    data_handling: bool = True,
    trust: bool = True,
) -> QualificationEvidence:
    return QualificationEvidence(
        synthetic_canary_passed=canary,
        data_handling_assessed=data_handling,
        trust_assessed=trust,
    )


class ExecutorMarketTests(unittest.TestCase):
    def test_complete_fresh_authorized_evidence_qualifies_candidate(self) -> None:
        result = qualify_executor(
            candidate(),
            evidence(),
            QualificationPolicy(),
            now_epoch_s=NOW,
        )
        self.assertIs(result.outcome, QualificationOutcome.QUALIFIED)

    def test_stale_or_unauthorized_discovery_fails_closed(self) -> None:
        stale = qualify_executor(
            candidate(observed_at=800.0),
            evidence(),
            QualificationPolicy(),
            now_epoch_s=NOW,
        )
        unauthorized = qualify_executor(
            candidate(authorized=False),
            evidence(),
            QualificationPolicy(),
            now_epoch_s=NOW,
        )
        self.assertIs(stale.outcome, QualificationOutcome.BLOCKED)
        self.assertIs(unauthorized.outcome, QualificationOutcome.BLOCKED)

    def test_low_confidence_or_failed_canary_is_unqualified(self) -> None:
        low_confidence = qualify_executor(
            candidate(confidence=0.5),
            evidence(),
            QualificationPolicy(minimum_confidence=0.8),
            now_epoch_s=NOW,
        )
        canary_failed = qualify_executor(
            candidate(),
            evidence(canary=False),
            QualificationPolicy(),
            now_epoch_s=NOW,
        )
        self.assertIs(low_confidence.outcome, QualificationOutcome.UNQUALIFIED)
        self.assertIs(canary_failed.outcome, QualificationOutcome.UNQUALIFIED)

    def test_unknown_provider_without_required_canary_is_blocked(self) -> None:
        result = qualify_executor(
            candidate(unknown_provider=True),
            evidence(canary=None),
            QualificationPolicy(require_canary_for_unknown_provider=True),
            now_epoch_s=NOW,
        )
        self.assertIs(result.outcome, QualificationOutcome.BLOCKED)

    def test_incomplete_trust_or_data_handling_is_restricted(self) -> None:
        result = qualify_executor(
            candidate(),
            evidence(data_handling=False),
            QualificationPolicy(),
            now_epoch_s=NOW,
        )
        self.assertIs(result.outcome, QualificationOutcome.QUALIFIED_RESTRICTED)

    def test_vendor_or_country_identity_has_no_qualification_effect(self) -> None:
        us = qualify_executor(
            candidate(vendor_or_country="US"),
            evidence(),
            QualificationPolicy(),
            now_epoch_s=NOW,
        )
        cn = qualify_executor(
            candidate(vendor_or_country="CN"),
            evidence(),
            QualificationPolicy(),
            now_epoch_s=NOW,
        )
        unnamed = qualify_executor(
            candidate(vendor_or_country=None),
            evidence(),
            QualificationPolicy(),
            now_epoch_s=NOW,
        )
        self.assertEqual(us, cn)
        self.assertEqual(cn, unnamed)

    def test_scout_writes_only_discovery_registry_and_cannot_self_authorize(self) -> None:
        registry = DiscoveredExecutorRegistry()
        scout = ExecutorMarketScout(registry)
        record = scout.record_observation(
            candidate(),
            evidence(),
            QualificationPolicy(),
            now_epoch_s=NOW,
        )

        self.assertEqual(registry.authority, RegistryAuthority.DISCOVERY_ONLY)
        self.assertEqual(registry.get("executor-1"), record)
        for forbidden in (
            "upsert",
            "enroll",
            "authorize_repository_access",
            "issue_credentials",
            "authorize_spending",
        ):
            self.assertFalse(hasattr(scout, forbidden))
            self.assertFalse(hasattr(registry, forbidden))

    def test_registry_replaces_discovery_facts_without_minting_authority(self) -> None:
        registry = DiscoveredExecutorRegistry()
        scout = ExecutorMarketScout(registry)
        scout.record_observation(
            candidate(confidence=0.9),
            evidence(),
            QualificationPolicy(),
            now_epoch_s=NOW,
        )
        scout.record_observation(
            candidate(confidence=0.4),
            evidence(),
            QualificationPolicy(),
            now_epoch_s=NOW,
        )
        record = registry.get("executor-1")
        self.assertIsNotNone(record)
        assert record is not None
        self.assertIs(record.qualification.outcome, QualificationOutcome.UNQUALIFIED)
        self.assertEqual(registry.authority, RegistryAuthority.DISCOVERY_ONLY)


if __name__ == "__main__":
    unittest.main()
