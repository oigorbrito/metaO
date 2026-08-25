# Roadmap 6 WU06 — Closeout / Readiness

Date: 2026-08-24

## Status

```text
ROADMAP_6_FUNCTIONAL_ASSEMBLY = COMPLETE
ROADMAP_6_COMPATIBILITY_CORRECTION = APPLIED
ROADMAP_6_RUNTIME_VALIDATION = PENDING
ROADMAP_6_REMOTE_EXECUTION = BLOCKED_EXTERNAL
ROADMAP_6_MERGE_GATE = PENDING
ROADMAP_6_PRODUCTION_CLAIM = NO
```

Roadmap 6 is complete only at implementation/readiness level. It is not validated or merge-ready until executable evidence exists.

## Historical selection and active pin

WU03 selected OpenAI Agents SDK as the third runtime after comparing OpenAI Agents, Microsoft Agent Framework and Google ADK. That runtime selection is preserved.

The originally prepared exact package version was 0.21.1. The first real joint pip resolution later proved that version incompatible with CrewAI 1.15.16 in one environment:

```text
openai-agents 0.21.1 -> openai >=3,<4
crewai 1.15.16       -> openai >=2.30,<3
```

The active executable version is therefore:

```text
OpenAI Agents 0.20.0 -> openai >=2.45,<3
CrewAI 1.15.16       -> openai >=2.30,<3
LangGraph 1.2.11
shared openai range  -> >=2.45,<3
```

See `docs/OPENAI-AGENTS-COMPATIBILITY-CORRECTION.md`.

## WU03 — Third Runtime Evaluation / Selection

Historical result:

```text
SELECTED_THIRD_RUNTIME = OpenAI Agents SDK
```

Selection rationale remains valid:

- synchronous `Runner.run_sync(...)` fits the existing metaO execution contract;
- provider-neutral public `Model` boundary supports deterministic provider-free testing;
- adapter remains a thin translation layer;
- no Core change is required;
- runtime architecture is distinct from LangGraph and CrewAI.

## WU04 — OpenAI Agents Runtime Adapter

Prepared:

- `src/metao/adapters/openai_agents.py`;
- SDK-neutral duck typing via `run_sync` and `final_output`;
- deterministic evidence normalization;
- SDK-free adapter unit suite;
- real `openai-agents==0.20.0` provider-free sandbox using the SDK public `Model` boundary;
- existing Runtime Conformance Harness reused unchanged;
- dedicated workflow and framework-boundary guard.

```text
CORE_CHANGED = NO
ORCHESTRATOR_CONTRACT_CHANGED = NO
SDK_IMPORT_IN_PRODUCTION_ADAPTER = NO
SDK_IMPORT_IN_CORE = NO
```

## WU05 — Three Runtime Declarative Regression

Active exact set:

```text
OpenAI Agents 0.20.0
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
8. full unit suite preserves latest-certification-verdict authority.

No WU05 production source change is required.

## Compatibility correction scope

Comparison from the last locally attempted candidate SHA before this dependency correction shows the correction touches only workflows, release-gate harness/docs and tests. No `src/metao/**` file changed for the version correction.

The 0.20.0 provider-free test seam is `tests/integration/_openai_agents_model.py`, which is test-only and based on the SDK public `Model` interface.

## External execution blocker

GitHub-hosted Actions still fails before job steps materialize, including minimal cross-OS diagnostics. Therefore hosted failures remain external pre-execution evidence rather than functional PASS/FAIL.

## Canonical architecture

```text
Mission
  -> Strategy / Selection
  -> Policy / Budget
  -> OrchestratorContract
  -> Runtime Adapter
  -> Real Orchestrator
  -> Evidence
  -> Independent Acceptance
  -> Accept / Replan / Failover / Block
```

```text
ORCHESTRATOR_DONE != METAO_ACCEPTED
```

metaO retains authority over selection, policy, budget, approval, acceptance, failover/replan, quarantine, certification lifecycle and audit. Runtime SDKs own internal execution only.

## Third-runtime architecture test

```text
Can the entire third orchestrator, including its agents, tools, memory,
model provider and workflows, be replaced without changing metaO Core?
```

Design answer:

```text
YES
```

Executable proof:

```text
PENDING
```

## Current canonical path

The historical stacked PRs are not the merge path. PR #68 / `roadmap7/integration-candidate-v1` is the canonical cumulative candidate.

Required next order:

1. execute the corrected full local release gate on PR #68;
2. classify any failure as bootstrap, harness or functional test evidence;
3. fix concrete failures without weakening Core boundaries;
4. rerun the complete gate;
5. only after verified green evidence consider the canonical candidate merge-eligible under the agreed policy;
6. do not individually merge the historical stacked PRs.

## Final declaration

```text
ROADMAP_6_WU03 = DOCUMENTED / RUNTIME_SELECTED
ROADMAP_6_WU04 = IMPLEMENTATION_PREPARED / COMPATIBILITY_CORRECTED / NOT_EXECUTED_AFTER_FIX
ROADMAP_6_WU05 = REGRESSION_PREPARED / COMPATIBILITY_CORRECTED / NOT_EXECUTED_AFTER_FIX
ROADMAP_6_WU06 = CLOSEOUT_UPDATED

THIRD_RUNTIME = OpenAI Agents SDK
ACTIVE_OPENAI_AGENTS_PIN = 0.20.0
THREE_RUNTIME_TARGET = OpenAI Agents + CrewAI + LangGraph
CORE_MODIFICATION_REQUIRED = NO
MAIN_MODIFIED = NO
FUNCTIONAL_PASS_AFTER_FIX = NOT CLAIMED
```
