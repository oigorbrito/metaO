from __future__ import annotations

import importlib.util
from pathlib import Path

import pytest


SCRIPT = Path(__file__).resolve().parents[1] / "scripts" / "project_multi_provider_preflight.py"
SPEC = importlib.util.spec_from_file_location("project_multi_provider_preflight", SCRIPT)
assert SPEC is not None and SPEC.loader is not None
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)


def test_presence_flag_accepts_only_literal_one(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("METAO_OPENAI_CREDENTIAL_PRESENT", "1")
    MODULE._require_presence("METAO_OPENAI_CREDENTIAL_PRESENT")

    for value in ("", "0", "true", "yes", "secret-value"):
        monkeypatch.setenv("METAO_OPENAI_CREDENTIAL_PRESENT", value)
        with pytest.raises(RuntimeError, match="presence flag missing"):
            MODULE._require_presence("METAO_OPENAI_CREDENTIAL_PRESENT")


def test_provider_secret_names_are_not_preflight_required_inputs() -> None:
    assert "METAO_OPENAI_API_KEY" not in MODULE._PROVIDER_PRESENCE
    assert "METAO_GEMINI_API_KEY" not in MODULE._PROVIDER_PRESENCE
    assert MODULE._PROVIDER_PRESENCE == (
        "METAO_OPENAI_CREDENTIAL_PRESENT",
        "METAO_GEMINI_CREDENTIAL_PRESENT",
    )


def test_ssh_configuration_remains_separate_from_provider_presence() -> None:
    assert "METAO_SSH_SMOKE_SOURCE_HOST" in MODULE._REQUIRED_SSH
    assert "METAO_SSH_SMOKE_DESTINATION_HOST" in MODULE._REQUIRED_SSH
    assert all("API_KEY" not in name for name in MODULE._REQUIRED_SSH)
