import inspect
import unittest

from metao.control_plane import execute_mission_once


class CapacityControlPlaneClockWiringTests(unittest.TestCase):
    def test_execute_mission_once_forwards_mission_clock_to_capacity_selector(self):
        source = inspect.getsource(execute_mission_once)
        self.assertIn(
            "select_orchestrator(eligible, now_epoch=now_epoch)",
            source,
            "capacity recovery must use the mission clock, not an implicit wall clock",
        )


if __name__ == "__main__":
    unittest.main()
