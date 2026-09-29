from __future__ import annotations

import argparse
from hashlib import sha256
from importlib.metadata import version as package_version
import json
import math
from pathlib import Path
import statistics
import sys
import time
from typing import Any

from agents import Agent as OpenAIAgent, Runner, set_tracing_disabled
from crewai import Agent, Crew, Process, Task
from crewai.llms.base_llm import BaseLLM
from langgraph.graph import END, START, StateGraph
from typing_extensions import TypedDict

sys.path.insert(0, str(Path("tests/integration").resolve()))
from _openai_agents_model import ScriptedModel, assistant_message  # noqa: E402

from metao.adapters.crewai import CrewAIOrchestratorAdapter
from metao.adapters.langgraph import LangGraphOrchestratorAdapter
from metao.adapters.openai_agents import OpenAIAgentsOrchestratorAdapter
from metao.core import ExecutionRequest, ExecutionStatus, Mission


OPENAI_AGENTS_VERSION = "0.20.0"
CREWAI_VERSION = "1.15.16"
LANGGRAPH_VERSION = "1.2.11"
REPETITIONS = 5
TASKS = {
    "coding_fixture": "Apply a deterministic coding-workload fixture.",
    "terminal_fixture": "Apply a deterministic terminal/runtime fixture.",
    "tool_api_fixture": "Apply a deterministic tool/API-use fixture.",
}


def digest(value: str) -> str:
    return "sha256:" + sha256(value.encode()).hexdigest()


class DeterministicCrewLLM(BaseLLM):
    response: str = "crewai-mechanical-matrix-ok"

    def call(
        self,
        messages: Any,
        tools: Any = None,
        callbacks: Any = None,
        available_functions: Any = None,
        from_task: Any = None,
        from_agent: Any = None,
        response_model: Any = None,
    ) -> str:
        return self.response


class GraphState(TypedDict, total=False):
    objective: str
    result: str


def build_graph():
    def step(state: GraphState):
        return {"result": "langgraph-mechanical-matrix-ok"}

    builder = StateGraph(GraphState)
    builder.add_node("run", step)
    builder.add_edge(START, "run")
    builder.add_edge("run", END)
    return builder.compile()


def build_crew() -> Crew:
    llm = DeterministicCrewLLM(model="metao-mechanical-matrix")
    agent = Agent(
        role="mechanical matrix worker",
        goal="Complete the deterministic fixture",
        backstory="Provider-free deterministic CrewAI fixture for metaO empirical evidence.",
        llm=llm,
        allow_delegation=False,
        verbose=False,
        max_iter=1,
    )
    task = Task(
        description="Execute this deterministic objective: {objective}",
        expected_output="One deterministic result.",
        agent=agent,
    )
    return Crew(
        agents=[agent],
        tasks=[task],
        process=Process.sequential,
        verbose=False,
        memory=False,
        cache=False,
    )


def build_adapters():
    steps = [
        [assistant_message(f"openai-agents-mechanical-{index}")]
        for index in range(REPETITIONS * len(TASKS))
    ]
    model = ScriptedModel(steps)
    openai_agent = OpenAIAgent(name="metaO mechanical matrix worker", model=model)
    set_tracing_disabled(True)

    return {
        "openai-agents-real": (
            OpenAIAgentsOrchestratorAdapter(
                Runner,
                openai_agent,
                orchestrator_id="openai-agents-real",
                version=OPENAI_AGENTS_VERSION,
            ),
            OPENAI_AGENTS_VERSION,
            "openai-agents-sdk-scripted-model",
        ),
        "crewai-real": (
            CrewAIOrchestratorAdapter(
                build_crew(),
                orchestrator_id="crewai-real",
                version=CREWAI_VERSION,
                config_id="mechanical-matrix-v1",
            ),
            CREWAI_VERSION,
            "crewai-sdk-base-llm",
        ),
        "langgraph-real": (
            LangGraphOrchestratorAdapter(
                build_graph(),
                orchestrator_id="langgraph-real",
                version=LANGGRAPH_VERSION,
                config_id="mechanical-matrix-v1",
            ),
            LANGGRAPH_VERSION,
            "langgraph-sdk-stategraph",
        ),
    }


def percentile95(values: list[float]) -> float:
    ordered = sorted(values)
    if len(ordered) == 1:
        return ordered[0]
    rank = 0.95 * (len(ordered) - 1)
    low = math.floor(rank)
    high = math.ceil(rank)
    if low == high:
        return ordered[low]
    fraction = rank - low
    return ordered[low] + (ordered[high] - ordered[low]) * fraction


