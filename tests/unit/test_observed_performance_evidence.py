import unittest


class ObservedPerformanceImportSmokeTests(unittest.TestCase):
    def test_modules_import(self):
        from metao.observed_performance import ObservedPerformanceEvidence
        from metao.observed_performance_store import SQLiteObservedPerformanceStore

        self.assertIsNotNone(ObservedPerformanceEvidence)
        self.assertIsNotNone(SQLiteObservedPerformanceStore)


if __name__ == "__main__":
    unittest.main(verbosity=2)
