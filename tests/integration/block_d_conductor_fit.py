from __future__ import annotations

import json
import os
import signal
import subprocess
import time
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path

BASE = "http://localhost:8080/api"


def request(method: str, path: str, body=None, *, expected=(200, 204), timeout=15):
    data = None if body is None else json.dumps(body).encode()
    req = urllib.request.Request(
        BASE + path,
        data=data,
        method=method,
        headers={"Content-Type": "application/json"} if data is not None else {},
    )
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            raw = resp.read().decode()
            if resp.status not in expected:
                raise AssertionError(f"{method} {path}: {resp.status} {raw}")
            if not raw:
                return None
            try:
                return json.loads(raw)
            except json.JSONDecodeError:
                return raw.strip('"')
    except urllib.error.HTTPError as exc:
        raw = exc.read().decode()
        raise AssertionError(f"{method} {path}: {exc.code} {raw}") from exc


def wait_workflow(workflow_id: str, statuses: set[str], timeout=40):
    deadline = time.time() + timeout
    last = None
    while time.time() < deadline:
        last = request("GET", f"/workflow/{workflow_id}?includeTasks=true")
        if last["status"] in statuses:
            return last
        time.sleep(0.25)
    raise AssertionError(f"workflow {workflow_id} did not reach {statuses}; last={last}")


def poll_task(task_type: str, timeout=30):
    deadline = time.time() + timeout
    while time.time() < deadline:
        try:
            task = request("GET", f"/tasks/poll/{urllib.parse.quote(task_type)}?workerid=metao-fit", expected=(200, 204))
        except AssertionError:
            raise
        if task:
            return task
        time.sleep(0.25)
    raise AssertionError(f"no task polled for {task_type}")


def update_task(task, status: str, output=None, reason=None):
    payload = {
        "workflowInstanceId": task["workflowInstanceId"],
        "taskId": task["taskId"],
        "status": status,
        "outputData": output or {},
    }
    if reason:
        payload["reasonForIncompletion"] = reason
    return request("POST", "/tasks", payload)


def dynamic_simple(name: str, task_type: str, *, retry_count=0, timeout_seconds=60, response_timeout_seconds=60):
    return {
        "name": name,
        "workflowDef": {
            "ownerApp": "metao",
            "ownerEmail": "metao@example.invalid",
            "name": name,
            "version": 1,
            "tasks": [
                {
                    "name": task_type,
                    "taskReferenceName": "work",
                    "type": "SIMPLE",
                    "inputParameters": {"mission": "${workflow.input.mission}"},
                    "taskDefinition": {
                        "name": task_type,
                        "retryCount": retry_count,
                        "retryLogic": "FIXED",
                        "retryDelaySeconds": 0,
                        "timeoutSeconds": timeout_seconds,
                        "timeoutPolicy": "TIME_OUT_WF",
                        "responseTimeoutSeconds": response_timeout_seconds,
                    },
                }
            ],
            "outputParameters": {"result": "${work.output.result}"},
        },
        "input": {"mission": name},
    }


def start(payload):
    result = request("POST", "/workflow", payload)
    assert isinstance(result, str) and result, result
    return result


def scenario_happy_worker_and_state():
    wid = start(dynamic_simple("metao_fit_happy", "metao_fit_happy_task"))
    task = poll_task("metao_fit_happy_task")
    assert task["workflowInstanceId"] == wid
    update_task(task, "COMPLETED", {"result": "worker-real-path-ok"})
    wf = wait_workflow(wid, {"COMPLETED"})
    assert wf["output"]["result"] == "worker-real-path-ok"
    assert wf["tasks"][0]["status"] == "COMPLETED"
    return wid


def scenario_retry():
    wid = start(dynamic_simple("metao_fit_retry", "metao_fit_retry_task", retry_count=1))
    first = poll_task("metao_fit_retry_task")
    update_task(first, "FAILED", reason="intentional-fit-failure")
    second = poll_task("metao_fit_retry_task")
    assert second["workflowInstanceId"] == wid
    assert second["taskId"] != first["taskId"] or int(second.get("retryCount", 0)) >= 1
    update_task(second, "COMPLETED", {"result": "retry-ok"})
    wf = wait_workflow(wid, {"COMPLETED"})
    assert any(int(t.get("retryCount", 0)) >= 1 for t in wf["tasks"]), wf["tasks"]
    return wid


