from __future__ import annotations

import json
from io import StringIO
from pathlib import Path
import tempfile
import unittest

from metao.cli import _load_run_spec
from metao.entrypoint import main


factory_calls = 0


def forbidden_factory(*, store):
    global factory_calls
    factory_calls += 1
    raise AssertionError("factory must not be invoked for invalid mission input")


def base_payload() -> dict:
    return {
        "mission": {
            "mission_id": "numeric-types",
            "objective": "validate numeric JSON contract",
            "required_capabilities": [],
        },
        "policy": {
            "policy_bundle_id": "policy-numeric",
            "allowed": False,
            "require_human": False,
            "reason": "numeric-contract-test",
        },
        "budget": {
            "money_limit": 1.5,
            "token_limit": 10,
            "wall_time_limit_s": 2,
            "verifier_attempt_limit": 1,
        },
        "acceptance_context": {
            "subject_id": "subject",
            "subject_state_id": "state",
            "verification_context_id": "verification",
            "policy_bundle_id": "policy-numeric",
            "required_obligations": [],
            "trusted_verifiers": [],
            "trusted_provenance_roots": [],
            "authorized_authorities": [],
        },
        "now_epoch": 3,
        "max_attempts": 2,
    }


class MissionJsonNumericTypeTests(unittest.TestCase):
    def setUp(self) -> None:
        global factory_calls
        factory_calls = 0

    def _run_invalid(self, mutate) -> dict:
        payload = base_payload()
        mutate(payload)
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            mission_file = root / "mission.json"
            db_path = root / "metao.db"
            mission_file.write_text(json.dumps(payload), encoding="utf-8")
            stdout = StringIO()
            stderr = StringIO()
            code = main(
                (
                    "--db",
                    str(db_path),
                    "run",
                    str(mission_file),
                    "--factory",
                    f"{__name__}:forbidden_factory",
                ),
                stdout=stdout,
                stderr=stderr,
            )
            self.assertEqual(code, 2)
            self.assertEqual(stdout.getvalue(), "")
            self.assertFalse(db_path.exists())
            self.assertEqual(factory_calls, 0)
            return json.loads(stderr.getvalue())

    def test_bool_is_not_accepted_as_budget_number(self) -> None:
        error = self._run_invalid(lambda payload: payload["budget"].__setitem__("money_limit", True))
        self.assertEqual(error["error"], "CLIInputError")
        self.assertEqual(error["message"], "budget requires numeric money/token/wall-time/verifier limits")

    def test_numeric_string_is_not_accepted_as_budget_integer(self) -> None:
        error = self._run_invalid(lambda payload: payload["budget"].__setitem__("token_limit", "10"))
        self.assertEqual(error["error"], "CLIInputError")
        self.assertEqual(error["message"], "budget requires numeric money/token/wall-time/verifier limits")

    def test_fractional_value_is_not_truncated_for_integer_field(self) -> None:
        error = self._run_invalid(lambda payload: payload["budget"].__setitem__("verifier_attempt_limit", 1.5))
        self.assertEqual(error["error"], "CLIInputError")
        self.assertEqual(error["message"], "budget requires numeric money/token/wall-time/verifier limits")

    def test_bool_and_fractional_execution_fields_are_rejected(self) -> None:
        error = self._run_invalid(lambda payload: payload.__setitem__("now_epoch", True))
        self.assertEqual(error["error"], "CLIInputError")
        self.assertEqual(error["message"], "now_epoch/max_attempts must be numeric")

        error = self._run_invalid(lambda payload: payload.__setitem__("max_attempts", 2.5))
        self.assertEqual(error["error"], "CLIInputError")
        self.assertEqual(error["message"], "now_epoch/max_attempts must be numeric")

    def test_valid_json_integer_and_float_values_are_preserved(self) -> None:
        payload = base_payload()
        payload["budget"]["money_limit"] = 2
        payload["budget"]["wall_time_limit_s"] = 2.5
        payload["now_epoch"] = 4
        with tempfile.TemporaryDirectory() as tmp:
            mission_file = Path(tmp) / "mission.json"
            mission_file.write_text(json.dumps(payload), encoding="utf-8")
            spec = _load_run_spec(mission_file)
        self.assertEqual(spec["budget"].money_limit, 2.0)
        self.assertEqual(spec["budget"].token_limit, 10)
        self.assertEqual(spec["budget"].wall_time_limit_s, 2.5)
        self.assertEqual(spec["budget"].verifier_attempt_limit, 1)
        self.assertEqual(spec["now_epoch"], 4.0)
        self.assertEqual(spec["max_attempts"], 2)


if __name__ == "__main__":
    unittest.main(verbosity=2)
