# metaO

**Framework-neutral control plane for governing pluggable agent orchestrators without letting the orchestrator own policy, runtime qualification, recovery, or final acceptance.**

metaO exists for a specific problem: when multiple orchestrators/runtimes are available, the system that *does the work* should not automatically become the system that decides whether the work was authorized, healthy, verified, or accepted.

```text
Mission
  ↓
Policy / Budget
  ↓
Runtime admission / selection
  ↓
Orchestrator / runtime
  ↓
Evidence
  ↓
Independent acceptance
  ↓
Accept / Replan / Block
```

The central rule is:

```text
ORCHESTRATOR_DONE != METAO_ACCEPTED
```

## What metaO owns

- policy and budget authority;
- runtime admission and health;
- certification and revocation;
- mission supervision and durable state;
- fencing / restart / recovery boundaries;
- evidence normalization;
- independent acceptance;
- framework/runtime adapters behind a neutral core boundary.

## What metaO deliberately does not claim

metaO is **not** presented as a proven production platform merely because these mechanisms exist.

Current evidence includes qualified local/operator paths, integration tests, multiprocess/fault-injection slices, real runtime evidence for selected boundaries, and a deterministic clean-room quickstart.

That does **not** automatically establish:

- production-scale economics;
- broad external-provider reliability;
- superiority over simpler embedded governance;
- that every control-plane mechanism is necessary in every deployment.

The project treats those as separate empirical questions.

## Architecture position

metaO is intentionally above concrete orchestrators:

```text
                 metaO
                   │
       ┌───────────┼───────────┐
       ▼           ▼           ▼
   runtime A   runtime B   runtime C
       │           │           │
       └───────────┼───────────┘
                   ▼
             normalized evidence
                   ▼
          independent acceptance
```

Framework-specific SDKs belong behind adapters. Replacing an orchestrator should not require moving policy, budget, recovery, or acceptance authority into that orchestrator.

## Evidence status

The current capability map distinguishes implementation from the level of evidence supporting each capability.

Representative qualified areas include:

- framework-neutral contract;
- independent acceptance;
- governance / budget / approval;
- durable mission state;
- runtime admission / health;
- runtime certification / revocation;
- adapter boundaries;
- local release gates;
- Rust discovery / governed-execution composition;
- external-effect deduplication;
- multiprocess fencing;
- composed fault-injection/system-closure tests;
- canonical operator bootstrap and clean-room onboarding.

Some areas remain partial, specified, or externally blocked. In particular, external-provider/runtime evidence is not generalized beyond the exact paths exercised.

Canonical evidence view:

- [Capability map](docs/CAPABILITY-MAP.md)
- [Post-MVP operational baseline](docs/POST-MVP-OPERATIONAL-BASELINE-V1.md)
- [Architecture](docs/ARCHITECTURE.md)
- [Requirements](docs/REQUIREMENTS.md)
- [Quality model](docs/QUALITY-MODEL.md)
- [Document authority map](docs/DOCUMENT-AUTHORITY-MAP.md)

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

- [`AGENTS.md`](AGENTS.md) — concise agent entrypoint and authority router.
- [`docs/AGENT-HARNESS-ENGINEERING-GUIDE.md`](docs/AGENT-HARNESS-ENGINEERING-GUIDE.md) — empirically grounded instruction/harness authoring, progressive disclosure, anti-redundancy, and evaluation rules.
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

The repository includes a deterministic local example runtime so a clean clone can exercise the real operator bootstrap path without external provider credentials or network calls. The example is for onboarding and operability verification only; it is **not** production-runtime or provider-backed evidence.

Python 3.13 or newer is required.

1. **Install the package from the repository root**:

   ```console
   python -m pip install -e .
   ```

   On Windows, if `python` does not select Python 3.13+, use the corresponding launcher explicitly, for example `py -3.13 -m pip install -e .`.

2. **Verify the installed console script**:

   ```console
   metao --help
   ```

   The top-level help should include `doctor`, mission commands, and runtime commands.

3. **Configure the repository-owned quickstart runtime**.

   The quickstart uses the canonical declarative factory `metao.runtime_factory:create_operator`, the committed catalog `examples/runtime-catalog-quickstart.json`, and separate local SQLite state under `.metao/`.

   PowerShell:

   ```powershell
   $env:METAO_OPERATOR_FACTORY="metao.runtime_factory:create_operator"
   $env:METAO_RUNTIME_CATALOG="examples/runtime-catalog-quickstart.json"
   $env:METAO_RUNTIME_CONTROL_DB=".metao/runtime-control.db"
   $env:METAO_RUNTIME_CERTIFICATION_DB=".metao/runtime-certification.db"
   $env:METAO_RUNTIME_CERTIFICATION_REVOCATION_DB=".metao/runtime-certification-revocation.db"
   ```

   Linux/POSIX shell:

   ```sh
   export METAO_OPERATOR_FACTORY="metao.runtime_factory:create_operator"
   export METAO_RUNTIME_CATALOG="examples/runtime-catalog-quickstart.json"
   export METAO_RUNTIME_CONTROL_DB=".metao/runtime-control.db"
   export METAO_RUNTIME_CERTIFICATION_DB=".metao/runtime-certification.db"
   export METAO_RUNTIME_CERTIFICATION_REVOCATION_DB=".metao/runtime-certification-revocation.db"
   ```