def evidence_record(
    *,
    executor_id: str,
    executor_version: str,
    harness_id: str,
    task_family: str,
    observed_at_epoch: float,
    success_rate: float,
    mean_latency_ms: float,
    p95_latency_ms: float,
    latency_stddev_ms: float,
) -> dict[str, Any]:
    identity = f"{executor_id}|{executor_version}|{harness_id}|{task_family}|mechanical-v1"
    return {
        "evidence_id": f"mechanical-matrix:{executor_id}:{task_family}:v1",
        "executor_id": executor_id,
        "executor_version": executor_version,
        "task_family": task_family,
        "runtime_config_digest": digest(identity + "|runtime"),
        "tool_policy_digest": digest("provider-free:no-network-tools:no-provider-calls:v1"),
        "environment_id": "github-actions:ubuntu-24.04:python-3.13",
        "observed_at_epoch": observed_at_epoch,
        "source": "metao_execution",
        "raw_result_ref": f"artifact://mechanical-executor-matrix/{executor_id}/{task_family}",
        "sample_count": REPETITIONS,
        "metrics": [
            {"name": "success_rate", "value": success_rate, "unit": "ratio"},
            {"name": "latency_ms", "value": mean_latency_ms, "unit": "ms"},
            {"name": "latency_p95_ms", "value": p95_latency_ms, "unit": "ms"},
            {"name": "latency_stddev_ms", "value": latency_stddev_ms, "unit": "ms"},
        ],
        "harness_identity": harness_id,
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--commit", required=True)
    args = parser.parse_args()

    if package_version("openai-agents") != OPENAI_AGENTS_VERSION:
        raise SystemExit("unexpected openai-agents version")
    if package_version("crewai") != CREWAI_VERSION:
        raise SystemExit("unexpected CrewAI version")
    if package_version("langgraph") != LANGGRAPH_VERSION:
        raise SystemExit("unexpected LangGraph version")

    args.output_dir.mkdir(parents=True, exist_ok=True)
    adapters = build_adapters()
    raw_samples: list[dict[str, Any]] = []
    evidence_records: list[dict[str, Any]] = []
    observed_at = time.time()

    for executor_id, (adapter, executor_version, harness_id) in adapters.items():
        for task_family, objective in TASKS.items():
            latencies: list[float] = []
            successes = 0
            for index in range(REPETITIONS):
                request = ExecutionRequest(
                    execution_id=f"matrix:{executor_id}:{task_family}:{index}",
                    mission=Mission(
                        f"matrix-{executor_id}-{task_family}-{index}",
                        objective,
                        frozenset({"workflow"}),
                    ),
                    context={
                        "fixture_family": task_family,
                        "provider_calls_authorized": False,
                    },
                )
                started = time.perf_counter()
                result = adapter.execute(request)
                elapsed_ms = (time.perf_counter() - started) * 1000.0
                success = result.status is ExecutionStatus.SUCCEEDED
                successes += int(success)
                latencies.append(elapsed_ms)
                raw_samples.append(
                    {
                        "executor_id": executor_id,
                        "executor_version": executor_version,
                        "harness_id": harness_id,
                        "task_family": task_family,
                        "sample_index": index,
                        "status": result.status.value,
                        "latency_ms": round(elapsed_ms, 6),
                    }
                )

            success_rate = successes / REPETITIONS
            mean_latency = statistics.fmean(latencies)
            p95_latency = percentile95(latencies)
            stddev = statistics.pstdev(latencies)
            record = evidence_record(
                executor_id=executor_id,
                executor_version=executor_version,
                harness_id=harness_id,
                task_family=task_family,
                observed_at_epoch=observed_at,
                success_rate=success_rate,
                mean_latency_ms=mean_latency,
                p95_latency_ms=p95_latency,
                latency_stddev_ms=stddev,
            )
            evidence_records.append(record)
            canonical = dict(record)
            canonical.pop("harness_identity")
            path = args.output_dir / f"{executor_id}-{task_family}.observed.json"
            path.write_text(json.dumps(canonical, indent=2, sort_keys=True) + "\n", encoding="utf-8")

    if any(record["metrics"][0]["value"] != 1.0 for record in evidence_records):
        raise SystemExit("mechanical executor matrix contained failed samples")

    manifest = {
        "schema": "metao-mechanical-executor-matrix-v1",
        "commit": args.commit,
        "classification": "PROVIDER_FREE_REAL_SDK_RUNTIME_OVERHEAD",
        "repetitions_per_cell": REPETITIONS,
        "executors": {
            executor_id: {
                "version": executor_version,
                "harness_id": harness_id,
            }
            for executor_id, (_, executor_version, harness_id) in adapters.items()
        },
        "task_families": list(TASKS),
        "samples": raw_samples,
        "evidence_records": evidence_records,
        "claims": {
            "three_real_sdk_harnesses": "EXECUTED",
            "three_fixture_families": "EXECUTED",
            "repeated_trials": "EXECUTED",
            "success_latency_variance": "RECORDED",
            "canonical_observed_performance_records": "EMITTED",
            "provider_calls": "NOT_EXECUTED",
            "provider_cost": "NOT_MEASURED",
            "model_quality": "NOT_MEASURED",
            "cross_model_same_harness": "NOT_EXECUTED",
            "cross_harness_same_model": "NOT_EXECUTED",
        },
        "claim_boundary": [
            "REAL_SDK_RUNTIME != REAL_PROVIDER_MODEL",
            "HARNESS_OVERHEAD != TASK_QUALITY",
            "NO_PROVIDER_COST != ZERO_PROVIDER_COST",
            "MECHANICAL_MATRIX != COMPLETE_#620_MATRIX",
        ],
    }
    (args.output_dir / "manifest.json").write_text(
        json.dumps(manifest, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    print(json.dumps(manifest["claims"], sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
