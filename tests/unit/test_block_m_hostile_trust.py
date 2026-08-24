import importlib
import unittest


class BlockMHostileTrustAcceptance(unittest.TestCase):
    def _security(self):
        return importlib.import_module("metao.security")

    def test_hostile_distributed_trust_profile_exists(self):
        security = self._security()
        self.assertTrue(hasattr(security, "TrustProfile"))
        self.assertTrue(hasattr(security, "HOSTILE_OR_DISTRIBUTED_BOUNDARY"))

    def test_standard_attestation_verifier_boundary_exists(self):
        security = self._security()
        self.assertTrue(hasattr(security, "AttestationVerifier"))
        self.assertTrue(hasattr(security, "StandardCryptoProvider"))

    def test_freshness_and_replay_protection_exist(self):
        security = self._security()
        self.assertTrue(hasattr(security, "verify_freshness"))
        self.assertTrue(hasattr(security, "reject_replay"))

    def test_revoked_or_untrusted_verifier_fails_closed(self):
        security = self._security()
        self.assertTrue(hasattr(security, "verify_trust_root"))
        self.assertTrue(hasattr(security, "RevokedVerifier"))

    def test_no_hand_rolled_crypto_contract_exists(self):
        security = self._security()
        self.assertTrue(hasattr(security, "CryptoProviderPort"))
        self.assertTrue(hasattr(security, "verify_attestation"))


if __name__ == "__main__":
    unittest.main()
