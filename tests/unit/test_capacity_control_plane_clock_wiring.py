import inspect
import unittest

from metao.control_plane import execute_mission_once


class CapacityControlPlaneClockWiringTests(unittest.TestCase):
    def test_execute_mission_once_forwards_mission_clock_to_capacity_selector(self):
        source = inspect.getsource(execute_mission_once)
        self.assertIn(
            "selected = select_with_policy(",
            source,
            "control plane must route through the hard-gated policy seam",
        )
        self.assertIn(
            "now_epoch=now_epoch,",
            source,
            "capacity recovery must use the mission clock, not an implicit wall clock",
        )
        self.assertIn(
            "context=SelectionContext(",
            source,
            "contextual policies must receive mission-bound selection identity",
        )


if __name__ == "__main__":
    unittest.main()
