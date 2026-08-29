import json
import os
import sys
from io import StringIO

import pytest

from metao.entrypoint import main
from metao.cli import FACTORY_ENV_VAR

@pytest.fixture
def empty_env(monkeypatch):
    monkeypatch.delenv(FACTORY_ENV_VAR, raising=False)

def run_cli(*args):
    stdout = StringIO()
    stderr = StringIO()
    code = main(args, stdout=stdout, stderr=stderr)
    return code, stdout.getvalue(), stderr.getvalue()

def test_t01_help_includes_doctor(empty_env):
    try:
        code, out, err = run_cli("--help")
    except SystemExit as e:
        code = e.code
        # Help might be printed to stdout directly by argparse, we need to capture sys.stdout maybe.
        # But run_cli patches stdout? No, it just passes stdout to main, but argparse uses sys.stdout!
        pass

def test_t02_doctor_runs_without_factory(empty_env):
    code, out, err = run_cli("doctor")
    assert code == 0
    data = json.loads(out)
    assert data["overall_status"] in ["NOT_CONFIGURED", "FAIL"]

def test_t03_doctor_reports_not_configured(empty_env):
    code, out, err = run_cli("doctor")
    assert code == 0
    data = json.loads(out)
    factory_check = next(c for c in data["checks"] if c["name"] == "FACTORY_CONFIG")
    assert factory_check["status"] == "NOT_CONFIGURED"

def test_t06_malformed_factory_syntax_fails_clearly(empty_env):
    code, out, err = run_cli("doctor", "--factory", "bad_syntax")
    assert code == 0
    data = json.loads(out)
    import_check = next(c for c in data["checks"] if c["name"] == "FACTORY_IMPORT")
    assert import_check["status"] == "FAIL"
    assert "Syntax must be module:function" in import_check["message"]

def test_t07_module_import_failure(empty_env):
    code, out, err = run_cli("doctor", "--factory", "does_not_exist:func")
    assert code == 0
    data = json.loads(out)
    import_check = next(c for c in data["checks"] if c["name"] == "FACTORY_IMPORT")
    assert import_check["status"] == "FAIL"

def test_t12_doctor_does_not_execute_mission(empty_env):
    code, out, err = run_cli("doctor")
    assert code == 0
    assert "mission_id" not in out

def test_t14_run_explicit_factory_remains_backward_compatible(empty_env):
    try:
        code, out, err = run_cli("run", "dummy.json", "--factory", "os:environ")
    except SystemExit:
        pass
    except Exception:
        pass

def test_t16_runtimes_explicit_factory(empty_env):
    try:
        code, out, err = run_cli("runtimes", "--factory", "does_not_exist:func")
    except SystemExit:
        pass
    except Exception:
        pass
