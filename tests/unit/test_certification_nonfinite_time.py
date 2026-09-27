from __future__ import annotations

import unittest

from metao.runtime_certification import (
    RuntimeCertification,
    certificate_identity,
    is_certificate_fresh,
)
from metao.runtime_factory import (
    RuntimeCatalogConfigError,
    _certificate_max_age_seconds,
    _certification_now_epoch,
)


class CertificationNonFiniteTimeTests(unittest.TestCase):
    @staticmethod
    def valid_certificate(*, certified_at_epoch: float = 100.0) -> RuntimeCertification:
        return RuntimeCertification(
            certificate_id="runtime:v1:probe:100.000000",
            orchestrator_id="runtime",
            runtime_version="v1",
            probe_execution_id="probe",
            passed=True,
            failed_checks=(),
            checks_digest="digest",
            total_checks=1,
            certified_at_epoch=certified_at_epoch,
        )

    def test_non_finite_certificate_time_is_rejected(self) -> None:
        for value in (float("nan"), float("inf"), float("-inf")):
            with self.subTest(value=value):
                with self.assertRaisesRegex(ValueError, "runtime certification time must be finite"):
                    self.valid_certificate(certified_at_epoch=value)

    def test_non_finite_certificate_identity_time_is_rejected(self) -> None:
        for value in (float("nan"), float("inf"), float("-inf")):
            with self.subTest(value=value):
                with self.assertRaisesRegex(ValueError, "runtime certification time must be finite"):
                    certificate_identity(
                        "runtime",
                        "v1",
                        "probe",
                        certified_at_epoch=value,
                    )

    def test_non_finite_current_time_is_rejected(self) -> None:
        certificate = self.valid_certificate()
        for value in (float("nan"), float("inf"), float("-inf")):
            with self.subTest(value=value):
                with self.assertRaisesRegex(ValueError, "current certification time must be finite"):
                    is_certificate_fresh(
                        certificate,
                        now_epoch=value,
                        max_age_seconds=20.0,
                    )

    def test_non_finite_max_age_is_rejected(self) -> None:
        certificate = self.valid_certificate()
        for value in (float("nan"), float("inf"), float("-inf")):
            with self.subTest(value=value):
                with self.assertRaisesRegex(ValueError, "certificate max age must be finite"):
                    is_certificate_fresh(
                        certificate,
                        now_epoch=110.0,
                        max_age_seconds=value,
                    )

    def test_catalog_rejects_non_finite_max_age_and_clock(self) -> None:
        for value in (float("nan"), float("inf"), float("-inf")):
            with self.subTest(value=value):
                entry = {
                    "certification": {
                        "mode": "required",
                        "max_age_seconds": value,
                    }
                }
                with self.assertRaisesRegex(
                    RuntimeCatalogConfigError,
                    "certification.max_age_seconds must be finite",
                ):
                    _certificate_max_age_seconds(entry)
                with self.assertRaisesRegex(
                    RuntimeCatalogConfigError,
                    "certification current time must be finite",
                ):
                    _certification_now_epoch(value)

    def test_finite_freshness_semantics_are_preserved(self) -> None:
        certificate = self.valid_certificate()
        self.assertTrue(
            is_certificate_fresh(
                certificate,
                now_epoch=110.0,
                max_age_seconds=20.0,
            )
        )
        self.assertFalse(
            is_certificate_fresh(
                certificate,
                now_epoch=110.0,
                max_age_seconds=5.0,
            )
        )
        self.assertEqual(
            _certificate_max_age_seconds(
                {"certification": {"mode": "required", "max_age_seconds": 20}}
            ),
            20.0,
        )
        self.assertEqual(_certification_now_epoch(110.0), 110.0)


if __name__ == "__main__":
    unittest.main(verbosity=2)