def scenario_timeout():
    wid = start(dynamic_simple(
        "metao_fit_timeout",
        "metao_fit_timeout_task",
        retry_count=0,
        timeout_seconds=2,
        response_timeout_seconds=1,
    ))
    task = poll_task("metao_fit_timeout_task")
    assert task["workflowInstanceId"] == wid
    wf = wait_workflow(wid, {"TIMED_OUT", "FAILED"}, timeout=20)
    assert wf["status"] in {"TIMED_OUT", "FAILED"}
    return wid


def scenario_pause_resume():
    wid = start(dynamic_simple("metao_fit_pause", "metao_fit_pause_task"))
    request("PUT", f"/workflow/{wid}/pause")
    paused = wait_workflow(wid, {"PAUSED"})
    assert paused["status"] == "PAUSED"
    request("PUT", f"/workflow/{wid}/resume")
    wait_workflow(wid, {"RUNNING"})
    task = poll_task("metao_fit_pause_task")
    update_task(task, "COMPLETED", {"result": "resume-ok"})
    wait_workflow(wid, {"COMPLETED"})
    return wid


def scenario_process_restart_preserves_state():
    wid = start(dynamic_simple("metao_fit_restart", "metao_fit_restart_task"))
    before = request("GET", f"/workflow/{wid}?includeTasks=true")
    assert before["status"] == "RUNNING"

    pid_file = Path("conductor.pid")
    assert pid_file.exists(), "workflow did not provide conductor.pid"
    pid = int(pid_file.read_text().strip())
    os.kill(pid, signal.SIGTERM)
    time.sleep(3)

    proc = subprocess.Popen(
        ["conductor", "server", "start", "latest"],
        stdout=open("conductor-restart.log", "ab"),
        stderr=subprocess.STDOUT,
        start_new_session=True,
    )
    pid_file.write_text(str(proc.pid))

    deadline = time.time() + 120
    while time.time() < deadline:
        try:
            request("GET", "/health", timeout=2)
            break
        except Exception:
            time.sleep(1)
    else:
        raise AssertionError("Conductor failed to restart")

    after = request("GET", f"/workflow/{wid}?includeTasks=true")
    assert after["workflowId"] == wid
    assert after["status"] == "RUNNING"
    task = poll_task("metao_fit_restart_task")
    assert task["workflowInstanceId"] == wid
    update_task(task, "COMPLETED", {"result": "restart-durable-ok"})
    wait_workflow(wid, {"COMPLETED"})
    return wid


def main():
    # Raw REST is deliberate: this is the thin foundation boundary and proves
    # metaO need not import Conductor SDK types into its Core.
    health = request("GET", "/health")
    print("HEALTH=PASS", health)
    ids = {
        "happy": scenario_happy_worker_and_state(),
        "retry": scenario_retry(),
        "timeout": scenario_timeout(),
        "pause_resume": scenario_pause_resume(),
        "restart": scenario_process_restart_preserves_state(),
    }
    print("CONDUCTOR_REAL_WORKFLOW=PASS")
    print("CONDUCTOR_REAL_WORKER=PASS")
    print("CONDUCTOR_STATE=PASS")
    print("CONDUCTOR_RETRY=PASS")
    print("CONDUCTOR_TIMEOUT=PASS")
    print("CONDUCTOR_PAUSE_RESUME=PASS")
    print("CONDUCTOR_PROCESS_RESTART=PASS")
    print("CORE_CONDUCTOR_SDK_IMPORT_REQUIRED=NO")
    print("WORKFLOW_IDS=" + json.dumps(ids, sort_keys=True))
    print("FOUNDATION_L5=PASS")


if __name__ == "__main__":
    main()
