from __future__ import annotations

import json
import urllib.error
import urllib.parse
import urllib.request
from typing import Any

from metao.durable import DurableExecutionSpec, DurableExecutionState, DurableStatus


_STATUS_MAP = {
    "RUNNING": DurableStatus.RUNNING,
    "PAUSED": DurableStatus.PAUSED,
    "COMPLETED": DurableStatus.COMPLETED,
    "FAILED": DurableStatus.FAILED,
    "TIMED_OUT": DurableStatus.TIMED_OUT,
    "TERMINATED": DurableStatus.TERMINATED,
}


class ConductorHttpAdapter:
    """Thin foundation adapter. No Conductor SDK types cross this boundary."""

    adapter_id = "conductor-http"
    adapter_version = "1"

    def __init__(self, base_url: str = "http://localhost:8080/api") -> None:
        self.base_url = base_url.rstrip("/")

    def _request(self, method: str, path: str, body: Any = None, *, expected=(200, 204), timeout=15):
        data = None if body is None else json.dumps(body).encode()
        request = urllib.request.Request(
            self.base_url + path,
            data=data,
            method=method,
            headers={"Content-Type": "application/json"} if data is not None else {},
        )
        try:
            with urllib.request.urlopen(request, timeout=timeout) as response:
                raw = response.read().decode()
                if response.status not in expected:
                    raise RuntimeError(f"Conductor HTTP {response.status}: {raw}")
                if not raw:
                    return None
                try:
                    return json.loads(raw)
                except json.JSONDecodeError:
                    return raw.strip('"')
        except urllib.error.HTTPError as exc:
            raw = exc.read().decode()
            raise RuntimeError(f"Conductor HTTP {exc.code}: {raw}") from exc

    def start(self, spec: DurableExecutionSpec) -> str:
        payload = {
            "name": spec.workflow_name,
            "workflowDef": {
                "ownerApp": "metao",
                "ownerEmail": "metao@example.invalid",
                "name": spec.workflow_name,
                "version": 1,
                "tasks": [
                    {
                        "name": spec.task_type,
                        "taskReferenceName": "work",
                        "type": "SIMPLE",
                        "inputParameters": {"payload": "${workflow.input.payload}"},
                        "taskDefinition": {
                            "name": spec.task_type,
                            "retryCount": spec.retry_count,
                            "retryLogic": "FIXED",
                            "retryDelaySeconds": 0,
                            "timeoutSeconds": spec.timeout_seconds,
                            "timeoutPolicy": "TIME_OUT_WF",
                            "responseTimeoutSeconds": spec.response_timeout_seconds,
                        },
                    }
                ],
                "outputParameters": {"result": "${work.output.result}"},
            },
            "input": {"payload": dict(spec.input)},
        }
        result = self._request("POST", "/workflow", payload)
        if not isinstance(result, str) or not result:
            raise RuntimeError("Conductor did not return a workflow id")
        return result

    def state(self, execution_id: str) -> DurableExecutionState:
        item = self._request("GET", f"/workflow/{urllib.parse.quote(execution_id)}?includeTasks=true")
        status = _STATUS_MAP.get(item["status"])
        if status is None:
            raise RuntimeError(f"unsupported Conductor status: {item['status']}")
        return DurableExecutionState(execution_id, status, item.get("output") or {})

    def pause(self, execution_id: str) -> None:
        self._request("PUT", f"/workflow/{urllib.parse.quote(execution_id)}/pause")

    def resume(self, execution_id: str) -> None:
        self._request("PUT", f"/workflow/{urllib.parse.quote(execution_id)}/resume")

    def cancel(self, execution_id: str) -> None:
        self._request("DELETE", f"/workflow/{urllib.parse.quote(execution_id)}")

    def poll_task(self, task_type: str, worker_id: str = "metao"):
        path = f"/tasks/poll/{urllib.parse.quote(task_type)}?workerid={urllib.parse.quote(worker_id)}"
        return self._request("GET", path, expected=(200, 204))

    def update_task(self, task: dict[str, Any], status: str, output: dict[str, Any] | None = None, reason: str = "") -> None:
        payload = {
            "workflowInstanceId": task["workflowInstanceId"],
            "taskId": task["taskId"],
            "status": status,
            "outputData": output or {},
        }
        if reason:
            payload["reasonForIncompletion"] = reason
        self._request("POST", "/tasks", payload)
