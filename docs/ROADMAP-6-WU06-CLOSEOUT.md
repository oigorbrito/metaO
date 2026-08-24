# Roadmap 6 WU06 — Closeout / Readiness

Date: 2026-08-24

## Status

```text
ROADMAP_6_FUNCTIONAL_ASSEMBLY = COMPLETE
ROADMAP_6_RUNTIME_VALIDATION = PENDING
ROADMAP_6_REMOTE_EXECUTION = BLOCKED_EXTERNAL
ROADMAP_6_MERGE_GATE = PENDING
ROADMAP_6_PRODUCTION_CLAIM = NO
```

Roadmap 6 is closed only at the implementation/readiness level. It is **not** validated, merge-ready, or production-proven because executable test evidence is still unavailable.

## Baseline preservation

Canonical pre-Roadmap-6 integration candidate:

```text
PR #56
branch: roadmap6/integration-candidate-v1
base: main
```

Roadmap 6 third-runtime work is stacked on top of that candidate. `main` remains untouched by WU03-WU06.

PR #56 remains draft/unmerged and must not be merged without real execution evidence.

## WU03 — Third Runtime Evaluation / Selection

PR #57

```text
branch: roadmap6/wu03-third-runtime-evaluation-v1
base: roadmap6/integration-candidate-v1
```

Result:

```text
SELECTED_THIRD_RUNTIME = OpenAI Agents SDK 0.21.1
```

Selection was based on current official upstream evidence across:

- OpenAI Agents SDK;
- Microsoft Agent Framework;
- Google ADK Python.

Primary deciding factors:

- first-party synchronous `Runner.run_sync(...)` fits the existing synchronous metaO contract;
- first-party provider-neutral deterministic `ScriptedModel` enables real SDK conformance without paid provider access;
- adapter can remain a thin translation layer;
- no Core change is required;
- runtime architecture adds a runner/handoff/guardrail-oriented implementation distinct from LangGraph and CrewAI.

Execution classification:

```text
DOCUMENTED = YES
EXECUTED = NO
PASS = NOT CLAIMED
```

## WU04 — OpenAI Agents Runtime Adapter

PR #58

```text
branch: roadmap6/wu04-openai-agents-runtime-adapter-v1
base: roadmap6/wu03-third-runtime-evaluation-v1
```

Prepared:

- `src/metao/adapters/openai_agents.py`;
- SDK-neutral duck typing via `run_sync` and `final_output`;
- deterministic evidence normalization;
- SDK-free adapter unit suite;
- real `openai-agents==0.21.1` sandbox using `agents.testing.ScriptedModel`;
- existing `Runtime Conformance Harness` reused unchanged;
- dedicated workflow and framework-boundary guard.

Architecture:

```text
CORE_CHANGED = NO
ORCHESTRATOR_CONTRACT_CHANGED = NO
SDK_IMPORT_IN_PRODUCTION_ADAPTER = NO
SDK_IMPORT_IN_CORE = NO
```

The existing metaO cancellation contract is preserved. WU04 does not expose an OpenAI Agents streaming result handle through Core.

## WU05 — Three Runtime Declarative Regression

PR #59

```text
branch: roadmap6/wu05-three-runtime-declarative-regression-v1
base: roadmap6/wu04-openai-agents-runtime-adapter-v1
```

Prepared one real three-runtime regression with exact pins:

```text
OpenAI Agents 0.21.1
CrewAI 1.15.16
LangGraph 1.2.11
```

Prepared scenarios:

1. one manifest actively certifies all three;
2. exact PASS reuse inside TTL without SDK reexecution;
3. expiry writes new certification generations;
4. selective OpenAI Agents certificate revocation recertifies only that runtime;
5. deterministic selection across three heterogeneous runtimes;
6. failed preferred OpenAI Agents runtime fails over to CrewAI;
7. quarantine overrides preferred routing score;
8. full existing unit suite preserves latest-certification-verdict authority.

WU05 changes only:

