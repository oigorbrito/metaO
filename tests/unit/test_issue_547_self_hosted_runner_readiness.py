from __future__ import annotations

import importlib.util
from pathlib import Path
from unittest import TestCase, mock


_SCRIPT = Path(__file__).resolve().parents[2] / "scripts" / "self_hosted_runner_readiness.py"
_SPEC = importlib.util.spec_from_file_location("self_hosted_runner_readiness", _SCRIPT)
assert _SPEC is not None and _SPEC.loader is not None
_module = importlib.util.module_from_spec(_SPEC)
_SPEC.loader.exec_module(_module)


class SelfHostedRunnerReadinessTests(TestCase):
    @mock.patch.object(_module.platform, "system", return_value="Linux")
    @mock.patch.object(_module.platform, "machine", return_value="x86_64")
    @mock.patch.object(_module.shutil, "which", return_value="/usr/bin/tool")
    def test_ready_machine_emits_bounded_non_secret_evidence(self, _which, _machine, _system):
        with mock.patch.object(_module.sys, "version_info", (3, 12, 1)):
            evidence = _module.evaluate_readiness()

        self.assertEqual(evidence["runner_readiness"], "PASS")
        self.assertEqual(
            evidence["required_labels"],
            ["self-hosted", "linux", "x64", "metao-project-pilot"],
        )
        self.assertFalse(evidence["registration_token_present"])
        self.assertFalse(evidence["repository_secrets_checked"])
        self.assertFalse(evidence["provider_calls_made"])
        self.assertFalse(evidence["credentials_emitted"])
        self.assertFalse(evidence["host_values_emitted"])
        self.assertFalse(evidence["pilot_operational_pass"])

    @mock.patch.object(_module.platform, "system", return_value="Linux")
    @mock.patch.object(_module.platform, "machine", return_value="aarch64")
    @mock.patch.object(_module.shutil, "which", return_value="/usr/bin/tool")
    def test_non_x64_machine_fails_closed(self, _which, _machine, _system):
        with mock.patch.object(_module.sys, "version_info", (3, 12, 1)):
            evidence = _module.evaluate_readiness()
        self.assertEqual(evidence["runner_readiness"], "FAIL")
        self.assertFalse(evidence["x64"])

    @mock.patch.object(_module.platform, "system", return_value="Linux")
    @mock.patch.object(_module.platform, "machine", return_value="x86_64")
    def test_missing_required_executable_fails_closed(self, _machine, _system):
        def which(name: str):
            return None if name == "ssh" else f"/usr/bin/{name}"

        with mock.patch.object(_module.shutil, "which", side_effect=which), mock.patch.object(
            _module.sys, "version_info", (3, 12, 1)
        ):
            evidence = _module.evaluate_readiness()
        self.assertEqual(evidence["runner_readiness"], "FAIL")
        self.assertFalse(evidence["required_executables"]["ssh"])
