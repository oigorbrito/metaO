import unittest

from metao.strategy import CapacityRecovery


class CapacityRecoveryEvidenceBasisHostileTests(unittest.TestCase):
    def test_non_enum_evidence_basis_fails_closed(self):
        recovery = CapacityRecovery(
            recover_at_epoch=200.0,
            evidence_basis="provider_api",  # type: ignore[arg-type]
            evidence_ref="provider://rate-limit/reset/primary",
        )

        self.assertFalse(
            recovery.valid(),
            "non-enum evidence basis must not be accepted as authoritative recovery evidence",
        )


if __name__ == "__main__":
    unittest.main()
