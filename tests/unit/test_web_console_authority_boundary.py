from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[2]


class WebConsoleAuthorityBoundaryTests(unittest.TestCase):
    def test_web_console_does_not_ship_duplicate_typescript_engine(self):
        self.assertFalse((ROOT / "src/lib/metaoEngine.ts").exists())

    def test_web_server_delegates_to_canonical_cli_and_is_read_only_by_default(self):
        server = (ROOT / "server.ts").read_text(encoding="utf-8")
        self.assertIn("METAO_CLI_BIN", server)
        self.assertIn("execFile(", server)
        self.assertIn("CLI_BIN", server)
        self.assertIn("METAO_WEB_MUTATIONS === '1'", server)
        self.assertIn("Custom mission submission is disabled", server)

    def test_web_reads_do_not_hide_canonical_backend_failures(self):
        server = (ROOT / "server.ts").read_text(encoding="utf-8")
        forbidden_fallbacks = (
            ".catch(() => [])",
            ".catch(() => item)",
            "catch { return { ...runtime, disposition: 'ACTIVE' }; }",
        )
        for token in forbidden_fallbacks:
            self.assertNotIn(token, server)

    def test_browser_does_not_mint_governance_authority(self):
        app = (ROOT / "src/App.tsx").read_text(encoding="utf-8")
        modal = (ROOT / "src/components/NewMissionModal.tsx").read_text(
            encoding="utf-8"
        )
        forbidden = (
            "trusted_verifiers",
            "authorized_authorities",
            "policy_bundle_id",
            "governance-authority",
        )
        for token in forbidden:
            self.assertNotIn(token, app)
            self.assertNotIn(token, modal)

        self.assertIn("/api/examples/quickstart-accepted", app)
        self.assertIn("/api/examples/policy-deny", app)

    def test_web_server_owns_operator_identity(self):
        server = (ROOT / "server.ts").read_text(encoding="utf-8")
        self.assertIn("METAO_UI_ACTOR", server)
        self.assertNotIn("String(req.body?.approver", server)
        self.assertNotIn("String(req.body?.actor", server)


if __name__ == "__main__":
    unittest.main()
