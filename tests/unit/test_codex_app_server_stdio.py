import sys
import textwrap
import time
import unittest

from metao.adapters.codex_app_server import CodexAppServerOrchestratorAdapter
from metao.adapters.codex_app_server_stdio import CodexAppServerStdioTransport
from metao.core import ExecutionRequest, ExecutionStatus, Mission


def _request():
    return ExecutionRequest(
        "codex-stdio-exec",
        Mission("codex-stdio-mission", "exercise app server transport", frozenset({"coding"})),
    )


class CodexAppServerStdioTests(unittest.TestCase):
    def test_string_server_request_id_is_resolved_by_explicit_handler(self):
        fake_server = textwrap.dedent(
            '''
            import json
            import sys

            def send(value):
                sys.stdout.write(json.dumps(value, separators=(",", ":")) + "\\n")
                sys.stdout.flush()

            for line in sys.stdin:
                message = json.loads(line)
                method = message.get("method")
                request_id = message.get("id")
                if method == "initialize" and request_id is not None:
                    send({"id": request_id, "result": {"userAgent": "fake-codex"}})
                elif method == "initialized":
                    pass
                elif method == "thread/start":
                    send({"id": request_id, "result": {"thread": {"id": "thr-handler", "status": "idle"}}})
                elif method == "turn/start":
                    send({"id": request_id, "result": {"turn": {"id": "turn-handler", "status": "inProgress", "items": []}}})
                    send({"method": "item/commandExecution/requestApproval", "id": "server-request-1", "params": {"reason": "test"}})
                    resolution = json.loads(sys.stdin.readline())
                    if resolution.get("id") != "server-request-1":
                        raise SystemExit(21)
                    if resolution.get("result", {}).get("decision") != "decline":
                        raise SystemExit(22)
                    sys.stderr.write("server-request-resolved\\n")
                    sys.stderr.flush()
                    send({"method": "turn/completed", "params": {"turn": {"id": "turn-handler", "status": "completed", "items": [{"type": "agentMessage", "id": "a1", "text": "handler-ok"}]}}})
            '''
        )
        handled = []

        def handler(method, params):
            handled.append((method, dict(params or {})))
            return {"decision": "decline"}

        command = (sys.executable, "-u", "-c", fake_server)
        with CodexAppServerStdioTransport(
            command,
            server_request_handler=handler,
            stderr_tail_lines=20,
        ) as transport:
            adapter = CodexAppServerOrchestratorAdapter(
                request_fn=transport.request,
                notify_fn=transport.notify,
                read_notification_fn=transport.read_notification,
                max_notifications=16,
            )
            result = adapter.execute(_request())
            for _ in range(20):
                if "server-request-resolved" in transport.stderr_tail():
                    break
                time.sleep(0.005)
            tail = transport.stderr_tail()

        self.assertIs(result.status, ExecutionStatus.SUCCEEDED)
        self.assertEqual(result.output["result"], "handler-ok")
        self.assertEqual(
            handled,
            [("item/commandExecution/requestApproval", {"reason": "test"})],
        )
        self.assertIn("server-request-resolved", tail)


if __name__ == "__main__":
    unittest.main()