- one integration regression;
- one workflow;
- one document.

Direct WU04→WU05 comparison confirms no production source file changed.

## External execution blocker — reconfirmed

The blocker is still GitHub-hosted Actions failing before job steps materialize.

Observed on Roadmap 6 itself:

### WU04 workflow

```text
Roadmap 6 OpenAI Agents Runtime
conclusion = failure
steps = null
```

### WU05 workflow

```text
Roadmap 6 Three Runtime Regression
conclusion = failure
steps = null
```

Therefore:

- checkout did not execute;
- dependency installation did not execute;
- unit tests did not execute;
- integration tests did not execute;
- architecture grep did not execute.

This remains an external execution blocker, not a functional PASS or FAIL result for the prepared code.

## Canonical architectural invariants preserved

Roadmap 6 does not change the frozen architecture:

```text
Mission
  -> Strategy / Selection
  -> Policy / Budget
  -> OrchestratorContract
  -> Runtime Adapter
  -> Orchestrator real
  -> Evidence
  -> Independent Acceptance
  -> Accept / Replan / Failover / Block
```

Still authoritative:

```text
ORCHESTRATOR_DONE != METAO_ACCEPTED
```

metaO continues to own:

- runtime selection;
- policy;
- budget;
- approval;
- acceptance;
- failover;
- replanning;
- quarantine;
- certification lifecycle;
- observability/audit authority.

Runtime SDKs own only their internal execution.

## Third-runtime architecture test

The intended acceptance question remains:

```text
Can the entire third orchestrator, including its agents, tools, memory,
model provider and workflows, be replaced without changing metaO Core?
```

Roadmap 6 implementation answer:

```text
YES BY DESIGN
```

Executable proof:

```text
PENDING
```

The OpenAI Agents adapter is outside Core and the three-runtime regression uses the same generic catalog/admission/routing/failover/lifecycle infrastructure already used by the previous runtimes.

## Merge and validation order

When executable infrastructure is available, do not merge historical PRs opportunistically.

Required order:

1. execute PR #56 canonical integration candidate against its complete gate;
2. fix any concrete regressions on the canonical candidate;
3. only after #56 is green, decide whether to merge #56 or build a newer canonical candidate containing Roadmap 6;
4. execute WU04 real OpenAI Agents conformance at the exact Roadmap 6 head;
5. execute WU05 three-runtime regression at the exact Roadmap 6 head;
6. run full unit regression and Block O O1-O5;
7. verify SDK-neutral boundary and no Core diff;
8. merge only green dependency-ordered work or a single newer canonical consolidation PR;
9. supersede historical stacked PRs only after the canonical merged state contains their intended artifacts.

Do not merge PRs #57-#60 into an unvalidated base merely to reduce the stack.

## Failure handling once execution works

If a real test fails:

```text
FAIL = functional evidence
```

Then:

1. identify the exact failing invariant;
2. prefer adapter/plugin correction;
3. do not alter Core merely to accommodate OpenAI Agents;
4. if the framework cannot satisfy the existing contract without invasive changes, reconsider the runtime selection rather than weakening the architecture;
5. rerun focused test, full regression, real sandbox, and canonical gate;
6. only then update PASS status.

## Roadmap 6 final declaration

```text
ROADMAP_6_WU03 = DOCUMENTED / SELECTED
ROADMAP_6_WU04 = IMPLEMENTATION_PREPARED / NOT_EXECUTED
ROADMAP_6_WU05 = REGRESSION_PREPARED / NOT_EXECUTED
ROADMAP_6_WU06 = CLOSEOUT_DOCUMENTED

THIRD_RUNTIME = OpenAI Agents SDK 0.21.1
THREE_RUNTIME_TARGET = OpenAI Agents + CrewAI + LangGraph
CORE_MODIFICATION_REQUIRED = NO
MAIN_MODIFIED = NO
PR_56_MERGED = NO
PASS_CLAIMED_WITHOUT_EXECUTION = NO
```
