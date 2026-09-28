from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]


def test_web_console_does_not_ship_duplicate_typescript_engine():
    assert not (ROOT / "src/lib/metaoEngine.ts").exists()


def test_web_server_delegates_to_canonical_cli_and_is_read_only_by_default():
    server = (ROOT / "server.ts").read_text(encoding="utf-8")
    assert "METAO_CLI_BIN" in server
    assert "execFile(" in server
    assert "CLI_BIN" in server
    assert "METAO_WEB_MUTATIONS === '1'" in server
    assert "Custom mission submission is disabled" in server


def test_web_reads_do_not_hide_canonical_backend_failures():
    server = (ROOT / "server.ts").read_text(encoding="utf-8")
    forbidden_fallbacks = (
        ".catch(() => [])",
        ".catch(() => item)",
        "catch { return { ...runtime, disposition: 'ACTIVE' }; }",
    )
    for token in forbidden_fallbacks:
        assert token not in server


def test_browser_does_not_mint_governance_authority():
    app = (ROOT / "src/App.tsx").read_text(encoding="utf-8")
    modal = (ROOT / "src/components/NewMissionModal.tsx").read_text(encoding="utf-8")

    forbidden = (
        "trusted_verifiers",
        "authorized_authorities",
        "policy_bundle_id",
        "governance-authority",
    )
    for token in forbidden:
        assert token not in app
        assert token not in modal

    assert "/api/examples/quickstart-accepted" in app
    assert "/api/examples/policy-deny" in app


def test_web_server_owns_operator_identity():
    server = (ROOT / "server.ts").read_text(encoding="utf-8")
    assert "METAO_UI_ACTOR" in server
    assert "String(req.body?.approver" not in server
    assert "String(req.body?.actor" not in server
