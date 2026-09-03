# Roadmap 7 WU03 — Three-Runtime Recovery Regression

Date: 2026-08-24

## Status

```text
WU03_IMPLEMENTATION = PREPARED
WU03_COMPATIBILITY_CORRECTION = APPLIED
WU03_EXECUTION_AFTER_FIX = PENDING
WU03_PASS = NOT CLAIMED
```

## Objective

Prove Roadmap 7 recovery semantics across three heterogeneous real runtime SDKs without adding framework-specific recovery logic to metaO.

Active pinned runtimes:

```text
OpenAI Agents SDK 0.20.0
CrewAI 1.15.16
LangGraph 1.2.11
```

The originally prepared OpenAI Agents 0.21.1 pin was superseded after the real local resolver proved it incompatible with CrewAI 1.15.16. See `docs/OPENAI-AGENTS-COMPATIBILITY-CORRECTION.md`.

The regression reuses existing adapters, declarative catalog, certification lifecycle, runtime controls, durable mission store and approval path. WU03 adds no production code.

## Deterministic provider-free scenario

### OpenAI Agents

Uses `tests/integration/_openai_agents_model.py`, a test-only deterministic implementation of the OpenAI Agents 0.20.0 public `Model` interface:

1. certification model call succeeds;
2. mission model call raises a deterministic runtime error.

### CrewAI

Uses a deterministic `BaseLLM` subclass:

1. certification call succeeds;
2. mission call raises a deterministic timeout.

### LangGraph

Uses a compiled real `StateGraph` with a deterministic local node. It certifies successfully and remains unused during the first two automatic attempts.

No paid model provider is required.

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

The third runtime cannot execute before human approval.

## Additional scenarios

### Quarantine after escalation

After `WAITING_APPROVAL`, quarantine the only remaining runtime before resume.

Expected:

```text
human approval remains valid
live quarantine remains authoritative
LangGraph does not execute
mission -> BLOCKED
reason -> approved_escalation_no_remaining_runtime
```

Approval never overrides runtime health/quarantine authority.

### SQLite restart

Prepared restart path:

1. certify three real runtimes;
2. execute OpenAI Agents + CrewAI failures;
3. persist `WAITING_APPROVAL` in SQLite;
4. restart operator;
5. reuse exact fresh certificates without SDK execution;
6. record human approval;
7. restart again;
8. reuse certificates again;
9. resume;
10. execute only remaining LangGraph;
11. preserve attempts `1,2,3` and approval binding.

This composes Roadmap 4 certificate reuse, Roadmap 5 freshness/revocation authority, Roadmap 6 third runtime, and Roadmap 7 failure-aware replan/durable escalation.

## Architecture invariants

```text
PRODUCTION_CODE_CHANGED = NO
CORE_CHANGED = NO
ORCHESTRATOR_CONTRACT_CHANGED = NO
RUNTIME_FACTORY_CHANGED = NO
FRAMEWORK_SPECIFIC_REPLAN_LOGIC = NO
PAID_PROVIDER_REQUIRED = NO
```

Framework SDK imports remain in integration/sandbox code or adapters.

## Test file

`tests/integration/test_r7_wu03_three_runtime_recovery.py`

Prepared checks:

1. exact active runtime versions;
2. two heterogeneous real runtime failures -> human escalation -> third real runtime acceptance;
3. quarantine of remaining runtime after wait blocks approved continuation;
4. SQLite restart reuses certificates and preserves full real-runtime attempt lineage.

## Gate

The dedicated workflow installs:

```text
openai-agents==0.20.0
crewai==1.15.16
langgraph==1.2.11
```

Then runs WU03 real recovery, WU01/WU02 focused regressions, Roadmap 6 three-runtime regression, full unit suite and SDK-neutral Core/control-plane boundary guard.

## Execution blocker

GitHub-hosted Actions still fails before job steps materialize. The local compatibility correction has not yet been followed by a complete functional gate run. Therefore the regression remains PREPARED and no PASS/FAIL is claimed until actual test commands execute.

---

Qualification trigger note (2026-08-26): this documentation-only change intentionally re-runs the existing Roadmap 7 recovery workflow for chassis qualification issue #197. It changes no product semantics or CI commands.
