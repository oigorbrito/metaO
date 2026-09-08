from __future__ import annotations

from io import StringIO
import unittest

from metao.entrypoint import main


class OperatorHelpSurfaceTests(unittest.TestCase):
    def test_top_level_help_lists_doctor(self) -> None:
        stdout = StringIO()
        stderr = StringIO()

        code = main(["--help"], stdout=stdout, stderr=stderr)

        self.assertEqual(code, 0)
        self.assertEqual(stderr.getvalue(), "")
        output = stdout.getvalue()
        self.assertIn("mission commands:", output)
        self.assertIn("doctor", output)
        self.assertIn("runtimes", output)


if __name__ == "__main__":
    unittest.main(verbosity=2)
