# metaO

metaO is a meta-orchestrator / control plane for selecting, governing, supervising, and independently accepting the work of pluggable agent orchestrators.

Architecture and implementation decisions are evidence-driven and documented under `docs/`.

Current canonical baseline:

- [`docs/POST-MVP-OPERATIONAL-BASELINE-V1.md`](docs/POST-MVP-OPERATIONAL-BASELINE-V1.md)
- [`docs/ARCHITECTURE.md`](docs/ARCHITECTURE.md)
- [`docs/CAPABILITY-MAP.md`](docs/CAPABILITY-MAP.md)
- [`docs/REQUIREMENTS.md`](docs/REQUIREMENTS.md)
- [`docs/QUALITY-MODEL.md`](docs/QUALITY-MODEL.md)

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

## Quickstart (Operator CLI)

metaO provides a CLI for managing missions and runtimes. On Windows (PowerShell) or Linux:

1. **Install the package**:
   ```powershell
   pip install -e .
   ```

2. **Verify installation**:
   ```powershell
   metao --help
   ```

3. **Configure your runtime factory**:
   Specify a Python module and function that returns a `MissionOperator`.
   ```powershell
   $env:METAO_OPERATOR_FACTORY="my_app.factory:create_operator"
   # Or use --factory my_app.factory:create_operator on every command
   ```

4. **Diagnose environment readiness**:
   ```powershell
   metao doctor
   ```

5. **List available runtimes**:
   ```powershell
   metao runtimes
   ```

6. **Run the canonical policy-gated example**:
   ```powershell
   metao run examples/mission-policy-deny.json
   ```
   This example is intentionally denied by policy before runtime selection. A `BLOCKED` result proves the mission-file/CLI/governance path is working; it does **not** claim provider-backed execution or metaO acceptance.

7. **Check mission status and inspect**:
   ```powershell
   metao status quickstart-policy-deny
   metao inspect quickstart-policy-deny
   ```

## Python API Quickstart

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
