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

## Canonical executable

The executable metaO surface today is the Python control-plane package defined in `pyproject.toml`:

- package name: `metao-control-plane`
- console command: `metao`, provided by `metao.entrypoint:main`
- supported Python version: `>=3.12`
- default durable state: SQLite at `.metao/metao.db`, override with `--db <path>`
- operator factory configuration: `METAO_OPERATOR_FACTORY` or `--factory module:function`

The Rust code under `experiments/rust-chassis-a/` is an experiment/chassis track, not the canonical operator quickstart.

## Quickstart (Operator CLI)

This quickstart is the canonical documented path for operating metaO from a checkout. Run the commands in order on Windows PowerShell:

1. **Install the Python package for local operation**:
   ```powershell
   python -m pip install -e .
   ```

2. **Verify that the installed console command is available**:
   ```powershell
   metao --help
   ```

   Expected command groups:
   ```text
   mission commands: run, status, inspect, list, events, approve, resume, cancel
   runtime commands: runtimes, runtime-quarantine, runtime-restore, runtime-history, runtime-certificates, runtime-certificate-revoke, runtime-certificate-revocations
   ```

3. **Configure the operator factory**:
   ```powershell
   $env:METAO_OPERATOR_FACTORY="metao.examples.readme_factory:create_operator"
   ```

   The factory spec must use `module:function` syntax. The callable must return a `metao.operator.MissionOperator`. You may also pass the same factory explicitly on commands that accept it:
   ```powershell
   metao doctor --factory metao.examples.readme_factory:create_operator
   metao run examples/readme_mission.json --factory metao.examples.readme_factory:create_operator
   ```

4. **Diagnose installation, database, factory, and runtime-catalog readiness**:
   ```powershell
   metao doctor
   ```

   `doctor` emits JSON. `overall_status` is `PASS` only when the package, database path, factory import, operator construction, and runtime catalog checks pass. Without a configured factory, `doctor` reports `NOT_CONFIGURED`; that is a configuration result, not a successful mission run.

5. **List configured runtimes**:
   ```powershell
   metao runtimes
   ```

   This command uses the configured factory and prints the runtime catalog with live/control health fields. It requires a factory-backed operator that exposes `runtime_entries()`.

6. **Run the first Mission**:
   ```powershell
   metao run examples/readme_mission.json
   ```

   `examples/readme_mission.json` is the packaged quickstart fixture. A mission file must be a JSON object with `mission`, `policy`, `budget`, and `acceptance_context` objects. The mission object must include `mission_id`, `objective`, and `required_capabilities`; use that `mission_id` in the status and inspect commands below.

7. **Observe status and inspect the audit record**:
   ```powershell
   metao status <mission_id>
   metao inspect <mission_id>
   ```

   `status` returns the current mission state and revision. `inspect` returns the auditable mission record, including attempted runtimes, execution status, acceptance decision, reasons, budget usage, and proof fields when present.

8. **Interpret runtime and metaO outcomes separately**:
   ```text
   runtime execution status SUCCEEDED != metaO mission status ACCEPTED
   ```

   `SUCCEEDED` is an execution status reported for a runtime attempt. `ACCEPTED` is a metaO mission status produced only after metaO evaluates policy, budget, required obligations, provenance/trust inputs, retry history, and the acceptance decision. A runtime can finish with `SUCCEEDED` while the mission remains `NOT_DONE`, `BLOCKED`, `WAITING_APPROVAL`, `FAILED`, or another non-accepted state.

## README quickstart gate

The README quickstart has an executable local gate:

```powershell
powershell -ExecutionPolicy Bypass -File .\scripts\run-readme-quickstart-gate.ps1
```

The gate creates an isolated Python 3.12 virtual environment outside the repository, installs the package through `pyproject.toml`, invokes the installed `metao` console command, configures a temporary factory, runs `doctor`, lists runtimes, executes a first mission, and verifies `status` plus cross-process `inspect`.

Evidence is written outside the repository:

```text
%LOCALAPPDATA%\metaO\readme-quickstart-evidence\readme-quickstart-<timestamp>.json
```

A release-quality README quickstart claim requires `clean_worktree = true`, every recorded command at `exit_code = 0`, `failure_count = 0`, and `overall = PASS`. A diagnostic run with `-AllowDirty` may expose defects, but it is not clean release evidence.

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
