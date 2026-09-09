"""Provider-neutral executor discovery and qualification boundary.

Discovery facts never grant repository, credential, enrollment, or spending authority.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from math import isfinite


class QualificationOutcome(str, Enum):
    QUALIFIED = "QUALIFIED"
    QUALIFIED_RESTRICTED = "QUALIFIED_RESTRICTED"
    UNQUALIFIED = "UNQUALIFIED"
    BLOCKED = "BLOCKED"


class RegistryAuthority(str, Enum):
    DISCOVERY_ONLY = "DISCOVERY_ONLY"


@dataclass(frozen=True)
class ExecutorSourceProvenance:
    source_id: str
    locator: str
    authorized: bool
    observed_at_epoch_s: float
    max_age_s: float
    vendor_or_country: str | None = None

    def validate(self) -> None:
        if not self.source_id.strip():
            raise ValueError("source_id is required")
        if not self.locator.strip():
            raise ValueError("locator is required")
        if not isfinite(self.observed_at_epoch_s):
            raise ValueError("observed_at_epoch_s must be finite")
        if not isfinite(self.max_age_s) or self.max_age_s <= 0:
            raise ValueError("max_age_s must be finite and positive")

    def is_fresh(self, now_epoch_s: float) -> bool:
        if not isfinite(now_epoch_s):
            raise ValueError("now_epoch_s must be finite")
        return max(0.0, now_epoch_s - self.observed_at_epoch_s) <= self.max_age_s


@dataclass(frozen=True)
class DiscoveredExecutor:
    executor_id: str
    provider_id: str
    capabilities: frozenset[str]
    provenance: ExecutorSourceProvenance
    confidence: float
    unknown_provider: bool = False

    def validate(self) -> None:
        if not self.executor_id.strip():
            raise ValueError("executor_id is required")
        if not self.provider_id.strip():
            raise ValueError("provider_id is required")
        if not isfinite(self.confidence) or not 0.0 <= self.confidence <= 1.0:
            raise ValueError("confidence must be within [0, 1]")
        self.provenance.validate()


@dataclass(frozen=True)
class QualificationEvidence:
    synthetic_canary_passed: bool | None
    data_handling_assessed: bool
    trust_assessed: bool


@dataclass(frozen=True)
class QualificationPolicy:
    minimum_confidence: float = 0.8
    require_canary_for_unknown_provider: bool = True

    def validate(self) -> None:
        if not isfinite(self.minimum_confidence) or not 0.0 <= self.minimum_confidence <= 1.0:
            raise ValueError("minimum_confidence must be within [0, 1]")


@dataclass(frozen=True)
class ExecutorQualification:
    outcome: QualificationOutcome
    reasons: tuple[str, ...]


@dataclass(frozen=True)
class DiscoveredExecutorRecord:
    executor: DiscoveredExecutor
    qualification: ExecutorQualification


def qualify_executor(
    candidate: DiscoveredExecutor,
    evidence: QualificationEvidence,
    policy: QualificationPolicy,
    *,
    now_epoch_s: float,
) -> ExecutorQualification:
    candidate.validate()
    policy.validate()

    if not candidate.provenance.authorized:
        return ExecutorQualification(
            QualificationOutcome.BLOCKED,
            ("discovery source is not user-authorized",),
        )
    if not candidate.provenance.is_fresh(now_epoch_s):
        return ExecutorQualification(
            QualificationOutcome.BLOCKED,
            ("discovery provenance is stale and must be refreshed",),
        )
    if candidate.confidence < policy.minimum_confidence:
        return ExecutorQualification(
            QualificationOutcome.UNQUALIFIED,
            ("discovery confidence is below qualification policy",),
        )
    if evidence.synthetic_canary_passed is False:
        return ExecutorQualification(
            QualificationOutcome.UNQUALIFIED,
            ("synthetic qualification canary failed",),
        )
    if (
        candidate.unknown_provider
        and policy.require_canary_for_unknown_provider
        and evidence.synthetic_canary_passed is None
    ):
        return ExecutorQualification(
            QualificationOutcome.BLOCKED,
            ("unknown provider requires synthetic qualification evidence",),
        )
    if not evidence.data_handling_assessed or not evidence.trust_assessed:
        return ExecutorQualification(
            QualificationOutcome.QUALIFIED_RESTRICTED,
            (
                "candidate lacks complete data-handling or trust evidence; sensitive access remains restricted",
            ),
        )
    return ExecutorQualification(
        QualificationOutcome.QUALIFIED,
        ("fresh authorized discovery and qualification evidence satisfy policy",),
    )


class DiscoveredExecutorRegistry:
    """Discovery ledger only; enrollment and authority live elsewhere."""

    authority = RegistryAuthority.DISCOVERY_ONLY

    def __init__(self) -> None:
        self._records: dict[str, DiscoveredExecutorRecord] = {}

    def _store(self, record: DiscoveredExecutorRecord) -> None:
        record.executor.validate()
        self._records[record.executor.executor_id] = record

    def get(self, executor_id: str) -> DiscoveredExecutorRecord | None:
        return self._records.get(executor_id)

    def records(self) -> tuple[DiscoveredExecutorRecord, ...]:
        return tuple(self._records[key] for key in sorted(self._records))


class ExecutorMarketScout:
    """Consumes already-authorized observations and writes discovery facts only."""

    def __init__(self, registry: DiscoveredExecutorRegistry) -> None:
        self._registry = registry

    def record_observation(
        self,
        candidate: DiscoveredExecutor,
        evidence: QualificationEvidence,
        policy: QualificationPolicy,
        *,
        now_epoch_s: float,
    ) -> DiscoveredExecutorRecord:
        qualification = qualify_executor(
            candidate,
            evidence,
            policy,
            now_epoch_s=now_epoch_s,
        )
        record = DiscoveredExecutorRecord(candidate, qualification)
        self._registry._store(record)
        return record


__all__ = [
    "DiscoveredExecutor",
    "DiscoveredExecutorRecord",
    "DiscoveredExecutorRegistry",
    "ExecutorMarketScout",
    "ExecutorQualification",
    "ExecutorSourceProvenance",
    "QualificationEvidence",
    "QualificationOutcome",
    "QualificationPolicy",
    "RegistryAuthority",
    "qualify_executor",
]
