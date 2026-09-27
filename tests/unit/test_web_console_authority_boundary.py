from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]

def test_web_console_does_not_ship_duplicate_typescript_engine():
    assert not (ROOT / "src/lib/metaoEngine.ts").exists()

def test_web_server_delegates_to_canonical_cli_and_is_read_only_by_default():
    server = (ROOT / "server.ts").read_text(encoding="utf-8")
    assert "METAO_CLI_BIN" in server
    assert "execFile(CLI_BIN" in server
    assert "METAO_WEB_MUTATIONS === '1'" in server
    assert "Custom mission submission is disabled" in server

def test_custom_mission_ui_cannot_mint_governance_authority():
    modal = (ROOT / "src/components/NewMissionModal.tsx").read_text(encoding="utf-8")
    forbidden = ("policyAllowed", "trusted_verifiers", "authorized_authorities", "acceptance_decision")
    for token in forbidden:
        assert token not in modal
