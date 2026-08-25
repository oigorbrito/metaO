from __future__ import annotations

import unittest

from metao.terminal_proof import (
    TerminalObservation,
    TerminalProofBuilder,
    TerminalProofError,
    TerminalValidationProfile,
)


class Roadmap8A16TerminalProofTests(unittest.TestCase):
    def setUp(self) -> None:
        self.profile = TerminalValidationProfile(
            "profile-1",
            "v1",
            frozenset({"state", "policy", "authority"}),
        )
        self.observations = (
            TerminalObservation("state", "state-port", "obs-state", "digest-state"),
            TerminalObservation("policy", "policy-port", "obs-policy", "digest-policy"),
            TerminalObservation("authority", "authority-port", "obs-authority", "digest-authority"),
        )

    def build(self, observations=None):
        return TerminalProofBuilder().build(
            mission_id="mission-1",
            execution_id="execution-1",
            decision="ACCEPT",
            profile=self.profile,
            observations=self.observations if observations is None else observations,
        )

    def test_proof_is_deterministic_independent_of_observation_order(self) -> None:
        first = self.build(self.observations)
        second = self.build(tuple(reversed(self.observations)))
        self.assertEqual(first, second)

    def test_missing_required_domain_fails_closed(self) -> None:
        with self.assertRaisesRegex(TerminalProofError, "missing required domains"):
            self.build(self.observations[:-1])

    def test_unexpected_domain_fails_closed(self) -> None:
        hostile = self.observations + (
            TerminalObservation("caller-claim", "caller", "obs-hostile", "digest-hostile"),
        )
        with self.assertRaisesRegex(TerminalProofError, "unexpected domains"):
            self.build(hostile)

    def test_duplicate_domain_fails_closed(self) -> None:
        duplicate = self.observations + (
            TerminalObservation("state", "other-source", "obs-state-2", "other-digest"),
        )
        with self.assertRaisesRegex(TerminalProofError, "duplicate observation domain"):
            self.build(duplicate)

    def test_duplicate_observation_id_fails_closed(self) -> None:
        duplicate_id = (
            self.observations[0],
            TerminalObservation("policy", "policy-port", "obs-state", "digest-policy"),
            self.observations[2],
        )
        with self.assertRaisesRegex(TerminalProofError, "duplicate observation id"):
            self.build(duplicate_id)

    def test_any_bound_observation_change_changes_digest(self) -> None:
        baseline = self.build()
        changed = self.build(
            (
                self.observations[0],
                TerminalObservation("policy", "policy-port", "obs-policy", "digest-policy-v2"),
                self.observations[2],
            )
        )
        self.assertNotEqual(baseline.proof_digest, changed.proof_digest)

    def test_digest_is_not_exposed_as_authenticity_or_authorization(self) -> None:
        proof = self.build()
        self.assertFalse(hasattr(proof, "authenticated"))
        self.assertFalse(hasattr(proof, "authorized"))
        self.assertFalse(hasattr(proof, "signature"))

    def test_profile_requires_explicit_domains(self) -> None:
        with self.assertRaises(TerminalProofError):
            TerminalValidationProfile("profile", "v1", frozenset())


if __name__ == "__main__":
    unittest.main(verbosity=2)
