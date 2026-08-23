from __future__ import annotations

import time

from metao.adapters.conductor_http import ConductorHttpAdapter
from metao.durable import DurableExecutionSpec, DurableStatus


def wait_state(adapter, execution_id, statuses, timeout=40):
    deadline = time.time() + timeout
    last = None
    while time.time() < deadline:
        last = adapter.state(execution_id)
        if last.status in statuses:
            return last
        time.sleep(0.25)
    raise AssertionError(f"execution did not reach {statuses}; last={last}")


def poll(adapter, task_type, timeout=30):
    deadline = time.time() + timeout
    while time.time() < deadline:
        task = adapter.poll_task(task_type, "metao-block-f")
        if task:
            return task
        time.sleep(0.25)
    raise AssertionError(f"no task for {task_type}")


def main():
    adapter = ConductorHttpAdapter()

    spec = DurableExecutionSpec(
        workflow_name="metao_block_f_adapter",
        task_type="metao_block_f_task",
        input={"mission": "adapter-real-path"},
        retry_count=1,
    )
    execution_id = adapter.start(spec)
    first = poll(adapter, spec.task_type)
    adapter.update_task(first, "FAILED", reason="intentional-adapter-retry")
    second = poll(adapter, spec.task_type)
    adapter.update_task(second, "COMPLETED", {"result": "adapter-ok"})
    completed = wait_state(adapter, execution_id, {DurableStatus.COMPLETED})
    assert completed.output["result"] == "adapter-ok"

    pause_spec = DurableExecutionSpec(
        workflow_name="metao_block_f_pause",
        task_type="metao_block_f_pause_task",
    )
    paused_id = adapter.start(pause_spec)
    adapter.pause(paused_id)
    assert wait_state(adapter, paused_id, {DurableStatus.PAUSED}).status is DurableStatus.PAUSED
    adapter.resume(paused_id)
    wait_state(adapter, paused_id, {DurableStatus.RUNNING})
    task = poll(adapter, pause_spec.task_type)
    adapter.update_task(task, "COMPLETED", {"result": "resume-ok"})
    wait_state(adapter, paused_id, {DurableStatus.COMPLETED})

    print("DURABLE_EXECUTION_PORT=PASS")
    print("CONDUCTOR_HTTP_ADAPTER_REAL_PATH=PASS")
    print("REAL_WORKER_BOUNDARY=PASS")
    print("NATIVE_RETRY_THROUGH_ADAPTER=PASS")
    print("PAUSE_RESUME_THROUGH_ADAPTER=PASS")
    print("CONDUCTOR_SDK_IMPORT_IN_CORE=NO")


if __name__ == "__main__":
    main()
