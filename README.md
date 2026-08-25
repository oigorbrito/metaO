# metaO

metaO is a meta-orchestrator / control plane for selecting, governing, supervising, and independently accepting the work of pluggable agent orchestrators.

Architecture and implementation decisions are evidence-driven and documented under `docs/`.

## Engineering workflow

metaO uses GitHub as the persistent engineering ledger and follows an **Issue-first** workflow:

```text
Project / Roadmap
-> Issue
-> Branch
-> Pull Request
-> Tests / Evidence
-> PASS / FAIL / BLOCKED
-> Merge
-> Close Issue
```

Operational rules and evidence discipline are documented in:

- [`docs/GITHUB-WORKFLOW.md`](docs/GITHUB-WORKFLOW.md) — Issue/branch/PR lifecycle, merge gates, failure classification, and architecture guardrails.
- [`docs/GITHUB-LABEL-TAXONOMY.md`](docs/GITHUB-LABEL-TAXONOMY.md) — canonical status/type/priority/area labels.
- [`docs/GITHUB-ACTIONS-SUPPORT-PACKET.md`](docs/GITHUB-ACTIONS-SUPPORT-PACKET.md) — current hosted-runner pre-step blocker evidence and escalation packet.

Evidence remains fail-closed:

```text
IMPLEMENTED != EXECUTED
EXECUTED != ACCEPTED
ORCHESTRATOR_DONE != METAO_ACCEPTED
```

## Quickstart

The public operator API takes an explicit durable-execution port. With a running Conductor instance:

```python
from metao import run, status
from metao.adapters.conductor_http import ConductorHttpAdapter
from metao.durable import DurableExecutionSpec

port = ConductorHttpAdapter("http://localhost:8080/api")
execution_id = run(
    port,
    DurableExecutionSpec(
        workflow_name="metao-example",
        task_type="agent_work",
        input={"objective": "complete the mission"},
        retry_count=2,
        timeout_seconds=60,
    ),
)
print(status(port, execution_id))
```

Framework adapters live outside Core. LangGraph-like runtimes are bridged through their `invoke` interface and CrewAI-like runtimes through `kickoff`; both normalize evidence at the metaO boundary.

## Evidence status

Passing repository tests prove the implemented contracts and integration boundaries exercised by those tests. They do not by themselves claim production readiness, external-provider availability, or cryptographic authenticity. See `docs/RELEASE-READINESS.md` for the current gate and remaining external validations.
