from __future__ import annotations

import unittest

from scripts.materialize_openai_agents_runtime_requirements import (
    normalize_name,
    render_requirements,
    runtime_closure,
)


class OpenAIAgentsRuntimeRequirementsTests(unittest.TestCase):
    def test_runtime_closure_preserves_conditional_dependency_marker(self) -> None:
        lock = {
            "package": [
                {
                    "name": "openai-agents",
                    "version": "0.20.0",
                    "dependencies": [
                        {"name": "mcp"},
                    ],
                },
                {
                    "name": "mcp",
                    "version": "2.0.0",
                    "source": {"registry": "https://pypi.org/simple"},
                    "wheels": [{"hash": "sha256:" + "1" * 64}],
                    "dependencies": [
                        {"name": "pywin32", "marker": "sys_platform == 'win32'"},
                    ],
                },
                {
                    "name": "pywin32",
                    "version": "311",
                    "source": {"registry": "https://pypi.org/simple"},
                    "wheels": [{"hash": "sha256:" + "2" * 64}],
                },
            ]
        }
        packages, markers = runtime_closure(lock)
        self.assertEqual(
            {"sys_platform == 'win32'"},
            markers[(normalize_name("pywin32"), "311")],
        )
        rendered = render_requirements(packages, markers)
        self.assertIn("pywin32==311 ; (sys_platform == 'win32')", rendered)

    def test_ambiguous_dependency_without_version_fails_closed(self) -> None:
        lock = {
            "package": [
                {
                    "name": "openai-agents",
                    "version": "0.20.0",
                    "dependencies": [{"name": "starlette"}],
                },
                {
                    "name": "starlette",
                    "version": "0.47.2",
                    "source": {"registry": "https://pypi.org/simple"},
                    "wheels": [{"hash": "sha256:" + "3" * 64}],
                },
                {
                    "name": "starlette",
                    "version": "1.3.1",
                    "source": {"registry": "https://pypi.org/simple"},
                    "wheels": [{"hash": "sha256:" + "4" * 64}],
                },
            ]
        }
        with self.assertRaises(SystemExit):
            runtime_closure(lock)


if __name__ == "__main__":
    unittest.main()
