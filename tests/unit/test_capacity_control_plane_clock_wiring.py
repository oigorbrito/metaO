import inspect
import unittest

from metao.control_plane import execute_mission_once


class CapacityControlPlaneClockWiringTests(unittest.TestCase):
    def test_execute_mission_once_forwards_mission_clock_to_capacity_selector(self):
        source = inspect.getsource(execute_mission_once)
        self.assertIn(
            "select_with_policy(\n        eligible,\n        selection_policy,\n        now_epoch=now_epoch,\n    )",
            source,
            "capacity recovery must use the mission clock, not an implicit wall clock",
        )


if __name__ == "__main__":
    unittest.main()
