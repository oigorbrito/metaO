# Roadmap 7 WU03 — Three-Runtime Recovery Regression

Date: 2026-08-24

## Status

```text
WU03_IMPLEMENTATION = PREPARED
WU03_EXECUTION = PENDING
WU03_PASS = NOT CLAIMED
```

## Objective

Prove the Roadmap 7 recovery semantics across three heterogeneous real runtime SDKs without adding framework-specific recovery logic to metaO.

Pinned runtimes:

```text
OpenAI Agents SDK 0.21.1
CrewAI 1.15.16
LangGraph 1.2.11
```

The regression reuses the existing adapters, declarative catalog, certification lifecycle, runtime controls, durable mission store and approval path.

WU03 adds no production code.

## Deterministic provider-free scenario

The real SDKs are configured with deterministic local test boundaries:

### OpenAI Agents

Uses first-party `agents.testing.ScriptedModel`:

1. certification model call succeeds;
2. mission model call raises a deterministic runtime error.

### CrewAI

Uses a `BaseLLM` subclass:

1. certification call succeeds;
2. mission call raises a deterministic timeout.

No paid model provider is required.

### LangGraph

Uses a compiled real `StateGraph` with a deterministic local node.

It certifies successfully and remains unused during the first two automatic attempts.

## Expected recovery flow

```text
OpenAI Agents
  -> mission runtime failure
  -> FailureClass.RUNTIME
  -> REPLAN

CrewAI
  -> deterministic timeout
  -> FailureClass.TIMEOUT
  -> replan attempt limit reached
  -> durable WAITING_APPROVAL

human approve
  -> fresh live routing snapshot
  -> previously attempted runtimes excluded

LangGraph
  -> exactly one approved extra attempt
  -> independent evidence normalization
  -> metaO acceptance
  -> ACCEPTED
```

Expected durable attempt lineage:

```text
1 openai-agents-real FAILED
2 crewai-real         FAILED
3 langgraph-real      SUCCEEDED
```

The third runtime is not allowed to execute before human approval.

## Additional scenarios

### Quarantine after escalation

After the mission reaches `WAITING_APPROVAL`, the only remaining runtime is quarantined before resume.

Expected result:

```text
human approval remains valid
live quarantine remains authoritative
LangGraph does not execute
mission -> BLOCKED
reason -> approved_escalation_no_remaining_runtime
```

Approval therefore never overrides runtime control-plane health/quarantine authority.

### SQLite restart

The regression also prepares a full restart path:

1. certify three real runtimes;
2. execute OpenAI Agents + CrewAI failures;
3. persist `WAITING_APPROVAL` in SQLite;
4. restart operator;
5. reuse exact fresh certificates without SDK execution;
6. record human approval;
7. restart again;
8. reuse certificates again;
9. resume;
10. execute only the remaining LangGraph runtime;
11. preserve attempts `1,2,3` and the approval binding.

This verifies composition between:

- Roadmap 4 certificate reuse;
- Roadmap 5 freshness/revocation authority;
- Roadmap 6 third runtime;
- Roadmap 7 failure-aware replan and durable escalation.

## Architecture invariants

```text
PRODUCTION_CODE_CHANGED = NO
CORE_CHANGED = NO
ORCHESTRATOR_CONTRACT_CHANGED = NO
RUNTIME_FACTORY_CHANGED = NO
FRAMEWORK_SPECIFIC_REPLAN_LOGIC = NO
PAID_PROVIDER_REQUIRED = NO
```

All framework SDK imports remain in integration/sandbox code or adapters.

## Test file

`tests/integration/test_r7_wu03_three_runtime_recovery.py`

Prepared checks:

1. exact pinned runtime versions;
2. two heterogeneous real runtime failures -> human escalation -> third real runtime acceptance;
3. quarantine of the remaining runtime after wait blocks the approved continuation;
4. SQLite restart reuses certificates and preserves full real-runtime attempt lineage.

## Gate

The dedicated workflow installs:

```text
openai-agents==0.21.1
crewai==1.15.16
langgraph==1.2.11
```

Then runs:

1. Roadmap 7 WU03 real regression;
2. Roadmap 7 WU01/WU02 focused unit regressions;
3. Roadmap 6 three-runtime regression;
4. full unit suite;
5. SDK-neutral Core/control-plane boundary check.

## Execution blocker

GitHub-hosted Actions is still failing before job steps materialize. Therefore this regression is PREPARED only and no PASS/FAIL is claimed until an executable runner produces real output.
