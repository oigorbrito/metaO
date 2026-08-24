import unittest

from metao.security import (
    AttestationRejected,
    AttestationVerifier,
    CryptoProviderPort,
    HOSTILE_OR_DISTRIBUTED_BOUNDARY,
    ReplayDetected,
    RevokedVerifier,
    StandardCryptoProvider,
    TrustProfile,
    UntrustedVerifier,
    reject_replay,
    verify_attestation,
    verify_freshness,
    verify_trust_root,
)


class RecordingStandardsVerifier:
    def __init__(self, accepted=True):
        self.accepted = accepted
        self.calls = []

    def __call__(self, *, artifact, attestation, identity):
        self.calls.append((artifact, attestation, identity))
        return self.accepted


class BlockMHostileTrustAcceptance(unittest.TestCase):
    def test_hostile_distributed_trust_profile_exists(self):
        self.assertEqual(
            HOSTILE_OR_DISTRIBUTED_BOUNDARY,
            TrustProfile.HOSTILE_OR_DISTRIBUTED_BOUNDARY,
        )

    def test_standard_attestation_verifier_boundary_delegates(self):
        external = RecordingStandardsVerifier(True)
        provider = StandardCryptoProvider(external)
        verifier = AttestationVerifier(provider, "issuer@example.com")
        self.assertTrue(verifier.verify(artifact=b"artifact", attestation=b"bundle"))
        self.assertEqual(
            external.calls,
            [(b"artifact", b"bundle", "issuer@example.com")],
        )
        self.assertIsInstance(provider, CryptoProviderPort)

    def test_freshness_and_replay_protection(self):
        self.assertTrue(
            verify_freshness(issued_at_epoch=10, expires_at_epoch=20, now_epoch=15)
        )
        seen = set()
        self.assertTrue(reject_replay("attestation-1", seen))
        with self.assertRaises(ReplayDetected):
            reject_replay("attestation-1", seen)

    def test_revoked_or_untrusted_verifier_fails_closed(self):
        trusted = {"verifier-good", "verifier-revoked"}
        self.assertTrue(
            verify_trust_root("verifier-good", trusted_verifiers=trusted)
        )
        with self.assertRaises(RevokedVerifier):
            verify_trust_root(
                "verifier-revoked",
                trusted_verifiers=trusted,
                revoked_verifiers={"verifier-revoked"},
            )
        with self.assertRaises(UntrustedVerifier):
            verify_trust_root("verifier-evil", trusted_verifiers=trusted)

    def test_no_hand_rolled_crypto_provider_contract(self):
        external = RecordingStandardsVerifier(False)
        provider = StandardCryptoProvider(external)
        with self.assertRaises(AttestationRejected):
            verify_attestation(
                provider,
                artifact=b"artifact",
                attestation=b"invalid-bundle",
                identity="issuer@example.com",
            )
        self.assertEqual(len(external.calls), 1)


if __name__ == "__main__":
    unittest.main()
