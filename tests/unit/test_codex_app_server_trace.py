import unittest

from metao.adapters.codex_app_server import CodexAppServerOrchestratorAdapter, normalize_evidence
from metao.core import ExecutionRequest, ExecutionStatus, Mission


class _Rpc:
    def __init__(self):
        self.calls = []
        self.notifications = [
            {
                "method": "item/completed",
                "params": {
                    "turnId": "other-turn",
                    "item": {"type": "commandExecution", "id": "ignore"},
                },
            },
            {
                "method": "item/completed",
                "params": {
                    "turnId": "turn-trace",
                    "item": {
                        "type": "commandExecution",
                        "id": "cmd-1",
                        "status": "completed",
                        "exitCode": 0,
                    },
                },
            },
            {
                "method": "turn/diff/updated",
                "params": {
                    "turnId": "turn-trace",
                    "diff": "--- a/file.py\n+++ b/file.py\n@@\n-old\n+new\n",
                },
            },
            {
                "method": "item/completed",
                "params": {
                    "turnId": "turn-trace",
                    "item": {
                        "type": "fileChange",
                        "id": "change-1",
                        "status": "completed",
                        "changes": [{"path": "file.py", "kind": "update"}],
                    },
                },
            },
            {
                "method": "turn/completed",
                "params": {
                    "turn": {
                        "id": "turn-trace",
                        "status": "completed",
                        "items": [
                            {
                                "type": "agentMessage",
                                "id": "agent-1",
                                "text": "trace-ok",
                            }
                        ],
                    }
                },
            },
        ]

    def request(self, method, params=None):
        self.calls.append((method, params))
        if method == "initialize":
            return {"userAgent": "fake"}
        if method == "thread/start":
            return {"thread": {"id": "thr-trace", "status": "idle"}}
        if method == "turn/start":
            return {"turn": {"id": "turn-trace", "status": "inProgress", "items": []}}
        raise AssertionError(f"unexpected RPC method: {method}")

    def notify(self, method, params=None):
        self.calls.append((method, params))

    def read_notification(self):
        return self.notifications.pop(0)


class CodexAppServerTraceTests(unittest.TestCase):
    def test_completed_items_and_latest_diff_are_bound_into_output_evidence(self):
        rpc = _Rpc()
        adapter = CodexAppServerOrchestratorAdapter(
            request_fn=rpc.request,
            notify_fn=rpc.notify,
            read_notification_fn=rpc.read_notification,
            max_notifications=16,
        )
        request = ExecutionRequest(
            "trace-exec",
            Mission("trace-mission", "modify file.py", frozenset({"coding"})),
            {
                "obligation_id": "execution_result",
                "subject_id": "subject-trace",
                "subject_state_id": "state-trace",
                "verification_context_id": "verify-trace",
                "policy_bundle_id": "policy-trace",
                "verifier_id": "adapter-observer",
                "authority_id": "metao-runtime",
            },
        )

        result = adapter.execute(request)

        self.assertIs(result.status, ExecutionStatus.SUCCEEDED)
        self.assertEqual(result.output["result"], "trace-ok")
        items = result.output["completed_items"]
        self.assertEqual([item["id"] for item in items], ["cmd-1", "change-1"])
        self.assertEqual(items[0]["exitCode"], 0)
        self.assertEqual(items[1]["changes"][0]["path"], "file.py")
        self.assertIn("+new", result.output["diff"])
        self.assertNotIn("ignore", repr(result.output))

        first = normalize_evidence(
            request=request,
            orchestrator_id=adapter.descriptor.orchestrator_id,
            adapter_version=adapter.descriptor.version,
            output=result.output,
        )
        mutated = dict(result.output)
        mutated["diff"] = mutated["diff"] + "# changed\n"
        second = normalize_evidence(
            request=request,
            orchestrator_id=adapter.descriptor.orchestrator_id,
            adapter_version=adapter.descriptor.version,
            output=mutated,
        )
        self.assertNotEqual(first.payload_digest, second.payload_digest)


if __name__ == "__main__":
    unittest.main()