4. **Diagnose bootstrap readiness**:

   ```console
   metao doctor
   ```

   For this committed quickstart configuration, `overall_status` should be `PASS` and `RUNTIME_CATALOG` should report `count=1`.

5. **List the admitted runtime**:

   ```console
   metao runtimes
   ```

   The result should contain the healthy local example runtime `quickstart-local`.

6. **Inspect the persisted runtime certification**:

   ```console
   metao runtime-certificates quickstart-local
   ```

   At least one certificate should report `passed: true` with probe execution id `quickstart-certification`.

7. **Run the committed accepted mission**:

   ```console
   metao run examples/mission-quickstart-accepted.json
   ```

   The expected mission state is `ACCEPTED`, with `acceptance_decision` equal to `ACCEPT` and `orchestrator_id` equal to `quickstart-local`.

8. **Verify persistence from separate CLI invocations**:

   ```console
   metao status quickstart-accepted
   metao inspect quickstart-accepted
   ```

   `status` should remain `ACCEPTED`. `inspect` should show execution status `SUCCEEDED`, output result `quickstart:quickstart mission`, and a non-null acceptance proof.

9. **Optional governance-only negative path**:

   ```console
   metao run examples/mission-policy-deny.json
   ```

   This second example is intentionally denied by policy before runtime selection. A `BLOCKED` result demonstrates that metaO governance remains authoritative before runtime execution.

### Re-running the quickstart

Mission and runtime state are durable under `.metao/`. Re-running a mission with the same mission id against the same database is intentionally rejected as a duplicate. To repeat the quickstart from a clean local state, remove `.metao/` first.

PowerShell:

```powershell
Remove-Item -Recurse -Force .metao
```

Linux/POSIX shell:

```sh
rm -rf .metao
```

For a real application/runtime, replace the example catalog entry with your own `RuntimePlugin` factory and keep the same `metao.runtime_factory:create_operator` composition path. Do not treat the committed `quickstart-local` runtime as a production runtime.

## Web Operator Console

The repository also contains a web operator console for observing and operating the canonical metaO control plane.

The console is a **presentation and adapter layer only**. It does not replace Core and must not mint or override metaO authority.

```text
WEB_CONSOLE != METAO_AUTHORITY
ORCHESTRATOR_DONE != METAO_ACCEPTED
```

The authority boundary is:

```text
React operator console
        |
        | HTTP / presentation DTOs
        v
server.ts web adapter
        |
        | delegates to the canonical metao CLI/backend
        v
metaO control plane
        |
        +-- policy and approval
        +-- runtime admission / quarantine / restore
        +-- certification and revocation
        +-- benchmark and observed evidence
        +-- mission supervision
        +-- independent acceptance
        +-- durable state and event ledger
```

The web layer may display canonical results and request governed operations, but it must not independently decide that a runtime is healthy, a certificate is valid, a policy is allowed, evidence is verified, or a mission is accepted.

### Run the console

First install and configure the Python backend as described in the Operator CLI quickstart above. Then install the web dependencies:

```console
npm install
```

Start the development server:

```console
npm run dev
```

By default, the web adapter is read-only for state-changing operations. To explicitly allow supported operator mutations in an authorized local environment, set:

PowerShell:

```powershell
$env:METAO_WEB_MUTATIONS="1"
npm run dev
```

Linux/POSIX shell:

```sh
export METAO_WEB_MUTATIONS=1
npm run dev
```

Optional adapter configuration:

- `METAO_CLI_BIN` — installed metaO CLI executable; defaults to `metao`.
- `METAO_DB` — canonical mission database path; defaults to `.metao/metao.db`.
- `METAO_UI_ACTOR` — operator identity recorded by supported backend mutations; defaults to `operator-ui`.

Supported console surfaces include missions, runtimes, runtime control, certificates, benchmarks/evidence, doctor diagnostics, and the event ledger.

Custom mission input is intentionally limited to **intent and budget**. The browser cannot declare policy approval, trusted verifiers, authorized authorities, or acceptance decisions. Until a backend-owned custom mission intake contract exists, arbitrary custom mission submission remains fail-closed.

The committed quickstart examples remain available through the console, but they execute the repository-owned canonical mission specifications under `examples/`; the browser does not generate their policy or acceptance authority.

## Python API Quickstart

The public durable-execution API takes an explicit durable-execution port. With a running Conductor instance:

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

This Python API example requires a separately running Conductor service; it is not part of the zero-network Operator CLI quickstart above.

Framework adapters live outside Core. LangGraph-like runtimes are bridged through their `invoke` interface and CrewAI-like runtimes through `kickoff`; both normalize evidence at the metaO boundary.

## Evidence status

Passing repository tests prove the implemented contracts and integration boundaries exercised by those tests. They do not by themselves claim production readiness, external-provider availability, or cryptographic authenticity. See `docs/RELEASE-READINESS.md` for the current gate and remaining external validations.
