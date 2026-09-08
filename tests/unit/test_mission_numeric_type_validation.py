from __future__ import annotations

from copy import deepcopy
import json
from io import StringIO
from pathlib import Path
import tempfile
import unittest

from metao.catalog import OrchestratorCatalog
from metao.core import OrchestratorRegistry
from metao.entrypoint import main
from metao.runtime_factory import RuntimeCatalogOperator


_FACTORY_CALLS = 0


def counting_operator_factory(*, store):
    global _FACTORY_CALLS
    _FACTORY_CALLS += 1
    registry = OrchestratorRegistry()
    catalog = OrchestratorCatalog(registry)
    return RuntimeCatalogOperator(registry=registry, catalog=catalog, store=store)


def valid_mission_payload() -> dict:
    return {
        "mission": {
            "mission_id": "numeric-type-probe",
            "objective": "reject silent numeric coercion",
            "required_capabilities": [],
        },
        "policy": {
            "policy_bundle_id": "policy-v1",
            "allowed": False,
            "require_human": False,
        },
        "budget": {
            "money_limit": 1.0,
            "token_limit": 10,
            "wall_time_limit_s": 1.0,
            "verifier_attempt_limit": 1,
        },
        "acceptance_context": {
            "subject_id": "subject",
            "subject_state_id": "state",
            "verification_context_id": "verification",
            "policy_bundle_id": "policy-v1",
            "required_obligations": [],
            "trusted_verifiers": [],
            "trusted_provenance_roots": [],
            "authorized_authorities": [],
        },
        "now_epoch": 0.0,
        "max_attempts": 1,
    }


class MissionNumericTypeValidationTests(unittest.TestCase):
    def run_invalid_payload(self, payload: dict) -> tuple[dict, bool, int]:
        global _FACTORY_CALLS
        _FACTORY_CALLS = 0
        factory_spec = f"{__name__}:counting_operator_factory"

        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            mission_file = root / "mission.json"
            mission_file.write_text(json.dumps(payload), encoding="utf-8")
            db_path = root / "metao.db"
            stdout = StringIO()
            stderr = StringIO()
            code = main(
                [
                    "--db",
                    str(db_path),
                    "run",
                    str(mission_file),
                    "--factory",
                    factory_spec,
                ],
                stdout=stdout,
                stderr=stderr,
            )
            db_exists = db_path.exists()

        self.assertEqual(code, 2)
        self.assertEqual(stdout.getvalue(), "")
        return json.loads(stderr.getvalue()), db_exists, _FACTORY_CALLS

    def test_invalid_numeric_types_are_rejected_before_side_effects(self) -> None:
        cases = (
            ("boolean-money", ("budget", "money_limit"), True),
            ("numeric-string-token", ("budget", "token_limit"), "10"),
            ("fractional-token", ("budget", "token_limit"), 1.5),
            ("fractional-verifier-limit", ("budget", "verifier_attempt_limit"), 1.5),
            ("numeric-string-now", ("now_epoch",), "1"),
            ("fractional-max-attempts", ("max_attempts",), 1.5),
            ("boolean-max-attempts", ("max_attempts",), True),
        )

        for name, path, invalid_value in cases:
            with self.subTest(name=name):
                payload = deepcopy(valid_mission_payload())
                target = payload
                for key in path[:-1]:
                    target = target[key]
                target[path[-1]] = invalid_value

                error, db_exists, factory_calls = self.run_invalid_payload(payload)
                self.assertEqual(error["error"], "CLIInputError")
                self.assertFalse(db_exists)
                self.assertEqual(factory_calls, 0)


if __name__ == "__main__":
    unittest.main(verbosity=2)
